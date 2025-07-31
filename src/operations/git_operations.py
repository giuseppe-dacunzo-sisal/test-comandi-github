import os
from typing import Dict, Any, List
from git import Repo, GitCommandError
from github import Github

class GitOperationsManager:
    """Gestore per le operazioni Git"""

    def __init__(self, local_repo_path: str, github_client: Github, repo_info: Dict[str, str]):
        self.local_repo_path = local_repo_path
        self.github_client = github_client
        self.repo_info = repo_info
        self.git_repo = Repo(local_repo_path)

    def pull(self) -> Dict[str, Any]:
        """
        Esegue pull dal repository remoto

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            origin = self.git_repo.remotes.origin
            pull_info = origin.pull()

            return {
                "success": True,
                "message": "Pull completata con successo",
                "changes": len(pull_info)
            }

        except GitCommandError as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore durante la pull: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore generico durante la pull: {str(e)}"
            }

    def commit(self, message: str) -> Dict[str, Any]:
        """
        Esegue commit delle modifiche

        Args:
            message: Messaggio di commit

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            # Aggiungi tutti i file modificati
            self.git_repo.git.add(A=True)

            # Verifica se ci sono modifiche da committare
            if not self.git_repo.is_dirty() and not self.git_repo.untracked_files:
                return {
                    "success": True,
                    "message": "Nessuna modifica da committare",
                    "commit_hash": None
                }

            # Esegui il commit
            commit = self.git_repo.index.commit(message)

            return {
                "success": True,
                "message": f"Commit creato: {commit.hexsha[:8]}",
                "commit_hash": commit.hexsha,
                "commit_message": message
            }

        except GitCommandError as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore durante il commit: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore generico durante il commit: {str(e)}"
            }

    def push(self, branch: str = None) -> Dict[str, Any]:
        """
        Esegue push verso il repository remoto

        Args:
            branch: Branch da pushare (default: current branch)

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            origin = self.git_repo.remotes.origin

            if branch:
                push_info = origin.push(f"refs/heads/{branch}")
            else:
                push_info = origin.push()

            return {
                "success": True,
                "message": "Push completata con successo",
                "pushed_refs": len(push_info)
            }

        except GitCommandError as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore durante la push: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore generico durante la push: {str(e)}"
            }

    def create_branch(self, branch_name: str) -> Dict[str, Any]:
        """
        Crea un nuovo branch

        Args:
            branch_name: Nome del nuovo branch

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            # Verifica se il branch esiste già
            if branch_name in [ref.name.split('/')[-1] for ref in self.git_repo.refs]:
                return {
                    "success": False,
                    "error": "Branch già esistente",
                    "message": f"Il branch '{branch_name}' esiste già"
                }

            # Crea il nuovo branch
            new_branch = self.git_repo.create_head(branch_name)

            return {
                "success": True,
                "message": f"Branch '{branch_name}' creato con successo",
                "branch_name": branch_name
            }

        except GitCommandError as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore durante la creazione del branch: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore generico durante la creazione del branch: {str(e)}"
            }

    def switch_branch(self, branch_name: str) -> Dict[str, Any]:
        """
        Cambia branch corrente

        Args:
            branch_name: Nome del branch su cui spostarsi

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            # Verifica se il branch esiste
            if branch_name not in [ref.name.split('/')[-1] for ref in self.git_repo.refs]:
                # Prova a vedere se esiste nel remote
                try:
                    origin = self.git_repo.remotes.origin
                    origin.fetch()

                    remote_branch = f"origin/{branch_name}"
                    if remote_branch in [ref.name for ref in self.git_repo.refs]:
                        # Crea un branch locale che traccia quello remoto
                        new_branch = self.git_repo.create_head(branch_name, f"origin/{branch_name}")
                        new_branch.set_tracking_branch(origin.refs[branch_name])
                    else:
                        return {
                            "success": False,
                            "error": "Branch non trovato",
                            "message": f"Il branch '{branch_name}' non esiste né localmente né nel remote"
                        }
                except:
                    return {
                        "success": False,
                        "error": "Branch non trovato",
                        "message": f"Il branch '{branch_name}' non esiste"
                    }

            # Cambia branch
            self.git_repo.heads[branch_name].checkout()

            return {
                "success": True,
                "message": f"Spostato sul branch '{branch_name}'",
                "current_branch": branch_name
            }

        except GitCommandError as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore durante il cambio di branch: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore generico durante il cambio di branch: {str(e)}"
            }

    def get_current_branch(self) -> str:
        """Ottieni il nome del branch corrente"""
        try:
            return self.git_repo.active_branch.name
        except:
            return "HEAD detached"

    def get_status(self) -> Dict[str, Any]:
        """
        Ottieni lo status del repository

        Returns:
            Dict con informazioni sullo status
        """
        try:
            return {
                "success": True,
                "current_branch": self.get_current_branch(),
                "is_dirty": self.git_repo.is_dirty(),
                "untracked_files": self.git_repo.untracked_files,
                "modified_files": [item.a_path for item in self.git_repo.index.diff(None)],
                "staged_files": [item.a_path for item in self.git_repo.index.diff("HEAD")]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nell'ottenimento dello status: {str(e)}"
            }
