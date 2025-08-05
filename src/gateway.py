import base64
import os
import tempfile
from typing import List, Dict, Any, Optional
from src.types.interfaces import GatewayResponse, ProcessedStep
from src.types.command_types import GitHubCommand, CommandType, SearchType, ModifyType
from src.types.validator import CommandValidator
from src.auth.device_flow_auth import GitHubDeviceFlowAuth
from src.operations.file_operations import FileOperationsManager
from src.operations.git_operations import GitOperationsManager

class GitHubGateway:
    """Gateway principale per l'estensione GitHub Copilot con Device Flow Authentication"""

    def __init__(self, workspace_path: Optional[str] = None):
        self.auth_manager = GitHubDeviceFlowAuth()
        self.file_manager = None
        self.git_manager = None
        self.is_initialized = False
        self.workspace_path = workspace_path or os.getcwd()
        self.validator = CommandValidator()

    def _ensure_authenticated(self) -> Dict[str, Any]:
        """
        Assicura che l'utente sia autenticato, gestendo il device flow se necessario

        Returns:
            Dict con risultato dell'autenticazione
        """
        if self.auth_manager.is_authenticated():
            return {"success": True, "message": "Già autenticato"}

        print("🔐 Avvio autenticazione GitHub Device Flow...")

        # Rileva repository dal workspace corrente
        repo_result = self.auth_manager.get_repository_from_context(self.workspace_path)
        if repo_result["success"]:
            print(f"📁 Repository rilevato: {repo_result['repository']['full_name']}")
        else:
            print(f"⚠️ Warning: {repo_result['error']}")

        # Avvia device flow
        device_result = self.auth_manager.start_device_flow()
        if not device_result["success"]:
            return device_result

        print(f"📱 {device_result['message']}")
        print("⏳ In attesa dell'autorizzazione utente...")

        # Polling per il token
        token_result = self.auth_manager.poll_for_token(
            device_result["device_code"],
            device_result["interval"]
        )

        if token_result["success"]:
            print(f"✅ Autenticazione completata! Benvenuto, {token_result['user']['name']}")

            # Setup del repository locale se rilevato
            if repo_result["success"]:
                try:
                    local_path = self.auth_manager.setup_local_clone(self.workspace_path)
                    print(f"📂 Repository clonato localmente: {local_path}")
                except Exception as e:
                    print(f"⚠️ Warning: Errore nel setup clone locale: {str(e)}")

            return token_result
        else:
            return token_result

    def _initialize_workspace(self) -> Dict[str, Any]:
        """
        Inizializza il workspace e i manager per le operazioni

        Returns:
            Dict con risultato dell'inizializzazione
        """
        try:
            if self.is_initialized:
                return {"success": True, "message": "Workspace già inizializzato"}

            # Verifica autenticazione
            auth_result = self._ensure_authenticated()
            if not auth_result["success"]:
                return auth_result

            # Verifica repository e permessi
            repo_info = self.auth_manager.get_current_repo_info()
            if not repo_info:
                return {
                    "success": False,
                    "error": "Nessun repository GitHub rilevato nel workspace corrente"
                }

            permissions_result = self.auth_manager.check_repository_permissions()
            if not permissions_result["success"]:
                return {
                    "success": False,
                    "error": f"Errore verifica permessi: {permissions_result['error']}"
                }

            if not permissions_result["permissions"]["write"]:
                return {
                    "success": False,
                    "error": "Permessi di scrittura insufficienti sul repository"
                }

            # Usa il clone locale se disponibile, altrimenti il workspace corrente
            base_path = self.auth_manager.local_repo_path or self.workspace_path

            # Inizializza i manager
            self.file_manager = FileOperationsManager(
                github_client=self.auth_manager.get_github_client(),
                repo_info=repo_info,
                base_path=base_path
            )

            self.git_manager = GitOperationsManager(
                github_client=self.auth_manager.get_github_client(),
                repo_info=repo_info,
                base_path=base_path,
                auth_token=self.auth_manager.access_token
            )

            self.is_initialized = True

            return {
                "success": True,
                "message": "Workspace inizializzato",
                "repository": repo_info,
                "permissions": permissions_result["permissions"],
                "user": self.auth_manager.get_user_info(),
                "base_path": base_path
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Errore nell'inizializzazione workspace: {str(e)}"
            }

    def process_commands(self, commands: List[Dict[str, Any]]) -> GatewayResponse:
        """
        Processa una lista di comandi GitHub

        Args:
            commands: Lista di comandi da processare

        Returns:
            GatewayResponse con risultati dell'elaborazione
        """
        try:
            # Validazione comandi
            validation_result = self.validator.validate_commands(commands)
            if not validation_result["is_valid"]:
                raise ValueError(f"Comandi non validi: {validation_result['error']}")

            # Inizializzazione workspace
            init_result = self._initialize_workspace()
            if not init_result["success"]:
                raise ValueError(f"Errore nell'inizializzazione: {init_result['error']}")

            # Conversione in oggetti GitHubCommand
            github_commands = []
            for cmd_data in commands:
                try:
                    github_command = GitHubCommand.from_dict(cmd_data)
                    github_commands.append(github_command)
                except Exception as e:
                    raise ValueError(f"Errore nella conversione comando step {cmd_data.get('step', '?')}: {str(e)}")

            # Processamento comandi
            processed_steps = []
            overall_success = True

            for github_command in github_commands:
                try:
                    step_result = self._execute_command(github_command)
                    processed_steps.append(step_result)

                    if not step_result.success:
                        overall_success = False

                except Exception as e:
                    error_step = ProcessedStep(
                        step=github_command.step,
                        success=False,
                        message=f"Errore nell'esecuzione del comando step {github_command.step}",
                        error=str(e),
                        details={}
                    )
                    processed_steps.append(error_step)
                    overall_success = False

            return GatewayResponse(
                success=overall_success,
                message="Elaborazione comandi completata" if overall_success else "Elaborazione completata con errori",
                processed_steps=processed_steps,
                repository_info=self.auth_manager.get_current_repo_info(),
                user_info=self.auth_manager.get_user_info()
            )

        except Exception as e:
            raise ValueError(f"Errore nella validazione comandi: {str(e)}")

    def _execute_command(self, command: GitHubCommand) -> ProcessedStep:
        """
        Esegue un singolo comando GitHub

        Args:
            command: Comando da eseguire

        Returns:
            ProcessedStep con risultato dell'esecuzione
        """
        try:
            # Dispatch del comando al metodo appropriato
            if command.command == CommandType.CREATE_FILE:
                result = self._execute_create_file(command)
            elif command.command == CommandType.READ_FILE:
                result = self._execute_read_file(command)
            elif command.command == CommandType.MODIFY_FILE:
                result = self._execute_modify_file(command)
            elif command.command == CommandType.DELETE_FILE:
                result = self._execute_delete_file(command)
            elif command.command == CommandType.SEARCH_FILE:
                result = self._execute_search_file(command)
            elif command.command == CommandType.PULL:
                result = self._execute_pull(command)
            elif command.command == CommandType.COMMIT:
                result = self._execute_commit(command)
            elif command.command == CommandType.PUSH:
                result = self._execute_push(command)
            elif command.command == CommandType.CREATE_BRANCH:
                result = self._execute_create_branch(command)
            elif command.command == CommandType.SWITCH_BRANCH:
                result = self._execute_switch_branch(command)
            elif command.command == CommandType.CLONE:
                result = self._execute_clone(command)
            else:
                return ProcessedStep(
                    step=command.step,
                    success=False,
                    message=f"Comando non supportato: {command.command}",
                    error=f"Comando non implementato: {command.command}",
                    details={}
                )

            return ProcessedStep(
                step=command.step,
                success=result.get("success", False),
                message=result.get("message", ""),
                error=result.get("error"),
                details=result.get("details", {})
            )

        except Exception as e:
            return ProcessedStep(
                step=command.step,
                success=False,
                message=f"Errore nell'esecuzione del comando step {command.step}",
                error=str(e),
                details={}
            )

    def _execute_create_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando create.file"""
        return self.file_manager.create_file(command.path, command.content)

    def _execute_read_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando read.file"""
        return self.file_manager.read_file(command.path)

    def _execute_modify_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando modify.file"""
        # Determina se è append o replace dal contenuto del comando
        # Se il path contiene "(append)", usa append mode
        append_mode = "(append)" in (command.path or "")
        if append_mode:
            command.path = command.path.replace("(append)", "").strip()

        return self.file_manager.modify_file(command.path, command.content, append_mode)

    def _execute_delete_file(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando delete.file"""
        return self.file_manager.delete_file(command.path)

    def _execute_search_file(self, command: GitHubCommand) -> Dict[str, Any]:
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

    def _execute_pull(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando pull"""
        return self.git_manager.pull()

    def _execute_commit(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando commit"""
        # Decodifica il messaggio di commit
        try:
            decoded_bytes = base64.b64decode(command.content)
            commit_message = decoded_bytes.decode('utf-8')
        except:
            commit_message = command.content

        return self.git_manager.commit(commit_message)

    def _execute_push(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando push"""
        return self.git_manager.push()

    def _execute_create_branch(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando create.branch"""
        return self.git_manager.create_branch(command.path)

    def _execute_switch_branch(self, command: GitHubCommand) -> Dict[str, Any]:
        """Gestisce il comando switch.branch"""
        return self.git_manager.switch_branch(command.path)

    def _execute_clone(self, command: GitHubCommand) -> Dict[str, Any]:
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
