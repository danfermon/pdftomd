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

# --- Configuração da Interface ---
st.set_page_config(
    page_title="Processador de Documentos para Markdown",
    layout="wide"
)

# Inicializa o banco de dados SQLite de usuários
auth.init_db()

# --- Inicialização de Estado de Autenticação ---
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
    st.markdown('<p class="login-subtitle">Sistema Seguro de Processamento de Documentos</p>', unsafe_allow_html=True)
    
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Usuário", placeholder="Digite seu usuário...")
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha...")
        submit_button = st.form_submit_button("Entrar", use_container_width=True)
        
        if submit_button:
            user = auth.authenticate_user(username, password)
            if user:
                st.session_state['authenticated'] = True
                st.session_state['user_id'] = user['id']
                st.session_state['username'] = user['username']
                st.session_state['is_admin'] = user['is_admin']
                st.session_state['needs_password_change'] = user['needs_password_change']
                st.success("Login efetuado com sucesso! Redirecionando...")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos. Tente novamente.")
                
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
    st.markdown('<h2 class="change-pwd-title">🔒 Alteração de Senha Obrigatória</h2>', unsafe_allow_html=True)
    st.markdown('<p class="change-pwd-subtitle">Este é o seu primeiro acesso ou sua senha foi resetada. Por questões de segurança, você deve escolher uma senha forte.</p>', unsafe_allow_html=True)
    
    with st.form("forced_change_pwd_form", clear_on_submit=False):
        new_pwd = st.text_input("Nova Senha", type="password", placeholder="Digite uma nova senha...")
        confirm_pwd = st.text_input("Confirme a Nova Senha", type="password", placeholder="Repita a nova senha...")
        submit_btn = st.form_submit_button("Alterar Senha e Entrar", use_container_width=True)
        
        if submit_btn:
            if not new_pwd:
                st.error("A nova senha não pode estar em branco.")
            elif len(new_pwd) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres por segurança.")
            elif new_pwd == "123456":
                st.error("A nova senha não pode ser a senha padrão '123456'. Defina uma senha mais segura.")
            elif new_pwd != confirm_pwd:
                st.error("As senhas digitadas não coincidem. Tente novamente.")
            else:
                user_id = st.session_state.get('user_id')
                if user_id:
                    success, msg = auth.change_password_on_first_login(user_id, new_pwd)
                    if success:
                        st.session_state['needs_password_change'] = False
                        st.success("Senha alterada com sucesso! Acessando o sistema...")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Erro interno do sistema. Por favor, tente fazer login novamente.")
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
            st.success("✅ PDF digital detectado. Usando MarkItDown/Fallback para extração estruturada (Local).")
            extract_structured_markitdown(input_path_str, output_path_str)
            
        else:
            st.warning("⚠️ PDF escaneado detectado. Tentando OCR local (Tesseract) primeiro.")
            
            # TENTATIVA 1: OCR LOCAL (Tesseract)
            tesseract_success = ocr_local_tesseract(input_path_str, output_path_str)
            
            if tesseract_success:
                st.success("✅ OCR Local (Tesseract) concluído. Verifique a qualidade.")
                
                if gemini_key and st.session_state.get('force_gemini', False):
                    st.info("Iniciando OCR e estruturação via Gemini (custo/nuvem).")
                    success = extract_ocr_to_markdown_gemini(input_path_str, output_path_str, gemini_key)
                    if success:
                        st.success("✅ Processamento Gemini concluído.")
                    else:
                        st.error("❌ Processamento Gemini falhou (Bloqueio de Conteúdo ou Erro de API).")
            
            elif gemini_key:
                st.error("❌ OCR Tesseract falhou.")
                st.info("Tentando OCR e estruturação via Gemini (custo/nuvem) como fallback.")
                success = extract_ocr_to_markdown_gemini(input_path_str, output_path_str, gemini_key)
                if success:
                    st.success("✅ Processamento Gemini concluído.")
                else:
                    st.error("❌ Processamento Gemini falhou (Bloqueio de Conteúdo ou Erro de API).")
            else:
                st.error("❌ Não foi possível processar o PDF. Chave Gemini não fornecida para fallback.")
                return False
                    
    elif file_extension in ['.docx', '.pptx', '.xlsx', '.doc', '.xls', '.csv', '.json', '.xml', '.html', '.zip', '.mp3', '.wav', '.jpg', '.png', '.epub']:
        # NOVA LÓGICA: Extração direta via MarkItDown para outros formatos
        st.success(f"✅ Arquivo {file_extension} detectado. Extração estruturada via MarkItDown.")
        extract_structured_markitdown(input_path_str, output_path_str) 
        
    else:
        st.error(f"❌ Formato de arquivo '{file_extension}' não suportado.")
        return False

    return True

