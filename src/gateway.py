import base64
import os
import tempfile
from typing import List, Dict, Any
from src.types.command_types import GitHubCommand, CommandType, SearchType, ModifyType
from src.auth.github_auth import GitHubAuthManager
from src.operations.file_operations import FileOperationsManager
from src.operations.git_operations import GitOperationsManager

class GitHubGateway:
    """Gateway principale per l'estensione GitHub Copilot con OAuth automatico"""

    def __init__(self):
        self.auth_manager = GitHubAuthManager()
        self.file_manager = None
        self.git_manager = None
        self.is_initialized = False

    def _ensure_authenticated(self) -> Dict[str, Any]:
        """
        Assicura che l'utente sia autenticato, avviando OAuth se necessario

        Returns:
            Dict con risultato dell'autenticazione
        """
        if self.auth_manager.is_authenticated():
            return {"success": True, "message": "Già autenticato"}

        # Avvia il flusso OAuth automatico
        oauth_result = self.auth_manager.start_oauth_flow()
        if not oauth_result["success"]:
            return oauth_result

        # Attende che l'utente completi l'autorizzazione
        print("⏳ In attesa dell'autorizzazione utente...")
        import time
        max_wait = 120  # 2 minuti di timeout
        waited = 0

        while not self.auth_manager.is_authenticated() and waited < max_wait:
            time.sleep(1)
            waited += 1

        if self.auth_manager.is_authenticated():
            return {"success": True, "message": "Autenticazione OAuth completata"}
        else:
            return {"success": False, "error": "Timeout nell'autenticazione OAuth"}

    def _initialize_workspace(self, workspace_path: str = None) -> Dict[str, Any]:
        """
        Inizializza il workspace e rileva il repository

        Args:
            workspace_path: Path del workspace (usa la directory corrente se None)

        Returns:
            Dict con risultato dell'inizializzazione
        """
        if workspace_path is None:
            workspace_path = os.getcwd()

        # Rileva il repository corrente
        repo_result = self.auth_manager.detect_current_repository(workspace_path)
        if not repo_result["success"]:
            return repo_result

        # Verifica i permessi
        perm_result = self.auth_manager.check_repository_permissions()
        if not perm_result["success"]:
            return perm_result

        # Configura il clone locale
        try:
            local_path = self.auth_manager.setup_local_clone(workspace_path)

            # Inizializza i manager
            self.file_manager = FileOperationsManager(local_path)
            self.git_manager = GitOperationsManager(
                local_repo_path=local_path,
                github_client=self.auth_manager.get_github_client(),
                repo_info=self.auth_manager.get_current_repo_info(),
                access_token=self.auth_manager.access_token  # Passa il token direttamente
            )

            self.is_initialized = True

            return {
                "success": True,
                "message": f"Workspace inizializzato per {repo_result['repository']['full_name']}",
                "repository": repo_result['repository'],
                "local_path": local_path
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nell'inizializzazione del workspace: {str(e)}"
            }

    def process_commands(self, commands: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """
        Processa una lista di comandi con autenticazione automatica

        Args:
            commands: Lista di comandi da processare

        Returns:
            Dict con risultati indicizzati per step
        """
        results = {}

        try:
            # Step 1: Assicura autenticazione automatica
            auth_result = self._ensure_authenticated()
            if not auth_result["success"]:
                return {0: auth_result}

            # Step 2: Inizializza workspace
            if not self.is_initialized:
                init_result = self._initialize_workspace()
                if not init_result["success"]:
                    return {0: init_result}

            # Step 3: Processa ogni comando
            for command_data in commands:
                step = command_data.get("step", 0)

                try:
                    # Converte in oggetto comando tipizzato
                    command = GitHubCommand.from_dict(command_data)

                    # Esegue il comando
                    result = self._execute_command(command)
                    results[step] = result

                    # Se un comando fallisce, ferma l'esecuzione
                    if not result.get("success", False):
                        break

                except Exception as e:
                    results[step] = {
                        "success": False,
                        "error": str(e),
                        "message": f"Errore nel comando step {step}: {str(e)}"
                    }
                    break

            return results

        except Exception as e:
            return {
                0: {
                    "success": False,
                    "error": str(e),
                    "message": f"Errore generale nel processamento: {str(e)}"
                }
            }

    def _execute_command(self, command: GitHubCommand) -> Dict[str, Any]:
        """
        Esegue un singolo comando

        Args:
            command: Comando da eseguire

        Returns:
            Dict con risultato dell'esecuzione
        """
        try:
            if command.command == CommandType.CREATE_FILE:
                return self._create_file(command)
            elif command.command == CommandType.READ_FILE:
                return self._read_file(command)
            elif command.command == CommandType.MODIFY_FILE:
                return self._modify_file(command)
            elif command.command == CommandType.DELETE_FILE:
                return self._delete_file(command)
            elif command.command == CommandType.SEARCH_FILE:
                return self._search_file(command)
            elif command.command == CommandType.PULL:
                return self._pull(command)
            elif command.command == CommandType.COMMIT:
                return self._commit(command)
            elif command.command == CommandType.PUSH:
                return self._push(command)
            elif command.command == CommandType.CREATE_BRANCH:
                return self._create_branch(command)
            elif command.command == CommandType.SWITCH_BRANCH:
                return self._switch_branch(command)
            elif command.command == CommandType.CLONE:
                return self._clone(command)
            else:
                return {
                    "success": False,
                    "error": f"Comando non supportato: {command.command}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nell'esecuzione del comando {command.command}: {str(e)}"
            }

    def _create_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando create.file"""
        return self.file_manager.create_file(command.path, command.content)

    def _read_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando read.file"""
        return self.file_manager.read_file(command.path)

    def _modify_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando modify.file"""
        # Determina se è append o replace dal contenuto del comando
        # Se il path contiene "(append)", usa append mode
        append_mode = "(append)" in (command.path or "")
        if append_mode:
            command.path = command.path.replace("(append)", "").strip()

        return self.file_manager.modify_file(command.path, command.content, append_mode)

    def _delete_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando delete.file"""
        return self.file_manager.delete_file(command.path)

    def _search_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando search.file"""
        # Il tipo di ricerca è determinato dal formato del content
        search_term = command.content

        # Decodifica il content se è in base64
        try:
            decoded_bytes = base64.b64decode(search_term)
            search_term = decoded_bytes.decode('utf-8')
        except:
            pass  # Se non è base64, usa il valore originale

        # Determina il tipo di ricerca dal prefisso
        if search_term.startswith("name:"):
            search_type = "name"
            search_term = search_term[5:].strip()
        elif search_term.startswith("ext:") or search_term.startswith("extension:"):
            search_type = "extension"
            search_term = search_term.split(":", 1)[1].strip()
        elif search_term.startswith("content:"):
            search_type = "content"
            search_term = search_term[8:].strip()
        else:
            # Default: ricerca per nome
            search_type = "name"

        return self.file_manager.search_files(search_term, search_type)

    def _pull(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando pull"""
        return self.git_manager.pull()

    def _commit(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando commit"""
        # Decodifica il messaggio di commit
        try:
            decoded_bytes = base64.b64decode(command.content)
            commit_message = decoded_bytes.decode('utf-8')
        except:
            commit_message = command.content

        return self.git_manager.commit(commit_message)

    def _push(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando push"""
        return self.git_manager.push()

    def _create_branch(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando create.branch"""
        return self.git_manager.create_branch(command.path)

    def _switch_branch(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando switch.branch"""
        return self.git_manager.switch_branch(command.path)

    def _clone(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando clone"""
        # Il clone è già stato fatto durante l'inizializzazione
        return {
            "success": True,
            "message": "Repository già clonato localmente",
            "local_path": self.auth_manager.local_repo_path
        }

    def get_status(self) -> Dict[str, Any]:
        """Ottieni lo status corrente del gateway e del repository"""
        if not self.is_initialized:
            return {
                "success": False,
                "error": "Gateway non inizializzato"
            }

        git_status = self.git_manager.get_status()

        return {
            "success": True,
            "initialized": self.is_initialized,
            "repository": self.auth_manager.get_current_repo_info(),
            "local_path": self.auth_manager.local_repo_path,
            "git_status": git_status
        }

    def cleanup(self):
        """Pulisce le risorse utilizzate"""
        if self.auth_manager:
            self.auth_manager.cleanup_local_clone()
        self.is_initialized = False
