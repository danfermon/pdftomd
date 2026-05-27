# app.py

import streamlit as st
import os
import sys
from pathlib import Path
try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except (ImportError, ModuleNotFoundError):
    HAS_TKINTER = False

IS_HEADLESS = os.name != 'nt' or os.getenv("RUNNING_IN_DOCKER") == "true" or not HAS_TKINTER
import google.generativeai as genai
from dotenv import load_dotenv
from dropbox_handler import DropboxHandler
import auth # IMPORTADO

# Importar as funções do pipeline
from pdf_detector import is_digital_pdf, extract_structured_markitdown # RENOMEADO
from gcv_ocr import ocr_local_tesseract, extract_ocr_to_markdown_gemini
from youtube_handler import is_youtube_url, extract_youtube_transcript # NOVO
from index_generator import generate_index_for_folder # NOVO RLM



# --- Sistema de Tradução ---
TRANSLATIONS = {
    "pt": {
        "page_title": "Processador de Documentos para Markdown",
        "login_subtitle": "Sistema Seguro de Processamento de Documentos",
        "username": "Usuário",
        "username_placeholder": "Digite seu usuário...",
        "password": "Senha",
        "password_placeholder": "Digite sua senha...",
        "enter": "Entrar",
        "login_success": "Login efetuado com sucesso! Redirecionando...",
        "login_error": "Usuário ou senha inválidos. Tente novamente.",
        "forced_change_pwd_title": "🔒 Alteração de Senha Obrigatória",
        "forced_change_pwd_subtitle": "Este é o seu primeiro acesso ou sua senha foi resetada. Por questões de segurança, você deve escolher uma senha forte.",
        "new_pwd": "Nova Senha",
        "new_pwd_placeholder": "Digite uma nova senha...",
        "confirm_pwd": "Confirme a Nova Senha",
        "confirm_pwd_placeholder": "Repita a nova senha...",
        "change_pwd_btn": "Alterar Senha e Entrar",
        "pwd_blank_error": "A nova senha não pode estar em branco.",
        "pwd_min_len_error": "A senha deve ter pelo menos 6 caracteres por segurança.",
        "pwd_default_error": "A nova senha não pode ser a senha padrão '123456'. Defina uma senha mais segura.",
        "pwd_mismatch_error": "As senhas digitadas não coincidem. Tente novamente.",
        "pwd_change_success": "Senha alterada com sucesso! Acessando o sistema...",
        "system_error_login": "Erro interno do sistema. Por favor, tente fazer login novamente.",
        "connected_user": "👤 Usuário Conectado",
        "role_admin": "🟢 Administrador",
        "role_user": "🔵 Usuário Padrão",
        "label_name": "Nome",
        "label_profile": "Perfil",
        "security_alert": "⚠️ **ALERTA DE SEGURANÇA:**\nA senha do usuário 'admin' ainda é a senha padrão provisória ('admin123'). Por favor, altere-a imediatamente na aba de Gestão de Usuários!",
        "navigation": "Navegação",
        "nav_process_docs": "📄 Processar Documentos",
        "nav_user_mgmt": "👥 Gestão de Usuários",
        "logout_btn": "🚪 Sair do Sistema",
        "logout_success": "Logout efetuado!",
        "user_mgmt_title": "👥 Gestão de Usuários",
        "tab_registered_users": "📋 Usuários Cadastrados",
        "tab_create_user": "➕ Criar Novo Usuário",
        "status_badge_admin": "🟢 Admin",
        "status_badge_user": "🔵 Usuário",
        "status_badge_pwd_pending": " &nbsp;&nbsp;&nbsp; ⚠️ *Alteração de senha pendente*",
        "created_at": "Criado em",
        "updated_at": "Atualizado em",
        "edit_user_help": "Editar Usuário",
        "reset_pwd_help": "Redefinir Senha",
        "delete_user_help": "Excluir Usuário",
        "edit_user_section_title": "##### Editar Usuário",
        "new_username_label": "Novo nome de usuário",
        "admin_checkbox_label": "Administrador?",
        "confirm_edit_btn": "Confirmar Edição",
        "reset_pwd_section_title": "##### Redefinir Senha",
        "reset_pwd_confirm_btn": "Confirmar Nova Senha",
        "delete_user_warning": "Tem certeza que deseja excluir o usuário `{}`? Esta ação não pode ser desfeita.",
        "delete_user_yes": "Sim, Excluir",
        "create_user_info": "ℹ️ Novos usuários são criados automaticamente com a senha provisória **123456** e serão obrigados a alterá-la no primeiro acesso por questões de segurança.",
        "new_username_placeholder": "Ex: joao.silva",
        "admin_privileges_checkbox": "Conceder privilégios de Administrador?",
        "create_user_btn": "Cadastrar Usuário",
        "process_docs_title": "📄 Processador de Documentos para Markdown",
        "input_data_subheader": "1. Entrada de Dados",
        "tab_local_file": "📂 Arquivo Local",
        "tab_batch_folder": "📦 Pasta (Lote)",
        "tab_dropbox": "☁️ Dropbox",
        "tab_youtube": "📺 YouTube",
        "local_tab_headless_info": "ℹ️ Faça o upload de um arquivo para converter e gerar a versão Markdown para download.",
        "local_tab_headless_uploader": "Selecione um arquivo para converter:",
        "local_tab_info": "ℹ️ Selecione um arquivo para salvar a versão Markdown na **mesma pasta original**.",
        "local_tab_select_btn": "📂 Selecionar Arquivo",
        "local_tab_no_selection": "Nenhum arquivo selecionado.",
        "all_supported": "Todos os Suportados",
        "pdf_docs": "Documentos PDF",
        "all_files": "Todos os Arquivos",
        "batch_tab_headless_warning": "⚠️ **Aviso:** O processamento de pastas locais (Lote) está desativado em modo servidor (VPS/Docker) pois requer acesso ao sistema de arquivos do servidor. Para processar múltiplos arquivos em lote na nuvem, utilize a aba **Dropbox**, que oferece navegação de pastas e processamento incremental seguro.",
        "batch_tab_info": "ℹ️ Selecione uma **PASTA** para converter TODOS os arquivos contidos nela (Recursivo).",
        "batch_tab_select_btn": "📂 Selecionar Pasta",
        "batch_tab_no_selection": "Nenhuma pasta selecionada.",
        "semantic_index_title": "📚 Índice Semântico (RLM)",
        "generate_index_local_btn": "🧠 Gerar Índice PDF desta Pasta",
        "gemini_key_required_error": "⚠️ É necessário configurar a Chave API Gemini para usar o RLM.",
        "index_running_spinner": "🧠 Analisando arquivos e gerando índice com RLM... (Isso pode demorar)",
        "index_success": "✅ Índice Gerado com Sucesso! {} arquivo(s) indexado(s). Verifique os arquivos '_INDEX_CONTENT*.pdf' na pasta.",
        "index_no_md_warning": "⚠️ Nenhum arquivo Markdown (.md) foi encontrado para indexar nesta pasta. Apenas arquivos convertidos para Markdown (.md) podem ser indexados. Converta seus arquivos primeiro nas abas correspondente!",
        "dropbox_info": "ℹ️ Navegue pelas pastas e clique em 'Selecionar Esta Pasta' para converter.",
        "dropbox_token_expander": "🔑 Configurar Token do Dropbox (Clique para expandir)",
        "dropbox_token_instructions": "**Como obter um novo token:**\n1. Acesse [dropbox.com/developers/apps](https://www.dropbox.com/developers/apps).\n2. Clique no seu App (`carroll_rag` ou similar).\n3. Vá na aba **Settings**.\n4. Role até a seção **OAuth 2**.\n5. Clique no botão **Generate** (abaixo de *Generated access token*).\n6. Copie o código e cole abaixo.",
        "dropbox_token_placeholder": "Cole seu Dropbox Access Token aqui:",
        "dropbox_token_updated": "Token atualizado na sessão! (Reinicie o app se quiser salvar no .env permanentemente)",
        "dropbox_token_missing": "⚠️ Token do Dropbox não encontrado. Por favor, insira acima.",
        "dropbox_token_invalid": "O token atual parece inválido ou expirado. Use a área 'Configurar Token' acima para corrigir.",
        "dropbox_current_folder": "Pasta Atual",
        "dropbox_up_level": "⬆️ Subir Nível",
        "dropbox_raiz": "Raiz (/)",
        "dropbox_select_folder_btn": "✅ Selecionar Esta Pasta para Conversão",
        "dropbox_selected_msg": "Pasta selecionada",
        "dropbox_subfolders_caption": "Subpastas (clique para entrar):",
        "dropbox_no_subfolders": "*(Nenhuma subpasta encontrada)*",
        "dropbox_ready_msg": "🎯 **Pronto para processar:** {}",
        "generate_index_dbx_btn": "🧠 Gerar Índice PDF (Dropbox)",
        "dbx_index_running_spinner": "🧠 Preparando arquivos do Dropbox para indexação...",
        "dbx_no_md_found": "Nenhum arquivo Markdown encontrado para indexar.",
        "dbx_downloaded_for_analysis": "Baixados {} arquivos para análise.",
        "dbx_rlm_processing_spinner": "🧠 RLM processando e gerando PDF...",
        "dbx_index_no_md_warning": "⚠️ Nenhum arquivo Markdown (.md) foi encontrado para indexar nesta pasta. Apenas arquivos convertidos para Markdown (.md) podem ser indexados. Converta seus arquivos do Dropbox primeiro na aba acima!",
        "dbx_no_index_generated": "Nenhum índice gerado. (Verifique logs/arquivos MD)",
        "dbx_sending_toast": "Enviando",
        "dbx_index_success": "✅ {} Índices Semânticos gerados e enviados para o Dropbox com sucesso!",
        "youtube_info": "ℹ️ Transcrição salva na pasta `markdown_output`.",
        "youtube_url_placeholder": "Cole uma URL do YouTube:",
        "ia_config_subheader": "2. Configuração de IA (Opcional)",
        "use_gemini_checkbox": "Usar Google Gemini AI? (Recomendado para PDFs escaneados ruins ou imagens complexas)",
        "gemini_key_placeholder": "Cole sua Chave API Gemini:",
        "gemini_key_valid": "✅ Chave Gemini validada!",
        "gemini_force_checkbox": "Forçar uso do Gemini mesmo se Tesseract funcionar?",
        "gemini_force_help": "Ignora OCR local e usa nuvem para tudo (custo/tempo maior).",
        "gemini_key_invalid": "❌ Chave inválida.",
        "gemini_key_warning": "⚠️ Insira a chave para ativar o modo IA.",
        "overwrite_checkbox": "Sobrescrever arquivos Markdown existentes?",
        "overwrite_help": "Se desmarcado, o sistema pulará arquivos que já possuem a versão _MD.md na pasta.",
        "ready_to_process_info": "📁 **Pronto para Processar:** {}",
        "start_processing_btn": "🚀 Iniciar Processamento",
        "processing_youtube": "Processando YouTube",
        "extracting_youtube": "Extraindo transcrição do YouTube...",
        "youtube_transcription_success": "✅ Transcrição concluída!",
        "youtube_transcription_error": "❌ Falha ao obter transcrição. Verifique se o vídeo tem legendas.",
        "youtube_url_invalid": "❌ URL do YouTube inválida.",
        "mode_hybrid_upload": "Modo de Processamento: Híbrido (Upload Web + Nuvem Gemini)",
        "mode_local_upload": "Modo de Processamento: 100% Local (Upload Web + MarkItDown/Tesseract)",
        "processing_upload": "Processando Upload Web...",
        "upload_success": "✅ Upload processado com sucesso!",
        "mode_hybrid_local": "Modo de Processamento: Híbrido (Local + Nuvem Gemini)",
        "mode_local_local": "Modo de Processamento: 100% Local (MarkItDown/Tesseract)",
        "processing_local": "Processando Arquivo Local...",
        "mode_hybrid_batch": "Modo Batch: Híbrido (Local + Nuvem Gemini)",
        "mode_local_batch": "Modo Batch: 100% Local",
        "mode_hybrid_dropbox": "Modo Dropbox: Híbrido (Download -> Process -> Upload)",
        "mode_local_dropbox": "Modo Dropbox: 100% Local (Download -> Process -> Upload)",
        "processing_done_subheader": "✅ Processamento Concluído",
        "preview_title": "### Pré-visualização do Conteúdo (Markdown)",
        "extracted_content_label": "Conteúdo Extraído",
        "download_md_btn": "⬇️ Baixar Arquivo Markdown",
        "clean_old_outputs_btn": "🗑️ Limpar Arquivos de Saída Antigos",
        "clean_success": "Pasta de saída limpa com sucesso!",
        "clean_empty_info": "Nenhum arquivo para limpar na pasta de saída.",
        "saved_locally_caption": "Arquivo salvo localmente no servidor em: {}",
        "scanning_files": "🔍 Varrendo arquivos...",
        "no_supported_files_found": "Nenhum arquivo suportado encontrado nesta pasta.",
        "found_incompatible_files": "📂 Encontrados {} arquivos incompatíveis para conversão.",
        "stop_batch_btn": "🛑 Parar Processamento em Lote",
        "stop_dbx_btn": "🛑 Parar Dropbox Batch",
        "batch_stopped_by_user": "Processamento interrompido pelo usuário.",
        "batch_skipping_existing": "⏩ Pulando (Já existe): {}",
        "batch_processing_file": "Processando [{}/{}]: {}...",
        "batch_completed_msg": "✅ Concluído! Processados: {}. Pulados: {}. Erros: {}.",
        "dbx_token_missing_error": "Token do Dropbox não encontrado.",
        "dbx_scanning_files": "☁️ Varrendo arquivos no Dropbox...",
        "dbx_no_supported_files": "Nenhum arquivo suportado encontrado em '{}'.",
        "dbx_found_files": "☁️ Encontrados {} arquivos no Dropbox.",
        "dbx_stopping": "Interrompido.",
        "dbx_skipping_existing": "⏩ Pulando (Já existe): {}",
        "dbx_download_processing": "Baixando e Processando [{}/{}]: {}...",
        "dbx_uploading": "⬆️ Fazendo Upload",
        "dbx_upload_error": "Erro no upload de {}",
        "dbx_batch_completed_msg": "✅ Dropbox Batch Concluído! Sucessos: {}. Pulados: {}. Erros: {}.",
        "pdf_digital_detected": "✅ PDF digital detectado. Usando MarkItDown/Fallback para extração estruturada (Local).",
        "pdf_scanned_detected": "⚠️ PDF escaneado detectado. Tentando OCR local (Tesseract) primeiro.",
        "tesseract_success": "✅ OCR Local (Tesseract) concluído. Verifique a qualidade.",
        "initiating_gemini_ocr": "Iniciando OCR e estruturação via Gemini (custo/nuvem).",
        "gemini_processing_success": "✅ Processamento Gemini concluído.",
        "gemini_processing_failure": "❌ Processamento Gemini falhou (Bloqueio de Conteúdo ou Erro de API).",
        "tesseract_failure": "❌ OCR Tesseract falhou.",
        "trying_gemini_fallback": "Tentando OCR e estruturação via Gemini (custo/nuvem) as fallback.",
        "pdf_processing_failure": "❌ Não foi possível processar o PDF. Chave Gemini não fornecida para fallback.",
        "markitdown_extraction": "✅ Arquivo {} detectado. Extração estruturada via MarkItDown.",
        "unsupported_format": "❌ Formato de arquivo '{}' não suportado.",
        "file_not_found": "❌ Arquivo não encontrado no caminho especificado.",
        "saving_local_mode": "💾 Modo Local: Salvando saída na mesma pasta: {}",
        "saving_upload_mode": "💾 Processando upload temporário e salvando resultado em: {}",
        "saving_upload_mode_simple": "📂 Modo Upload: Salvando saída em {}"
    },
    "en": {
        "page_title": "Document Processor to Markdown",
        "login_subtitle": "Secure Document Processing System",
        "username": "Username",
        "username_placeholder": "Enter your username...",
        "password": "Password",
        "password_placeholder": "Enter your password...",
        "enter": "Sign In",
        "login_success": "Login successful! Redirecting...",
        "login_error": "Invalid username or password. Please try again.",
        "forced_change_pwd_title": "🔒 Mandatory Password Change",
        "forced_change_pwd_subtitle": "This is your first access or your password has been reset. For security reasons, you must choose a strong password.",
        "new_pwd": "New Password",
        "new_pwd_placeholder": "Enter a new password...",
        "confirm_pwd": "Confirm New Password",
        "confirm_pwd_placeholder": "Repeat new password...",
        "change_pwd_btn": "Change Password and Sign In",
        "pwd_blank_error": "New password cannot be blank.",
        "pwd_min_len_error": "Password must be at least 6 characters long for security.",
        "pwd_default_error": "New password cannot be the default password '123456'. Set a more secure password.",
        "pwd_mismatch_error": "The passwords entered do not match. Please try again.",
        "pwd_change_success": "Password changed successfully! Accessing system...",
        "system_error_login": "Internal system error. Please try logging in again.",
        "connected_user": "👤 Connected User",
        "role_admin": "🟢 Administrator",
        "role_user": "🔵 Standard User",
        "label_name": "Name",
        "label_profile": "Profile",
        "security_alert": "⚠️ **SECURITY ALERT:**\nThe password for the 'admin' user is still the temporary default password ('admin123'). Please change it immediately in the User Management tab!",
        "navigation": "Navigation",
        "nav_process_docs": "📄 Process Documents",
        "nav_user_mgmt": "👥 User Management",
        "logout_btn": "🚪 Sign Out",
        "logout_success": "Logged out successfully!",
        "user_mgmt_title": "👥 User Management",
        "tab_registered_users": "📋 Registered Users",
        "tab_create_user": "➕ Create New User",
        "status_badge_admin": "🟢 Admin",
        "status_badge_user": "🔵 User",
        "status_badge_pwd_pending": " &nbsp;&nbsp;&nbsp; ⚠️ *Password change pending*",
        "created_at": "Created at",
        "updated_at": "Updated at",
        "edit_user_help": "Edit User",
        "reset_pwd_help": "Reset Password",
        "delete_user_help": "Delete User",
        "edit_user_section_title": "##### Edit User",
        "new_username_label": "New username",
        "admin_checkbox_label": "Administrator?",
        "confirm_edit_btn": "Confirm Edit",
        "reset_pwd_section_title": "##### Reset Password",
        "reset_pwd_confirm_btn": "Confirm New Password",
        "delete_user_warning": "Are you sure you want to delete user `{}`? This action cannot be undone.",
        "delete_user_yes": "Yes, Delete",
        "create_user_info": "ℹ️ New users are automatically created with the temporary password **123456** and will be forced to change it on their first access for security reasons.",
        "new_username_placeholder": "E.g., john.doe",
        "admin_privileges_checkbox": "Grant Administrator privileges?",
        "create_user_btn": "Register User",
        "process_docs_title": "📄 Document Processor to Markdown",
        "input_data_subheader": "1. Data Input",
        "tab_local_file": "📂 Local File",
        "tab_batch_folder": "📦 Folder (Batch)",
        "tab_dropbox": "☁️ Dropbox",
        "tab_youtube": "📺 YouTube",
        "local_tab_headless_info": "ℹ️ Upload a file to convert and generate the Markdown version for download.",
        "local_tab_headless_uploader": "Select a file to convert:",
        "local_tab_info": "ℹ️ Select a file to save the Markdown version in the **same original folder**.",
        "local_tab_select_btn": "📂 Select File",
        "local_tab_no_selection": "No file selected.",
        "all_supported": "All Supported",
        "pdf_docs": "PDF Documents",
        "all_files": "All Files",
        "batch_tab_headless_warning": "⚠️ **Warning:** Local folder processing (Batch) is disabled in server mode (VPS/Docker) as it requires access to the server's file system. To process multiple files in batch on the cloud, use the **Dropbox** tab, which offers safe folder navigation and incremental processing.",
        "batch_tab_info": "ℹ️ Select a **FOLDER** to convert ALL files contained within it (Recursive).",
        "batch_tab_select_btn": "📂 Select Folder",
        "batch_tab_no_selection": "No folder selected.",
        "semantic_index_title": "📚 Semantic Index (RLM)",
        "generate_index_local_btn": "🧠 Generate PDF Index of this Folder",
        "gemini_key_required_error": "⚠️ Configuring the Gemini API Key is required to use RLM.",
        "index_running_spinner": "🧠 Analyzing files and generating index with RLM... (This may take a while)",
        "index_success": "✅ Index Generated Successfully! {} file(s) indexed. Check the '_INDEX_CONTENT*.pdf' files in the folder.",
        "index_no_md_warning": "⚠️ No Markdown (.md) files were found to index in this folder. Only files converted to Markdown (.md) can be indexed. Convert your files first in the corresponding tabs!",
        "dropbox_info": "ℹ️ Navigate through folders and click 'Select This Folder' to convert.",
        "dropbox_token_expander": "🔑 Configure Dropbox Token (Click to expand)",
        "dropbox_token_instructions": "**How to obtain a new token:**\n1. Access [dropbox.com/developers/apps](https://www.dropbox.com/developers/apps).\n2. Click on your App (`carroll_rag` or similar).\n3. Go to the **Settings** tab.\n4. Scroll down to the **OAuth 2** section.\n5. Click on the **Generate** button (under *Generated access token*).\n6. Copy the code and paste it below.",
        "dropbox_token_placeholder": "Paste your Dropbox Access Token here:",
        "dropbox_token_updated": "Token updated in session! (Restart app to save in .env permanently)",
        "dropbox_token_missing": "⚠️ Dropbox Token not found. Please insert it above.",
        "dropbox_token_invalid": "The current token seems invalid or expired. Use the 'Configure Token' area above to fix it.",
        "dropbox_current_folder": "Current Folder",
        "dropbox_up_level": "⬆️ Go Up One Level",
        "dropbox_raiz": "Root (/)",
        "dropbox_select_folder_btn": "✅ Select This Folder for Conversion",
        "dropbox_selected_msg": "Folder selected",
        "dropbox_subfolders_caption": "Subfolders (click to enter):",
        "dropbox_no_subfolders": "*(No subfolders found)*",
        "dropbox_ready_msg": "🎯 **Ready to process:** {}",
        "generate_index_dbx_btn": "🧠 Generate PDF Index (Dropbox)",
        "dbx_index_running_spinner": "🧠 Preparing Dropbox files for indexing...",
        "dbx_no_md_found": "No Markdown files found to index.",
        "dbx_downloaded_for_analysis": "Downloaded {} files for analysis.",
        "dbx_rlm_processing_spinner": "🧠 RLM processing and generating PDF...",
        "dbx_index_no_md_warning": "⚠️ No Markdown (.md) files were found to index in this folder. Only files converted to Markdown (.md) can be indexed. Convert your Dropbox files first in the tab above!",
        "dbx_no_index_generated": "No index generated. (Check logs/MD files)",
        "dbx_sending_toast": "Uploading",
        "dbx_index_success": "✅ {} Semantic Indexes successfully generated and uploaded to Dropbox!",
        "youtube_info": "ℹ️ Transcript saved in folder `markdown_output`.",
        "youtube_url_placeholder": "Paste a YouTube URL:",
        "ia_config_subheader": "2. AI Configuration (Optional)",
        "use_gemini_checkbox": "Use Google Gemini AI? (Recommended for poor quality scanned PDFs or complex images)",
        "gemini_key_placeholder": "Paste your Gemini API Key:",
        "gemini_key_valid": "✅ Gemini Key validated!",
        "gemini_force_checkbox": "Force Gemini usage even if Tesseract works?",
        "gemini_force_help": "Bypasses local OCR and uses the cloud for everything (higher cost/time).",
        "gemini_key_invalid": "❌ Invalid Key.",
        "gemini_key_warning": "⚠️ Insert the key to enable AI mode.",
        "overwrite_checkbox": "Overwrite existing Markdown files?",
        "overwrite_help": "If unchecked, the system will skip files that already have an _MD.md version in the folder.",
        "ready_to_process_info": "📁 **Ready to Process:** {}",
        "start_processing_btn": "🚀 Start Processing",
        "processing_youtube": "Processing YouTube",
        "extracting_youtube": "Extracting YouTube transcript...",
        "youtube_transcription_success": "✅ Transcription completed!",
        "youtube_transcription_error": "❌ Failed to obtain transcription. Verify if the video has subtitles.",
        "youtube_url_invalid": "❌ Invalid YouTube URL.",
        "mode_hybrid_upload": "Processing Mode: Hybrid (Web Upload + Gemini Cloud)",
        "mode_local_upload": "Processing Mode: 100% Local (Web Upload + MarkItDown/Tesseract)",
        "processing_upload": "Processing Web Upload...",
        "upload_success": "✅ Upload processed successfully!",
        "mode_hybrid_local": "Processing Mode: Hybrid (Local + Gemini Cloud)",
        "mode_local_local": "Processing Mode: 100% Local (MarkItDown/Tesseract)",
        "processing_local": "Processing Local File...",
        "mode_hybrid_batch": "Batch Mode: Hybrid (Local + Gemini Cloud)",
        "mode_local_batch": "Batch Mode: 100% Local",
        "mode_hybrid_dropbox": "Dropbox Mode: Hybrid (Download -> Process -> Upload)",
        "mode_local_dropbox": "Dropbox Mode: 100% Local (Download -> Process -> Upload)",
        "processing_done_subheader": "✅ Processing Completed",
        "preview_title": "### Content Preview (Markdown)",
        "extracted_content_label": "Extracted Content",
        "download_md_btn": "⬇️ Download Markdown File",
        "clean_old_outputs_btn": "🗑️ Clean Old Output Files",
        "clean_success": "Output folder successfully cleaned!",
        "clean_empty_info": "No files to clean in the output folder.",
        "saved_locally_caption": "File saved locally on the server at: {}",
        "scanning_files": "🔍 Scanning files...",
        "no_supported_files_found": "No supported files found in this folder.",
        "found_incompatible_files": "📂 Found {} incompatible files for conversion.",
        "stop_batch_btn": "🛑 Stop Batch Processing",
        "stop_dbx_btn": "🛑 Stop Dropbox Batch",
        "batch_stopped_by_user": "Processing stopped by user.",
        "batch_skipping_existing": "⏩ Skipping (Already exists): {}",
        "batch_processing_file": "Processing [{}/{}]: {}...",
        "batch_completed_msg": "✅ Completed! Processed: {}. Skipped: {}. Errors: {}.",
        "dbx_token_missing_error": "Dropbox Token not found.",
        "dbx_scanning_files": "☁️ Scanning files on Dropbox...",
        "dbx_no_supported_files": "No supported files found in '{}'.",
        "dbx_found_files": "☁️ Found {} files on Dropbox.",
        "dbx_stopping": "Stopped.",
        "dbx_skipping_existing": "⏩ Skipping (Already exists): {}",
        "dbx_download_processing": "Downloading and Processing [{}/{}]: {}...",
        "dbx_uploading": "⬆️ Uploading",
        "dbx_upload_error": "Upload error for {}",
        "dbx_batch_completed_msg": "✅ Dropbox Batch Completed! Successes: {}. Skipped: {}. Errors: {}.",
        "pdf_digital_detected": "✅ Digital PDF detected. Using MarkItDown/Fallback for structured extraction (Local).",
        "pdf_scanned_detected": "⚠️ Scanned PDF detected. Attempting local OCR (Tesseract) first.",
        "tesseract_success": "✅ Local OCR (Tesseract) completed. Verify the quality.",
        "initiating_gemini_ocr": "Initiating OCR and structuring via Gemini (cost/cloud).",
        "gemini_processing_success": "✅ Gemini processing completed.",
        "gemini_processing_failure": "❌ Gemini processing failed (Content Blocked or API Error).",
        "tesseract_failure": "❌ Tesseract OCR failed.",
        "trying_gemini_fallback": "Attempting OCR and structuring via Gemini (cost/cloud) as fallback.",
        "pdf_processing_failure": "❌ Could not process PDF. Gemini key not provided for fallback.",
        "markitdown_extraction": "✅ File {} detected. Structured extraction via MarkItDown.",
        "unsupported_format": "❌ Unsupported file format '{}'.",
        "file_not_found": "❌ File not found at the specified path.",
        "saving_local_mode": "💾 Local Mode: Saving output in the same folder: {}",
        "saving_upload_mode": "💾 Processing temporary upload and saving result in: {}",
        "saving_upload_mode_simple": "📂 Upload Mode: Saving output in {}"
    }
}

