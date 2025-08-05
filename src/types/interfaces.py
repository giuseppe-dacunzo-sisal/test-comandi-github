"""
Interfacce per input/output dell'estensione GitHub Copilot
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class ProcessedStep:
    """Risultato dell'elaborazione di un singolo step"""
    step: int
    success: bool
    message: str
    error: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class GatewayResponse:
    """Risposta completa del gateway per l'elaborazione dei comandi"""
    success: bool
    message: str
    processed_steps: List[ProcessedStep]
    repository_info: Optional[Dict[str, str]] = None
    user_info: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.repository_info is None:
            self.repository_info = {}
        if self.user_info is None:
            self.user_info = {}


@dataclass
class CommandExecutionRequest:
    """Richiesta per l'esecuzione di comandi tramite API"""
    repo_owner: str
    repo_name: str
    user_id: str
    commands: List[Dict[str, Any]]


@dataclass
class AuthenticationRequest:
    """Richiesta per l'avvio dell'autenticazione"""
    repo_owner: str
    repo_name: str
    user_id: str
    workspace_path: Optional[str] = None


@dataclass
class AuthenticationResponse:
    """Risposta per l'autenticazione device flow"""
    success: bool
    session_id: Optional[str] = None
    user_code: Optional[str] = None
    verification_uri: Optional[str] = None
    message: Optional[str] = None
    expires_in: Optional[int] = None
    error: Optional[str] = None


@dataclass
class AuthStatusResponse:
    """Risposta per lo stato dell'autenticazione"""
    success: bool
    status: str  # 'pending', 'authenticated', 'expired', 'error'
    user: Optional[Dict[str, Any]] = None
    repository: Optional[Dict[str, str]] = None
    error: Optional[str] = None
    message: Optional[str] = None
