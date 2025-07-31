# 📚 Guida Tecnica Completa - GitHub Copilot Extension

## 🎯 Panoramica Architetturale

L'estensione GitHub Copilot segue un'architettura modulare basata su quattro componenti principali:

1. **Auth Manager**: Gestisce autenticazione e identificazione repository
2. **File Operations Manager**: Gestisce operazioni sui file locali
3. **Git Operations Manager**: Gestisce operazioni Git/GitHub
4. **Gateway**: Orchestratore principale che coordina tutti i componenti

---

## 🔍 1. RECUPERO DEL REPOSITORY E IDENTIFICAZIONE

### 1.1 Processo di Identificazione del Repository

Il sistema identifica automaticamente il repository corrente attraverso il workspace Git locale:

```python
# File: src/auth/github_auth.py - metodo detect_current_repository()

def detect_current_repository(self, workspace_path: str) -> Dict[str, Any]:
    try:
        # STEP 1: Inizializza repository Git locale
        repo = Repo(workspace_path)
        
        # STEP 2: Verifica che esistano remote configurati
        if not repo.remotes:
            raise Exception("Nessun remote configurato")
        
        # STEP 3: Ottiene URL del remote 'origin'
        origin_url = repo.remotes.origin.url
        
        # STEP 4: Parsing dell'URL GitHub
        parsed_url = urlparse(origin_url)
        if 'github.com' not in parsed_url.netloc:
            raise Exception("Non è un repository GitHub")
        
        # STEP 5: Estrazione owner e repository name
        path_parts = parsed_url.path.strip('/').replace('.git', '').split('/')
        if len(path_parts) < 2:
            raise Exception("URL del repository non valido")
        
        owner, repo_name = path_parts[0], path_parts[1]
        
        # STEP 6: Memorizzazione informazioni repository
        self.current_repo_info = {
            "owner": owner,
            "repo": repo_name,
            "full_name": f"{owner}/{repo_name}"
        }
        
        return {
            "success": True,
            "repository": self.current_repo_info
        }
```

### 1.2 Formati URL Supportati

Il sistema supporta diversi formati di URL GitHub:

```bash
# HTTPS
https://github.com/username/repository.git
https://github.com/username/repository

# SSH
git@github.com:username/repository.git

# Parsing unificato
parsed_url.path -> "/username/repository.git"
path_parts = [username, repository]
```

### 1.3 Validazione Repository

Dopo l'identificazione, il sistema verifica:

```python
# Controllo che sia effettivamente un repository GitHub
if 'github.com' not in parsed_url.netloc:
    raise Exception("Non è un repository GitHub")

# Controllo formato path
if len(path_parts) < 2:
    raise Exception("URL del repository non valido")
```

---

## 🔐 2. GESTIONE DELL'AUTENTICAZIONE OAUTH

### 2.1 Flusso di Autenticazione

L'autenticazione avviene tramite token di accesso GitHub:

```python
# File: src/auth/github_auth.py - metodo authenticate()

def authenticate(self, access_token: str) -> Dict[str, Any]:
    try:
        # STEP 1: Creazione oggetto Auth con token
        auth = Auth.Token(access_token)
        
        # STEP 2: Inizializzazione client GitHub
        self.github_client = Github(auth=auth)
        
        # STEP 3: Verifica autenticazione tramite API call
        user = self.github_client.get_user()
        self.authenticated = True
        
        # STEP 4: Ritorno informazioni utente
        return {
            "success": True,
            "user": user.login,
            "message": f"Autenticato come: {user.login}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
```

### 2.2 Verifica Permessi Repository

Dopo l'autenticazione, il sistema verifica i permessi:

```python
def check_repository_permissions(self) -> Dict[str, Any]:
    try:
        # STEP 1: Ottiene oggetto repository da GitHub API
        repo = self.github_client.get_repo(self.current_repo_info["full_name"])
        
        # STEP 2: Estrae permessi dal repository
        permissions = {
            "can_read": True,  # Se otteniamo il repo, possiamo leggerlo
            "can_write": repo.permissions.push,  # Permesso di push
            "can_admin": repo.permissions.admin   # Permesso di admin
        }
        
        return {
            "success": True,
            "permissions": permissions
        }
    except Exception as e:
        # Gestione errori di accesso
        return {
            "success": False,
            "error": str(e)
        }
```

