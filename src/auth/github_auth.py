import os
import tempfile
from typing import Optional, Dict, Any
from github import Github, Auth
from git import Repo
import requests
from urllib.parse import urlparse

class GitHubAuthManager:
    """Gestore per l'autenticazione OAuth con GitHub"""

    def __init__(self):
        self.github_client: Optional[Github] = None
        self.authenticated = False
        self.current_repo_info: Optional[Dict[str, str]] = None
        self.local_repo_path: Optional[str] = None

    def authenticate(self, access_token: str) -> Dict[str, Any]:
        """
        Autentica l'utente con GitHub usando un token di accesso

        Args:
            access_token: Token di accesso GitHub

        Returns:
            Dict con risultato dell'autenticazione
        """
        try:
            auth = Auth.Token(access_token)
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

    def setup_local_clone(self) -> str:
        """
        Configura un clone locale temporaneo del repository

        Returns:
            Path del repository locale
        """
        if not self.authenticated or not self.current_repo_info:
            raise Exception("Autenticazione o repository non configurati")

        if self.local_repo_path and os.path.exists(self.local_repo_path):
            return self.local_repo_path

        # Crea una directory temporanea
        temp_dir = tempfile.mkdtemp(prefix="github_copilot_")

        # URL del repository per il clone
        repo_url = f"https://github.com/{self.current_repo_info['full_name']}.git"

        try:
            # Clona il repository
            Repo.clone_from(repo_url, temp_dir)
            self.local_repo_path = temp_dir
            return temp_dir
        except Exception as e:
            # Pulisci in caso di errore
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise Exception(f"Errore durante il clone: {str(e)}")

    def cleanup_local_clone(self):
        """Pulisce il clone locale temporaneo"""
        if self.local_repo_path and os.path.exists(self.local_repo_path):
            import shutil
            shutil.rmtree(self.local_repo_path)
            self.local_repo_path = None
