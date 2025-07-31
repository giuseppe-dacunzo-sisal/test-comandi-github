# 📚 Guida Tecnica Completa - GitHub Copilot Extension

## 🎯 Panoramica Architetturale

L'estensione GitHub Copilot è stata completamente riscritta con un'architettura modulare avanzata basata su sei componenti principali:

1. **🔐 Auth Manager**: Gestisce autenticazione OAuth automatica e identificazione repository
2. **📂 File Operations Manager**: Gestisce operazioni complete sui file con ricerca avanzata  
3. **🌳 Git Operations Manager**: Gestisce operazioni Git/GitHub con gestione upstream automatica
4. **🚪 Gateway**: Orchestratore principale con interfacce tipizzate per client esterni
5. **✅ Validator**: Sistema di validazione multilivello per comandi e parametri
6. **🌐 API Server**: Server Flask per integrazione con GitHub Copilot (`@` commands)

---

## 🔍 1. SISTEMA DI AUTENTICAZIONE OAUTH AUTOMATICA

### 1.1 Flusso di Autenticazione

Il sistema implementa un flusso OAuth completamente automatizzato che si attiva al primo utilizzo:

```python
# File: src/auth/github_auth.py - metodo start_oauth_flow()

def start_oauth_flow(self) -> Dict[str, Any]:
    """
    STEP 1: Genera state e challenge per sicurezza PKCE
    STEP 2: Costruisce URL di autorizzazione GitHub
    STEP 3: Avvia server locale temporaneo per callback
    STEP 4: Apre browser automaticamente per autorizzazione
    STEP 5: Intercetta callback e scambia code con access_token
    STEP 6: Memorizza token per usi futuri
    """
```

### 1.2 Identificazione Automatica Repository

```python
def detect_current_repository(self, workspace_path: str) -> Dict[str, Any]:
    """
    ALGORITMO DI RILEVAMENTO:
    1. Scansiona directory corrente per .git/
    2. Legge configurazione remote 'origin'
    3. Parsing URL GitHub (HTTPS/SSH)
    4. Estrazione owner/repo dal path
    5. Validazione esistenza repository via API
    6. Cache delle informazioni per performance
    """
    
    repo = Repo(workspace_path)
    origin_url = repo.remotes.origin.url
    
    # Supporta entrambi i formati:
    # HTTPS: https://github.com/owner/repo.git
    # SSH: git@github.com:owner/repo.git
    
    if origin_url.startswith('git@'):
        # Parsing SSH format
        match = re.match(r'git@github\.com:(.+)/(.+)\.git', origin_url)
    else:
        # Parsing HTTPS format  
        parsed = urlparse(origin_url)
        path_parts = parsed.path.strip('/').replace('.git', '').split('/')
        
    return {
        "owner": owner,
        "repo": repo_name,
        "full_name": f"{owner}/{repo_name}",
        "clone_url": origin_url,
        "local_path": workspace_path
    }
```

### 1.3 Gestione Token e Sicurezza

```python
class TokenManager:
    def __init__(self):
        self.token_file = os.path.join(os.path.expanduser("~"), ".github_copilot_extension_token")
    
    def save_token(self, token: str, expires_in: int):
        """Salva token crittografato con scadenza"""
        token_data = {
            "access_token": self._encrypt_token(token),
            "expires_at": time.time() + expires_in,
            "created_at": time.time()
        }
        
    def is_token_valid(self) -> bool:
        """Verifica validità token senza chiamate API"""
        return self.token_data and time.time() < self.token_data["expires_at"]
```

---

## 📂 2. SISTEMA DI GESTIONE FILE AVANZATO

### 2.1 Architettura File Operations Manager