### 2.3 Tipi di Token Supportati

L'estensione supporta diversi tipi di token GitHub:

1. **Personal Access Token (PAT)**: Token generato dall'utente
2. **OAuth App Token**: Token generato da app OAuth
3. **GitHub App Token**: Token per GitHub Apps

```python
# Configurazione flessibile del token
auth = Auth.Token(access_token)  # Funziona con tutti i tipi
```

---

## 🏗️ 3. SETUP DEL CLONE LOCALE

### 3.1 Creazione Clone Temporaneo

Il sistema crea un clone locale temporaneo per le operazioni:

```python
# File: src/auth/github_auth.py - metodo setup_local_clone()

def setup_local_clone(self) -> str:
    # STEP 1: Verifica prerequisiti
    if not self.authenticated or not self.current_repo_info:
        raise Exception("Autenticazione o repository non configurati")
    
    # STEP 2: Controlla se esiste già un clone
    if self.local_repo_path and os.path.exists(self.local_repo_path):
        return self.local_repo_path
    
    # STEP 3: Crea directory temporanea
    temp_dir = tempfile.mkdtemp(prefix="github_copilot_")
    
    # STEP 4: Costruisce URL per clone
    repo_url = f"https://github.com/{self.current_repo_info['full_name']}.git"
    
    try:
        # STEP 5: Esegue clone del repository
        Repo.clone_from(repo_url, temp_dir)
        self.local_repo_path = temp_dir
        return temp_dir
    except Exception as e:
        # STEP 6: Cleanup in caso di errore
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise Exception(f"Errore durante il clone: {str(e)}")
```

### 3.2 Gestione Directory Temporanee

```python
# Creazione con prefisso identificativo
temp_dir = tempfile.mkdtemp(prefix="github_copilot_")

# Esempio di path generato:
# /tmp/github_copilot_xyz123/
# C:\Users\username\AppData\Local\Temp\github_copilot_xyz123\
```

### 3.3 Cleanup Automatico

```python
def cleanup_local_clone(self):
    """Pulisce il clone locale temporaneo"""
    if self.local_repo_path and os.path.exists(self.local_repo_path):
        import shutil
        shutil.rmtree(self.local_repo_path)
        self.local_repo_path = None
```

---

## 🔄 4. ORCHESTRAZIONE DEL GATEWAY

### 4.1 Processo di Inizializzazione

Il Gateway coordina l'inizializzazione di tutti i componenti:

```python
# File: src/gateway.py - metodo initialize()

def initialize(self, access_token: str, workspace_path: str) -> Dict[str, Any]:
    try:
        # STEP 1: Autenticazione GitHub
        auth_result = self.auth_manager.authenticate(access_token)
        if not auth_result["success"]:
            return auth_result
        
        # STEP 2: Identificazione repository
        repo_result = self.auth_manager.detect_current_repository(workspace_path)
        if not repo_result["success"]:
            return repo_result
        
        # STEP 3: Verifica permessi
        perm_result = self.auth_manager.check_repository_permissions()
        if not perm_result["success"]:
            return perm_result
        
        # STEP 4: Setup clone locale
        local_path = self.auth_manager.setup_local_clone()
        
        # STEP 5: Inizializzazione managers con path locale
        self.file_manager = FileOperationsManager(local_path)
        self.git_manager = GitOperationsManager(
            local_path,
            self.auth_manager.get_github_client(),
            self.auth_manager.get_current_repo_info()
        )
        
        # STEP 6: Conferma inizializzazione
        self.is_initialized = True
        
        return {
            "success": True,
            "repository": self.auth_manager.get_current_repo_info(),
            "permissions": perm_result.get("permissions", {}),
            "local_path": local_path
        }
```

### 4.2 Flusso di Esecuzione Comandi

