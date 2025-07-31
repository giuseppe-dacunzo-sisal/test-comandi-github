import os
import tempfile
import secrets
import webbrowser
from typing import Optional, Dict, Any
from github import Github, Auth
from git import Repo
import requests
from urllib.parse import urlparse, urlencode
from flask import Flask, request, redirect
import threading
import time

class GitHubAuthManager:
    """Gestore per l'autenticazione OAuth con GitHub per estensioni Copilot"""

    def __init__(self):
        self.github_client: Optional[Github] = None
        self.authenticated = False
        self.current_repo_info: Optional[Dict[str, str]] = None
        self.local_repo_path: Optional[str] = None
        self.access_token: Optional[str] = None
        self.oauth_state = None
        self.auth_app = None

        # Configurazione OAuth (questi dovrebbero essere nelle variabili d'ambiente)
        self.client_id = os.getenv("GITHUB_CLIENT_ID")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        self.redirect_uri = "http://localhost:8080/callback"

    def start_oauth_flow(self) -> Dict[str, Any]:
        """
        Avvia il flusso OAuth per l'autenticazione GitHub
        Questo è il metodo che dovrebbe essere chiamato dall'estensione Copilot
        """
        if not self.client_id or not self.client_secret:
            return {
                "success": False,
                "error": "GitHub OAuth app non configurata. Imposta GITHUB_CLIENT_ID e GITHUB_CLIENT_SECRET"
            }

        try:
            # Genera uno stato casuale per sicurezza
            self.oauth_state = secrets.token_urlsafe(32)

            # Avvia il server Flask per gestire il callback
            self._start_callback_server()

            # Costruisce l'URL di autorizzazione GitHub
            auth_params = {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": "repo,user,workflow",  # Permessi necessari per l'estensione
                "state": self.oauth_state
            }

            auth_url = f"https://github.com/login/oauth/authorize?{urlencode(auth_params)}"

            # Apre il browser per l'autorizzazione
            webbrowser.open(auth_url)

            return {
                "success": True,
                "message": "Flusso OAuth avviato. Autorizza l'accesso nel browser.",
                "auth_url": auth_url
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nell'avvio del flusso OAuth: {str(e)}"
            }

    def _start_callback_server(self):
        """Avvia un server Flask temporaneo per gestire il callback OAuth"""
        self.auth_app = Flask(__name__)

        # Disabilita i log di Flask per evitare spam
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        @self.auth_app.route('/callback')
        def oauth_callback():
            code = request.args.get('code')
            state = request.args.get('state')

            if not code:
                return "Errore: Codice di autorizzazione non ricevuto", 400

            if state != self.oauth_state:
                return "Errore: Stato OAuth non valido", 400

            # Scambia il codice con un token di accesso
            token_result = self._exchange_code_for_token(code)

            if token_result["success"]:
                return """
                <html>
                    <body>
                        <h2>✅ Autenticazione completata con successo!</h2>
                        <p>Puoi chiudere questa finestra e tornare a GitHub Copilot.</p>
                        <script>window.close();</script>
                    </body>
                </html>
                """
            else:
                return f"Errore durante l'autenticazione: {token_result['error']}", 500

        @self.auth_app.route('/')
        def home():
            return "GitHub Copilot OAuth Server - In attesa del callback..."

        # Avvia il server in un thread separato
        def run_server():
            try:
                print("🚀 Avvio server OAuth su http://localhost:8080")
                self.auth_app.run(host='localhost', port=8080, debug=False, use_reloader=False)
            except Exception as e:
                print(f"❌ Errore nell'avvio del server Flask: {e}")

        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # Aspetta un momento che il server si avvii
        import time
        time.sleep(1)

    def _exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Scambia il codice di autorizzazione con un token di accesso"""
        try:
            token_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri
            }

            headers = {"Accept": "application/json"}

            response = requests.post(
                "https://github.com/login/oauth/access_token",
                data=token_data,
                headers=headers
            )

            if response.status_code == 200:
                token_info = response.json()
                self.access_token = token_info.get("access_token")

                if self.access_token:
                    # Completa l'autenticazione con il token
                    auth_result = self._complete_authentication()
                    # Salva il token in modo sicuro
                    self._save_token()
                    return auth_result
                else:
                    return {
                        "success": False,
                        "error": "Token di accesso non ricevuto"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Errore nella richiesta del token: {response.status_code}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _complete_authentication(self) -> Dict[str, Any]:
        """Completa il processo di autenticazione con il token ottenuto"""
        try:
            auth = Auth.Token(self.access_token)
            self.github_client = Github(auth=auth)

            # Verifica l'autenticazione
            user = self.github_client.get_user()
            self.authenticated = True

            return {
                "success": True,
                "user": user.login,
                "message": f"Autenticato come: {user.login}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore durante l'autenticazione: {str(e)}"
            }

    def is_authenticated(self) -> bool:
        """Verifica se l'utente è già autenticato"""
        return self.authenticated and self.github_client is not None

    def detect_current_repository(self, workspace_path: str) -> Dict[str, Any]:
        """
        Rileva automaticamente il repository corrente dal workspace

        Args:
            workspace_path: Path del workspace corrente

        Returns:
            Dict con informazioni del repository
        """
        try:
            # Cerca un repository Git nel workspace
            repo = Repo(workspace_path)

            # Ottieni l'URL del remote origin
            if not repo.remotes:
                raise Exception("Nessun remote configurato")

            origin_url = repo.remotes.origin.url

            # Estrai owner e repo dall'URL
            parsed_url = urlparse(origin_url)
            if 'github.com' not in parsed_url.netloc:
                raise Exception("Non è un repository GitHub")

            # Rimuovi .git dalla fine se presente
            path_parts = parsed_url.path.strip('/').replace('.git', '').split('/')
            if len(path_parts) < 2:
                raise Exception("URL del repository non valido")

            owner, repo_name = path_parts[0], path_parts[1]

            self.current_repo_info = {
                "owner": owner,
                "repo": repo_name,
                "full_name": f"{owner}/{repo_name}"
            }

            return {
                "success": True,
                "repository": self.current_repo_info,
                "message": f"Repository rilevato: {self.current_repo_info['full_name']}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nel rilevamento del repository: {str(e)}"
            }

    def check_repository_permissions(self) -> Dict[str, Any]:
        """
        Verifica i permessi sul repository corrente

        Returns:
            Dict con informazioni sui permessi
        """
        if not self.authenticated or not self.current_repo_info:
            return {
                "success": False,
                "error": "Autenticazione o repository non configurati"
            }

        try:
            repo = self.github_client.get_repo(self.current_repo_info["full_name"])

            permissions = {
                "can_read": True,  # Se riusciamo a ottenere il repo, possiamo leggerlo
                "can_write": repo.permissions.push,
                "can_admin": repo.permissions.admin
            }

            return {
                "success": True,
                "permissions": permissions,
                "message": "Permessi verificati con successo"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nel controllo permessi: {str(e)}"
            }

    def get_github_client(self) -> Github:
        """Ottieni l'istanza GitHub autenticata"""
        if not self.authenticated:
            raise Exception("Non autenticato")
        return self.github_client

    def get_current_repo_info(self) -> Optional[Dict[str, str]]:
        """Ottieni le informazioni del repository corrente"""
        return self.current_repo_info

    def setup_local_clone(self, workspace_path: str = None) -> str:
        """
        Configura un clone locale temporaneo del repository nella directory del progetto

        Args:
            workspace_path: Path del workspace corrente (opzionale)

        Returns:
            Path del repository locale clonato
        """
        if not self.authenticated or not self.current_repo_info:
            raise Exception("Autenticazione o repository non configurati")

        # Se abbiamo già un path locale configurato, usalo
        if self.local_repo_path and os.path.exists(self.local_repo_path):
            return self.local_repo_path

        # Determina la directory base del progetto
        if workspace_path:
            project_base = workspace_path
        else:
            # Usa la directory corrente come fallback
            project_base = os.getcwd()

        # Crea una directory "temp_repos" nel progetto principale
        temp_repos_dir = os.path.join(project_base, "temp_repos")
        if not os.path.exists(temp_repos_dir):
            os.makedirs(temp_repos_dir)

        # Nome unico per questo clone basato sul repository
        repo_name = self.current_repo_info['repo']
        import time
        timestamp = int(time.time())
        clone_dir_name = f"{repo_name}_{timestamp}"

        # Path completo del clone temporaneo
        temp_clone_path = os.path.join(temp_repos_dir, clone_dir_name)

        # URL del repository per il clone
        repo_url = f"https://github.com/{self.current_repo_info['full_name']}.git"

        try:
            print(f"📥 Clono repository in: {temp_clone_path}")
            # Clona il repository
            Repo.clone_from(repo_url, temp_clone_path)
            self.local_repo_path = temp_clone_path
            return temp_clone_path
        except Exception as e:
            # Pulisci in caso di errore
            import shutil
            if os.path.exists(temp_clone_path):
                shutil.rmtree(temp_clone_path)
            raise Exception(f"Errore durante il clone: {str(e)}")

    def cleanup_local_clone(self):
        """Pulisce il clone locale temporaneo"""
        if self.local_repo_path and os.path.exists(self.local_repo_path):
            import shutil
            shutil.rmtree(self.local_repo_path)
            self.local_repo_path = None