def process_local_file(local_path_str, gemini_key):
    """
    Processa um arquivo local, salvando na MESMA pasta original.
    """
    path = Path(local_path_str).resolve()
    if not path.exists():
        st.error("❌ Arquivo não encontrado no caminho especificado.")
        return None
        
    # Salva na mesma pasta: NomeOriginalMD.md
    output_path = path.parent / f"{path.stem}MD.md"
    
    st.info(f"💾 Modo Local: Salvando saída na mesma pasta: {output_path}")
    
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
    
    st.info(f"💾 Processando upload temporário e salvando resultado em: {output_md_path}")
    
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
    status_text.info("🔍 Varrendo arquivos...")
    
    for path in root_dir.rglob('*'):
        if path.is_file() and path.suffix.lower() in supported_extensions:
            files_to_process.append(path)
            
    if not files_to_process:
        st.warning("Nenhum arquivo suportado encontrado nesta pasta.")
        return

    st.success(f"📂 Encontrados {len(files_to_process)} arquivos incompatíveis para conversão.")
    
    # 2. Barra de Progresso
    progress_bar = st.progress(0)
    log_area = st.empty()
    
    processed_count = 0
    skipped_count = 0 # NOVO
    errors_count = 0
    
    stop_button = st.button("🛑 Parar Processamento em Lote")
    
    for i, file_path in enumerate(files_to_process):
        if stop_button:
            st.warning("Processamento interrompido pelo usuário.")
            break
            
        rel_path = file_path.relative_to(root_dir)
        
        # Define saída: Nome_MD.md (na mesma pasta)
        output_path = file_path.parent / f"{file_path.stem}MD.md"
        
        # LÓGICA INCREMENTAL
        if output_path.exists() and not overwrite:
            log_area.code(f"⏩ Pulando (Já existe): {rel_path}")
            skipped_count += 1
            progress = (i + 1) / len(files_to_process)
            progress_bar.progress(progress)
            continue

        log_area.code(f"Processando [{i+1}/{len(files_to_process)}]: {rel_path}...")

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
    
    status_text.success(f"✅ Concluído! Processados: {processed_count}. Pulados: {skipped_count}. Erros: {errors_count}.")
    st.balloons()


def process_dropbox_batch(folder_path_str: str, gemini_key: str, overwrite: bool = False):
    """
    Processamento em lote via Dropbox (Download -> Convert -> Upload).
    Args:
        overwrite: Se True, refaz arquivos já existentes. Se False, pula.
    """
    token = st.session_state.get('dropbox_token')
    if not token:
        st.error("Token do Dropbox não encontrado.")
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
    
    with st.spinner("☁️ Varrendo arquivos no Dropbox..."):
        file_entries = dbx.list_files_recursive(folder_path_str, supported_extensions)
        
    if not file_entries:
        st.warning(f"Nenhum arquivo suportado encontrado em '{folder_path_str}'.")
        return
        
    st.success(f"☁️ Encontrados {len(file_entries)} arquivos no Dropbox.")
    
    # 3. Processamento
    progress_bar = st.progress(0)
    log_area = st.empty()
    stop_button = st.button("🛑 Parar Dropbox Batch")
    
    temp_dir = Path("temp_dropbox")
    temp_dir.mkdir(exist_ok=True)
    
    processed_count = 0
    skipped_count = 0 # NOVO
    errors_count = 0
    
    for i, entry in enumerate(file_entries):
        if stop_button:
            st.warning("Interrompido.")
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
                 log_area.code(f"⏩ Pulando (Já existe): {entry.path_display}")
                 skipped_count += 1
                 progress_bar.progress((i + 1) / len(file_entries))
                 continue

        log_area.code(f"Baixando e Processando [{i+1}/{len(file_entries)}]: {entry.path_display}...")
        
        # Paths do download temporário
        local_input = temp_dir / entry.name
        local_output = temp_dir / local_output_name
        
        try:
            # Download
            if dbx.download_file(entry.path_display, str(local_input)):
                # Converte
                if run_file_pipeline(str(local_input), str(local_output), gemini_key):
                    # Upload
                    log_area.code(f"⬆️ Fazendo Upload: {dropbox_output_path}")
                    if dbx.upload_file(str(local_output), dropbox_output_path):
                         processed_count += 1
                    else:
                         errors_count += 1
                         st.error(f"Erro no upload de {entry.name}")
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
        
    st.success(f"✅ Dropbox Batch Concluído! Sucessos: {processed_count}. Pulados: {skipped_count}. Erros: {errors_count}.")
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
    
    st.info(f"📂 Modo Upload: Salvando saída em {output_md_path}")
    
    # 3. Executar Pipeline
    success = run_file_pipeline(str(pdf_path), str(output_md_path), gemini_key)
    
    # 4. Limpeza e Retorno
    os.remove(pdf_path)
    return output_md_path if success else None

