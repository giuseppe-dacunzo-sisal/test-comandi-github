# 🚀 Guida Configurazione GitHub App Pubblica

## Passo 1: Registrazione GitHub App

### 1.1 Accesso al Portale GitHub
1. Vai su **https://github.com/settings/apps**
2. Clicca **"New GitHub App"**

### 1.2 Configurazione Generale
```
App name: GitHub Copilot Commands Extension
Description: Automazione comandi GitHub tramite pseudo-script per GitHub Copilot
Homepage URL: https://github.com/giuseppe-dacunzo-sisal/test-comandi-github
User authorization callback URL: https://your-app-domain.herokuapp.com/auth/callback
```

### 1.3 Identificazione e Chiavi
- **Client ID**: Verrà generato automaticamente (copialo nel .env)
- **Client Secret**: Genera e copia nel .env
- **Webhook Secret**: Genera un secret sicuro e copialo nel .env

### 1.4 Configurazione Webhook
```
Webhook URL: https://your-app-domain.herokuapp.com/webhook
Webhook secret: il-secret-che-hai-generato
SSL verification: Enabled
```

### 1.5 Repository Permissions
Imposta le seguenti permissions:
```
✅ Contents: Read & Write
   - Necessario per creare, modificare, eliminare file

✅ Metadata: Read
   - Necessario per accedere alle informazioni del repository

✅ Pull requests: Read & Write
   - Opzionale, se vuoi gestire PR in futuro

✅ Issues: Read & Write
   - Opzionale, se vuoi gestire issues in futuro
```

### 1.6 Account Permissions
```
✅ Email addresses: Read
   - Necessario per configurare git con l'email dell'utente
```

### 1.7 Subscribe to Events (Webhook)
Seleziona questi eventi per ricevere notifiche:
```
✅ Installation
✅ Installation repositories
✅ Repository
```

### 1.8 Configurazione Features
```
✅ Device flow: ENABLED (FONDAMENTALE!)
✅ Webhook: Active
```

### 1.9 Installazione
```
Where can this GitHub App be installed?: Any account
```

## Passo 2: Deploy su Heroku

### 2.1 Preparazione Heroku
```bash
# Installa Heroku CLI se non ce l'hai
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Crea app Heroku
heroku create your-github-copilot-extension

# Aggiungi buildpack Python
heroku buildpacks:set heroku/python
```

### 2.2 Configurazione Variabili Ambiente
```bash
# Configura le variabili ambiente su Heroku
heroku config:set GITHUB_CLIENT_ID=your_client_id_from_github_app
heroku config:set GITHUB_CLIENT_SECRET=your_client_secret_from_github_app
heroku config:set GITHUB_WEBHOOK_SECRET=your_webhook_secret
heroku config:set SECRET_KEY=your_flask_secret_key
heroku config:set FLASK_ENV=production
heroku config:set APP_BASE_URL=https://your-github-copilot-extension.herokuapp.com
```

### 2.3 Deploy
```bash
# Aggiungi git remote se non esiste
heroku git:remote -a your-github-copilot-extension

# Deploy
git add .
git commit -m "Deploy GitHub App pubblica"
git push heroku main
```

### 2.4 Verifica Deploy
```bash
# Controlla logs
heroku logs --tail

# Verifica salute app
curl https://your-github-copilot-extension.herokuapp.com/health
```

## Passo 3: Aggiorna Configurazione GitHub App

Dopo il deploy, torna sulla GitHub App e aggiorna:

### 3.1 URL Webhook
```
Webhook URL: https://your-github-copilot-extension.herokuapp.com/webhook
```

### 3.2 Callback URL
```
User authorization callback URL: https://your-github-copilot-extension.herokuapp.com/auth/callback
```

## Passo 4: Test Installazione

### 4.1 Installa l'App
1. Vai sulla pagina della tua GitHub App
2. Clicca **"Install App"**
3. Scegli l'account/organizzazione
4. Seleziona repository (tutti o specifici)

### 4.2 Test API
```bash
# Test health check
curl https://your-github-copilot-extension.herokuapp.com/health

# Test avvio autenticazione
curl -X POST https://your-github-copilot-extension.herokuapp.com/auth/start \
  -H "Content-Type: application/json" \
  -d '{
    "repo_owner": "tuo-username",
    "repo_name": "tuo-repo",
    "user_id": "tuo-github-user-id"
  }'
```

## Passo 5: Integrazione con GitHub Copilot

### 5.1 Endpoint per GitHub Copilot
La tua app espone questi endpoint:

```
POST /auth/start
- Avvia autenticazione device flow per un repository

GET /auth/status/{session_id}
- Controlla stato autenticazione

POST /commands/execute
- Esegue comandi per un repository autenticato

POST /auth/logout
- Logout e cleanup
```

### 5.2 Utilizzo da GitHub Copilot Chat
Una volta deployata, l'estensione potrà essere richiamata da GitHub Copilot con:

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

## Variabili Ambiente Richieste

### Produzione (.env o Heroku Config)
```env
GITHUB_CLIENT_ID=Iv1.abc123def456
GITHUB_CLIENT_SECRET=abc123def456ghi789
GITHUB_WEBHOOK_SECRET=your-secure-webhook-secret
SECRET_KEY=your-flask-secret-key-for-sessions
APP_BASE_URL=https://your-github-copilot-extension.herokuapp.com
FLASK_ENV=production
LOG_LEVEL=INFO
```

## Troubleshooting

### Errore 403 su Webhook
- Verifica che GITHUB_WEBHOOK_SECRET sia configurato correttamente
- Controlla che l'URL webhook sia raggiungibile

### Errore Device Flow
- Verifica che Device Flow sia abilitato nella GitHub App
- Controlla che GITHUB_CLIENT_ID sia corretto

### Errore Permissions
- Verifica che l'app sia installata sul repository
- Controlla che le permissions siano configurate correttamente

## Monitoraggio

### Logs Heroku
```bash
heroku logs --tail -a your-github-copilot-extension
```

### Metriche
```bash
heroku ps -a your-github-copilot-extension
heroku releases -a your-github-copilot-extension
```
