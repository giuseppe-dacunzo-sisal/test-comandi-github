#!/usr/bin/env python3
"""
GitHub Copilot Extension per la conversione di comandi pseudo script
in operazioni reali su repository GitHub con OAuth automatico.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any
from src.gateway import GitHubGateway  # Aggiornato per usare il nuovo gateway OAuth

class GitHubCopilotExtension:
    """Classe principale dell'estensione GitHub Copilot con OAuth automatico"""

    def __init__(self):
        self.gateway = GitHubGateway()  # Usa il nuovo gateway con OAuth

    def run(self, commands: List[Dict[str, Any]], workspace_path: str = None) -> Dict[str, Any]:
        """
        Esegue l'estensione con OAuth automatico

        Args:
            commands: Lista di comandi da eseguire
            workspace_path: Path del workspace (opzionale, usa directory corrente se None)

        Returns:
            Dict con risultati dell'esecuzione
        """
        try:
            # Il gateway gestisce automaticamente autenticazione e inizializzazione
            results = self.gateway.process_commands(commands)

            return {
                "success": True,
                "results": results,
                "message": "Comandi eseguiti con successo"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nell'esecuzione: {str(e)}"
            }

def main():
    """Funzione principale per uso da linea di comando"""
    parser = argparse.ArgumentParser(description="GitHub Copilot Extension con OAuth")
    parser.add_argument("--commands", type=str, required=True,
                       help="JSON string o path del file con i comandi")
    parser.add_argument("--workspace", type=str,
                       help="Path del workspace (opzionale)")

    args = parser.parse_args()

    # Carica i comandi
    try:
        if os.path.isfile(args.commands):
            with open(args.commands, 'r') as f:
                commands = json.load(f)
        else:
            commands = json.loads(args.commands)
    except Exception as e:
        print(f"❌ Errore nel caricamento comandi: {e}")
        return 1

    # Esegui l'estensione
    extension = GitHubCopilotExtension()
    result = extension.run(commands, args.workspace)

    # Mostra risultati
    if result["success"]:
        print("✅ Estensione eseguita con successo!")
        print(json.dumps(result["results"], indent=2))
        return 0
    else:
        print(f"❌ Errore: {result['message']}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
