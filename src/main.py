#!/usr/bin/env python3
"""
GitHub Copilot Extension - Main Entry Point
GitHub App pubblica per automazione comandi GitHub
"""

import os
import sys
import argparse
import json
from typing import Dict, Any, List

# Aggiungi il percorso src al PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.gateway import GitHubGateway
from src.auth.github_app import GitHubCopilotApp, start_github_app
from src.auth.device_flow_auth import GitHubDeviceFlowAuth
from src.types.interfaces import GatewayResponse

class GitHubCopilotExtension:
    """
    Classe principale per l'estensione GitHub Copilot
    Supporta modalità locale e GitHub App pubblica
    """

    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or os.getcwd()
        self.gateway = GitHubGateway(workspace_path=self.workspace_path)
        self.auth_manager = GitHubDeviceFlowAuth()

    def authenticate_interactive(self) -> Dict[str, Any]:
        """
        Autenticazione interattiva con device flow

        Returns:
            Risultato dell'autenticazione
        """
        print("🚀 GitHub Copilot Extension - Autenticazione")
        print("=" * 50)

        # Rileva repository dal workspace
        print(f"📁 Workspace: {self.workspace_path}")
        repo_result = self.auth_manager.get_repository_from_context(self.workspace_path)

        if repo_result["success"]:
            print(f"📂 Repository rilevato: {repo_result['repository']['full_name']}")
        else:
            print(f"⚠️ {repo_result['error']}")
            print("💡 L'estensione funzionerà comunque, ma senza contesto del repository")

        # Avvia device flow
        device_result = self.auth_manager.start_device_flow()
        if not device_result["success"]:
            return device_result

        print("\n🔐 Autenticazione GitHub Device Flow")
        print(f"📱 {device_result['message']}")
        print(f"⏰ Scade in {device_result['expires_in'] // 60} minuti")
        print("\n⏳ In attesa dell'autorizzazione...")

        # Polling per il token
        token_result = self.auth_manager.poll_for_token(
            device_result["device_code"],
            device_result["interval"]
        )

        if token_result["success"]:
            user = token_result["user"]
            print(f"\n✅ Autenticazione completata!")
            print(f"👤 Benvenuto, {user['name']} ({user['login']})")

            # Setup repository locale se possibile
            if repo_result["success"]:
                try:
                    local_path = self.auth_manager.setup_local_clone(self.workspace_path)
                    print(f"📂 Repository clonato: {local_path}")
                except Exception as e:
                    print(f"⚠️ Warning setup clone: {str(e)}")

            return token_result
        else:
            print(f"\n❌ Errore autenticazione: {token_result['error']}")
            return token_result

    def process_commands_from_file(self, commands_file: str) -> GatewayResponse:
        """
        Processa comandi da file JSON

        Args:
            commands_file: Path al file JSON con i comandi

        Returns:
            Risultato dell'elaborazione
        """
        try:
            with open(commands_file, 'r', encoding='utf-8') as f:
                commands = json.load(f)

            return self.gateway.process_commands(commands)

        except Exception as e:
            raise Exception(f"Errore nel caricamento file comandi: {str(e)}")

    def process_commands_interactive(self) -> GatewayResponse:
        """
        Modalità interattiva per inserire comandi

        Returns:
            Risultato dell'elaborazione
        """
        print("\n📝 Inserimento comandi interattivo")
        print("Inserisci i comandi in formato JSON (premi CTRL+D per terminare):")

        try:
            # Leggi input multilinea
            lines = []
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    break

            commands_json = '\n'.join(lines)
            commands = json.loads(commands_json)

            return self.gateway.process_commands(commands)

        except Exception as e:
            raise Exception(f"Errore nel parsing comandi: {str(e)}")

    def print_results(self, response: GatewayResponse):
        """
        Stampa i risultati in formato user-friendly

        Args:
            response: Risposta del gateway
        """
        print("\n" + "="*60)
        print("📊 RISULTATI ELABORAZIONE")
        print("="*60)

        # Status generale
        status_icon = "✅" if response.success else "❌"
        print(f"{status_icon} Status: {response.message}")

        # Informazioni repository e utente
        if response.repository_info:
            repo = response.repository_info
            print(f"📂 Repository: {repo['full_name']}")

        if response.user_info:
            user = response.user_info
            print(f"👤 Utente: {user['name']} ({user['login']})")

        print("\nDettaglio per step:")

        # Risultati per step
        for step in response.processed_steps:
            status_icon = "✅" if step.success else "❌"
            print(f"   {status_icon} Step {step.step}: {step.message}")

            if not step.success and step.error:
                print(f"      ⚠️ Errore: {step.error}")

            if step.details:
                for key, value in step.details.items():
                    print(f"      💡 {key}: {value}")

        print("="*60)

def main():
    """Funzione principale per l'esecuzione da command line"""
    parser = argparse.ArgumentParser(
        description="GitHub Copilot Extension - Automazione comandi GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:

  # Modalità GitHub App pubblica (per deployment cloud)
  python main.py app --port 3000

  # Esegui comandi da file (modalità standalone)
  python main.py run --file examples/sample_commands.json

  # Modalità interattiva (modalità standalone)
  python main.py run --interactive

  # Test autenticazione
  python main.py auth
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandi disponibili')

    # Comando app (GitHub App pubblica)
    app_parser = subparsers.add_parser('app', help='Avvia GitHub App pubblica')
    app_parser.add_argument('--port', type=int, default=int(os.getenv('PORT', 3000)), help='Porta server')
    app_parser.add_argument('--debug', action='store_true', help='Modalità debug')

    # Comando run (modalità standalone)
    run_parser = subparsers.add_parser('run', help='Esegui comandi GitHub in modalità standalone')
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument('--file', '-f', help='File JSON con comandi da eseguire')
    run_group.add_argument('--interactive', '-i', action='store_true', help='Modalità interattiva')
    run_parser.add_argument('--workspace', '-w', help='Path del workspace (default: directory corrente)')

    # Comando auth
    auth_parser = subparsers.add_parser('auth', help='Test autenticazione device flow')
    auth_parser.add_argument('--workspace', '-w', help='Path del workspace (default: directory corrente)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == 'app':
            print(f"🚀 Avvio GitHub App pubblica sulla porta {args.port}")
            start_github_app(port=args.port, debug=args.debug)

        elif args.command == 'run':
            workspace = args.workspace or os.getcwd()
            extension = GitHubCopilotExtension(workspace_path=workspace)

            # Autenticazione
            auth_result = extension.authenticate_interactive()
            if not auth_result["success"]:
                print(f"❌ Autenticazione fallita: {auth_result['error']}")
                return 1

            # Esecuzione comandi
            if args.file:
                if not os.path.exists(args.file):
                    print(f"❌ File non trovato: {args.file}")
                    return 1

                print(f"\n📁 Caricamento comandi da: {args.file}")
                response = extension.process_commands_from_file(args.file)
            else:
                response = extension.process_commands_interactive()

            # Stampa risultati
            extension.print_results(response)

            return 0 if response.success else 1

        elif args.command == 'auth':
            workspace = args.workspace or os.getcwd()
            extension = GitHubCopilotExtension(workspace_path=workspace)

            auth_result = extension.authenticate_interactive()
            if auth_result["success"]:
                print("\n✅ Test autenticazione completato con successo!")
                return 0
            else:
                print(f"\n❌ Test autenticazione fallito: {auth_result['error']}")
                return 1

    except KeyboardInterrupt:
        print("\n\n⏹️ Operazione interrotta dall'utente")
        return 1
    except Exception as e:
        print(f"\n❌ Errore: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
