#!/usr/bin/env python3
"""
GitHub Copilot Extension per la conversione di comandi pseudo script
in operazioni reali su repository GitHub.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any
from src.gateway import GitHubCopilotGateway

class GitHubCopilotExtension:
    """Classe principale dell'estensione GitHub Copilot"""

    def __init__(self):
        self.gateway = GitHubCopilotGateway()

    def run(self, access_token: str, workspace_path: str, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Esegue l'estensione con i parametri forniti

        Args:
            access_token: Token di accesso GitHub
            workspace_path: Path del workspace corrente
            commands: Lista di comandi da eseguire

        Returns:
            Dict con risultati dell'esecuzione
        """
        try:
            # Inizializza il gateway
            init_result = self.gateway.initialize(access_token, workspace_path)
            if not init_result["success"]:
                return {
                    "success": False,
                    "error": "Inizializzazione fallita",
                    "details": init_result
                }

            # Esegui i comandi
            execution_result = self.gateway.execute_commands(commands)

            # Aggiungi informazioni di inizializzazione al risultato
            execution_result["initialization"] = init_result

            return execution_result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore durante l'esecuzione dell'estensione: {str(e)}"
            }
        finally:
            # Pulisci le risorse
            self.gateway.cleanup()

def main():
    """Funzione principale per l'esecuzione da command line"""
    parser = argparse.ArgumentParser(description="GitHub Copilot Extension")
    parser.add_argument("--token", required=True, help="GitHub access token")
    parser.add_argument("--workspace", required=True, help="Workspace path")
    parser.add_argument("--commands", required=True, help="JSON file with commands or JSON string")
    parser.add_argument("--output", help="Output file path (optional)")

    args = parser.parse_args()

    try:
        # Carica i comandi
        if os.path.isfile(args.commands):
            with open(args.commands, 'r', encoding='utf-8') as f:
                commands = json.load(f)
        else:
            commands = json.loads(args.commands)

        # Esegui l'estensione
        extension = GitHubCopilotExtension()
        result = extension.run(args.token, args.workspace, commands)

        # Output del risultato
        output_json = json.dumps(result, indent=2, ensure_ascii=False)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"Risultato salvato in: {args.output}")
        else:
            print(output_json)

        # Exit code basato sul successo
        sys.exit(0 if result["success"] else 1)

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "message": f"Errore nell'esecuzione del main: {str(e)}"
        }
        print(json.dumps(error_result, indent=2, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