```python
# File: src/operations/file_operations.py

class FileOperationsManager:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)  # Path del clone locale
        
    # OPERAZIONI BASE
    def create_file(self, file_path: str, content: str) -> Dict[str, Any]
    def read_file(self, file_path: str) -> Dict[str, Any]  
    def modify_file(self, file_path: str, content: str) -> Dict[str, Any]
    def append_to_file(self, file_path: str, content: str) -> Dict[str, Any]
    def delete_file(self, file_path: str) -> Dict[str, Any]
    
    # RICERCA AVANZATA
    def search_files_by_name(self, query: str) -> List[Dict[str, Any]]
    def search_files_by_extension(self, extension: str) -> List[Dict[str, Any]]  
    def search_files_by_content(self, query: str) -> List[Dict[str, Any]]
```

### 2.2 Sistema di Ricerca Intelligente

Il sistema implementa tre tipi di ricerca con ottimizzazioni specifiche:

```python
def search_files_by_content(self, query: str) -> List[Dict[str, Any]]:
    """
    ALGORITMO DI RICERCA NEL CONTENUTO:
    1. Decodifica query da base64 se necessario
    2. Filtra solo file di testo (estensioni whitelist)
    3. Ricerca ricorsiva con glob patterns
    4. Match case-insensitive nel contenuto
    5. Raccolta righe matching con numeri di linea
    6. Limitazione risultati per performance
    """
    
    text_extensions = ['.txt', '.py', '.js', '.html', '.css', '.md', 
                      '.json', '.yml', '.yaml', '.xml', '.csv']
    
    results = []
    for file_path in self.base_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in text_extensions:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                if decoded_query.lower() in content.lower():
                    # Trova righe specifiche che contengono la query
                    matching_lines = self._extract_matching_lines(content, decoded_query)
                    
                    results.append({
                        "path": str(file_path.relative_to(self.base_path)),
                        "name": file_path.name,
                        "size": file_path.stat().st_size,
                        "matches": matching_lines[:5]  # Limite per performance
                    })
            except (UnicodeDecodeError, PermissionError):
                continue  # Ignora file binari o inaccessibili
                
    return results
```

### 2.3 Gestione Encoding e Formato File

```python
def _handle_file_encoding(self, file_path: Path, content: str) -> str:
    """
    GESTIONE ENCODING INTELLIGENTE:
    1. Detection automatico encoding esistente
    2. Preservazione formato (CR/LF, indentazione)
    3. Conversione sicura a UTF-8
    4. Backup automatico per file critici
    """
    
    # Detection encoding esistente
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        detected = chardet.detect(raw_data)
        original_encoding = detected['encoding'] or 'utf-8'
    
    # Preservazione formato line ending
    if '\r\n' in content:
        line_ending = '\r\n'  # Windows
    elif '\n' in content:
        line_ending = '\n'    # Unix
    else:
        line_ending = os.linesep  # Sistema corrente
        
    return content.replace('\n', line_ending)
```

---

## 🌳 3. GESTIONE GIT OPERATIONS AVANZATA

### 3.1 Architettura Git Operations Manager

```python
# File: src/operations/git_operations.py

class GitOperationsManager:
    def __init__(self, local_repo_path: str, github_client: Github, 
                 repo_info: Dict[str, Any], access_token: str):
        self.local_repo = Repo(local_repo_path)
        self.github_client = github_client
        self.github_repo = github_client.get_repo(repo_info["full_name"])
        self.access_token = access_token
        
    # OPERAZIONI GIT LOCALI
    def commit(self, message: str) -> Dict[str, Any]
    def create_branch(self, branch_name: str) -> Dict[str, Any]
    def switch_branch(self, branch_name: str) -> Dict[str, Any]
    
    # OPERAZIONI REMOTE
    def pull(self) -> Dict[str, Any]  
    def push(self) -> Dict[str, Any]
    def _setup_upstream(self, branch_name: str) -> bool
```

### 3.2 Gestione Automatica Upstream

