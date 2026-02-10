import os
import dropbox
from dropbox.exceptions import AuthError, ApiError
from dropbox.files import WriteMode
from pathlib import Path
import streamlit as st

class DropboxHandler:
    def __init__(self, access_token):
        self.dbx = dropbox.Dropbox(access_token)

    def check_connection(self):
        """Verifica se a conexão e o token são validos."""
        try:
            account = self.dbx.users_get_current_account()
            return True, f"Conectado como: {account.name.display_name}"
        except AuthError:
            return False, "Erro de Autenticação: Token expirado ou inválido."
        except Exception as e:
            return False, f"Erro de Conexão: {str(e)}"

    def list_files_recursive(self, folder_path, supported_extensions):
        """Lista arquivos recursivamente filtrando por extensão."""
        files_found = []
        try:
            # Garante formato correto do path (vazio para root ou iniciando com /)
            path = folder_path if folder_path != "/" else ""
            
            result = self.dbx.files_list_folder(path, recursive=True)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in supported_extensions:
                            files_found.append(entry)

            process_entries(result.entries)

            # Paginação
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                process_entries(result.entries)

            return files_found
        except ApiError as e:
            st.error(f"Erro ao listar arquivos do Dropbox: {e}")
            return []

    def list_subfolders(self, folder_path):
        """Lista apenas as subpastas diretas de um diretório (para navegação)."""
        folders = []
        try:
            # Garante formato correto do path (vazio para root ou iniciando com /)
            path = folder_path if folder_path != "/" else ""
            
            result = self.dbx.files_list_folder(path)
            
            def process_entries(entries):
                for entry in entries:
                    if isinstance(entry, dropbox.files.FolderMetadata):
                        folders.append(entry)

            process_entries(result.entries)
            
            # Paginação (se houver muitas pastas)
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                process_entries(result.entries)

            return sorted(folders, key=lambda x: x.name)
            return sorted(folders, key=lambda x: x.name)
        except AuthError:
            print("Erro de Autenticação ao listar pastas.")
            return []
        except ApiError as e:
            # Tratamento silencioso ou log
            print(f"Erro ao listar pastas: {e}")
            return []

    def file_exists(self, dropbox_path):
        """Verifica se um arquivo existe."""
        try:
            self.dbx.files_get_metadata(dropbox_path)
            return True
        except:
            return False

    def download_file(self, dropbox_path, local_path):
        """Baixa um arquivo do Dropbox para o disco local."""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.dbx.files_download_to_file(local_path, dropbox_path)
            return True
        except Exception as e:
            print(f"Erro ao baixar {dropbox_path}: {e}")
            return False

    def upload_file(self, local_path, dropbox_path):
        """Faz upload de um arquivo local para o Dropbox (Sobrescrevendo se existir)."""
        try:
            with open(local_path, "rb") as f:
                self.dbx.files_upload(
                    f.read(), 
                    dropbox_path, 
                    mode=WriteMode('overwrite')
                )
            return True
        except Exception as e:
            print(f"Erro ao subir {dropbox_path}: {e}")
            return False