```python
def execute_commands(self, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
    # STEP 1: Verifica inizializzazione
    if not self.is_initialized:
        return {"success": False, "error": "Gateway non inizializzato"}
    
    results = []
    overall_success = True
    
    # STEP 2: Ordina comandi per step
    sorted_commands = sorted(commands, key=lambda x: x.get("step", 0))
    
    # STEP 3: Esecuzione sequenziale
    for cmd_dict in sorted_commands:
        try:
            # STEP 3a: Creazione oggetto comando
            command = GitHubCommand(**cmd_dict)
            
            # STEP 3b: Validazione comando
            if not command.validate():
                # Comando non valido - continua con il prossimo
                continue
            
            # STEP 3c: Esecuzione comando
            result = self._execute_single_command(command)
            result["step"] = command.step
            result["command"] = command.command.value
            
            results.append(result)
            
            # STEP 3d: Tracciamento fallimenti
            if not result["success"]:
                overall_success = False
                
        except Exception as e:
            # Gestione errori a livello di comando
            results.append({
                "step": cmd_dict.get("step", -1),
                "success": False,
                "error": str(e)
            })
            overall_success = False
    
    return {
        "success": overall_success,
        "results": results,
        "total_commands": len(commands),
        "successful_commands": len([r for r in results if r["success"]]),
        "failed_commands": len([r for r in results if not r["success"]])
    }
```

---

## 📁 5. OPERAZIONI SUI FILE

### 5.1 Gestione Path e Directory

```python
# File: src/operations/file_operations.py

class FileOperationsManager:
    def __init__(self, base_path: str):
        # Memorizza path del clone locale
        self.base_path = Path(base_path)
        
    def create_file(self, file_path: str, content: Optional[str] = None):
        # STEP 1: Costruzione path completo
        full_path = self.base_path / file_path
        
        # STEP 2: Creazione directory parent automatica
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # STEP 3: Decodifica contenuto base64
        file_content = ""
        if content:
            try:
                decoded_bytes = base64.b64decode(content)
                file_content = decoded_bytes.decode('utf-8')
            except Exception as e:
                return {"success": False, "error": f"Errore decodifica: {str(e)}"}
        
        # STEP 4: Scrittura file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
            
        return {
            "success": True,
            "message": f"File creato: {file_path}",
            "path": str(full_path)
        }
```

### 5.2 Gestione Codifica Base64

```python
# Decodifica con preservazione di formatting
try:
    decoded_bytes = base64.b64decode(content)
    file_content = decoded_bytes.decode('utf-8')
except Exception as e:
    return {"success": False, "error": f"Errore decodifica: {str(e)}"}

# Esempio di contenuto base64:
# Input:  "cHJpbnQoIkhlbGxvLCBXb3JsZCEiKQ==" 
# Output: 'print("Hello, World!")'
```

### 5.3 Sistema di Ricerca

```python
def search_files(self, search_term: str, search_type: str = "name"):
    results = []
    
    for root, dirs, files in os.walk(self.base_path):
        # STEP 1: Esclusione directory .git
        dirs[:] = [d for d in dirs if d != '.git']
        
        for file in files:
            file_path = Path(root) / file
            relative_path = file_path.relative_to(self.base_path)
            
            match = False
            
            if search_type == "name":
                # Ricerca per nome con wildcard
                match = fnmatch.fnmatch(file.lower(), f"*{search_term.lower()}*")
            
            elif search_type == "extension":
                # Ricerca per estensione
                file_ext = file_path.suffix.lstrip('.')
                match = file_ext.lower() == search_term.lower()
            
            elif search_type == "content":
                # Ricerca nel contenuto
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        match = re.search(search_term, content, re.IGNORECASE) is not None
                except:
                    continue  # Salta file binari
            
            if match:
                results.append({
                    "path": str(relative_path),
                    "name": file,
                    "size": file_path.stat().st_size
                })
    
    return {
        "success": True,
        "results": results,
        "count": len(results)
    }
```

---

## 🔧 6. OPERAZIONI GIT