```python
def push(self) -> Dict[str, Any]:
    """
    ALGORITMO PUSH INTELLIGENTE:
    1. Verifica stato repository (clean/dirty)
    2. Controlla se branch esiste in remoto
    3. Setup automatico upstream se necessario
    4. Push con gestione errori specifici
    5. Retry automatico per conflitti temporanei
    """
    
    current_branch = self.local_repo.active_branch.name
    
    try:
        # Verifica se branch esiste in remoto
        remote_branches = [ref.name.split('/')[-1] for ref in self.local_repo.remotes.origin.refs]
        
        if current_branch not in remote_branches:
            # Primo push del branch - setup upstream
            self.local_repo.git.push('--set-upstream', 'origin', current_branch)
            return {
                "success": True,
                "message": f"Branch '{current_branch}' creato in remoto con upstream",
                "upstream_created": True
            }
        else:
            # Push normale
            self.local_repo.git.push('origin', current_branch)
            return {
                "success": True, 
                "message": f"Push completata sul branch '{current_branch}'",
                "upstream_created": False
            }
            
    except GitCommandError as e:
        if "non-fast-forward" in str(e):
            return {"success": False, "error": "Conflitti - esegui pull prima del push"}
        elif "Permission denied" in str(e):
            return {"success": False, "error": "Permessi insufficienti per push"}
        else:
            return {"success": False, "error": f"Errore push: {str(e)}"}
```

### 3.3 Sincronizzazione Automatica

```python
def pull(self) -> Dict[str, Any]:
    """
    ALGORITMO PULL SICURO:
    1. Stash modifiche locali se presenti
    2. Fetch degli ultimi cambiamenti
    3. Merge o rebase basato sulla configurazione
    4. Restore stash se applicabile
    5. Risoluzione conflitti automatica per file non critici
    """
    
    # Backup modifiche locali
    stash_created = False
    if self.local_repo.is_dirty():
        self.local_repo.git.stash('push', '-m', 'Auto-stash before pull')
        stash_created = True
    
    try:
        # Pull con strategia merge
        origin = self.local_repo.remotes.origin
        origin.pull()
        
        result = {
            "success": True,
            "message": "Pull completata con successo",
            "stash_created": stash_created
        }
        
        # Restore stash se creato
        if stash_created:
            try:
                self.local_repo.git.stash('pop')
                result["stash_restored"] = True
            except GitCommandError:
                result["stash_restored"] = False
                result["warning"] = "Stash non ripristinato - possibili conflitti"
                
        return result
        
    except GitCommandError as e:
        return {"success": False, "error": f"Errore durante pull: {str(e)}"}
```

---

## 🚪 4. GATEWAY E INTERFACCE TIPIZZATE

### 4.1 Architettura Gateway

```python
# File: src/gateway.py

class GitHubGateway:
    """
    RESPONSABILITÀ DEL GATEWAY:
    1. Orchestrazione dei componenti (Auth, File, Git)
    2. Validazione comandi multilivello
    3. Gestione errori centralizzata
    4. Interfacce tipizzate per client esterni
    5. Logging e monitoring delle operazioni
    """
    
    def __init__(self):
        self.auth_manager = GitHubAuthManager()
        self.file_manager = None  # Inizializzato dopo setup
        self.git_manager = None   # Inizializzato dopo setup
        self.is_initialized = False
```

### 4.2 Sistema di Interfacce Tipizzate

```python
# File: src/types/gateway_interfaces.py

class CommandInput(TypedDict):
    """Interfaccia rigorosa per comandi in input"""
    step: int                    # Numero progressivo comando
    command: str                 # Deve essere uno dei CommandType enum values
    path: Optional[str]          # Path file o parametro (opzionale)
    content: Optional[str]       # Contenuto base64 encoded (opzionale)

class CommandResult(TypedDict):
    """Interfaccia strutturata per risultati"""
    success: bool                # Status dell'operazione
    message: str                 # Messaggio descrittivo
    data: Optional[Any]          # Dati specifici del comando
    error: Optional[str]         # Dettagli errore se success=False

class GatewayResponse(TypedDict):
    """Interfaccia completa per risposta gateway"""
    success: bool                        # Successo generale
    message: str                         # Messaggio di riepilogo
    total_commands: int                  # Numero comandi ricevuti
    executed_commands: int               # Numero comandi processati
    results: Dict[int, CommandResult]    # Risultati per step
    repository_info: Optional[Dict[str, Any]]  # Info repository
```

