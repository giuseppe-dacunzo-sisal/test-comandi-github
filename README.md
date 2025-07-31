# GitHub Copilot Extension - Pseudo Script Commands

Un'estensione di GitHub Copilot che converte comandi pseudo script in operazioni reali su repository GitHub.

## 🚀 Caratteristiche

- **Conversione comandi**: Trasforma comandi pseudo script in operazioni GitHub
- **Autenticazione OAuth**: Gestione sicura dell'accesso ai repository
- **Operazioni complete**: Supporto per file operations e Git operations
- **Validazione robusta**: Controllo di integrità per tutti i comandi
- **Clone locale**: Lavora su copie temporanee locali del repository

## 📋 Comandi Supportati

| Comando | Descrizione | Parametri |
|---------|-------------|-----------|
| `create.file` | Crea un file con contenuto | `path`, `content` (base64) |
| `search.file` | Ricerca file per nome/estensione/contenuto | `content` (termine ricerca) |
| `read.file` | Legge il contenuto di un file | `path` |
| `modify.file` | Modifica un file esistente | `path`, `content` (base64) |
| `delete.file` | Elimina un file | `path` |
| `pull` | Esegue pull dal repository remoto | - |
| `commit` | Crea un commit | `content` (messaggio, base64) |
| `push` | Esegue push verso il repository remoto | - |
| `create.branch` | Crea un nuovo branch | `path` (nome branch) |
| `switch.branch` | Cambia branch corrente | `path` (nome branch) |
| `clone` | Clona il repository localmente | - |

## 🏗️ Struttura del Progetto

```
src/
├── gateway.py              # Gateway principale
├── main.py                 # Entry point dell'estensione
├── auth/
│   └── github_auth.py      # Gestione autenticazione OAuth
├── operations/
│   ├── file_operations.py  # Operazioni sui file
│   └── git_operations.py   # Operazioni Git
└── types/
    ├── command_types.py     # Enum e interfacce comandi
    └── validator.py         # Validazione comandi
```

## 📦 Installazione

1. **Clona il repository**:
   ```bash
   git clone <repository-url>
   cd test-comandi-github
   ```

2. **Installa le dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configura il token GitHub**:
   ```bash
   export GITHUB_TOKEN="your_github_token"
   ```

## 🔧 Utilizzo

### Utilizzo Programmatico

```python
from src.gateway import GitHubCopilotGateway

# Inizializza il gateway
gateway = GitHubCopilotGateway()

# Lista di comandi
commands = [
    {
        "step": 1,
        "command": "create.file",
        "path": "hello.py",
        "content": "cHJpbnQoIkhlbGxvLCBXb3JsZCEiKQ=="  # base64 di 'print("Hello, World!")'
    },
    {
        "step": 2,
        "command": "commit",
        "content": "QWdnaXVudG8gZmlsZSBoZWxsby5weQ=="  # base64 di "Aggiunto file hello.py"
    }
]

# Esegui i comandi
result = gateway.run("your_token", "/path/to/workspace", commands)
```

### Utilizzo da Command Line

```bash
python src/main.py --token "your_token" --workspace "." --commands examples/sample_commands.json
```

## 📝 Formato Comandi

Ogni comando deve seguire questa struttura:

```json
{
  "step": 1,
  "command": "create.file",
  "path": "optional/path",
  "content": "optional_base64_content"
}
```

### Parametri:
- **step**: Numero progressivo del comando (obbligatorio)
- **command**: Tipo di comando (vedi enum CommandType)
- **path**: Path del file o nome del branch (opzionale)
- **content**: Contenuto codificato in base64 (opzionale)

## 🔍 Esempi di Ricerca

### Ricerca per nome file:
```json
{
  "command": "search.file",
  "content": "bmFtZTpbZXhhbXBsZQ=="  // base64 di "name:*example*"
}
```

### Ricerca per estensione:
```json
{
  "command": "search.file",
  "content": "ZXh0Oi5weQ=="  // base64 di "ext:.py"
}
```

### Ricerca nel contenuto:
```json
{
  "command": "search.file",
  "content": "Y29udGVudDpwcmludA=="  // base64 di "content:print"
}
```

## 🧪 Test

Esegui i test dell'estensione:

```bash
python test_extension.py
```

Il test verificherà:
- Validazione dei comandi
- Autenticazione GitHub
- Operazioni sui file
- Operazioni Git

## 🔐 Sicurezza

- **OAuth**: L'estensione usa autenticazione OAuth per GitHub
- **Permessi**: Verifica automaticamente i permessi sul repository
- **Sandboxing**: Le operazioni avvengono su clone locali temporanei
- **Validazione**: Tutti i comandi vengono validati prima dell'esecuzione

## 🌟 Caratteristiche Avanzate

### Gestione Directory
Se durante `create.file` il path contiene directory inesistenti, vengono create automaticamente.

### Modalità Append
Per `modify.file`, aggiungi `(append)` al path per aggiungere contenuto invece di sostituire:
```json
{
  "command": "modify.file",
  "path": "file.txt (append)",
  "content": "base64_content"
}
```

### Sincronizzazione Automatica
Dopo ogni `commit` + `push`, il repository locale viene automaticamente aggiornato.

## 🚨 Gestione Errori

L'estensione gestisce vari tipi di errore:
- Comandi malformati
- File non trovati
- Permessi insufficienti
- Errori di rete
- Conflitti Git

Ogni operazione restituisce un oggetto con:
```json
{
  "success": true/false,
  "message": "Descrizione dell'operazione",
  "error": "Dettagli errore (se presente)"
}
```

## 🤝 Contribuire

1. Fork del progetto
2. Crea un feature branch
3. Commit delle modifiche
4. Push del branch
5. Apri una Pull Request

## 📄 Licenza

MIT License - vedi il file LICENSE per i dettagli.