# --- Layout da Aplicação ---

# --- Barra Lateral (Controle de Navegação e Logout) ---
with st.sidebar:
    st.markdown("### 👤 Usuário Conectado")
    role_badge = "🟢 Administrador" if st.session_state['is_admin'] else "🔵 Usuário Padrão"
    st.markdown(f"**Nome:** `{st.session_state['username']}`")
    st.markdown(f"**Perfil:** {role_badge}")
    
    # Alerta de Segurança se o admin estiver usando a senha padrão
    if st.session_state['username'] == 'admin':
        if auth.authenticate_user("admin", "admin123"):
            st.warning("⚠️ **ALERTA DE SEGURANÇA:**\nA senha do usuário 'admin' ainda é a senha padrão provisória ('admin123'). Por favor, altere-a imediatamente na aba de Gestão de Usuários!")
            
    st.markdown("---")
    
    # Navegação de Telas (Somente visível para Admin)
    app_mode = "📄 Processar Documentos"
    if st.session_state['is_admin']:
        app_mode = st.radio(
            "Navegação",
            ["📄 Processar Documentos", "👥 Gestão de Usuários"],
            key="nav_mode"
        )
    
    st.markdown("---")
    if st.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state['authenticated'] = False
        st.session_state['username'] = ""
        st.session_state['is_admin'] = False
        st.success("Logout efetuado!")
        st.rerun()