### 6.1 Gestione Repository Git

```python
# File: src/operations/git_operations.py

class GitOperationsManager:
    def __init__(self, local_repo_path: str, github_client: Github, repo_info: Dict[str, str]):
        self.local_repo_path = local_repo_path
        self.github_client = github_client
        self.repo_info = repo_info
        self.git_repo = Repo(local_repo_path)  # Repository Git locale
```

### 6.2 Operazioni di Sincronizzazione

```python
def pull(self) -> Dict[str, Any]:
    try:
        # STEP 1: Ottiene remote origin
        origin = self.git_repo.remotes.origin
        
        # STEP 2: Esegue pull
        pull_info = origin.pull()
        
        return {
            "success": True,
            "message": "Pull completata con successo",
            "changes": len(pull_info)
        }
    except GitCommandError as e:
        return {
            "success": False,
            "error": str(e)
        }

def commit(self, message: str) -> Dict[str, Any]:
    try:
        # STEP 1: Stage di tutti i file modificati
        self.git_repo.git.add(A=True)
        
        # STEP 2: Verifica se ci sono modifiche
        if not self.git_repo.is_dirty() and not self.git_repo.untracked_files:
            return {
                "success": True,
                "message": "Nessuna modifica da committare"
            }
        
        # STEP 3: Esegue commit
        commit = self.git_repo.index.commit(message)
        
        return {
            "success": True,
            "message": f"Commit creato: {commit.hexsha[:8]}",
            "commit_hash": commit.hexsha
        }
    except GitCommandError as e:
        return {
            "success": False,
            "error": str(e)
        }

def push(self, branch: str = None) -> Dict[str, Any]:
    try:
        origin = self.git_repo.remotes.origin
        
        if branch:
            push_info = origin.push(f"refs/heads/{branch}")
        else:
            push_info = origin.push()
        
        return {
            "success": True,
            "message": "Push completata con successo"
        }
    except GitCommandError as e:
        return {
            "success": False,
            "error": str(e)
        }
```

### 6.3 Gestione Branch

```python
def create_branch(self, branch_name: str) -> Dict[str, Any]:
    try:
        # STEP 1: Verifica se branch esiste già
        existing_branches = [ref.name.split('/')[-1] for ref in self.git_repo.refs]
        if branch_name in existing_branches:
            return {
                "success": False,
                "error": "Branch già esistente"
            }
        
        # STEP 2: Crea nuovo branch
        new_branch = self.git_repo.create_head(branch_name)
        
        return {
            "success": True,
            "message": f"Branch '{branch_name}' creato con successo"
        }
    except GitCommandError as e:
        return {
            "success": False,
            "error": str(e)
        }

def switch_branch(self, branch_name: str) -> Dict[str, Any]:
    try:
        # STEP 1: Verifica esistenza branch locale
        local_branches = [ref.name.split('/')[-1] for ref in self.git_repo.refs]
        
        if branch_name not in local_branches:
            # STEP 2: Cerca nel remote
            try:
                origin = self.git_repo.remotes.origin
                origin.fetch()
                
                remote_branch = f"origin/{branch_name}"
                if remote_branch in [ref.name for ref in self.git_repo.refs]:
                    # STEP 3: Crea branch locale che traccia quello remoto
                    new_branch = self.git_repo.create_head(branch_name, f"origin/{branch_name}")
                    new_branch.set_tracking_branch(origin.refs[branch_name])
                else:
                    return {
                        "success": False,
                        "error": "Branch non trovato"
                    }
            except:
                return {
                    "success": False,
                    "error": "Branch non trovato"
                }
        
        # STEP 4: Esegue checkout
        self.git_repo.heads[branch_name].checkout()
        
        return {
            "success": True,
            "message": f"Spostato sul branch '{branch_name}'"
        }
    except GitCommandError as e:
        return {
            "success": False,
            "error": str(e)
        }
```

---

## 🎛️ 7. GESTIONE COMANDI SPECIFICI

### 7.1 Parsing Comandi Speciali

