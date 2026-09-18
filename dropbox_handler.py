import os
import time
import dropbox
from dropbox.exceptions import AuthError, ApiError
from dropbox.files import WriteMode
from dropbox.common import PathRoot
from pathlib import Path
import streamlit as st

SYSTEM_FILE_PREFIXES = ("._", ".~$", "~$")
SYSTEM_FILE_NAMES = (".ds_store", "thumbs.db")

def is_system_file(file_name: str) -> bool:
    """Verifica se o arquivo é um metadado oculto de sistema (ex: macOS ._*, Windows .DS_Store, ~$ lock)."""
    name_lower = file_name.lower()
    if name_lower in SYSTEM_FILE_NAMES:
        return True
    for prefix in SYSTEM_FILE_PREFIXES:
        if file_name.startswith(prefix):
            return True
    return False

def with_retry(api_func, max_retries=5, initial_delay=2.0):
    """
    Executa uma função da API do Dropbox com retries e exponential backoff.
    Trata erros de Rate Limit (HTTP 429) e falhas temporárias de rede.
    """
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return api_func()
        except ApiError as err:
            is_rate_limit = False
            retry_after = delay
            if hasattr(err, 'error') and hasattr(err.error, 'is_rate_limit') and err.error.is_rate_limit():
                is_rate_limit = True
                if hasattr(err.error, 'get_rate_limit_reason') and hasattr(err.error.get_rate_limit_reason(), 'retry_after'):
                    retry_after = max(err.error.get_rate_limit_reason().retry_after, delay)
            
            if is_rate_limit and attempt < max_retries - 1:
                print(f"[DROPBOX RATE LIMIT] Aguardando {retry_after}s antes da tentativa {attempt + 2}/{max_retries}...")
                time.sleep(retry_after)
                delay *= 2
            elif attempt < max_retries - 1:
                print(f"[DROPBOX API ERROR] {err}. Tentando novamente ({attempt + 2}/{max_retries}) em {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                raise err
        except AuthError as err:
            # Erro de autenticação (token inválido ou expirado) não deve ter retry
            raise err
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[DROPBOX NET ERROR] {e}. Tentando novamente ({attempt + 2}/{max_retries}) em {delay}s...")
                time.sleep(delay)
                delay *= 2
            else:
                raise e

class DropboxHandler:
    def __init__(self, access_token):
        self.base_dbx = dropbox.Dropbox(access_token)
        self.dbx = self.base_dbx
        try:
            account = with_retry(lambda: self.base_dbx.users_get_current_account())
            if hasattr(account, 'root_info') and account.root_info:
                root_namespace_id = account.root_info.root_namespace_id
                candidate_dbx = self.base_dbx.with_path_root(PathRoot.root(root_namespace_id))
                # Testa se o path_root é aceito pela API (Sandbox/App Folder apps rejeitam)
                with_retry(lambda: candidate_dbx.files_list_folder("", limit=1))
                self.dbx = candidate_dbx
        except Exception:
            self.dbx = self.base_dbx

    def check_connection(self):
        """Verifica se a conexão e o token são validos."""
        try:
            account = with_retry(lambda: self.base_dbx.users_get_current_account())
            lang = st.session_state.get('lang', 'pt')
            connected_msg = f"Connected as: {account.name.display_name}" if lang == 'en' else f"Conectado como: {account.name.display_name}"
            return True, connected_msg
        except AuthError:
            lang = st.session_state.get('lang', 'pt')
            err_msg = "Authentication Error: Expired or invalid token." if lang == 'en' else "Erro de Autenticação: Token expirado ou inválido."
            return False, err_msg
        except Exception as e:
            lang = st.session_state.get('lang', 'pt')
            err_msg = f"Connection Error: {str(e)}" if lang == 'en' else f"Erro de Conexão: {str(e)}"
            return False, err_msg

    def scan_folder_tree(self, folder_path, supported_extensions):
        """
        Executa uma ÚNICA varredura recursiva da subárvore do Dropbox com retries automáticos.
        Descarta arquivos ocultos/metadados do sistema (ex: ._*, .DS_Store, ~$*).
        Retorna uma tupla: (files_found, existing_md_set, existing_indices_set)
        """
        files_found = []
        existing_md_set = set()
        existing_indices_set = set()
        
        try:
            path = folder_path if folder_path != "/" else ""
            result = with_retry(lambda: self.dbx.files_list_folder(path, recursive=True))
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if is_system_file(entry.name):
                            continue
                        
                        path_posix = entry.path_display.lower()
                        ext = os.path.splitext(entry.name)[1].lower()
                        
                        if ext == '.md':
                            existing_md_set.add(path_posix)
                        
                        if entry.name.lower() == "_index_content.pdf":
                            existing_indices_set.add(path_posix)
                        
                        if ext in supported_extensions:
                            files_found.append(entry)

            process_entries(result.entries)

            while result.has_more:
                cursor = result.cursor
                result = with_retry(lambda: self.dbx.files_list_folder_continue(cursor))
                process_entries(result.entries)

            return files_found, existing_md_set, existing_indices_set
        except ApiError as e:
            lang = st.session_state.get('lang', 'pt')
            msg = f"Erro ao listar arquivos do Dropbox: {e}" if lang == 'pt' else f"Error listing Dropbox files: {e}"
            st.error(msg)
            return [], set(), set()

    def list_files_recursive(self, folder_path, supported_extensions):
        """Lista arquivos recursivamente filtrando por extensão e ignorando arquivos de sistema."""
        files_found = []
        try:
            path = folder_path if folder_path != "/" else ""
            result = with_retry(lambda: self.dbx.files_list_folder(path, recursive=True))
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if is_system_file(entry.name):
                            continue
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in supported_extensions:
                            files_found.append(entry)

            process_entries(result.entries)

            while result.has_more:
                cursor = result.cursor
                result = with_retry(lambda: self.dbx.files_list_folder_continue(cursor))
                process_entries(result.entries)

            return files_found
        except ApiError as e:
            lang = st.session_state.get('lang', 'pt')
            msg = f"Erro ao listar arquivos do Dropbox: {e}" if lang == 'pt' else f"Error listing Dropbox files: {e}"
            st.error(msg)
            return []

    def list_subfolders(self, folder_path):
        """Lista apenas as subpastas diretas de um diretório (para navegação)."""
        folders = []
        try:
            path = folder_path if folder_path != "/" else ""
            result = with_retry(lambda: self.dbx.files_list_folder(path))
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FolderMetadata):
                        folders.append(entry)

            process_entries(result.entries)
            
            while result.has_more:
                cursor = result.cursor
                result = with_retry(lambda: self.dbx.files_list_folder_continue(cursor))
                process_entries(result.entries)

            return sorted(folders, key=lambda x: x.name)
        except AuthError:
            print("Erro de Autenticação ao listar pastas.")
            return []
        except ApiError as e:
            print(f"Erro ao listar pastas: {e}")
            return []

    def list_direct_files(self, folder_path, supported_extensions=None):
        """Lista arquivos diretos (não recursivo) de uma pasta ignorando arquivos de sistema."""
        files = []
        try:
            path = folder_path if folder_path != "/" else ""
            result = with_retry(lambda: self.dbx.files_list_folder(path))
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if is_system_file(entry.name):
                            continue
                        if supported_extensions:
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext not in supported_extensions:
                                continue
                        files.append(entry)

            process_entries(result.entries)
            while result.has_more:
                cursor = result.cursor
                result = with_retry(lambda: self.dbx.files_list_folder_continue(cursor))
                process_entries(result.entries)

            return sorted(files, key=lambda x: x.name)
        except Exception as e:
            print(f"Erro ao listar arquivos diretos: {e}")
            return []

    def file_exists(self, dropbox_path):
        """Verifica se um arquivo existe."""
        try:
            with_retry(lambda: self.dbx.files_get_metadata(dropbox_path))
            return True
        except:
            return False

    def download_file(self, dropbox_path, local_path):
        """Baixa um arquivo do Dropbox para o disco local com retries."""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with_retry(lambda: self.dbx.files_download_to_file(local_path, dropbox_path))
            return True
        except Exception as e:
            print(f"Erro ao baixar {dropbox_path}: {e}")
            return False

    def upload_file(self, local_path, dropbox_path):
        """Faz upload de um arquivo local para o Dropbox (Sobrescrevendo se existir) com retries."""
        self.last_error = ""
        try:
            if not os.path.exists(local_path):
                self.last_error = f"Arquivo local não encontrado: {local_path}"
                print(f"[WARN] {self.last_error}", flush=True)
                return False
            with open(local_path, "rb") as f:
                content = f.read()
            
            # Tenta com o cliente atual (self.dbx)
            try:
                with_retry(lambda: self.dbx.files_upload(
                    content, 
                    dropbox_path, 
                    mode=WriteMode('overwrite')
                ))
                return True
            except Exception as e_primary:
                # Se houver PathRoot configurado e falhar, tenta fallback com self.base_dbx
                if self.dbx != self.base_dbx:
                    try:
                        with_retry(lambda: self.base_dbx.files_upload(
                            content, 
                            dropbox_path, 
                            mode=WriteMode('overwrite')
                        ))
                        return True
                    except Exception:
                        pass
                raise e_primary
        except Exception as e:
            self.last_error = str(e)
            print(f"[ERRO UPLOAD DROPBOX] {dropbox_path}: {e}", flush=True)
            return False

