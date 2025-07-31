# GitHub Copilot Extension - Pseudo Script Commands

Un'estensione avanzata di GitHub Copilot che converte comandi pseudo script in operazioni reali su repository GitHub, con autenticazione OAuth automatica e interfacce tipizzate per client esterni.

## 🚀 Caratteristiche Principali

- **🔐 Autenticazione OAuth Automatica**: Sistema di autenticazione trasparente che si attiva al primo utilizzo
- **📝 Interfacce Tipizzate**: API completamente tipizzata con validazione rigorosa dei comandi
- **🌐 API REST per GitHub Copilot**: Server Flask integrato per l'uso come estensione `@` in GitHub Copilot
- **🔍 Ricerca Avanzata**: Ricerca file per nome, estensione o contenuto con pattern intelligenti
- **📂 Gestione File Completa**: Creazione, lettura, modifica, eliminazione con supporto encoding UTF-8
- **🌳 Operazioni Git Complete**: Branch, commit, push con gestione automatica upstream
- **🧹 Clone Temporaneo Intelligente**: Gestione automatica di repository locali con pulizia preventiva
- **✅ Validazione Robusta**: Controllo di integrità multilivello per tutti i comandi
- **🔄 Gestione Errori Avanzata**: Messaggi di errore dettagliati e recovery automatico

## 📋 Comandi Supportati

### **File Operations**

| Comando | Descrizione | Parametri | Esempio |
|---------|-------------|-----------|---------|
| `create.file` | Crea un file con contenuto | `path`, `content` (base64) | Crea file con cartelle automatiche |
| `read.file` | Legge il contenuto di un file | `path` | Restituisce contenuto completo |
| `modify.file` | Modifica un file esistente | `path`, `content` (base64) | Supporta `append:` e `replace:` |
| `delete.file` | Elimina un file | `path` | Rimozione sicura |

### **Ricerca Avanzata**

| Comando | Tipo | Parametri | Descrizione |
|---------|------|-----------|-------------|
| `search.file` | Per nome (default) | `content`: `"nome_file"` | Ricerca nel nome del file |
| `search.file` | Per estensione | `content`: `"ext:.py"` | Ricerca per estensione |
| `search.file` | Nel contenuto | `content`: `"content:import os"` | Ricerca nel contenuto dei file |

### **Git Operations**

| Comando | Descrizione | Parametri | Note |
|---------|-------------|-----------|------|
| `pull` | Esegue pull dal repository remoto | - | Sincronizza automaticamente |
| `commit` | Crea un commit | `content` (messaggio, base64) | Con autore configurato |
| `push` | Esegue push verso il repository remoto | - | Gestione automatica upstream |
| `create.branch` | Crea un nuovo branch | `content` (nome, base64) | Branch locale + remoto |
| `switch.branch` | Cambia branch corrente | `content` (nome, base64) | Switch sicuro |
| `clone` | Clona il repository localmente | - | Auto-eseguito all'inizializzazione |

## 🏗️ Architettura del Progetto

```
├── README.md                           # Documentazione principale
├── requirements.txt                    # Dipendenze Python
├── test_extension.py                   # Test completo con OAuth
├── copilot_api.py                      # 🆕 API Server per GitHub Copilot
├── copilot-extension.yml               # 🆕 Configurazione estensione
├── Procfile                            # 🆕 Deploy configuration
├── .env                                # Credenziali OAuth (non in git)
├── docs/
│   └── TECHNICAL_GUIDE.md             # Guida tecnica dettagliata
├── examples/
│   └── sample_commands.json          # Esempi di comandi
├── src/
│   ├── gateway.py                     # 🔄 Gateway principale con interfacce tipizzate
│   ├── main.py                        # Entry point dell'estensione
│   ├── auth/
│   │   └── github_auth.py             # 🔄 Autenticazione OAuth automatica
│   ├── operations/
│   │   ├── file_operations.py         # 🔄 Operazioni file complete
│   │   └── git_operations.py          # 🔄 Operazioni Git avanzate
│   └── types/
│       ├── command_types.py           # 🔄 Enum e validazione avanzata
│       ├── validator.py               # 🔄 Validazione multilivello
│       └── gateway_interfaces.py      # 🆕 Interfacce tipizzate per client esterni
└── temp_repos/                        # Directory clone temporanei (auto-gestita)
```

## 📦 Installazione e Setup

### **1. Installazione Locale**

```bash
# 1. Clona il repository
git clone https://github.com/giuseppe-dacunzo-sisal/test-comandi-github.git
cd test-comandi-github

# 2. Crea ambiente virtuale
python -m venv .venv

# 3. Attiva ambiente (Windows)
.venv\Scripts\activate

# 4. Installa dipendenze
pip install -r requirements.txt

# 5. Configura OAuth (vedi sezione OAuth Setup)
cp .env.example .env
# Modifica .env con le tue credenziali
```

### **2. Configurazione OAuth**