def t(key, *args):
    lang = st.session_state.get('lang', 'pt')
    text = TRANSLATIONS.get(lang, TRANSLATIONS['pt']).get(key, key)
    if args:
        return text.format(*args)
    return text

# --- Configuração da Interface ---
st.set_page_config(
    page_title=t("page_title"),
    layout="wide"
)


# Inicializa o banco de dados SQLite de usuários
auth.init_db()

# --- Inicialização de Estado de Autenticação ---
if 'lang' not in st.session_state:
    st.session_state['lang'] = 'pt'
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False
if 'needs_password_change' not in st.session_state:
    st.session_state['needs_password_change'] = False

def show_login_screen():
    # Centraliza o card de login na tela com estilo moderno (Glassmorphism)
    st.markdown("""
        <style>
        .login-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            padding-top: 50px;
        }
        .login-container {
            width: 450px;
            padding: 40px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.2);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        .login-title {
            font-size: 36px;
            font-weight: 800;
            background: linear-gradient(135deg, #1E90FF 0%, #3CB371 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        .login-subtitle {
            font-size: 14px;
            color: #888;
            margin-bottom: 24px;
        }
        /* Customizar os campos de texto no login */
        div[data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
            background-color: transparent !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="login-title">📄 PDFtoMD</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="login-subtitle">{t("login_subtitle")}</p>', unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input(t("username"), placeholder=t("username_placeholder"))
        password = st.text_input(t("password"), type="password", placeholder=t("password_placeholder"))
        submit_button = st.form_submit_button(t("enter"), use_container_width=True)
        
        if submit_button:
            user = auth.authenticate_user(username, password)
            if user:
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = user['id']
                st.session_state['username'] = user['username']
                st.session_state['is_admin'] = user['is_admin']
                st.session_state['needs_password_change'] = user['needs_password_change']
                st.success(t("login_success"))
                st.rerun()
            else:
                st.error(t("login_error"))
                
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_change_password_on_first_login_screen():
    st.markdown("""
        <style>
        .change-pwd-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            padding-top: 50px;
        }
        .change-pwd-container {
            width: 480px;
            padding: 40px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.2);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        .change-pwd-title {
            font-size: 28px;
            font-weight: 800;
            color: #FF8C00;
            margin-bottom: 8px;
        }
        .change-pwd-subtitle {
            font-size: 14px;
            color: #ccc;
            margin-bottom: 24px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="change-pwd-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="change-pwd-container">', unsafe_allow_html=True)
    st.markdown(f'<h2 class="change-pwd-title">{t("forced_change_pwd_title")}</h2>', unsafe_allow_html=True)
    st.markdown(f'<p class="change-pwd-subtitle">{t("forced_change_pwd_subtitle")}</p>', unsafe_allow_html=True)
    
    with st.form("forced_change_pwd_form", clear_on_submit=False):
        new_pwd = st.text_input(t("new_pwd"), type="password", placeholder=t("new_pwd_placeholder"))
        confirm_pwd = st.text_input(t("confirm_pwd"), type="password", placeholder=t("confirm_pwd_placeholder"))
        submit_btn = st.form_submit_button(t("change_pwd_btn"), use_container_width=True)
        
        if submit_btn:
            if not new_pwd:
                st.error(t("pwd_blank_error"))
            elif len(new_pwd) < 6:
                st.error(t("pwd_min_len_error"))
            elif new_pwd == "123456":
                st.error(t("pwd_default_error"))
            elif new_pwd != confirm_pwd:
                st.error(t("pwd_mismatch_error"))
            else:
                user_id = st.session_state.get('user_id')
                if user_id:
                    success, msg = auth.change_password_on_first_login(user_id, new_pwd)
                    if success:
                        st.session_state['needs_password_change'] = False
                        st.success(t("pwd_change_success"))
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error(t("system_error_login"))
                    st.session_state['authenticated'] = False
                    st.rerun()
                    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state['authenticated']:
    show_login_screen()
    st.stop()

if st.session_state.get('needs_password_change', False):
    show_change_password_on_first_login_screen()
    st.stop()


# --- Estilo CSS para melhor visualização ---
st.markdown("""
    <style>
    /* Aumenta o tamanho da fonte geral para melhor leitura */
    html, body, [class*="stText"] {
        font-size: 16px;
    }
    /* Estilo para cabeçalhos */
    h1 { color: #1E90FF; } /* Azul para o título principal */
    h3 { color: #3CB371; } /* Verde para subtítulos */
    /* Estilo para o text_area de visualização */
    [data-testid="stTextarea"] textarea {
        font-family: monospace;
        font-size: 14px;
    }
    
    /* Botão Verde Personalizado */
    div.stButton > button {
        background-color: #28a745;
        color: white;
        border: none;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #218838;
        color: white;
        border-color: #1e7e34;
    }
    div.stButton > button:active {
        background-color: #1e7e34;
        color: white;
        border-color: #1e7e34;
    }
    div.stButton > button:active {
        background-color: #1e7e34;
        color: white;
        border-color: #1e7e34;
    }
    </style>
    """, unsafe_allow_html=True)

# Inicialização de Estado
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = os.getenv("GOOGLE_GEMINI_API_KEY", "")

if 'dropbox_token' not in st.session_state:
    st.session_state['dropbox_token'] = os.getenv("DROPBOX_ACCESS_TOKEN", "")

if 'processed_file' not in st.session_state:
    st.session_state['processed_file'] = None
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None
if 'reset_counter' not in st.session_state:
    st.session_state['reset_counter'] = 0

# --- Funções de Utilidade ---

def clean_output_directory(output_dir_name="markdown_output"):
    """
    Remove todos os arquivos .md da pasta de saída.
    """
    output_path = Path(output_dir_name)
    if output_path.exists():
        files_to_remove = list(output_path.glob("*.md"))
        if files_to_remove:
            st.info(f"Limpando {len(files_to_remove)} arquivos antigos da pasta de saída...")
            for file_path in files_to_remove:
                try:
                    os.remove(file_path)
                except Exception as e:
                    st.warning(f"Não foi possível remover o arquivo {file_path}: {e}")
            return True
    return False

def validate_gemini_api_key(api_key: str) -> bool:
    """Tenta configurar o SDK e listar modelos para validar a chave API."""
    if not api_key:
        return False
    try:
        genai.configure(api_key=api_key)
        # Tenta listar modelos para garantir que a chave é válida
        list(genai.list_models())
        return True
    except Exception:
        return False

def run_file_pipeline(input_path_str: str, output_path_str: str, gemini_key: str):
    """
    Executa o pipeline de conversão (Core Logic).
    Retorna True se sucesso, False caso contrário.
    """
    input_path = Path(input_path_str)
    file_extension = input_path.suffix.lower()

    # --- LÓGICA CORE DE PROCESSAMENTO ---
    if file_extension == '.pdf':
        is_digital = is_digital_pdf(input_path_str)
        
        if is_digital:
            st.success(t("pdf_digital_detected"))
            extract_structured_markitdown(input_path_str, output_path_str)
            
        else:
            st.warning(t("pdf_scanned_detected"))
            
            # TENTATIVA 1: OCR LOCAL (Tesseract)
            tesseract_success = ocr_local_tesseract(input_path_str, output_path_str)
            
            if tesseract_success:
                st.success(t("tesseract_success"))
                
                if gemini_key and st.session_state.get('force_gemini', False):
                    st.info(t("initiating_gemini_ocr"))
                    success = extract_ocr_to_markdown_gemini(input_path_str, output_path_str, gemini_key)
                    if success:
                        st.success(t("gemini_processing_success"))
                    else:
                        st.error(t("gemini_processing_failure"))
            
            elif gemini_key:
                st.error(t("tesseract_failure"))
                st.info(t("trying_gemini_fallback"))
                success = extract_ocr_to_markdown_gemini(input_path_str, output_path_str, gemini_key)
                if success:
                    st.success(t("gemini_processing_success"))
                else:
                    st.error(t("gemini_processing_failure"))
            else:
                st.error(t("pdf_processing_failure"))
                return False
                    
    elif file_extension in ['.docx', '.pptx', '.xlsx', '.doc', '.xls', '.csv', '.json', '.xml', '.html', '.zip', '.mp3', '.wav', '.jpg', '.png', '.epub']:
        # NOVA LÓGICA: Extração direta via MarkItDown para outros formatos
        st.success(t("markitdown_extraction").format(file_extension))
        extract_structured_markitdown(input_path_str, output_path_str) 
        
    else:
        st.error(t("unsupported_format").format(file_extension))
        return False

    return True

def process_local_file(local_path_str, gemini_key):
    """
    Processa um arquivo local, salvando na MESMA pasta original.
    """
    path = Path(local_path_str).resolve()
    if not path.exists():
        st.error(t("file_not_found"))
        return None
        
    # Salva na mesma pasta: NomeOriginalMD.md
    output_path = path.parent / f"{path.stem}MD.md"
    
    st.info(t("saving_local_mode", output_path))
    
    success = run_file_pipeline(str(path), str(output_path), gemini_key)
    return output_path if success else None

def process_uploaded_file(uploaded_file, gemini_key):
    """
    Salva o arquivo enviado via web temporariamente, processa-o e gera o Markdown de saída na pasta markdown_output.
    Retorna o caminho do arquivo Markdown gerado.
    """
    # 1. Cria pasta temporária de uploads
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    # Salva o arquivo temporariamente com seu nome original
    temp_file_path = temp_dir / uploaded_file.name
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    # 2. Cria pasta de saída de markdown se não existir
    output_dir = Path("markdown_output")
    output_dir.mkdir(exist_ok=True)
    
    output_md_path = output_dir / f"{temp_file_path.prefix if hasattr(temp_file_path, 'prefix') else temp_file_path.stem}MD.md"
    
    st.info(t("saving_upload_mode", output_md_path))
    
    # 3. Executa o pipeline
    success = run_file_pipeline(str(temp_file_path), str(output_md_path), gemini_key)
    
    # 4. Remove o arquivo temporário original para manter o sistema limpo
    try:
        if temp_file_path.exists():
            os.remove(temp_file_path)
    except Exception as e:
        print(f"Erro ao remover arquivo temporário {temp_file_path}: {e}")
        
    return output_md_path if success else None

def process_batch_directory(directory_path_str: str, gemini_key: str, overwrite: bool = False):
    """
    Varre um diretório recursivamente e converte arquivos suportados.
    Args:
        overwrite: Se True, refaz arquivos já existentes. Se False, pula.
    """
    root_dir = Path(directory_path_str).resolve()
    if not root_dir.exists() or not root_dir.is_dir():
        st.error("❌ Diretório inválido.")
        return
    
    supported_extensions = {'.pdf', '.docx', '.pptx', '.xlsx', '.doc', '.xls', '.csv', '.json', '.xml', '.html', '.zip', '.mp3', '.wav', '.jpg', '.png', '.epub'}
    files_to_process = []
    
    # 1. Varredura
    status_text = st.empty()
    status_text.info(t("scanning_files"))
    
    for path in root_dir.rglob('*'):
        if path.is_file() and path.suffix.lower() in supported_extensions:
            files_to_process.append(path)
            
    if not files_to_process:
        st.warning(t("no_supported_files_found"))
        return

    st.success(t("found_incompatible_files").format(len(files_to_process)))
    
    # 2. Barra de Progresso
    progress_bar = st.progress(0)
    log_area = st.empty()
    
    processed_count = 0
    skipped_count = 0 # NOVO
    errors_count = 0
    
    stop_button = st.button(t("stop_batch_btn"))
    
    for i, file_path in enumerate(files_to_process):
        if stop_button:
            st.warning(t("batch_stopped_by_user"))
            break
            
        rel_path = file_path.relative_to(root_dir)
        
        # Define saída: Nome_MD.md (na mesma pasta)
        output_path = file_path.parent / f"{file_path.stem}MD.md"
        
        # LÓGICA INCREMENTAL
        if output_path.exists() and not overwrite:
            log_area.code(t("batch_skipping_existing", rel_path))
            skipped_count += 1
            progress = (i + 1) / len(files_to_process)
            progress_bar.progress(progress)
            continue

        log_area.code(t("batch_processing_file", i+1, len(files_to_process), rel_path))

        try:
             # Chama Pipeline
             success = run_file_pipeline(str(file_path), str(output_path), gemini_key)
             if success:
                 processed_count += 1
             else:
                 errors_count += 1
        except Exception as e:
             print(f"Erro no batch para {file_path}: {e}")
             errors_count += 1

        # Atualiza progresso
        progress = (i + 1) / len(files_to_process)
        progress_bar.progress(progress)
    
    status_text.success(t("batch_completed_msg", processed_count, skipped_count, errors_count))
    st.balloons()


def process_dropbox_batch(folder_path_str: str, gemini_key: str, overwrite: bool = False):
    """
    Processamento em lote via Dropbox (Download -> Convert -> Upload).
    Args:
        overwrite: Se True, refaz arquivos já existentes. Se False, pula.
    """
    token = st.session_state.get('dropbox_token')
    if not token:
        st.error(t("dbx_token_missing_error"))
        return

    dbx = DropboxHandler(token)
    
    # 1. Verifica Conexão
    status, msg = dbx.check_connection()
    if not status:
        st.error(msg)
        return
        
    st.toast(msg, icon="☁️")
    
    # 2. Varredura
    supported_extensions = {'.pdf', '.docx', '.pptx', '.xlsx', '.doc', '.xls', '.csv', '.json', '.xml', '.html', '.zip', '.mp3', '.wav', '.jpg', '.png', '.epub'}
    
    with st.spinner(t("dbx_scanning_files")):
        file_entries = dbx.list_files_recursive(folder_path_str, supported_extensions)
        
    if not file_entries:
        st.warning(t("dbx_no_supported_files").format(folder_path_str))
        return
        
    st.success(t("dbx_found_files").format(len(file_entries)))
    
    # 3. Processamento
    progress_bar = st.progress(0)
    log_area = st.empty()
    stop_button = st.button(t("stop_dbx_btn"))
    
    temp_dir = Path("temp_dropbox")
    temp_dir.mkdir(exist_ok=True)
    
    processed_count = 0
    skipped_count = 0 # NOVO
    errors_count = 0
    
    for i, entry in enumerate(file_entries):
        if stop_button:
            st.warning(t("dbx_stopping"))
            break
            
        local_output_name = f"{Path(entry.name).stem}MD.md"
        # Dropbox Output Path
        dropbox_output_path = f"{Path(entry.path_display).parent.as_posix()}/{local_output_name}"
        if dropbox_output_path.startswith("//"):
             dropbox_output_path = dropbox_output_path[1:]

        # LÓGICA INCREMENTAL (DROPBOX)
        if not overwrite:
            # Verifica se existe chamando metadados
            if dbx.file_exists(dropbox_output_path):
                 log_area.code(t("dbx_skipping_existing", entry.path_display))
                 skipped_count += 1
                 progress_bar.progress((i + 1) / len(file_entries))
                 continue

        log_area.code(t("dbx_download_processing", i+1, len(file_entries), entry.path_display))
        
        # Paths do download temporário
        local_input = temp_dir / entry.name
        local_output = temp_dir / local_output_name
        
        try:
            # Download
            if dbx.download_file(entry.path_display, str(local_input)):
                # Converte
                if run_file_pipeline(str(local_input), str(local_output), gemini_key):
                    # Upload
                    log_area.code(t("dbx_uploading") + f": {dropbox_output_path}")
                    if dbx.upload_file(str(local_output), dropbox_output_path):
                         processed_count += 1
                    else:
                         errors_count += 1
                         st.error(t("dbx_upload_error").format(entry.name))
                else:
                    errors_count += 1
            else:
                 errors_count += 1
        except Exception as e:
            st.error(f"Erro DBX: {e}")
            errors_count += 1
        finally:
            # Limpeza Temp
            if local_input.exists(): os.remove(local_input)
            if local_output.exists(): os.remove(local_output)

        progress_bar.progress((i + 1) / len(file_entries))
        
    st.success(t("dbx_batch_completed_msg", processed_count, skipped_count, errors_count))
    st.balloons()


def process_uploaded_file(uploaded_file, gemini_key): # RENOMEADO
    """
    Salva o arquivo temporariamente e executa o pipeline principal.
    Retorna o caminho do arquivo Markdown gerado.
    """
    # 1. Salvar arquivo temporariamente
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    pdf_path = temp_dir / uploaded_file.name
    
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # 2. Definir Caminho de Saída (Browser Limit: pasta markdown_output)
    output_dir = Path("markdown_output")
    output_dir.mkdir(exist_ok=True)
    
    # NAMING CHANGE: NomeOriginalMD.md
    output_md_path = output_dir / f"{pdf_path.stem}MD.md"
    
    st.info(t("saving_upload_mode_simple", output_md_path))
    
    # 3. Executar Pipeline
    success = run_file_pipeline(str(pdf_path), str(output_md_path), gemini_key)
    
    # 4. Limpeza e Retorno
    os.remove(pdf_path)
    return output_md_path if success else None

# --- Layout da Aplicação ---

# --- Barra Lateral (Controle de Navegação e Logout) ---
with st.sidebar:
    st.markdown("### " + t("connected_user"))
    role_badge = t("role_admin") if st.session_state['is_admin'] else t("role_user")
    st.markdown(f"**{t('label_name')}:** `{st.session_state['username']}`")
    st.markdown(f"**{t('label_profile')}:** {role_badge}")
    
    # Alerta de Segurança se o admin estiver usando a senha padrão
    if st.session_state['username'] == 'admin':
        if auth.authenticate_user("admin", "admin123"):
            st.warning(t("security_alert"))
            
    st.markdown("---")
    
    # Navegação de Telas (Somente visível para Admin)
    app_mode = t("nav_process_docs")
    if st.session_state['is_admin']:
        app_mode = st.radio(
            t("navigation"),
            [t("nav_process_docs"), t("nav_user_mgmt")],
            key="nav_mode"
        )
    
    st.markdown("---")
    # Language Selector UI
    lang_choice = st.selectbox(
        "🌐 Idioma / Language",
        ["Português", "English"],
        index=0 if st.session_state.get('lang', 'pt') == 'pt' else 1,
        key="lang_choice_selectbox"
    )
    new_lang = "pt" if lang_choice == "Português" else "en"
    if new_lang != st.session_state.get('lang', 'pt'):
        st.session_state['lang'] = new_lang
        st.rerun()

    st.markdown("---")
    if st.button(t("logout_btn"), use_container_width=True):
        st.session_state['authenticated'] = False
        st.session_state['username'] = ""
        st.session_state['is_admin'] = False
        st.success(t("logout_success"))
        st.rerun()

# --- Conteúdo Principal dependendo da Seleção ---
if app_mode == t("nav_user_mgmt"):
    st.title(t("user_mgmt_title"))
    st.markdown("---")
    
    tab_list, tab_create = st.tabs([t("tab_registered_users"), t("tab_create_user")])
    
    with tab_list:
        users = auth.list_users()
        
        for u in users:
            u_id = u['id']
            u_name = u['username']
            u_admin = u['is_admin']
            
            with st.container(border=True):
                col_info, col_actions = st.columns([2, 1], vertical_alignment="center")
                with col_info:
                    badge = t("status_badge_admin") if u_admin else t("status_badge_user")
                    status_badge = t("status_badge_pwd_pending") if u.get('needs_password_change') else ""
                    st.markdown(f"**{t('username')}:** `{u_name}` &nbsp;&nbsp;&nbsp; {badge}{status_badge}")
                    st.caption(f"{t('created_at')}: {u['created_at']} | {t('updated_at')}: {u['updated_at']}")
                
                with col_actions:
                    col_edit, col_pwd, col_del = st.columns(3)
                    
                    with col_edit:
                        if st.button("✏️", key=f"edit_{u_id}", help=t("edit_user_help")):
                            st.session_state[f"show_edit_{u_id}"] = not st.session_state.get(f"show_edit_{u_id}", False)
                            st.session_state[f"show_pwd_{u_id}"] = False
                            st.session_state[f"show_del_{u_id}"] = False
                            st.rerun()
                            
                    with col_pwd:
                        if st.button("🔑", key=f"pwd_{u_id}", help=t("reset_pwd_help")):
                            st.session_state[f"show_pwd_{u_id}"] = not st.session_state.get(f"show_pwd_{u_id}", False)
                            st.session_state[f"show_edit_{u_id}"] = False
                            st.session_state[f"show_del_{u_id}"] = False
                            st.rerun()
                            
                    with col_del:
                        if st.button("🗑️", key=f"del_{u_id}", help=t("delete_user_help")):
                            st.session_state[f"show_del_{u_id}"] = not st.session_state.get(f"show_del_{u_id}", False)
                            st.session_state[f"show_edit_{u_id}"] = False
                            st.session_state[f"show_pwd_{u_id}"] = False
                            st.rerun()
                
                # Seções expansíveis de ação
                if st.session_state.get(f"show_edit_{u_id}", False):
                    st.markdown(t("edit_user_section_title"))
                    new_u_name = st.text_input(t("new_username_label"), value=u_name, key=f"input_edit_name_{u_id}")
                    new_u_admin = st.checkbox(t("admin_checkbox_label"), value=u_admin, key=f"input_edit_admin_{u_id}")
                    if st.button(t("confirm_edit_btn"), key=f"btn_edit_confirm_{u_id}", type="primary"):
                        success, msg = auth.update_user(u_id, new_u_name, new_u_admin)
                        if success:
                            st.success(msg)
                            st.session_state[f"show_edit_{u_id}"] = False
                            st.rerun()
                        else:
                            st.error(msg)
                            
                if st.session_state.get(f"show_pwd_{u_id}", False):
                    st.markdown(t("reset_pwd_section_title"))
                    new_pwd = st.text_input(t("new_pwd"), type="password", key=f"input_pwd_{u_id}")
                    if st.button(t("reset_pwd_confirm_btn"), key=f"btn_pwd_confirm_{u_id}", type="primary"):
                        success, msg = auth.reset_password(u_id, new_pwd)
                        if success:
                            st.success(msg)
                            st.session_state[f"show_pwd_{u_id}"] = False
                            st.rerun()
                        else:
                            st.error(msg)
                            
                if st.session_state.get(f"show_del_{u_id}", False):
                    st.warning(t("delete_user_warning").format(u_name))
                    if st.button(t("delete_user_yes"), key=f"btn_del_confirm_{u_id}", type="primary"):
                        success, msg = auth.delete_user(u_id, st.session_state['username'])
                        if success:
                            st.success(msg)
                            st.session_state[f"show_del_{u_id}"] = False
                            st.rerun()
                        else:
                            st.error(msg)
                            
    with tab_create:
        st.markdown("### " + t("tab_create_user"))
        st.info(t("create_user_info"))
        with st.form("create_user_form", clear_on_submit=True):
            new_username = st.text_input(t("new_username_label"), placeholder=t("new_username_placeholder"))
            new_is_admin = st.checkbox(t("admin_privileges_checkbox"))
            create_submit = st.form_submit_button(t("create_user_btn"), use_container_width=True)
            
            if create_submit:
                success, msg = auth.create_user(new_username, new_is_admin)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    st.stop() # Interrompe a execução aqui para administradores na tela de Gestão de Usuários

# --- Layout da Aplicação Original ---
st.title(t("process_docs_title"))
st.markdown("---")

# 1. Entrada de Dados (MOVIDO PARA O TOPO)
st.subheader(t("input_data_subheader"))

col_input1, col_input2 = st.columns([1, 1])

# Nova Interface com Tabs: Arquivo Local, Pasta (Lote), Dropbox, YouTube
tab_local, tab_batch, tab_dropbox, tab_youtube = st.tabs([t("tab_local_file"), t("tab_batch_folder"), t("tab_dropbox"), t("tab_youtube")])

with tab_local:
    if IS_HEADLESS:
        st.info(t("local_tab_headless_info"))
        uploaded_file = st.file_uploader(
            t("local_tab_headless_uploader"),
            type=['pdf', 'docx', 'pptx', 'xlsx', 'doc', 'xls', 'csv', 'json', 'xml', 'html', 'zip', 'mp3', 'wav', 'jpg', 'png', 'epub'],
            key=f"file_uploader_{st.session_state['reset_counter']}"
        )
        if uploaded_file:
            st.session_state['uploaded_file'] = uploaded_file
            # Limpa outras seleções para evitar conflitos
            st.session_state['selected_local_path'] = None
            st.session_state['selected_batch_dir'] = None
            st.session_state['dbx_selected_for_processing'] = None
    else:
        st.info(t("local_tab_info"))
        
        col_btn, col_txt = st.columns([1, 4], vertical_alignment="bottom")
        
        with col_btn:
            if st.button(t("local_tab_select_btn"), use_container_width=True):
                import subprocess, sys
                code = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)
