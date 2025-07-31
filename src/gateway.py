import base64
import os
import tempfile
from typing import List, Dict, Any
from src.types.command_types import GitHubCommand, CommandType, SearchType, ModifyType
from src.auth.github_auth import GitHubAuthManager
from src.operations.file_operations import FileOperationsManager
from src.operations.git_operations import GitOperationsManager

class GitHubCopilotGateway:
    """Gateway principale per l'estensione GitHub Copilot"""

    def __init__(self):
        self.auth_manager = GitHubAuthManager()
        self.file_manager = None
        self.git_manager = None
        self.is_initialized = False

    def initialize(self, access_token: str, workspace_path: str) -> Dict[str, Any]:
        """
        Inizializza il gateway con autenticazione e workspace

        Args:
            access_token: Token di accesso GitHub
            workspace_path: Path del workspace corrente

        Returns:
            Dict con risultato dell'inizializzazione
        """
        try:
            # Autentica con GitHub
            auth_result = self.auth_manager.authenticate(access_token)
            if not auth_result["success"]:
                return auth_result

            # Rileva il repository corrente
            repo_result = self.auth_manager.detect_current_repository(workspace_path)
            if not repo_result["success"]:
                return repo_result

            # Verifica i permessi
            perm_result = self.auth_manager.check_repository_permissions()
            if not perm_result["success"]:
                return perm_result

            # Configura il clone locale
            local_path = self.auth_manager.setup_local_clone()

            # Inizializza i manager
            self.file_manager = FileOperationsManager(local_path)
            self.git_manager = GitOperationsManager(
                local_path,
                self.auth_manager.get_github_client(),
                self.auth_manager.get_current_repo_info()
            )

            self.is_initialized = True

            return {
                "success": True,
                "message": "Gateway inizializzato con successo",
                "repository": self.auth_manager.get_current_repo_info(),
                "permissions": perm_result.get("permissions", {}),
                "local_path": local_path
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore durante l'inizializzazione: {str(e)}"
            }

    def execute_commands(self, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Esegue una lista di comandi in sequenza

        Args:
            commands: Lista di comandi da eseguire

        Returns:
            Dict con risultati dell'esecuzione
        """
        if not self.is_initialized:
            return {
                "success": False,
                "error": "Gateway non inizializzato",
                "message": "Chiamare initialize() prima di eseguire comandi"
            }

        results = []
        overall_success = True

        # Ordina i comandi per step
        sorted_commands = sorted(commands, key=lambda x: x.get("step", 0))

        for cmd_dict in sorted_commands:
            try:
                # Crea l'oggetto comando
                command = GitHubCommand(**cmd_dict)

                # Valida il comando
                if not command.validate():
                    result = {
                        "step": command.step,
                        "command": command.command.value,
                        "success": False,
                        "error": "Comando non valido",
                        "message": f"Il comando {command.command.value} non è valido"
                    }
                    results.append(result)
                    overall_success = False
                    continue

                # Esegui il comando
                result = self._execute_single_command(command)
                result["step"] = command.step
                result["command"] = command.command.value

                results.append(result)

                if not result["success"]:
                    overall_success = False

            except Exception as e:
                result = {
                    "step": cmd_dict.get("step", -1),
                    "command": cmd_dict.get("command", "unknown"),
                    "success": False,
                    "error": str(e),
                    "message": f"Errore nell'esecuzione del comando: {str(e)}"
                }
                results.append(result)
                overall_success = False

        return {
            "success": overall_success,
            "results": results,
            "total_commands": len(commands),
            "successful_commands": len([r for r in results if r["success"]]),
            "failed_commands": len([r for r in results if not r["success"]])
        }

    def _execute_single_command(self, command: GitHubCommand) -> Dict[str, Any]:
        """
        Esegue un singolo comando

        Args:
            command: Comando da eseguire

        Returns:
            Dict con risultato dell'esecuzione
        """
        try:
            if command.command == CommandType.CREATE_FILE:
                return self._handle_create_file(command)

            elif command.command == CommandType.READ_FILE:
                return self._handle_read_file(command)

            elif command.command == CommandType.MODIFY_FILE:
                return self._handle_modify_file(command)

            elif command.command == CommandType.DELETE_FILE:
                return self._handle_delete_file(command)

            elif command.command == CommandType.SEARCH_FILE:
                return self._handle_search_file(command)

            elif command.command == CommandType.PULL:
                return self._handle_pull()

            elif command.command == CommandType.COMMIT:
                return self._handle_commit(command)

            elif command.command == CommandType.PUSH:
                return self._handle_push()

            elif command.command == CommandType.CREATE_BRANCH:
                return self._handle_create_branch(command)

            elif command.command == CommandType.SWITCH_BRANCH:
                return self._handle_switch_branch(command)

            elif command.command == CommandType.CLONE:
                return self._handle_clone()

            else:
                return {
                    "success": False,
                    "error": "Comando non implementato",
                    "message": f"Il comando {command.command.value} non è ancora implementato"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nell'esecuzione del comando {command.command.value}: {str(e)}"
            }

    def _handle_create_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando create.file"""
        return self.file_manager.create_file(command.path, command.content)

    def _handle_read_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando read.file"""
        return self.file_manager.read_file(command.path)

    def _handle_modify_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando modify.file"""
        # Determina se è append o replace dal contenuto del comando
        # Se il path contiene "(append)", usa append mode
        append_mode = "(append)" in (command.path or "")
        if append_mode:
            command.path = command.path.replace("(append)", "").strip()

        return self.file_manager.modify_file(command.path, command.content, append_mode)

    def _handle_delete_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando delete.file"""
        return self.file_manager.delete_file(command.path)

    def _handle_search_file(self, command: GitHubCommand) -> Dict[str, Any]:
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

    def _handle_pull(self) -> Dict[str, Any]:
        """Gestisce il comando pull"""
        return self.git_manager.pull()

    def _handle_commit(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando commit"""
        # Decodifica il messaggio di commit
        try:
            decoded_bytes = base64.b64decode(command.content)
            commit_message = decoded_bytes.decode('utf-8')
        except:
            commit_message = command.content

        return self.git_manager.commit(commit_message)

    def _handle_push(self) -> Dict[str, Any]:
        """Gestisce il comando push"""
        return self.git_manager.push()

    def _handle_create_branch(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando create.branch"""
        return self.git_manager.create_branch(command.path)

    def _handle_switch_branch(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando switch.branch"""
        return self.git_manager.switch_branch(command.path)

    def _handle_clone(self) -> Dict[str, Any]:
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