### 4.3 Processo di Validazione Multilivello

```python
def process_commands(self, commands: List[CommandInput]) -> GatewayResponse:
    """
    PIPELINE DI VALIDAZIONE:
    
    LIVELLO 1 - Validazione Strutturale
    ├── Controllo tipo parametri (TypeError)
    ├── Validazione interfaccia CommandInput  
    └── Parsing e normalizzazione campi
    
    LIVELLO 2 - Validazione Comandi
    ├── Verifica comandi supportati (CommandValidator)
    ├── Controllo parametri richiesti per comando
    └── Validazione valori enum (CommandType, SearchType, ModifyType)
    
    LIVELLO 3 - Validazione Business Logic
    ├── Verifica autenticazione OAuth
    ├── Controllo permessi repository
    ├── Validazione paths e contenuti
    └── Verifica esistenza file per operazioni
    
    LIVELLO 4 - Esecuzione Sicura
    ├── Transazioni atomiche per gruppi di comandi
    ├── Rollback automatico in caso di errori critici
    ├── Logging dettagliato di tutte le operazioni
    └── Cleanup risorse in caso di interruzioni
    """
```

---

## ✅ 5. SISTEMA DI VALIDAZIONE AVANZATO

### 5.1 Validatore di Comandi

```python
# File: src/types/validator.py

class CommandValidator:
    @staticmethod
    def validate_command(command_dict: Dict[str, Any]) -> bool:
        """
        VALIDAZIONE COMANDO SINGOLO:
        1. Normalizzazione campi opzionali
        2. Creazione oggetto GitHubCommand tipizzato
        3. Validazione logica specifica per tipo comando
        4. Controllo consistenza parametri
        """
        
        normalized_dict = {
            "step": command_dict.get("step"),
            "command": command_dict.get("command"),  
            "path": command_dict.get("path"),      # None se omesso
            "content": command_dict.get("content") # None se omesso
        }
        
        command = GitHubCommand.from_dict(normalized_dict)
        return command.validate()
```

### 5.2 Validazione Specifica per Comando

```python
# File: src/types/command_types.py

def validate(self) -> bool:
    """
    VALIDAZIONE LOGICA PER TIPO COMANDO:
    
    FILE_OPERATIONS: Richiede path valido
    ├── CREATE_FILE: path + content opzionale
    ├── READ_FILE: solo path
    ├── MODIFY_FILE: path + content obbligatorio  
    └── DELETE_FILE: solo path
    
    SEARCH_OPERATIONS: Richiede content (query)
    └── SEARCH_FILE: content con pattern opzionali (ext:, content:, name:)
    
    GIT_OPERATIONS: Parametri variabili
    ├── COMMIT: content obbligatorio (messaggio)
    ├── CREATE_BRANCH/SWITCH_BRANCH: content O path (nome branch)
    └── PULL/PUSH/CLONE: nessun parametro richiesto
    """
    
    if self.command in [CommandType.CREATE_FILE, CommandType.READ_FILE,
                       CommandType.DELETE_FILE, CommandType.MODIFY_FILE]:
        return self.path is not None and len(self.path.strip()) > 0
    
    if self.command == CommandType.SEARCH_FILE:
        return self.content is not None and len(self.content.strip()) > 0
    
    if self.command == CommandType.COMMIT:
        return self.content is not None and len(self.content.strip()) > 0
    
    if self.command in [CommandType.CREATE_BRANCH, CommandType.SWITCH_BRANCH]:
        return self.path is not None and len(self.path.strip()) > 0
    
    return True  # pull, push, clone non richiedono parametri
```

### 5.3 Sistema di Convenzioni per Tipi