path = filedialog.askopenfilename(
    title=t("local_tab_headless_uploader"),
    filetypes=[
        (t("all_supported"), '*.pdf *.docx *.pptx *.xlsx *.doc *.xls *.csv *.json *.xml *.html *.zip *.mp3 *.wav *.jpg *.png *.epub'),
        (t("pdf_docs"), '*.pdf'),
        (t("all_files"), '*.*')
    ]
)
print(path)
"""
                result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
                file_path = result.stdout.strip()
                
                if file_path:
                    st.session_state['selected_local_path'] = file_path
                    st.session_state['uploaded_file'] = None
                    # Limpa outras seleções
                    st.session_state['selected_batch_dir'] = None
                    st.session_state['dbx_selected_for_processing'] = None
                    st.session_state['processed_file'] = None
                    st.rerun() 
        
        with col_txt:
            # Mostra o caminho selecionado (Usa st.code para garantir atualização visual)
            current_path = st.session_state.get('selected_local_path', '')
            if current_path:
                 st.code(current_path, language=None)
            else:
                 st.info(t("local_tab_no_selection"), icon="ℹ️")

with tab_batch:
    if IS_HEADLESS:
        st.warning(t("batch_tab_headless_warning"))
    else:
        st.info(t("batch_tab_info"))
        
        col_btn_batch, col_txt_batch = st.columns([1, 4], vertical_alignment="bottom")
        
        with col_btn_batch:
            if st.button(t("batch_tab_select_btn"), use_container_width=True):
                import subprocess, sys
                code = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)
path = filedialog.askdirectory(title=t("batch_tab_select_btn"))
print(path)
"""
                result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
                dir_path = result.stdout.strip()
                
                if dir_path:
                    st.session_state['selected_batch_dir'] = dir_path
                    st.session_state['uploaded_file'] = None
                    # Limpa outras seleções
                    st.session_state['selected_local_path'] = None
                    st.session_state['dbx_selected_for_processing'] = None
                    st.session_state['processed_file'] = None
                    st.rerun()
                    
        with col_txt_batch:
            current_dir = st.session_state.get('selected_batch_dir', '')
            if current_dir:
                st.code(current_dir, language=None)
            else:
                st.info(t("batch_tab_no_selection"), icon="ℹ️")
            
            # --- RLM INDEX GENERATION (LOCAL) ---
            if current_dir:
                st.divider()
                st.subheader(t("semantic_index_title"))
                if st.button(t("generate_index_local_btn"), key="btn_index_local_main"):
                    gemini_key = st.session_state.get('api_key')
                    if not gemini_key:
                        st.error(t("gemini_key_required_error"))
                    else:
                        with st.spinner(t("index_running_spinner")):
                            indexed_count = generate_index_for_folder(current_dir, gemini_key, recursive=True)
                        if indexed_count > 0:
                            st.success(t("index_success").format(indexed_count))
                        else:
                            st.warning(t("index_no_md_warning"))

