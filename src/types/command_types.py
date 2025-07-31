from enum import Enum
from typing import Optional, Union
from dataclasses import dataclass

class CommandType(Enum):
    """Enum per i comandi supportati dall'estensione"""
    CREATE_FILE = "create.file"
    SEARCH_FILE = "search.file"
    READ_FILE = "read.file"
    MODIFY_FILE = "modify.file"
    DELETE_FILE = "delete.file"
    PULL = "pull"
    COMMIT = "commit"
    PUSH = "push"
    CREATE_BRANCH = "create.branch"
    SWITCH_BRANCH = "switch.branch"
    CLONE = "clone"

class SearchType(Enum):
    """Enum per i tipi di ricerca"""
    BY_NAME = "name"
    BY_EXTENSION = "extension"
    BY_CONTENT = "content"

class ModifyType(Enum):
    """Enum per i tipi di modifica file"""
    REPLACE = "replace"
    APPEND = "append"

@dataclass
class GitHubCommand:
    """Classe che rappresenta un comando per GitHub"""
    step: int
    command: CommandType
    path: Optional[str] = None
    content: Optional[str] = None  # Content in base64

    def __post_init__(self):
        """Validazione post-inizializzazione"""
        if isinstance(self.command, str):
            try:
                self.command = CommandType(self.command)
            except ValueError:
                raise ValueError(f"Comando non valido: {self.command}")

    @classmethod
    def from_dict(cls, data: dict) -> 'GitHubCommand':
        """Crea un GitHubCommand da un dizionario"""
        return cls(
            step=data.get('step', 0),
            command=data.get('command', ''),
            path=data.get('path'),
            content=data.get('content')
        )

    def validate(self) -> bool:
        """Valida la struttura del comando"""
        # Validazioni specifiche per comando
        if self.command in [CommandType.CREATE_FILE, CommandType.READ_FILE,
                           CommandType.DELETE_FILE, CommandType.MODIFY_FILE]:
            return self.path is not None and len(self.path.strip()) > 0

        if self.command == CommandType.SEARCH_FILE:
            return self.content is not None and len(self.content.strip()) > 0

        if self.command == CommandType.COMMIT:
            return self.content is not None and len(self.content.strip()) > 0

        if self.command in [CommandType.CREATE_BRANCH, CommandType.SWITCH_BRANCH]:
            return self.path is not None and len(self.path.strip()) > 0

        # Per pull, push, clone non servono parametri aggiuntivi
        return True
