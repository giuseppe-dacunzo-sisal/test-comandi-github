# GitHub Copilot Extension - Automazione Comandi GitHub

Un'estensione GitHub App pubblica che permette di automatizzare operazioni Git e GitHub attraverso comandi pseudo-script, utilizzabile direttamente da GitHub Copilot su qualsiasi repository.

## 🚀 Caratteristiche Principali

- **GitHub App Pubblica**: Installabile su qualsiasi repository GitHub
- **Autenticazione Device Flow**: Autenticazione sicura senza token pre-configurati
- **Multi-Repository**: Gestisce sessioni multiple per utenti e repository diversi
- **Rilevamento Automatico**: Rileva automaticamente il repository dal contesto GitHub Copilot
- **Configurazione Git Automatica**: Configura automaticamente nome e email dall'utente GitHub
- **Deploy Cloud**: Pronta per deployment su Heroku, AWS, Azure
- **Modalità Standalone**: Utilizzabile anche come applicazione indipendente per test

## 🏗️ Architettura

```
src/
├── main.py                    # Entry point principale
├── config.py                  # Configurazione per deployment
├── gateway.py                 # Gateway per processamento comandi
├── auth/
│   ├── device_flow_auth.py    # Autenticazione Device Flow
│   └── github_app.py          # GitHub App pubblica con webhook
├── operations/
│   ├── file_operations.py     # Operazioni sui file
│   └── git_operations.py      # Operazioni Git
└── types/
    ├── command_types.py       # Enum e tipi dei comandi
    ├── interfaces.py          # Interfacce per API
    └── validator.py           # Validazione comandi
```

## 📦 Installazione e Setup

### Prerequisiti
- Python 3.11+
- Git installato
- Account GitHub
- Heroku CLI (per deployment)

### Setup Locale per Sviluppo

1. **Clona il repository**
```bash
git clone https://github.com/giuseppe-dacunzo-sisal/test-comandi-github.git
cd test-comandi-github
```

2. **Crea ambiente virtuale**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. **Installa dipendenze**
```bash
pip install -r requirements.txt
```

## 🚀 Deploy GitHub App Pubblica

### Passo 1: Registra GitHub App

1. Vai su **https://github.com/settings/apps**
2. Clicca **"New GitHub App"**
3. Configura come indicato in `docs/GITHUB_APP_SETUP.md`

### Passo 2: Deploy su Heroku

```bash
# Crea app Heroku
heroku create your-github-copilot-extension

# Configura variabili ambiente
heroku config:set GITHUB_CLIENT_ID=your_client_id
heroku config:set GITHUB_CLIENT_SECRET=your_client_secret
heroku config:set GITHUB_WEBHOOK_SECRET=your_webhook_secret
heroku config:set SECRET_KEY=your_flask_secret
heroku config:set FLASK_ENV=production

# Deploy
git push heroku main
```

### Passo 3: Configura Webhook

Aggiorna la GitHub App con:
```
Webhook URL: https://your-app.herokuapp.com/webhook
```

## 🔧 Utilizzo

### Modalità GitHub App (Produzione)

Una volta deployata e installata su un repository, l'app è utilizzabile tramite GitHub Copilot:

```
@github-copilot-commands esegui questi comandi:
[
  {
    "step": 1,
    "command": "create.file",
    "path": "src/nuovo.py", 
    "content": "cHJpbnQoIkhlbGxvIFdvcmxkIik="
  }
]
```

### Modalità Standalone (Sviluppo/Test)

#### Test Autenticazione
```bash
python copilot_extension.py auth
```

#### Esecuzione da File
```bash
python copilot_extension.py run --file examples/sample_commands.json
```

#### Modalità Interattiva
```bash
python copilot_extension.py run --interactive
```

#### Avvio Server Locale per Test
```bash
python copilot_extension.py app --port 3000
```

## 📝 Comandi Supportati

### File Operations
- `create.file path/filename contenuto` - Crea file con contenuto
- `read.file path/filename` - Legge contenuto file
- `modify.file path/filename contenuto` - Modifica file
- `modify.file path/filename (append) contenuto` - Aggiunge contenuto
- `delete.file path/filename` - Elimina file
- `search.file name:filename` - Cerca per nome
- `search.file ext:.py` - Cerca per estensione
- `search.file content:testo` - Cerca per contenuto