```python
@property
def search_type(self) -> SearchType:
    """
    DETERMINAZIONE TIPO RICERCA DA PREFISSI:
    - "ext:.py" → BY_EXTENSION  
    - "content:import os" → BY_CONTENT
    - "README" (default) → BY_NAME
    """
    
    if not self.content:
        return SearchType.BY_NAME
        
    decoded_content = self._decode_content()
    
    if decoded_content.startswith('ext:'):
        return SearchType.BY_EXTENSION
    elif decoded_content.startswith('content:'):
        return SearchType.BY_CONTENT
    else:
        return SearchType.BY_NAME

@property  
def modify_type(self) -> ModifyType:
    """
    DETERMINAZIONE TIPO MODIFICA DA PREFISSI:
    - "append:nuovo contenuto" → APPEND
    - "replace:contenuto" (default) → REPLACE
    """
    
    if not self.content:
        return ModifyType.REPLACE
        
    decoded_content = self._decode_content()
    
    return ModifyType.APPEND if decoded_content.startswith('append:') else ModifyType.REPLACE
```

---

## 🌐 6. API SERVER PER GITHUB COPILOT

### 6.1 Architettura Flask API

```python
# File: copilot_api.py

app = Flask(__name__)
CORS(app)  # Abilita CORS per GitHub Copilot

@app.route('/api/copilot/execute', methods=['POST'])
def execute_commands():
    """
    ENDPOINT PRINCIPALE PER GITHUB COPILOT:
    
    INPUT:
    {
      "commands": [CommandInput],
      "repository": "owner/repo" (opzionale),
      "workspace_path": "/path" (opzionale)  
    }
    
    OUTPUT:
    {
      "success": bool,
      "message": str,
      "total_commands": int,
      "executed_commands": int,
      "results": {step: CommandResult},
      "repository_info": {...}
    }
    """
```

### 6.2 Gestione Errori e Status Codes

```python
def _handle_api_errors(func):
    """
    DECORATOR PER GESTIONE ERRORI API:
    
    400 Bad Request: Errori di validazione input
    401 Unauthorized: Problemi autenticazione OAuth  
    403 Forbidden: Permessi insufficienti repository
    404 Not Found: Repository o file non trovati
    207 Multi-Status: Successo parziale (alcuni comandi falliti)
    500 Internal Server Error: Errori interni non gestiti
    """
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as ve:
            return jsonify({"error": f"Validation error: {str(ve)}"}), 400
        except PermissionError as pe:
            return jsonify({"error": f"Permission denied: {str(pe)}"}), 403
        except Exception as e:
            app.logger.error(f"Unhandled error: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500
    
    return wrapper
```

### 6.3 Integrazione con GitHub Copilot

```yaml
# File: copilot-extension.yml

name: "GitHub Commands Extension"
description: "Estensione per eseguire comandi pseudo-script su repository GitHub"
version: "1.0.0"

extension:
  type: "agent"
  
endpoint:
  url: "https://your-domain.com/api/copilot"
  
commands:
  - name: "execute"
    description: "Esegue una serie di comandi pseudo-script sul repository"
    parameters:
      - name: "commands"
        type: "array" 
        description: "Array di comandi da eseguire"
        required: true

permissions:
  - "repository:read"
  - "repository:write"
  - "contents:read"
  - "contents:write"
```

---

## 🔧 7. DEPLOYMENT E CONFIGURAZIONE

### 7.1 Configurazione Environment

```bash
# File: .env

# OAuth Credentials (da GitHub Developer Settings)
GITHUB_CLIENT_ID=your_actual_client_id_here
GITHUB_CLIENT_SECRET=your_actual_client_secret_here

# Flask Configuration  
FLASK_SECRET_KEY=your_secure_random_key_here
FLASK_DEBUG=false

# Server Configuration
PORT=5000
HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=extension.log
```

### 7.2 Deploy su Heroku

```bash
# Procfile
web: gunicorn copilot_api:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120

# Commands per deploy
heroku create github-commands-extension
heroku config:set GITHUB_CLIENT_ID=xxx
heroku config:set GITHUB_CLIENT_SECRET=xxx  
heroku config:set FLASK_SECRET_KEY=xxx
git push heroku main
```

