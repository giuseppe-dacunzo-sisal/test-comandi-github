#!/usr/bin/env python3
"""
Test dell'estensione GitHub Copilot con autenticazione OAuth automatica
"""

import os
import sys
import json
import base64

# Aggiungi il path src per gli import
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from gateway import GitHubGateway
from dotenv import load_dotenv


def test_oauth_authentication():
    """Test del nuovo flusso di autenticazione OAuth"""
    print("🔐 Test Autenticazione OAuth")
    print("=" * 50)

    # Carica le variabili d'ambiente
    load_dotenv()

    # Verifica che le credenziali OAuth siano configurate
    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")

    if not client_id or client_id == "your_client_id_here":
        print("❌ ATTENZIONE: GITHUB_CLIENT_ID non configurato!")
        print("   Apri il file .env e sostituisci:")
        print("   GITHUB_CLIENT_ID=il_tuo_client_id_reale")
        return False

    if not client_secret or client_secret == "your_client_secret_here":
        print("❌ ATTENZIONE: GITHUB_CLIENT_SECRET non configurato!")
        print("   Apri il file .env e sostituisci:")
        print("   GITHUB_CLIENT_SECRET=il_tuo_client_secret_reale")
        return False

    print("✅ Credenziali OAuth configurate correttamente")
    print(f"📋 Client ID: {client_id[:8]}...")
    print("📝 Nota: Se non sei autenticato, si aprirà automaticamente il browser")

    return True


def test_commands_with_oauth():
    """Test dei comandi con il nuovo sistema OAuth"""
    print("\n📋 Test Comandi con OAuth")
    print("=" * 50)

    # Rileva automaticamente il repository corrente
    current_dir = os.getcwd()
    print(f"📁 Directory corrente: {current_dir}")

    # Comandi di esempio che testano il nuovo flusso
    test_commands = [
        {
            "step": 1,
            "command": "read.file",
            "path": "README.md"
        },
        {
            "step": 2,
            "command": "search.file",
            "content": base64.b64encode("README".encode()).decode()  # Cerca file Python
        },
        {
            "step": 3,
            "command": "create.file",
            "path": "test_oauth_success.txt",
            "content": base64.b64encode("🎉 Test OAuth completato con successo!".encode()).decode()
        },
        {
            "step": 4,
            "command": "create.branch",
            "path": "feature/test"
        },
        {
            "step": 5,
            "command": "commit",
            "content": base64.b64encode("test commit".encode()).decode()
        },
        {
            "step": 6,
            "command": "push",
        },
    ]

    print(f"🚀 Eseguo {len(test_commands)} comandi di test...")

    try:
        gateway = GitHubGateway()

        # Esegui i comandi - l'autenticazione avverrà automaticamente se necessaria
        result = gateway.process_commands(test_commands)

        print("\n📊 Risultati:")
        for step, step_result in result.items():
            status = "✅" if step_result.get("success", False) else "❌"
            message = step_result.get("message", "N/A")
            print(f"   {status} Step {step}: {message}")

        return result

    except Exception as e:
        print(f"❌ Errore durante l'esecuzione: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Funzione principale per il test"""
    print("🧪 Test Estensione GitHub Copilot")
    print("=" * 60)
    print("🆕 Sistema di autenticazione OAuth automatico")
    print()

    # Test 1: Verifica credenziali OAuth
    auth_success = test_oauth_authentication()

    if auth_success:
        # Test 2: Esegui comandi con OAuth
        result = test_commands_with_oauth()

        if result:
            print("\n🎉 Test completato con successo!")
        else:
            print("\n❌ Test fallito durante l'esecuzione dei comandi")
    else:
        print("\n❌ Test interrotto: configura prima le credenziali OAuth nel file .env")
        print("\n🔧 Passaggi per configurare:")
        print("   1. Vai su https://github.com/settings/developers")
        print("   2. Clicca sulla tua OAuth App")
        print("   3. Copia Client ID e Client Secret")
        print("   4. Incollali nel file .env")

    print("\n" + "=" * 60)
    print("🏁 Test terminato!")
    print()
    print("💡 Ricorda:")
    print("   - L'autenticazione avviene automaticamente tramite browser")
    print("   - Non serve più fornire token manuali")
    print("   - L'autorizzazione viene richiesta solo la prima volta")


if __name__ == "__main__":
    main()