with tab_dropbox:
    st.info(t("dropbox_info"))
    
    # Init State
    if 'dbx_current_path' not in st.session_state:
        st.session_state['dbx_current_path'] = "" # Root
    if 'dbx_selected_for_processing' not in st.session_state:
        st.session_state['dbx_selected_for_processing'] = None 

    # --- NOVA ÁREA DE CONFIGURAÇÃO DO TOKEN ---
    with st.expander(t("dropbox_token_expander")):
        st.markdown(t("dropbox_token_instructions"))
        
        new_token = st.text_input(
            t("dropbox_token_placeholder"), 
            value=st.session_state.get('dropbox_token', ''),
            type="password",
            help="Este token deve ter permissões de leitura e escrita (files.content.write)."
        )
        
        if new_token and new_token != st.session_state.get('dropbox_token'):
            st.session_state['dropbox_token'] = new_token
            st.success(t("dropbox_token_updated"))
            st.rerun()

    # Validação Básica de Token
    if not st.session_state.get('dropbox_token'):
        st.warning(t("dropbox_token_missing"))
    else:
        # Instancia Handler
        dbx = DropboxHandler(st.session_state['dropbox_token'])
        
        # 1. VERIFICAÇÃO PREVENTIVA DE CONEXÃO
        is_connected, msg_connection = dbx.check_connection()
        
        if not is_connected:
            st.warning(f"⚠️ {msg_connection}")
            st.error(t("dropbox_token_invalid"))
        else:
            # --- Interface de Navegação (Somente se conectado) ---
            current = st.session_state['dbx_current_path']
            display_path = current if current else "Raiz (/)"
            
            st.markdown(f"**📂 {t('dropbox_current_folder')}:** `{display_path}`")
            
            # Botões de Ação (Voltar / Selecionar)
            col_nav_1, col_nav_2 = st.columns([1, 4])
        
            with col_nav_1:
                if current != "":
                    if st.button(t("dropbox_up_level"), use_container_width=True):
                        # Remove o último segmento do path
                        st.session_state['dbx_current_path'] = str(Path(current).parent).replace("\\", "/")
                        if st.session_state['dbx_current_path'] == ".": 
                            st.session_state['dbx_current_path'] = ""
                        st.rerun()
                else:
                    st.button(t("dropbox_up_level") + " (" + t("dropbox_raiz") + ")", disabled=True, use_container_width=True)
                    
            with col_nav_2:
                 if st.button(t("dropbox_select_folder_btn"), use_container_width=True, type="primary"):
                     st.session_state['dbx_selected_for_processing'] = current if current else ""
                     # Limpa outras seleções para evitar conflito
                     st.session_state['selected_local_path'] = None
                     st.session_state['selected_batch_dir'] = None
                     st.session_state['processed_file'] = None
                     
                     st.success(t("dropbox_selected_msg") + f": {display_path}")
                     st.rerun()

            st.divider()
            st.caption(t("dropbox_subfolders_caption"))
            
            # Listagem de Subpastas
            subfolders = dbx.list_subfolders(current)
            
            if not subfolders:
                st.caption(t("dropbox_no_subfolders"))
            else:
                # Grid de pastas para economizar espaço
                cols = st.columns(3)
                for idx, folder in enumerate(subfolders):
                    # Distribui entre colunas
                    with cols[idx % 3]:
                        if st.button(f"📁 {folder.name}", key=f"btn_folder_{folder.id}", use_container_width=True):
                            st.session_state['dbx_current_path'] = folder.path_display
                            st.rerun()

    # Mostra qual foi selecionada para o "Motor" do app
    selected_dbx = st.session_state.get('dbx_selected_for_processing')
    if selected_dbx is not None:
         st.success(t("dropbox_ready_msg").format(selected_dbx if selected_dbx else t("dropbox_raiz")))
         
         # --- RLM INDEX GENERATION (DROPBOX) ---
         st.divider()
         st.subheader(t("semantic_index_title"))
         
         if st.button(t("generate_index_dbx_btn"), key="btn_index_dbx_main"):
            gemini_key = st.session_state.get('api_key')
            if not gemini_key:
                st.error(t("gemini_key_required_error"))
            else:
                # Lógica Específica para Dropbox
                dest_path = selected_dbx if selected_dbx else ""
                with st.spinner(t("dbx_index_running_spinner")):
                    # 1. Criar temp dir
                    index_temp_dir = Path("temp_dropbox_index")
                    index_temp_dir.mkdir(exist_ok=True)
                    
                    # 2. Listar apenas MDs
                    md_entries = dbx.list_files_recursive(dest_path, {'.md'})
                    
                    if not md_entries:
                        st.warning(t("dbx_no_md_found"))
                    else:
                        downloaded_count = 0
                        for entry in md_entries:
                            # Mantém estrutura relativa
                            if dest_path:
                                 rel_path = entry.path_display.replace(dest_path, "", 1).lstrip("/")
                            else:
                                 rel_path = entry.path_display.lstrip("/")
                                 
                            local_dest = index_temp_dir / rel_path
                            local_dest.parent.mkdir(parents=True, exist_ok=True)
                            
                            dbx.download_file(entry.path_display, str(local_dest))
                            downloaded_count += 1
                        
                        st.info(t("dbx_downloaded_for_analysis").format(downloaded_count))
                        
                        # 3. Gerar Índice
                        with st.spinner(t("dbx_rlm_processing_spinner")):
                            indexed_count = generate_index_for_folder(str(index_temp_dir), gemini_key, recursive=True)
                        
                        if indexed_count == 0:
                            st.warning(t("dbx_index_no_md_warning"))
                        else:
                            # 4. Upload
                            pdf_files = list(index_temp_dir.rglob("_INDEX_CONTENT*.pdf"))
                            if not pdf_files:
                                st.error(t("dbx_no_index_generated"))
                            else:
                                uploaded_indexes = 0
                                for pdf in pdf_files:
                                    rel_pdf_path = pdf.relative_to(index_temp_dir)
                                    base = dest_path if dest_path != "" else ""
                                    remote_pdf_path = f"{base}/{rel_pdf_path.as_posix()}"
                                    if remote_pdf_path.startswith("//"): remote_pdf_path = remote_pdf_path[1:]
                                    
                                    st.toast(t("dbx_sending_toast") + f": {rel_pdf_path.name}")
                                    dbx.upload_file(str(pdf), remote_pdf_path)
                                    uploaded_indexes += 1
                                
                                st.success(t("dbx_index_success").format(uploaded_indexes))
                        
                        # Limpeza
                        import shutil
                        shutil.rmtree(index_temp_dir, ignore_errors=True)