# --- Conteúdo Principal dependendo da Seleção ---
if app_mode == "👥 Gestão de Usuários":
    st.title("👥 Gestão de Usuários")
    st.markdown("---")
    
    tab_list, tab_create = st.tabs(["📋 Usuários Cadastrados", "➕ Criar Novo Usuário"])
    
    with tab_list:
        users = auth.list_users()
        
        for u in users:
            u_id = u['id']
            u_name = u['username']
            u_admin = u['is_admin']
            
            with st.container(border=True):
                col_info, col_actions = st.columns([2, 1], vertical_alignment="center")
                with col_info:
                    badge = "🟢 Admin" if u_admin else "🔵 Usuário"
                    status_badge = " &nbsp;&nbsp;&nbsp; ⚠️ *Alteração de senha pendente*" if u.get('needs_password_change') else ""
                    st.markdown(f"**Usuário:** `{u_name}` &nbsp;&nbsp;&nbsp; {badge}{status_badge}")
                    st.caption(f"Criado em: {u['created_at']} | Atualizado em: {u['updated_at']}")
                
                with col_actions:
                    col_edit, col_pwd, col_del = st.columns(3)
                    
                    with col_edit:
                        if st.button("✏️", key=f"edit_{u_id}", help="Editar Usuário"):
                            st.session_state[f"show_edit_{u_id}"] = not st.session_state.get(f"show_edit_{u_id}", False)
                            st.session_state[f"show_pwd_{u_id}"] = False
                            st.session_state[f"show_del_{u_id}"] = False
                            st.rerun()
                            
                    with col_pwd:
                        if st.button("🔑", key=f"pwd_{u_id}", help="Redefinir Senha"):
                            st.session_state[f"show_pwd_{u_id}"] = not st.session_state.get(f"show_pwd_{u_id}", False)
                            st.session_state[f"show_edit_{u_id}"] = False
                            st.session_state[f"show_del_{u_id}"] = False
                            st.rerun()
                            
                    with col_del:
                        if st.button("🗑️", key=f"del_{u_id}", help="Excluir Usuário"):
                            st.session_state[f"show_del_{u_id}"] = not st.session_state.get(f"show_del_{u_id}", False)
                            st.session_state[f"show_edit_{u_id}"] = False
                            st.session_state[f"show_pwd_{u_id}"] = False
                            st.rerun()
                
                # Seções expansíveis de ação
                if st.session_state.get(f"show_edit_{u_id}", False):
                    st.markdown("##### Editar Usuário")
                    new_u_name = st.text_input("Novo nome de usuário", value=u_name, key=f"input_edit_name_{u_id}")
                    new_u_admin = st.checkbox("Administrador?", value=u_admin, key=f"input_edit_admin_{u_id}")
                    if st.button("Confirmar Edição", key=f"btn_edit_confirm_{u_id}", type="primary"):
                        success, msg = auth.update_user(u_id, new_u_name, new_u_admin)
                        if success:
                            st.success(msg)
                            st.session_state[f"show_edit_{u_id}"] = False
                            st.rerun()
                        else:
                            st.error(msg)
                            
                if st.session_state.get(f"show_pwd_{u_id}", False):
                    st.markdown("##### Redefinir Senha")
                    new_pwd = st.text_input("Nova Senha", type="password", key=f"input_pwd_{u_id}")
                    if st.button("Confirmar Nova Senha", key=f"btn_pwd_confirm_{u_id}", type="primary"):
                        success, msg = auth.reset_password(u_id, new_pwd)
                        if success:
                            st.success(msg)
                            st.session_state[f"show_pwd_{u_id}"] = False
                            st.rerun()
                        else:
                            st.error(msg)
                            
                if st.session_state.get(f"show_del_{u_id}", False):
                    st.warning(f"Tem certeza que deseja excluir o usuário `{u_name}`? Esta ação não pode ser desfeita.")
                    if st.button("Sim, Excluir", key=f"btn_del_confirm_{u_id}", type="primary"):
                        success, msg = auth.delete_user(u_id, st.session_state['username'])
                        if success:
                            st.success(msg)
                            st.session_state[f"show_del_{u_id}"] = False
                            st.rerun()
                        else:
                            st.error(msg)
                            
    with tab_create:
        st.markdown("### ➕ Cadastrar Novo Usuário")
        st.info("ℹ️ Novos usuários são criados automaticamente com a senha provisória **123456** e serão obrigados a alterá-la no primeiro acesso por questões de segurança.")
        with st.form("create_user_form", clear_on_submit=True):
            new_username = st.text_input("Nome de Usuário", placeholder="Ex: joao.silva")
            new_is_admin = st.checkbox("Conceder privilégios de Administrador?")
            create_submit = st.form_submit_button("Cadastrar Usuário", use_container_width=True)
            
            if create_submit:
                success, msg = auth.create_user(new_username, new_is_admin)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
    
    st.stop() # Interrompe a execução aqui para administradores na tela de Gestão de Usuários

# --- Layout da Aplicação Original ---
st.title("📄 Processador de Documentos para Markdown")
st.markdown("---")

# 1. Entrada de Dados (MOVIDO PARA O TOPO)
st.subheader("1. Entrada de Dados")

col_input1, col_input2 = st.columns([1, 1])

# Nova Interface com Tabs: Arquivo Local, Pasta (Lote), Dropbox, YouTube
tab_local, tab_batch, tab_dropbox, tab_youtube = st.tabs(["📂 Arquivo Local", "📦 Pasta (Lote)", "☁️ Dropbox", "📺 YouTube"])