```python
# File: src/gateway.py

def _handle_modify_file(self, command: GitHubCommand) -> Dict[str, Any]:
    # Determina modalità append dal path
    append_mode = "(append)" in (command.path or "")
    if append_mode:
        command.path = command.path.replace("(append)", "").strip()
    
    return self.file_manager.modify_file(command.path, command.content, append_mode)

def _handle_search_file(self, command: GitHubCommand) -> Dict[str, Any]:
    search_term = command.content
    
    # Decodifica base64 se necessario
    try:
        decoded_bytes = base64.b64decode(search_term)
        search_term = decoded_bytes.decode('utf-8')
    except:
        pass  # Usa valore originale se non è base64
    
    # Determina tipo ricerca da prefisso
    if search_term.startswith("name:"):
        search_type = "name"
        search_term = search_term[5:].strip()
    elif search_term.startswith("ext:") or search_term.startswith("extension:"):
        search_type = "extension"
        search_term = search_term.split(":", 1)[1].strip()
    elif search_term.startswith("content:"):
        search_type = "content"
        search_term = search_term[8:].strip()
    else:
        search_type = "name"  # Default
    
    return self.file_manager.search_files(search_term, search_type)
```

### 7.2 Validazione Comandi

```python
# File: src/types/command_types.py

@dataclass
class GitHubCommand:
    step: int
    command: CommandType
    path: Optional[str] = None
    content: Optional[str] = None
    
    def validate(self) -> bool:
        # Validazioni specifiche per comando
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

---

## 🚨 8. GESTIONE ERRORI E SICUREZZA

### 8.1 Livelli di Gestione Errori

1. **Livello Comando**: Errori specifici del singolo comando
2. **Livello Manager**: Errori delle operazioni (file/git)
3. **Livello Gateway**: Errori di orchestrazione
4. **Livello Applicazione**: Errori generali

```python
# Esempio di gestione stratificata
try:
    # Operazione specifica
    result = self.file_manager.create_file(path, content)
except FileNotFoundError as e:
    return {"success": False, "error": "Directory parent non trovata"}
except PermissionError as e:
    return {"success": False, "error": "Permessi insufficienti"}
except Exception as e:
    return {"success": False, "error": f"Errore generico: {str(e)}"}
```

### 8.2 Sicurezza del Sistema

```python
# Sandboxing: operazioni solo nel clone locale
full_path = self.base_path / file_path  # Sempre all'interno del clone

# Validazione path per prevenire directory traversal
if ".." in file_path or file_path.startswith("/"):
    return {"success": False, "error": "Path non sicuro"}

# Cleanup automatico delle risorse
def cleanup(self):
    if self.auth_manager:
        self.auth_manager.cleanup_local_clone()
    self.is_initialized = False
```

---

## 🔄 9. WORKFLOW COMPLETO

### 9.1 Sequenza di Esecuzione Tipica

```
1. initialize(token, workspace_path)
   ├── authenticate(token)
   ├── detect_current_repository(workspace_path)
   ├── check_repository_permissions()
   ├── setup_local_clone()
   └── create_managers(local_path)

2. execute_commands(commands)
   ├── validate_commands()
   ├── sort_by_step()
   └── for each command:
       ├── validate_command()
       ├── execute_single_command()
       └── collect_result()

3. cleanup()
   └── cleanup_local_clone()
```

### 9.2 Esempio di Flusso Completo

```python
# Inizializzazione
gateway = GitHubCopilotGateway()
init_result = gateway.initialize("token", "/workspace")

# Comandi di esempio
commands = [
    {"step": 1, "command": "create.file", "path": "src/new.py", "content": "base64_content"},
    {"step": 2, "command": "commit", "content": "base64_commit_message"},
    {"step": 3, "command": "push"}
]

# Esecuzione
result = gateway.execute_commands(commands)

# Cleanup
gateway.cleanup()
```

Questa guida copre tutti gli aspetti tecnici dell'estensione, dal recupero del repository alla gestione delle operazioni, fornendo una comprensione completa del funzionamento interno del sistema.