with tab_youtube:
    st.caption(t("youtube_info"))
    # Usa reset_counter no key para forçar recriação do widget ao limpar
    youtube_url = st.text_input(
        t("youtube_url_placeholder"), 
        placeholder="https://www.youtube.com/watch?v=...", 
        key=f"youtube_url_{st.session_state['reset_counter']}"
    )

st.markdown("---")

# 2. Configuração Opcional (Gemini)
st.subheader(t("ia_config_subheader"))

use_gemini = st.checkbox(t("use_gemini_checkbox"))

if use_gemini:
    gemini_key_input = st.text_input(t("gemini_key_placeholder"), type="password", key="gemini_key_in")
    if gemini_key_input:
        if validate_gemini_api_key(gemini_key_input):
            st.session_state['api_key'] = gemini_key_input
            st.success(t("gemini_key_valid"))
            
            # Opção de forçar
            st.checkbox(
                t("gemini_force_checkbox"), 
                key="force_gemini",
                help=t("gemini_force_help")
            )
        else:
            st.error(t("gemini_key_invalid"))
            st.session_state['api_key'] = None
    else:
        st.warning(t("gemini_key_warning"))
        st.session_state['api_key'] = None
else:
    st.session_state['api_key'] = None

# Nova Opção: Sobrescrever
force_overwrite = st.checkbox(
    t("overwrite_checkbox"), 
    value=False,
    help=t("overwrite_help")
)

