import os
import time
import requests
import json
from typing import Optional, Dict, Any
from github import Github, Auth
from git import Repo
import tempfile
import shutil

class GitHubDeviceFlowAuth:
    """
    Gestore per l'autenticazione GitHub usando Device Flow
    Progettato per estensioni GitHub Copilot
    """

    def __init__(self):
        self.github_client: Optional[Github] = None
        self.authenticated = False
        self.access_token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None
        self.current_repo_info: Optional[Dict[str, str]] = None
        self.local_repo_path: Optional[str] = None

        # Configurazione per GitHub App/OAuth App
        self.client_id = os.getenv("GITHUB_CLIENT_ID")

        # URL per GitHub Device Flow
        self.device_code_url = "https://github.com/login/device/code"
        self.access_token_url = "https://github.com/login/oauth/access_token"
        self.api_base_url = "https://api.github.com"

    def start_device_flow(self) -> Dict[str, Any]:
        """
        Avvia il flusso di autenticazione device flow

        Returns:
            Dict contenente le informazioni per l'autenticazione
        """
        if not self.client_id:
            return {
                "success": False,
                "error": "GitHub Client ID non configurato. Imposta GITHUB_CLIENT_ID"
            }

        try:
            # Step 1: Richiedi device code
            device_response = requests.post(
                self.device_code_url,
                data={
                    "client_id": self.client_id,
                    "scope": "repo user"  # Permessi necessari
                },
                headers={
                    "Accept": "application/json"
                }
            )

            if device_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Errore nella richiesta device code: {device_response.status_code}"
                }

            device_data = device_response.json()

            return {
                "success": True,
                "device_code": device_data["device_code"],
                "user_code": device_data["user_code"],
                "verification_uri": device_data["verification_uri"],
                "expires_in": device_data["expires_in"],
                "interval": device_data["interval"],
                "message": f"Vai su {device_data['verification_uri']} e inserisci il codice: {device_data['user_code']}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Errore nel device flow: {str(e)}"
            }

    def poll_for_token(self, device_code: str, interval: int = 5, timeout: int = 600) -> Dict[str, Any]:
        """
        Polling per ottenere l'access token dopo l'autorizzazione utente

        Args:
            device_code: Device code ottenuto dal device flow
            interval: Intervallo in secondi tra le richieste
            timeout: Timeout massimo in secondi

        Returns:
            Dict con risultato dell'autenticazione
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = requests.post(
                    self.access_token_url,
                    data={
                        "client_id": self.client_id,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
                    },
                    headers={
                        "Accept": "application/json"
                    }
                )

                if response.status_code == 200:
                    token_data = response.json()

                    if "access_token" in token_data:
                        self.access_token = token_data["access_token"]

                        # Inizializza il client GitHub
                        auth = Auth.Token(self.access_token)
                        self.github_client = Github(auth=auth)

                        # Ottieni informazioni utente
                        user_result = self._get_user_info()
                        if user_result["success"]:
                            self.authenticated = True
                            return {
                                "success": True,
                                "message": "Autenticazione completata",
                                "user": self.user_info
                            }
                        else:
                            return user_result

                    elif token_data.get("error") == "authorization_pending":
                        # L'utente non ha ancora autorizzato, continua il polling
                        time.sleep(interval)
                        continue

                    elif token_data.get("error") == "slow_down":
                        # GitHub chiede di rallentare il polling
                        interval += 5
                        time.sleep(interval)
                        continue

                    elif token_data.get("error") == "expired_token":
                        return {
                            "success": False,
                            "error": "Device code scaduto. Riavvia il processo di autenticazione"
                        }

                    elif token_data.get("error") == "access_denied":
                        return {
                            "success": False,
                            "error": "Accesso negato dall'utente"
                        }

                    else:
                        return {
                            "success": False,
                            "error": f"Errore sconosciuto: {token_data.get('error', 'Unknown')}"
                        }

                else:
                    time.sleep(interval)

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Errore durante il polling: {str(e)}"
                }

        return {
            "success": False,
            "error": "Timeout nell'attesa dell'autorizzazione utente"
        }

    def _get_user_info(self) -> Dict[str, Any]:
        """Ottiene le informazioni dell'utente autenticato"""
        try:
            user = self.github_client.get_user()
            self.user_info = {
                "login": user.login,
                "name": user.name or user.login,
                "email": user.email,
                "id": user.id
            }

            # Se l'email non è pubblica, prova a ottenerla dalle email private
            if not self.user_info["email"]:
                try:
                    emails = user.get_emails()
                    primary_email = next((email for email in emails if email.primary), None)
                    if primary_email:
                        self.user_info["email"] = primary_email.email
                except:
                    pass

            return {
                "success": True,
                "user": self.user_info
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Errore nel recupero informazioni utente: {str(e)}"
            }

    def get_repository_from_context(self, workspace_path: str = None) -> Dict[str, Any]:
        """
        Rileva il repository dal contesto del workspace GitHub Copilot

        Args:
            workspace_path: Path del workspace (usa directory corrente se None)

        Returns:
            Dict con informazioni del repository
        """
        if workspace_path is None:
            workspace_path = os.getcwd()

        try:
            # Cerca un repository git nella directory corrente o nelle parent
            current_path = os.path.abspath(workspace_path)

            while current_path != os.path.dirname(current_path):  # Fino alla root
                git_path = os.path.join(current_path, '.git')

                if os.path.exists(git_path):
                    # Trovato un repository git
                    try:
                        repo = Repo(current_path)

                        # Ottieni il remote origin
                        if 'origin' in repo.remotes:
                            origin_url = repo.remotes.origin.url

                            # Parse dell'URL GitHub
                            repo_info = self._parse_github_url(origin_url)
                            if repo_info:
                                self.current_repo_info = repo_info
                                return {
                                    "success": True,
                                    "repository": repo_info,
                                    "local_path": current_path
                                }

                    except Exception as e:
                        pass  # Continua la ricerca nelle directory parent

                current_path = os.path.dirname(current_path)

            return {
                "success": False,
                "error": "Nessun repository GitHub trovato nel workspace corrente"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Errore nella rilevazione del repository: {str(e)}"
            }

    def _parse_github_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Parse di un URL GitHub per estrarre owner e repo name

        Args:
            url: URL del repository (HTTPS o SSH)

        Returns:
            Dict con owner e repo name, None se non è un URL GitHub valido
        """
        try:
            # Normalizza l'URL
            if url.startswith('git@github.com:'):
                # SSH format: git@github.com:owner/repo.git
                url = url.replace('git@github.com:', 'https://github.com/')

            if url.endswith('.git'):
                url = url[:-4]

            if 'github.com' in url:
                # Extract owner/repo from URL
                parts = url.split('/')
                if len(parts) >= 2:
                    repo_name = parts[-1]
                    owner = parts[-2]

                    return {
                        "owner": owner,
                        "repo": repo_name,
                        "full_name": f"{owner}/{repo_name}",
                        "url": f"https://github.com/{owner}/{repo_name}"
                    }

            return None

        except Exception:
            return None

    def check_repository_permissions(self) -> Dict[str, Any]:
        """Verifica i permessi sul repository corrente"""
        if not self.authenticated or not self.current_repo_info:
            return {
                "success": False,
                "error": "Non autenticato o repository non rilevato"
            }

        try:
            repo = self.github_client.get_repo(self.current_repo_info["full_name"])

            # Verifica permessi di scrittura
            permissions = repo.permissions
            can_write = permissions.push if hasattr(permissions, 'push') else False

            return {
                "success": True,
                "permissions": {
                    "read": True,  # Se riusciamo a ottenere il repo, abbiamo accesso in lettura
                    "write": can_write,
                    "admin": permissions.admin if hasattr(permissions, 'admin') else False
                },
                "repository": {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "private": repo.private
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Errore nella verifica permessi: {str(e)}"
            }

    def setup_local_clone(self, workspace_path: str) -> str:
        """
        Configura un clone locale temporaneo del repository

        Args:
            workspace_path: Path del workspace di origine

        Returns:
            Path del repository clonato
        """
        if not self.authenticated or not self.current_repo_info:
            raise Exception("Non autenticato o repository non rilevato")

        # Crea directory temporanea per il clone
        temp_dir = tempfile.mkdtemp(prefix="github_copilot_")
        clone_path = os.path.join(temp_dir, self.current_repo_info["repo"])

        try:
            # Se esiste già un clone locale, rimuovilo
            if self.local_repo_path and os.path.exists(self.local_repo_path):
                shutil.rmtree(os.path.dirname(self.local_repo_path), ignore_errors=True)

            # Clona il repository
            repo_url = f"https://x-access-token:{self.access_token}@github.com/{self.current_repo_info['full_name']}.git"
            repo = Repo.clone_from(repo_url, clone_path)

            # Configura git con le informazioni dell'utente autenticato
            self._configure_git_user(repo)

            self.local_repo_path = clone_path
            return clone_path

        except Exception as e:
            # Cleanup in caso di errore
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Errore nel setup del clone locale: {str(e)}")

    def _configure_git_user(self, repo: Repo):
        """
        Configura le informazioni utente Git per il repository locale

        Args:
            repo: Repository Git da configurare
        """
        if not self.user_info:
            return

        try:
            # Configura nome e email per il repository locale
            config_writer = repo.config_writer()

            # Usa il nome e email dell'utente GitHub autenticato
            name = self.user_info.get("name", self.user_info.get("login"))
            email = self.user_info.get("email")

            if name:
                config_writer.set_value("user", "name", name)

            if email:
                config_writer.set_value("user", "email", email)
            else:
                # Fallback email se non disponibile
                config_writer.set_value("user", "email", f"{self.user_info['login']}@users.noreply.github.com")

            config_writer.release()

        except Exception as e:
            print(f"Warning: Impossibile configurare git user: {str(e)}")

    def is_authenticated(self) -> bool:
        """Verifica se l'utente è autenticato"""
        return self.authenticated and self.access_token is not None

    def get_github_client(self) -> Github:
        """Restituisce il client GitHub autenticato"""
        return self.github_client

    def get_current_repo_info(self) -> Optional[Dict[str, str]]:
        """Restituisce le informazioni del repository corrente"""
        return self.current_repo_info

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Restituisce le informazioni dell'utente autenticato"""
        return self.user_info

    def cleanup_local_clone(self):
        """Pulisce il clone locale temporaneo"""
        if self.local_repo_path and os.path.exists(self.local_repo_path):
            try:
                shutil.rmtree(os.path.dirname(self.local_repo_path), ignore_errors=True)
                self.local_repo_path = None
            except Exception as e:
                print(f"Warning: Impossibile pulire il clone locale: {str(e)}")
