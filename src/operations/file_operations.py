import os
import base64
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path
import fnmatch
import re

class FileOperationsManager:
    """Gestore per le operazioni sui file locali"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def create_file(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea un file al path indicato con il contenuto specificato

        Args:
            file_path: Path relativo del file da creare
            content: Contenuto del file (base64 encoded)

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            full_path = self.base_path / file_path

            # Crea le directory parent se non esistono
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Decodifica il contenuto se presente
            file_content = ""
            if content:
                try:
                    decoded_bytes = base64.b64decode(content)
                    file_content = decoded_bytes.decode('utf-8')
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Errore nella decodifica del contenuto: {str(e)}"
                    }

            # Scrivi il file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(file_content)

            return {
                "success": True,
                "message": f"File creato: {file_path}",
                "path": str(full_path)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nella creazione del file: {str(e)}"
            }

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Legge il contenuto di un file

        Args:
            file_path: Path relativo del file da leggere

        Returns:
            Dict con contenuto del file
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                return {
                    "success": False,
                    "error": "File non trovato",
                    "message": f"Il file {file_path} non esiste"
                }

            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Codifica in base64 per mantenere formatting
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('ascii')

            return {
                "success": True,
                "content": encoded_content,
                "raw_content": content,  # Per debug
                "message": f"File letto: {file_path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nella lettura del file: {str(e)}"
            }

    def modify_file(self, file_path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        Modifica un file esistente

        Args:
            file_path: Path relativo del file da modificare
            content: Nuovo contenuto (base64 encoded)
            append: Se True, aggiunge in fondo al file

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                return {
                    "success": False,
                    "error": "File non trovato",
                    "message": f"Il file {file_path} non esiste"
                }

            # Decodifica il contenuto
            try:
                decoded_bytes = base64.b64decode(content)
                new_content = decoded_bytes.decode('utf-8')
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Errore nella decodifica del contenuto: {str(e)}"
                }

            # Leggi il contenuto esistente se in modalità append
            if append:
                with open(full_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                new_content = existing_content + new_content

            # Scrivi il file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return {
                "success": True,
                "message": f"File modificato: {file_path}",
                "mode": "append" if append else "replace"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nella modifica del file: {str(e)}"
            }

    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """
        Elimina un file

        Args:
            file_path: Path relativo del file da eliminare

        Returns:
            Dict con risultato dell'operazione
        """
        try:
            full_path = self.base_path / file_path

            if not full_path.exists():
                return {
                    "success": False,
                    "error": "File non trovato",
                    "message": f"Il file {file_path} non esiste"
                }

            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()

            return {
                "success": True,
                "message": f"File eliminato: {file_path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nell'eliminazione del file: {str(e)}"
            }

    def search_files(self, search_term: str, search_type: str = "name") -> Dict[str, Any]:
        """
        Cerca file nel repository

        Args:
            search_term: Termine di ricerca
            search_type: Tipo di ricerca (name, extension, content)

        Returns:
            Dict con risultati della ricerca
        """
        try:
            results = []

            for root, dirs, files in os.walk(self.base_path):
                # Salta le directory .git
                dirs[:] = [d for d in dirs if d != '.git']

                for file in files:
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.base_path)

                    match = False

                    if search_type == "name":
                        # Ricerca per nome file (con wildcard)
                        match = fnmatch.fnmatch(file.lower(), f"*{search_term.lower()}*")

                    elif search_type == "extension":
                        # Ricerca per estensione
                        file_ext = file_path.suffix.lstrip('.')
                        match = file_ext.lower() == search_term.lower()

                    elif search_type == "content":
                        # Ricerca nel contenuto del file
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                match = re.search(search_term, content, re.IGNORECASE) is not None
                        except:
                            # Salta file binari o non leggibili
                            continue

                    if match:
                        results.append({
                            "path": str(relative_path),
                            "name": file,
                            "size": file_path.stat().st_size if file_path.exists() else 0
                        })

            return {
                "success": True,
                "results": results,
                "count": len(results),
                "search_term": search_term,
                "search_type": search_type,
                "message": f"Trovati {len(results)} risultati"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Errore nella ricerca: {str(e)}"
            }
