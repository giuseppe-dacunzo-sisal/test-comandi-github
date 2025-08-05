import os
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from flask import Flask, jsonify, request, redirect
from threading import Thread
import time
import logging

from .device_flow_auth import GitHubDeviceFlowAuth

class GitHubCopilotApp:
    """
    GitHub App pubblica per l'estensione Copilot
    Gestisce installazioni multiple e webhook
    """

    def __init__(self, port: int = 3000):
        self.port = port
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

        # Configurazione GitHub App
        self.client_id = os.getenv("GITHUB_CLIENT_ID")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
        self.app_base_url = os.getenv("APP_BASE_URL", f"http://localhost:{port}")

        # Gestione sessioni multi-utente
        self.user_sessions: Dict[str, GitHubDeviceFlowAuth] = {}
        self.active_auth_sessions: Dict[str, Dict[str, Any]] = {}

        # Setup logging
        logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
        self.logger = logging.getLogger(__name__)

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Configura le routes per la GitHub App"""

        @self.app.route('/', methods=['GET'])
        def home():
            """Home page della GitHub App"""
            return jsonify({
                "name": "GitHub Copilot Commands Extension",
                "description": "Automazione comandi GitHub tramite pseudo-script",
                "version": "2.0.0",
                "endpoints": {
                    "auth_start": f"{self.app_base_url}/auth/start",
                    "auth_callback": f"{self.app_base_url}/auth/callback",
                    "webhook": f"{self.app_base_url}/webhook",
                    "health": f"{self.app_base_url}/health"
                }
            })

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "active_sessions": len(self.active_auth_sessions),
                "timestamp": time.time()
            })

        @self.app.route('/auth/start', methods=['POST'])
        def start_auth():
            """Avvia autenticazione per un repository specifico"""
            try:
                data = request.get_json() or {}

                # Repository info dal client
                repo_owner = data.get('repo_owner')
                repo_name = data.get('repo_name')
                user_id = data.get('user_id')  # ID utente GitHub

                if not all([repo_owner, repo_name, user_id]):
                    return jsonify({
                        "success": False,
                        "error": "Parametri mancanti: repo_owner, repo_name, user_id richiesti"
                    }), 400

                # Crea sessione di autenticazione per l'utente
                session_key = f"{user_id}_{repo_owner}_{repo_name}"

                if session_key not in self.user_sessions:
                    self.user_sessions[session_key] = GitHubDeviceFlowAuth()

                auth_manager = self.user_sessions[session_key]

                # Avvia device flow
                device_result = auth_manager.start_device_flow()

                if device_result["success"]:
                    # Salva sessione di autenticazione
                    session_id = device_result["device_code"]
                    self.active_auth_sessions[session_id] = {
                        "device_code": device_result["device_code"],
                        "user_code": device_result["user_code"],
                        "started_at": time.time(),
                        "expires_in": device_result["expires_in"],
                        "repo_owner": repo_owner,
                        "repo_name": repo_name,
                        "user_id": user_id,
                        "session_key": session_key
                    }

                    # Avvia polling in background
                    Thread(
                        target=self._background_token_polling,
                        args=(session_id, device_result["device_code"], device_result["interval"]),
                        daemon=True
                    ).start()

                    return jsonify({
                        "success": True,
                        "session_id": session_id,
                        "user_code": device_result["user_code"],
                        "verification_uri": device_result["verification_uri"],
                        "message": device_result["message"],
                        "expires_in": device_result["expires_in"]
                    })
                else:
                    return jsonify(device_result), 400

            except Exception as e:
                self.logger.error(f"Errore start_auth: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Errore interno: {str(e)}"
                }), 500

        @self.app.route('/auth/status/<session_id>', methods=['GET'])
        def check_auth_status(session_id):
            """Controlla lo stato dell'autenticazione"""
            try:
                if session_id not in self.active_auth_sessions:
                    return jsonify({
                        "success": False,
                        "error": "Sessione non trovata"
                    }), 404

                session = self.active_auth_sessions[session_id]
                session_key = session["session_key"]

                # Controlla se la sessione è scaduta
                if time.time() - session["started_at"] > session["expires_in"]:
                    self._cleanup_session(session_id, session_key)
                    return jsonify({
                        "success": False,
                        "status": "expired",
                        "error": "Sessione scaduta"
                    })

                # Controlla se l'autenticazione è completata
                auth_manager = self.user_sessions.get(session_key)
                if auth_manager and auth_manager.is_authenticated():
                    # Cleanup sessione completata
                    del self.active_auth_sessions[session_id]

                    return jsonify({
                        "success": True,
                        "status": "authenticated",
                        "user": auth_manager.get_user_info(),
                        "repository": {
                            "owner": session["repo_owner"],
                            "name": session["repo_name"],
                            "full_name": f"{session['repo_owner']}/{session['repo_name']}"
                        }
                    })
                else:
                    return jsonify({
                        "success": True,
                        "status": "pending",
                        "message": "In attesa dell'autorizzazione utente"
                    })

            except Exception as e:
                self.logger.error(f"Errore check_auth_status: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Errore interno: {str(e)}"
                }), 500

        @self.app.route('/commands/execute', methods=['POST'])
        def execute_commands():
            """Esegue comandi per un repository autenticato"""
            try:
                data = request.get_json() or {}

                repo_owner = data.get('repo_owner')
                repo_name = data.get('repo_name')
                user_id = data.get('user_id')
                commands = data.get('commands', [])

                if not all([repo_owner, repo_name, user_id, commands]):
                    return jsonify({
                        "success": False,
                        "error": "Parametri mancanti: repo_owner, repo_name, user_id, commands richiesti"
                    }), 400

                session_key = f"{user_id}_{repo_owner}_{repo_name}"

                # Verifica autenticazione
                if session_key not in self.user_sessions:
                    return jsonify({
                        "success": False,
                        "error": "Sessione non autenticata. Avvia prima l'autenticazione."
                    }), 401

                auth_manager = self.user_sessions[session_key]
                if not auth_manager.is_authenticated():
                    return jsonify({
                        "success": False,
                        "error": "Autenticazione scaduta. Riavvia l'autenticazione."
                    }), 401

                # Importa gateway e processa comandi
                from ..gateway import GitHubGateway

                # Imposta repository info nell'auth manager
                auth_manager.current_repo_info = {
                    "owner": repo_owner,
                    "repo": repo_name,
                    "full_name": f"{repo_owner}/{repo_name}"
                }

                # Crea gateway con auth manager già configurato
                gateway = GitHubGateway()
                gateway.auth_manager = auth_manager

                # Processa comandi
                result = gateway.process_commands(commands)

                return jsonify({
                    "success": result.success,
                    "message": result.message,
                    "processed_steps": [
                        {
                            "step": step.step,
                            "success": step.success,
                            "message": step.message,
                            "error": step.error,
                            "details": step.details
                        }
                        for step in result.processed_steps
                    ],
                    "repository_info": result.repository_info,
                    "user_info": result.user_info
                })

            except Exception as e:
                self.logger.error(f"Errore execute_commands: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Errore nell'esecuzione: {str(e)}"
                }), 500

        @self.app.route('/webhook', methods=['POST'])
        def github_webhook():
            """Gestisce webhook GitHub per eventi dell'app"""
            try:
                # Verifica signature del webhook
                signature = request.headers.get('X-Hub-Signature-256')
                if not self._verify_webhook_signature(request.data, signature):
                    return jsonify({"error": "Invalid signature"}), 403

                event_type = request.headers.get('X-GitHub-Event')
                payload = request.get_json()

                self.logger.info(f"Ricevuto webhook: {event_type}")

                # Gestisci eventi specifici
                if event_type == 'installation':
                    return self._handle_installation_event(payload)
                elif event_type == 'installation_repositories':
                    return self._handle_installation_repositories_event(payload)

                return jsonify({"message": "Event processed"}), 200

            except Exception as e:
                self.logger.error(f"Errore webhook: {str(e)}")
                return jsonify({"error": "Internal error"}), 500

        @self.app.route('/auth/logout', methods=['POST'])
        def logout():
            """Effettua logout per un utente/repository specifico"""
            try:
                data = request.get_json() or {}
                repo_owner = data.get('repo_owner')
                repo_name = data.get('repo_name')
                user_id = data.get('user_id')

                session_key = f"{user_id}_{repo_owner}_{repo_name}"

                # Cleanup sessione utente
                if session_key in self.user_sessions:
                    auth_manager = self.user_sessions[session_key]
                    auth_manager.cleanup_local_clone()
                    del self.user_sessions[session_key]

                # Cleanup sessioni di autenticazione attive
                to_remove = []
                for session_id, session in self.active_auth_sessions.items():
                    if session.get("session_key") == session_key:
                        to_remove.append(session_id)

                for session_id in to_remove:
                    del self.active_auth_sessions[session_id]

                return jsonify({
                    "success": True,
                    "message": "Logout completato"
                })

            except Exception as e:
                self.logger.error(f"Errore logout: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Errore durante logout: {str(e)}"
                }), 500

    def _verify_webhook_signature(self, payload_body: bytes, signature_header: str) -> bool:
        """Verifica la signature del webhook GitHub"""
        if not self.webhook_secret or not signature_header:
            return False

        try:
            hash_object = hmac.new(
                self.webhook_secret.encode('utf-8'),
                msg=payload_body,
                digestmod=hashlib.sha256
            )
            expected_signature = "sha256=" + hash_object.hexdigest()
            return hmac.compare_digest(expected_signature, signature_header)
        except Exception:
            return False

    def _handle_installation_event(self, payload: Dict[str, Any]) -> tuple:
        """Gestisce eventi di installazione/disinstallazione dell'app"""
        action = payload.get('action')
        installation = payload.get('installation', {})

        self.logger.info(f"Installation event: {action} for installation {installation.get('id')}")

        if action == 'deleted':
            # Cleanup sessioni per questa installazione
            installation_id = installation.get('id')
            # TODO: Implementa cleanup basato su installation_id se necessario

        return jsonify({"message": f"Installation {action} processed"}), 200

    def _handle_installation_repositories_event(self, payload: Dict[str, Any]) -> tuple:
        """Gestisce eventi di aggiunta/rimozione repository"""
        action = payload.get('action')
        repositories = payload.get('repositories_added', []) if action == 'added' else payload.get('repositories_removed', [])

        self.logger.info(f"Repository {action}: {[repo.get('name') for repo in repositories]}")

        return jsonify({"message": f"Repositories {action} processed"}), 200

    def _background_token_polling(self, session_id: str, device_code: str, interval: int):
        """Polling in background per ottenere l'access token"""
        try:
            if session_id not in self.active_auth_sessions:
                return

            session = self.active_auth_sessions[session_id]
            session_key = session["session_key"]
            auth_manager = self.user_sessions.get(session_key)

            if auth_manager:
                result = auth_manager.poll_for_token(device_code, interval)
                self.logger.info(f"Token polling result for {session_id}: {result.get('success', False)}")

        except Exception as e:
            self.logger.error(f"Errore nel polling token per sessione {session_id}: {str(e)}")
            self._cleanup_session(session_id, session.get("session_key"))

    def _cleanup_session(self, session_id: str, session_key: str):
        """Pulisce una sessione scaduta o in errore"""
        if session_id in self.active_auth_sessions:
            del self.active_auth_sessions[session_id]

        if session_key and session_key in self.user_sessions:
            self.user_sessions[session_key].cleanup_local_clone()
            del self.user_sessions[session_key]

    def start_server(self, debug: bool = False):
        """Avvia il server Flask"""
        self.logger.info(f"🚀 Avvio GitHub Copilot App su porta {self.port}")
        self.logger.info(f"🌐 URL base: {self.app_base_url}")
        self.logger.info(f"📡 Endpoint webhook: {self.app_base_url}/webhook")

        self.app.run(
            host='0.0.0.0',
            port=self.port,
            debug=debug,
            threaded=True
        )

# Funzione per avviare l'app GitHub
def start_github_app(port: int = 3000, debug: bool = False):
    """Avvia la GitHub App"""
    app = GitHubCopilotApp(port)
    app.start_server(debug)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="GitHub Copilot Extension App")
    parser.add_argument("--port", type=int, default=3000, help="Porta del server")
    parser.add_argument("--debug", action="store_true", help="Modalità debug")

    args = parser.parse_args()
    start_github_app(args.port, args.debug)
