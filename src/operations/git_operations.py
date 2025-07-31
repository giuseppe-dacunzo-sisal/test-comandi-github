import os
from typing import Dict, Any, List
from git import Repo, GitCommandError
from github import Github

class GitOperationsManager:
    """Gestore per le operazioni Git"""

    def __init__(self, local_repo_path: str, github_client: Github, repo_info: Dict[str, str], access_token: str = None):
        self.local_repo_path = local_repo_path
        self.github_client = github_client
        self.repo_info = repo_info
        self.access_token = access_token  # Token OAuth passato direttamente
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
        Esegue commit delle modifiche con l'identità corretta del repository

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

            # Configura l'identità Git per questo repository
            try:
                # Leggi la configurazione locale del repository
                config_reader = self.git_repo.config_reader()

                # Prova a ottenere user.name e user.email dalla configurazione locale
                try:
                    local_name = config_reader.get_value("user", "name")
                    local_email = config_reader.get_value("user", "email")
                    print(f"📝 Usando identità locale: {local_name} <{local_email}>")

                    # Configura l'identità per questo commit
                    with self.git_repo.git.custom_environment(
                        GIT_AUTHOR_NAME=local_name,
                        GIT_AUTHOR_EMAIL=local_email,
                        GIT_COMMITTER_NAME=local_name,
                        GIT_COMMITTER_EMAIL=local_email
                    ):
                        # Esegui il commit con l'identità configurata
                        commit = self.git_repo.index.commit(message)

                except Exception:
                    # Se non c'è configurazione locale, usa quella globale con warning
                    print("⚠️ Nessuna configurazione utente locale trovata, usando configurazione globale")
                    commit = self.git_repo.index.commit(message)

            except Exception as config_error:
                print(f"⚠️ Errore nella lettura configurazione: {config_error}")
                # Fallback: commit normale
                commit = self.git_repo.index.commit(message)

            return {
                "success": True,
                "message": f"Commit creato: {commit.hexsha[:8]}",
                "commit_hash": commit.hexsha,
                "commit_message": message,
                "author": f"{commit.author.name} <{commit.author.email}>"
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
        Esegue push verso il repository remoto con gestione automatica dell'upstream

        Args:
            branch: Branch da pushare (default: current branch)

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            origin = self.git_repo.remotes.origin

            # Determina il branch corrente se non specificato
            if not branch:
                current_branch = self.git_repo.active_branch
                branch_name = current_branch.name
            else:
                branch_name = branch
                current_branch = self.git_repo.heads[branch_name]

            # Configura le credenziali Git usando il token OAuth
            try:
                # Ottieni il token dall'oggetto GitHub
                access_token = self.access_token
                if access_token:
                    # Configura Git per usare il token come username con password vuota
                    with self.git_repo.git.custom_environment(
                        GIT_USERNAME=access_token,
                        GIT_PASSWORD='',
                        GIT_ASKPASS='echo',
                        GIT_TERMINAL_PROMPT='0'
                    ):
                        # Configura temporaneamente le credenziali
                        original_url = origin.url

                        if original_url.startswith('https://github.com/'):
                            # Modifica l'URL per includere il token
                            authenticated_url = original_url.replace(
                                'https://github.com/',
                                f'https://{access_token}:x-oauth-basic@github.com/'
                            )

                            # Aggiorna l'URL del remote temporaneamente
                            origin.set_url(authenticated_url)

                            try:
                                # Controlla se il branch ha già un upstream configurato
                                tracking_branch = current_branch.tracking_branch()

                                if tracking_branch is None:
                                    # Il branch non ha upstream - prima push, imposta upstream
                                    print(f"🔗 Primo push del branch '{branch_name}' con autenticazione OAuth...")
                                    push_info = origin.push(f"refs/heads/{branch_name}:refs/heads/{branch_name}", set_upstream=True)

                                    result = {
                                        "success": True,
                                        "message": f"Branch '{branch_name}' pushato e upstream configurato con successo",
                                        "branch": branch_name,
                                        "upstream_set": True,
                                        "pushed_refs": len(push_info)
                                    }
                                else:
                                    # Il branch ha già upstream - push normale
                                    print(f"📤 Push del branch '{branch_name}' con autenticazione OAuth...")
                                    push_info = origin.push()

                                    result = {
                                        "success": True,
                                        "message": f"Push del branch '{branch_name}' completata con successo",
                                        "branch": branch_name,
                                        "upstream_set": False,
                                        "pushed_refs": len(push_info)
                                    }
                            finally:
                                # Ripristina sempre l'URL originale
                                origin.set_url(original_url)

                        return result
                else:
                    return {
                        "success": False,
                        "error": "Token OAuth non disponibile",
                        "message": "Impossibile ottenere il token OAuth per l'autenticazione"
                    }

            except Exception as auth_error:
                return {
                    "success": False,
                    "error": str(auth_error),
                    "message": f"Errore nella configurazione dell'autenticazione OAuth: {str(auth_error)}"
                }

        except GitCommandError as e:
            # Gestione specifica per errori di upstream
            if "has no upstream branch" in str(e):
                try:
                    # Retry con set_upstream se il primo tentativo fallisce
                    print(f"🔄 Retry push con configurazione upstream per '{branch_name}'...")
                    push_info = origin.push(f"refs/heads/{branch_name}:refs/heads/{branch_name}", set_upstream=True)

                    return {
                        "success": True,
                        "message": f"Branch '{branch_name}' pushato con upstream configurato (retry)",
                        "branch": branch_name,
                        "upstream_set": True,
                        "pushed_refs": len(push_info)
                    }
                except Exception as retry_error:
                    return {
                        "success": False,
                        "error": str(retry_error),
                        "message": f"Errore durante il retry push con upstream: {str(retry_error)}"
                    }
            else:
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

            # Fai automaticamente il checkout del nuovo branch
            new_branch.checkout()

            return {
                "success": True,
                "message": f"Branch '{branch_name}' creato e attivato con successo",
                "branch_name": branch_name,
                "current_branch": branch_name
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