### Git Operations
- `pull` - Pull del repository
- `commit -m "messaggio"` - Commit con messaggio
- `push` - Push al repository remoto
- `create.branch nome-branch` - Crea nuovo branch
- `switch.branch nome-branch` - Cambia branch
- `clone` - Clona repository (automatico in GitHub App)

## 🔗 Formato Comandi JSON

```json
[
  {
    "step": 1,
    "command": "create.file",
    "path": "src/nuovo_file.py",
    "content": "cHJpbnQoIkhlbGxvIFdvcmxkIik="
  },
  {
    "step": 2,
    "command": "commit", 
    "content": "QWdnaXVudG8gbnVvdm8gZmlsZQ=="
  },
  {
    "step": 3,
    "command": "push"
  }
]
```

**Note:**
- `content` deve essere codificato in Base64
- `path` è opzionale per alcuni comandi (pull, push, clone)
- `content` è opzionale per comandi senza payload

## 🌐 API Endpoints (GitHub App)

La GitHub App espone questi endpoint REST:

```
POST /auth/start
Body: {"repo_owner": "user", "repo_name": "repo", "user_id": "123"}
- Avvia autenticazione device flow per repository specifico

GET /auth/status/{session_id}
- Controlla stato autenticazione

POST /commands/execute  
Body: {"repo_owner": "user", "repo_name": "repo", "user_id": "123", "commands": [...]}
- Esegue comandi per repository autenticato

POST /webhook
- Gestisce eventi GitHub (installazione, repository)

GET /health
- Health check dell'applicazione
```

## 🔐 Sicurezza e Autenticazione

### Device Flow Authentication
1. **Avvio**: L'app genera device code e user code
2. **Autorizzazione**: L'utente va su GitHub e inserisce il codice
3. **Polling**: L'app attende l'autorizzazione
4. **Token**: Riceve access token e configura client GitHub

### Multi-Tenancy
- Ogni utente/repository ha sessione indipendente
- Gestione automatica scadenze sessioni
- Cleanup automatico risorse

## 📊 Monitoraggio

### Logs Heroku
```bash
heroku logs --tail -a your-app-name
```

### Metriche
```bash
heroku ps -a your-app-name
heroku releases -a your-app-name
```

## 🔍 Esempi Avanzati

### Workflow Completo Feature Branch
```json
[
  {"step": 1, "command": "create.branch", "path": "feature/new-api"},
  {"step": 2, "command": "switch.branch", "path": "feature/new-api"},
  {"step": 3, "command": "create.file", "path": "api/endpoint.py", "content": "..."},
  {"step": 4, "command": "commit", "content": "QWdnaXVudG8gQVBJ"},
  {"step": 5, "command": "push"}
]
```

### Refactoring Multipli File
```json
[
  {"step": 1, "command": "modify.file", "path": "src/main.py", "content": "..."},
  {"step": 2, "command": "modify.file", "path": "src/utils.py", "content": "..."},
  {"step": 3, "command": "delete.file", "path": "src/deprecated.py"},
  {"step": 4, "command": "commit", "content": "UmVmYWN0b3Jpbmc="},
  {"step": 5, "command": "push"}
]
```

## 🚨 Risoluzione Problemi

### Errore Device Flow
- Verifica che Device Flow sia abilitato nella GitHub App
- Controlla `GITHUB_CLIENT_ID` nelle variabili ambiente

### Errore Permissions
- Verifica che l'app sia installata sul repository
- Controlla permissions nella configurazione GitHub App

### Errore Webhook
- Verifica `GITHUB_WEBHOOK_SECRET` nelle variabili ambiente
- Controlla che l'URL webhook sia raggiungibile

## 📄 Documentazione Aggiuntiva

- `docs/GITHUB_APP_SETUP.md` - Guida dettagliata setup GitHub App
- `docs/TECHNICAL_GUIDE.md` - Guida tecnica architettura
- `examples/sample_commands.json` - Esempi comandi

## 🤝 Contribuire

1. Fork del repository
2. Crea feature branch (`git checkout -b feature/amazing-feature`)
3. Commit modifiche (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Apri Pull Request

## 📄 Licenza

Progetto rilasciato sotto licenza MIT. Vedi `LICENSE` per dettagli.

## 📞 Supporto

Per supporto e bug reports, apri un issue su GitHub o contatta il team di sviluppo.