st.markdown("---")


# Validação do trigger (qual tab tem input?)
has_input = False
input_name = "Desconhecido"
selected_local_path = st.session_state.get('selected_local_path')
selected_batch_dir = st.session_state.get('selected_batch_dir')
# Dropbox input (Seleção via Navegador)
dropbox_selected_processing = st.session_state.get('dbx_selected_for_processing')
uploaded_file = st.session_state.get('uploaded_file')

if uploaded_file:
    has_input = True
    input_name = f"Upload Web: {uploaded_file.name}"
elif selected_local_path:
    has_input = True
    input_name = f"Arquivo Local: {os.path.basename(selected_local_path)}"
elif selected_batch_dir:
    has_input = True
    input_name = f"Lote Local: {os.path.basename(selected_batch_dir)}"
elif dropbox_selected_processing is not None:
    has_input = True
    display_name = dropbox_selected_processing if dropbox_selected_processing else "Raiz (/)"
    input_name = f"Dropbox: {display_name}"
elif youtube_url:
    has_input = True
    input_name = f"YouTube: {youtube_url}"

if has_input:
    
    # Feedback Visual de Prontidão
    st.info(t("ready_to_process_info").format(input_name))
    
    # Botão de Processamento
    if st.button(t("start_processing_btn"), use_container_width=True):
        st.session_state['processed_file'] = None
        
        # 1. YouTube
        if youtube_url:
             if is_youtube_url(youtube_url):
                 st.info(t("processing_youtube") + f": {youtube_url}")
                 output_dir = Path("markdown_output")
                 output_dir.mkdir(exist_ok=True)
                 # Cria um nome de arquivo seguro a partir da URL (simplificado)
                 video_id = youtube_url.split("v=")[-1].split("&")[0]
                 output_md_path = output_dir / f"youtube_{video_id}.md"
                 
                 with st.spinner(t("extracting_youtube")):
                     success = extract_youtube_transcript(youtube_url, str(output_md_path))
                     if success:
                         st.session_state['processed_file'] = str(output_md_path)
                         st.success(t("youtube_transcription_success"))
                     else:
                         st.error(t("youtube_transcription_error"))
             else:
                 st.error(t("youtube_url_invalid"))

        # 2. Upload Web (Headless)
        elif uploaded_file:
            if st.session_state['api_key']:
                st.info(t("mode_hybrid_upload"))
            else:
                st.info(t("mode_local_upload"))
                
            with st.spinner(t("processing_upload")):
                 output_path = process_uploaded_file(uploaded_file, st.session_state['api_key'])
                 if output_path:
                     st.session_state['processed_file'] = str(output_path)
                     st.success(t("upload_success"))

        # 3. Arquivo Local (Via Dialogo Nativo)
        elif selected_local_path:
            
            if st.session_state['api_key']:
                st.info(t("mode_hybrid_local"))
            else:
                st.info(t("mode_local_local"))
                
            with st.spinner(t("processing_local")):
                 output_path = process_local_file(selected_local_path, st.session_state['api_key'])
                 if output_path:
                     st.session_state['processed_file'] = str(output_path)
        
        # 3. Lote (Pasta)
        elif selected_batch_dir:
             if st.session_state['api_key']:
                st.info(t("mode_hybrid_batch"))
             else:
                st.info(t("mode_local_batch"))
             
             # Chama a função de lote (ela gerencia seu próprio spinner/progresso)
             process_batch_directory(selected_batch_dir, st.session_state['api_key'], overwrite=force_overwrite)
        
        # 4. Dropbox Batch
        elif dropbox_selected_processing is not None:
             if st.session_state['api_key']:
                st.info(t("mode_hybrid_dropbox"))
             else:
                st.info(t("mode_local_dropbox"))
             
             # Passa o path selecionado (pode ser "" para raiz)
             process_dropbox_batch(dropbox_selected_processing, st.session_state['api_key'], overwrite=force_overwrite)
            