1. **Crea GitHub OAuth App**:
   - Vai su https://github.com/settings/developers
   - Clicca "New OAuth App"
   - **Application name**: `GitHub Commands Extension`
   - **Homepage URL**: `https://github.com/your-username/your-repo`
   - **Authorization callback URL**: `http://localhost:8080/callback`

2. **Configura credenziali nel file `.env`**:
   ```env
   GITHUB_CLIENT_ID=your_actual_client_id_here
   GITHUB_CLIENT_SECRET=your_actual_client_secret_here
   FLASK_SECRET_KEY=your_secure_random_key_here
   ```

## 🧪 Test e Utilizzo

### **Test Locale**

```bash
# Test completo con OAuth
python test_extension.py

# Test API server
python copilot_api.py
```

### **Utilizzo come Libreria**

```python
from src.gateway import GitHubGateway
from src.types.gateway_interfaces import CommandInput, GatewayResponse

# Inizializza gateway
gateway = GitHubGateway()

# Definisci comandi tipizzati
commands: list[CommandInput] = [
    {
        "step": 1,
        "command": "create.file",
        "path": "test.txt",
        "content": base64.b64encode("Hello World!".encode()).decode()
    },
    {
        "step": 2,
        "command": "search.file",
        "content": base64.b64encode("README".encode()).decode()
    }
]

# Esegui comandi
result: GatewayResponse = gateway.process_commands(commands)
print(f"Successo: {result['success']}")
```

### **Utilizzo come API REST**

```bash
# Avvia server API
python copilot_api.py

# Test con curl
curl -X POST http://localhost:5000/api/copilot/execute \
  -H "Content-Type: application/json" \
  -d '{
    "commands": [
      {
        "step": 1,
        "command": "create.file",
        "path": "api-test.txt",
        "content": "SGVsbG8gZnJvbSBBUEkh"
      }
    ]
  }'
```

## 🔧 Deploy come GitHub Copilot Extension

### **1. Deploy su Heroku**

```bash
# Installa Heroku CLI e login
heroku login

# Crea app
heroku create github-commands-extension

# Configura variabili d'ambiente
heroku config:set GITHUB_CLIENT_ID=your_client_id
heroku config:set GITHUB_CLIENT_SECRET=your_client_secret
heroku config:set FLASK_SECRET_KEY=your_secret_key

# Deploy
git add .
git commit -m "Deploy GitHub Copilot Extension"
git push heroku main
```

### **2. Registrazione in GitHub Marketplace**

1. Vai su https://github.com/marketplace/manage
2. Crea nuova GitHub App con:
   - **Webhook URL**: `https://your-app.herokuapp.com/api/copilot/execute`
   - **Permissions**: Repository Read/Write per Contents e Metadata

### **3. Utilizzo in GitHub Copilot**

```
@github-commands execute create.file "test.py" with content "print('Hello from Copilot!')"
@github-commands search files containing "import os"
@github-commands create branch "feature/new-feature"
```

## 🎯 Funzionalità Avanzate

### **Convenzioni per Tipi di Operazione**

- **Ricerca**: `"README"` (nome), `"ext:.py"` (estensione), `"content:import"` (contenuto)
- **Modifica**: `"replace:nuovo_contenuto"` (sostituisce), `"append:\nnuova_riga"` (aggiunge)

### **Gestione Automatica Repository**

- **Auto-rilevamento**: Repository corrente da `.git`
- **Clone temporaneo**: In `./temp_repos/` con pulizia automatica
- **Sincronizzazione**: Pull automatico prima delle operazioni

### **Validazione Multilivello**

- **Struttura comandi**: Validazione di tipo e formato
- **Parametri richiesti**: Controllo campi obbligatori per comando
- **Permessi repository**: Verifica accesso lettura/scrittura
- **Integrità file**: Controllo esistenza e encoding

## 🔍 Troubleshooting

### **Errori Comuni**

1. **"OAuth non configurato"**: Verifica credenziali in `.env`
2. **"Repository non trovato"**: Esegui da directory con `.git`
3. **"Permission denied"**: Verifica permessi GitHub OAuth App
4. **"Command validation failed"**: Controlla sintassi comandi

### **Debug Mode**

```bash
# Abilita debug dettagliato
export FLASK_DEBUG=true
python copilot_api.py
```

## 🤝 Contribuire

1. Fork del repository
2. Crea branch per feature: `git checkout -b feature/nome-feature`
3. Commit delle modifiche: `git commit -m 'Add: nuova feature'`
4. Push del branch: `git push origin feature/nome-feature`
5. Apri Pull Request

## 📄 Licenza

Questo progetto è licenziato sotto MIT License - vedi il file [LICENSE](LICENSE) per i dettagli.

## 🔗 Link Utili

- **Repository**: https://github.com/giuseppe-dacunzo-sisal/test-comandi-github
- **Issues**: https://github.com/giuseppe-dacunzo-sisal/test-comandi-github/issues
- **GitHub Copilot Extensions**: https://docs.github.com/en/copilot/building-copilot-extensions
- **OAuth Apps**: https://docs.github.com/en/developers/apps/building-oauth-apps