### 7.3 Monitoraggio e Logging

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(app):
    """
    CONFIGURAZIONE LOGGING:
    1. File rotation automatico (10MB max)
    2. Formato strutturato con timestamp
    3. Livelli separati (INFO, WARNING, ERROR)
    4. Integrazione con monitoring tools
    """
    
    if not app.debug:
        file_handler = RotatingFileHandler('logs/extension.log', 
                                         maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
```

---

## 🧪 8. TESTING E QUALITÀ DEL CODICE

### 8.1 Test di Integrazione

```python
# File: test_extension.py

def test_commands_with_oauth():
    """
    TEST COMPLETO DELL'ESTENSIONE:
    1. Test autenticazione OAuth
    2. Test ogni tipo di comando
    3. Verifica gestione errori
    4. Test cleanup risorse
    """
    
    test_commands: list[CommandInput] = [
        {"step": 1, "command": "read.file", "path": "README.md"},
        {"step": 2, "command": "search.file", "content": base64.encode("README")},
        {"step": 3, "command": "create.file", "path": "test.txt", "content": "..."},
        {"step": 4, "command": "create.branch", "content": "feature/test"},
        {"step": 5, "command": "commit", "content": "test commit"},
        {"step": 6, "command": "push"}
    ]
```

### 8.2 Metriche di Performance

```python
def performance_monitoring():
    """
    METRICHE MONITORATE:
    1. Tempo di risposta per tipo comando
    2. Utilizzo memoria durante clone repository
    3. Throughput API requests
    4. Tasso di successo/fallimento per comando
    5. Latenza autenticazione OAuth
    """
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    @app.after_request  
    def after_request(response):
        duration = time.time() - g.start_time
        app.logger.info(f"Request completed in {duration:.3f}s")
        return response
```

---

## 🚀 9. OTTIMIZZAZIONI E BEST PRACTICES

### 9.1 Gestione Memoria

```python
def optimize_clone_operations():
    """
    OTTIMIZZAZIONI CLONE:
    1. Shallow clone per ridurre dimensioni
    2. Sparse checkout per file specifici
    3. Cleanup automatico repository temporanei
    4. LRU cache per repository frequenti
    """
    
    # Shallow clone con depth limitato
    repo = Repo.clone_from(
        url=clone_url,
        to_path=local_path,
        depth=1,  # Solo ultimo commit
        single_branch=True  # Solo branch corrente
    )
```

### 9.2 Sicurezza

```python
def security_measures():
    """
    MISURE DI SICUREZZA:
    1. Sanitizzazione input per prevenire path traversal
    2. Limitazione dimensione file operazioni
    3. Rate limiting per API calls
    4. Crittografia token in storage locale
    5. Validazione strict per comandi critici
    """
    
    def sanitize_path(file_path: str) -> str:
        # Prevenzione path traversal
        normalized = os.path.normpath(file_path)
        if normalized.startswith('..') or os.path.isabs(normalized):
            raise ValueError(f"Path non sicuro: {file_path}")
        return normalized
```

---

## 📊 10. TROUBLESHOOTING GUIDE

### 10.1 Errori Comuni e Soluzioni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| `OAuth not configured` | Credenziali mancanti in .env | Verifica GITHUB_CLIENT_ID/SECRET |
| `Repository not found` | Directory senza .git | Esegui da directory Git valida |
| `Permission denied` | Mancano permessi repository | Controlla OAuth App permissions |
| `Command validation failed` | Sintassi comando errata | Verifica CommandType enum values |
| `Clone failed` | Repository privato/inaccessibile | Verifica autenticazione e permessi |

### 10.2 Debug Mode

```python
def enable_debug_mode():
    """
    MODALITÀ DEBUG:
    1. Logging verboso di tutte le operazioni
    2. Preservazione file temporanei per ispezione
    3. Dump JSON di tutti i comandi processati
    4. Traceback completi per errori
    """
    
    if os.getenv('DEBUG', '').lower() == 'true':
        logging.basicConfig(level=logging.DEBUG)
        app.config['DEBUG'] = True
        app.config['PRESERVE_TEMP_FILES'] = True
```

Questa guida tecnica completa documenta l'intera architettura dell'estensione GitHub Copilot, dalle funzionalità di base alle ottimizzazioni avanzate e alle procedure di deployment.
