from typing import List, Dict, Any
from src.types.command_types import GitHubCommand, CommandType

class CommandValidator:
    """Validatore per la struttura dei comandi"""

    @staticmethod
    def validate_command(command_dict: Dict[str, Any]) -> bool:
        """
        Valida un singolo comando

        Args:
            command_dict: Dizionario del comando da validare

        Returns:
            bool: True se valido, False altrimenti
        """
        try:
            # Crea l'oggetto comando per validazione
            command = GitHubCommand(**command_dict)
            return command.validate()
        except Exception:
            return False

    @staticmethod
    def validateCommands(commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Valida un array di comandi

        Args:
            commands: Lista di comandi da validare

        Returns:
            Dict: Risultato della validazione
        """
        if not isinstance(commands, list):
            return {
                "valid": False,
                "error": "Commands must be an array"
            }

        for i, cmd_dict in enumerate(commands):
            if not CommandValidator.validate_command(cmd_dict):
                return {
                    "valid": False,
                    "error": f"Invalid command at index {i}",
                    "command": cmd_dict
                }

        return {"valid": True}