# 3. Download do Resultado
if st.session_state['processed_file'] and os.path.exists(st.session_state['processed_file']):
    st.markdown("---")
    st.subheader(t("processing_done_subheader"))
    
    # Leitura do conteúdo
    with open(st.session_state['processed_file'], "r", encoding="utf-8") as f:
        md_content = f.read()
        
    st.markdown(t("preview_title"))
    
    # Usando st.text_area para limitar a altura e adicionar barra de rolagem
    st.text_area(
        label=t("extracted_content_label"),
        value=md_content,
        height=300,  # Altura fixa de 300 pixels
        key="markdown_preview"
    )
    
    # Criamos colunas para acomodar o botão de download (especialmente importante para Headless/VPS)
    col_download, col_cleanup = st.columns(2)
    with col_download:
        st.download_button(
            label=t("download_md_btn"),
            data=md_content,
            file_name=Path(st.session_state['processed_file']).name,
            mime="text/markdown",
            use_container_width=True
        )
    with col_cleanup:
        if st.button(t("clean_old_outputs_btn"), use_container_width=True):
            if clean_output_directory():
                st.success(t("clean_success"))
            else:
                st.info(t("clean_empty_info"))
            
            # Limpa o estado da sessão e inputs
            st.session_state['processed_file'] = None
            st.session_state['uploaded_file'] = None    # Limpa arquivo web upload
            st.session_state['reset_counter'] += 1      # Incrementa contador para resetar TODOS os inputs
            st.session_state['selected_local_path'] = None # Limpa seleção de arquivo local
            st.session_state['selected_batch_dir'] = None # Limpa seleção de pasta
            st.rerun() 

    # Exibir o caminho de salvamento final
    st.caption(t("saved_locally_caption", Path(st.session_state['processed_file']).resolve()))


# --- Inicialização do Streamlit ---
if __name__ == "__main__":
    # Se estiver rodando como executável PyInstaller, o servidor é iniciado aqui.
    if getattr(sys, 'frozen', False):
        from streamlit.web import server
        
        # Configurações de servidor (garantindo que o modo headless esteja ativo)
        st.cli.get_config_options().set_option('server.headless', True, write=False)
        st.cli.get_config_options().set_option('server.port', 8501, write=False)
        
        print("Iniciando servidor Streamlit...")
        print("Por favor, abra seu navegador e acesse: http://localhost:8501")
        
        try:
            server.run_app(os.path.abspath(__file__))
        except SystemExit:
            pass
        except Exception as e:
            print(f"Erro Crítico ao iniciar o Streamlit: {e}")
            
        print("\n--- Servidor Streamlit Encerrado ---")
        print("Pressione ENTER para fechar a janela.")
        input()
    else:
        # Se não estiver empacotado, o usuário deve rodar via 'streamlit run app.py'
        pass