with tab_local:
    if IS_HEADLESS:
        st.info("ℹ️ Faça o upload de um arquivo para converter e gerar a versão Markdown para download.")
        uploaded_file = st.file_uploader(
            "Selecione um arquivo para converter:",
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
        st.info("ℹ️ Selecione um arquivo para salvar a versão Markdown na **mesma pasta original**.")
        
        col_btn, col_txt = st.columns([1, 4], vertical_alignment="bottom")
        
        with col_btn:
            if st.button("📂 Selecionar Arquivo", use_container_width=True):
                import subprocess, sys
                code = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)
path = filedialog.askopenfilename(
    title='Selecione um arquivo para converter',
    filetypes=[
        ('Todos os Suportados', '*.pdf *.docx *.pptx *.xlsx *.doc *.xls *.csv *.json *.xml *.html *.zip *.mp3 *.wav *.jpg *.png *.epub'),
        ('Documentos PDF', '*.pdf'),
        ('Todos os Arquivos', '*.*')
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
                 st.info("Nenhum arquivo selecionado.", icon="ℹ️")

with tab_batch:
    if IS_HEADLESS:
        st.warning("⚠️ **Aviso:** O processamento de pastas locais (Lote) está desativado em modo servidor (VPS/Docker) pois requer acesso ao sistema de arquivos do servidor. Para processar múltiplos arquivos em lote na nuvem, utilize a aba **Dropbox**, que oferece navegação de pastas e processamento incremental seguro.")
    else:
        st.info("ℹ️ Selecione uma **PASTA** para converter TODOS os arquivos contidos nela (Recursivo).")
        
        col_btn_batch, col_txt_batch = st.columns([1, 4], vertical_alignment="bottom")
        
        with col_btn_batch:
            if st.button("📂 Selecionar Pasta", use_container_width=True):
                import subprocess, sys
                code = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes('-topmost', 1)
path = filedialog.askdirectory(title='Selecione a Pasta para Processamento em Lote')
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
                st.info("Nenhuma pasta selecionada.", icon="ℹ️")
            
            # --- RLM INDEX GENERATION (LOCAL) ---
            if current_dir:
                st.divider()
                st.subheader("📚 Índice Semântico (RLM)")
                if st.button("🧠 Gerar Índice PDF desta Pasta", key="btn_index_local_main"):
                    gemini_key = st.session_state.get('api_key')
                    if not gemini_key:
                        st.error("⚠️ É necessário configurar a Chave API Gemini para usar o RLM.")
                    else:
                        with st.spinner("🧠 Analisando arquivos e gerando índice com RLM... (Isso pode demorar)"):
                            indexed_count = generate_index_for_folder(current_dir, gemini_key, recursive=True)
                        if indexed_count > 0:
                            st.success(f"✅ Índice Gerado com Sucesso! {indexed_count} arquivo(s) indexado(s). Verifique os arquivos '_INDEX_CONTENT*.pdf' na pasta.")
                        else:
                            st.warning("⚠️ Nenhum arquivo Markdown (.md) foi encontrado para indexar nesta pasta. Apenas arquivos convertidos para Markdown (.md) podem ser indexados. Converta seus arquivos primeiro nas abas correspondente!")

with tab_dropbox:
    st.info("ℹ️ Navegue pelas pastas e clique em 'Selecionar Esta Pasta' para converter.")
    
    # Init State
    if 'dbx_current_path' not in st.session_state:
        st.session_state['dbx_current_path'] = "" # Root
    if 'dbx_selected_for_processing' not in st.session_state:
        st.session_state['dbx_selected_for_processing'] = None 

    # --- NOVA ÁREA DE CONFIGURAÇÃO DO TOKEN ---
    with st.expander("🔑 Configurar Token do Dropbox (Clique para expandir)"):
        st.markdown("""
        **Como obter um novo token:**
        1. Acesse [dropbox.com/developers/apps](https://www.dropbox.com/developers/apps).
        2. Clique no seu App (`carroll_rag` ou similar).
        3. Vá na aba **Settings**.
        4. Role até a seção **OAuth 2**.
        5. Clique no botão **Generate** (abaixo de *Generated access token*).
        6. Copie o código e cole abaixo.
        """)
        
        new_token = st.text_input(
            "Cole seu Dropbox Access Token aqui:", 
            value=st.session_state.get('dropbox_token', ''),
            type="password",
            help="Este token deve ter permissões de leitura e escrita (files.content.write)."
        )
        
        if new_token and new_token != st.session_state.get('dropbox_token'):
            st.session_state['dropbox_token'] = new_token
            st.success("Token atualizado na sessão! (Reinicie o app se quiser salvar no .env permanentemente)")
            st.rerun()

    # Validação Básica de Token
    if not st.session_state.get('dropbox_token'):
        st.warning("⚠️ Token do Dropbox não encontrado. Por favor, insira acima.")
    else:
        # Instancia Handler
        dbx = DropboxHandler(st.session_state['dropbox_token'])
        
        # 1. VERIFICAÇÃO PREVENTIVA DE CONEXÃO
        is_connected, msg_connection = dbx.check_connection()
        
        if not is_connected:
            st.warning(f"⚠️ {msg_connection}")
            st.error("O token atual parece inválido ou expirado. Use a área 'Configurar Token' acima para corrigir.")
        else:
            # --- Interface de Navegação (Somente se conectado) ---
            current = st.session_state['dbx_current_path']
            display_path = current if current else "Raiz (/)"
            
            st.markdown(f"**📂 Pasta Atual:** `{display_path}`")
            
            # Botões de Ação (Voltar / Selecionar)
            col_nav_1, col_nav_2 = st.columns([1, 4])
        
            with col_nav_1:
                if current != "":
                    if st.button("⬆️ Subir Nível", use_container_width=True):
                        # Remove o último segmento do path
                        st.session_state['dbx_current_path'] = str(Path(current).parent).replace("\\", "/")
                        if st.session_state['dbx_current_path'] == ".": 
                            st.session_state['dbx_current_path'] = ""
                        st.rerun()
                else:
                    st.button("⬆️ (Raiz)", disabled=True, use_container_width=True)
                    
            with col_nav_2:
                 if st.button(f"✅ Selecionar Esta Pasta para Conversão", use_container_width=True, type="primary"):
                     st.session_state['dbx_selected_for_processing'] = current if current else ""
                     # Limpa outras seleções para evitar conflito
                     st.session_state['selected_local_path'] = None
                     st.session_state['selected_batch_dir'] = None
                     st.session_state['processed_file'] = None
                     
                     st.success(f"Pasta selecionada: {display_path}")
                     st.rerun()

            st.divider()
            st.caption("Subpastas (clique para entrar):")
            
            # Listagem de Subpastas
            subfolders = dbx.list_subfolders(current)
            
            if not subfolders:
                st.caption("*(Nenhuma subpasta encontrada)*")
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
         st.success(f"🎯 **Pronto para processar:** {selected_dbx if selected_dbx else 'Raiz (/)'}")
         
         # --- RLM INDEX GENERATION (DROPBOX) ---
         st.divider()
         st.subheader("📚 Índice Semântico (RLM)")
         
         if st.button("🧠 Gerar Índice PDF (Dropbox)", key="btn_index_dbx_main"):
            gemini_key = st.session_state.get('api_key')
            if not gemini_key:
                st.error("⚠️ É necessário configurar a Chave API Gemini para usar o RLM.")
            else:
                # Lógica Específica para Dropbox
                dest_path = selected_dbx if selected_dbx else ""
                with st.spinner("🧠 Preparando arquivos do Dropbox para indexação..."):
                    # 1. Criar temp dir
                    index_temp_dir = Path("temp_dropbox_index")
                    index_temp_dir.mkdir(exist_ok=True)
                    
                    # 2. Listar apenas MDs
                    md_entries = dbx.list_files_recursive(dest_path, {'.md'})
                    
                    if not md_entries:
                        st.warning("Nenhum arquivo Markdown encontrado para indexar.")
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
                        
                        st.info(f"Baixados {downloaded_count} arquivos para análise.")
                        
                        # 3. Gerar Índice
                        with st.spinner("🧠 RLM processando e gerando PDF..."):
                            indexed_count = generate_index_for_folder(str(index_temp_dir), gemini_key, recursive=True)
                        
                        if indexed_count == 0:
                            st.warning("⚠️ Nenhum arquivo Markdown (.md) foi encontrado para indexar nesta pasta. Apenas arquivos convertidos para Markdown (.md) podem ser indexados. Converta seus arquivos do Dropbox primeiro na aba acima!")
                        else:
                            # 4. Upload
                            pdf_files = list(index_temp_dir.rglob("_INDEX_CONTENT*.pdf"))
                            if not pdf_files:
                                st.error("Nenhum índice gerado. (Verifique logs/arquivos MD)")
                            else:
                                uploaded_indexes = 0
                                for pdf in pdf_files:
                                    rel_pdf_path = pdf.relative_to(index_temp_dir)
                                    base = dest_path if dest_path != "" else ""
                                    remote_pdf_path = f"{base}/{rel_pdf_path.as_posix()}"
                                    if remote_pdf_path.startswith("//"): remote_pdf_path = remote_pdf_path[1:]
                                    
                                    st.toast(f"⬆️ Enviando: {rel_pdf_path.name}")
                                    dbx.upload_file(str(pdf), remote_pdf_path)
                                    uploaded_indexes += 1
                                
                                st.success(f"✅ {uploaded_indexes} Índices Semânticos gerados e enviados para o Dropbox com sucesso!")
                        
                        # Limpeza
                        import shutil
                        shutil.rmtree(index_temp_dir, ignore_errors=True)

with tab_youtube:
    st.caption("ℹ️ Transcrição salva na pasta `markdown_output`.")
    # Usa reset_counter no key para forçar recriação do widget ao limpar
    youtube_url = st.text_input(
        "Cole uma URL do YouTube:", 
        placeholder="https://www.youtube.com/watch?v=...", 
        key=f"youtube_url_{st.session_state['reset_counter']}"
    )

st.markdown("---")

# 2. Configuração Opcional (Gemini)
st.subheader("2. Configuração de IA (Opcional)")

use_gemini = st.checkbox("Usar Google Gemini AI? (Recomendado para PDFs escaneados ruins ou imagens complexas)")

if use_gemini:
    gemini_key_input = st.text_input("Cole sua Chave API Gemini:", type="password", key="gemini_key_in")
    if gemini_key_input:
        if validate_gemini_api_key(gemini_key_input):
            st.session_state['api_key'] = gemini_key_input
            st.success("✅ Chave Gemini validada!")
            
            # Opção de forçar
            st.checkbox(
                "Forçar uso do Gemini mesmo se Tesseract funcionar?", 
                key="force_gemini",
                help="Ignora OCR local e usa nuvem para tudo (custo/tempo maior)."
            )
        else:
            st.error("❌ Chave inválida.")
            st.session_state['api_key'] = None
    else:
        st.warning("⚠️ Insira a chave para ativar o modo IA.")
        st.session_state['api_key'] = None
else:
    st.session_state['api_key'] = None

# Nova Opção: Sobrescrever
force_overwrite = st.checkbox(
    "Sobrescrever arquivos Markdown existentes?", 
    value=False,
    help="Se desmarcado, o sistema pulará arquivos que já possuem a versão _MD.md na pasta."
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
    st.info(f"📁 **Pronto para Processar:** {input_name}")
    
    # Botão de Processamento
    if st.button("🚀 Iniciar Processamento", use_container_width=True):
        st.session_state['processed_file'] = None
        
        # 1. YouTube
        if youtube_url:
             if is_youtube_url(youtube_url):
                 st.info(f"Processando YouTube: {youtube_url}")
                 output_dir = Path("markdown_output")
                 output_dir.mkdir(exist_ok=True)
                 # Cria um nome de arquivo seguro a partir da URL (simplificado)
                 video_id = youtube_url.split("v=")[-1].split("&")[0]
                 output_md_path = output_dir / f"youtube_{video_id}.md"
                 
                 with st.spinner("Extraindo transcrição do YouTube..."):
                     success = extract_youtube_transcript(youtube_url, str(output_md_path))
                     if success:
                         st.session_state['processed_file'] = str(output_md_path)
                         st.success("✅ Transcrição concluída!")
                     else:
                         st.error("❌ Falha ao obter transcrição. Verifique se o vídeo tem legendas.")
             else:
                 st.error("❌ URL do YouTube inválida.")

        # 2. Upload Web (Headless)
        elif uploaded_file:
            if st.session_state['api_key']:
                st.info("Modo de Processamento: Híbrido (Upload Web + Nuvem Gemini)")
            else:
                st.info("Modo de Processamento: 100% Local (Upload Web + MarkItDown/Tesseract)")
                
            with st.spinner("Processando Upload Web..."):
                 output_path = process_uploaded_file(uploaded_file, st.session_state['api_key'])
                 if output_path:
                     st.session_state['processed_file'] = str(output_path)
                     st.success("✅ Upload processado com sucesso!")

        # 3. Arquivo Local (Via Dialogo Nativo)
        elif selected_local_path:
            
            if st.session_state['api_key']:
                st.info("Modo de Processamento: Híbrido (Local + Nuvem Gemini)")
            else:
                st.info("Modo de Processamento: 100% Local (MarkItDown/Tesseract)")
                
            with st.spinner("Processando Arquivo Local..."):
                 output_path = process_local_file(selected_local_path, st.session_state['api_key'])
                 if output_path:
                     st.session_state['processed_file'] = str(output_path)
        
        # 3. Lote (Pasta)
        elif selected_batch_dir:
             if st.session_state['api_key']:
                st.info("Modo Batch: Híbrido (Local + Nuvem Gemini)")
             else:
                st.info("Modo Batch: 100% Local")
             
             # Chama a função de lote (ela gerencia seu próprio spinner/progresso)
             process_batch_directory(selected_batch_dir, st.session_state['api_key'], overwrite=force_overwrite)
        
        # 4. Dropbox Batch
        elif dropbox_selected_processing is not None:
             if st.session_state['api_key']:
                st.info("Modo Dropbox: Híbrido (Download -> Process -> Upload)")
             else:
                st.info("Modo Dropbox: 100% Local (Download -> Process -> Upload)")
             
             # Passa o path selecionado (pode ser "" para raiz)
             process_dropbox_batch(dropbox_selected_processing, st.session_state['api_key'], overwrite=force_overwrite)
            
# 3. Download do Resultado
if st.session_state['processed_file'] and os.path.exists(st.session_state['processed_file']):
    st.markdown("---")
    st.subheader("✅ Processamento Concluído")
    
    # Leitura do conteúdo
    with open(st.session_state['processed_file'], "r", encoding="utf-8") as f:
        md_content = f.read()
        
    st.markdown("### Pré-visualização do Conteúdo (Markdown)")
    
    # Usando st.text_area para limitar a altura e adicionar barra de rolagem
    st.text_area(
        label="Conteúdo Extraído",
        value=md_content,
        height=300,  # Altura fixa de 300 pixels
        key="markdown_preview"
    )
    
    # Criamos colunas para acomodar o botão de download (especialmente importante para Headless/VPS)
    col_download, col_cleanup = st.columns(2)
    with col_download:
        st.download_button(
            label="⬇️ Baixar Arquivo Markdown",
            data=md_content,
            file_name=Path(st.session_state['processed_file']).name,
            mime="text/markdown",
            use_container_width=True
        )
    with col_cleanup:
        if st.button("🗑️ Limpar Arquivos de Saída Antigos", use_container_width=True):
            if clean_output_directory():
                st.success("Pasta de saída limpa com sucesso!")
            else:
                st.info("Nenhum arquivo para limpar na pasta de saída.")
            
            # Limpa o estado da sessão e inputs
            st.session_state['processed_file'] = None
            st.session_state['uploaded_file'] = None    # Limpa arquivo web upload
            st.session_state['reset_counter'] += 1      # Incrementa contador para resetar TODOS os inputs
            st.session_state['selected_local_path'] = None # Limpa seleção de arquivo local
            st.session_state['selected_batch_dir'] = None # Limpa seleção de pasta
            st.rerun() 

    # Exibir o caminho de salvamento final
    st.caption(f"Arquivo salvo localmente no servidor em: {Path(st.session_state['processed_file']).resolve()}")


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