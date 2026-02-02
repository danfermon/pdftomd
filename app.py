# C:\pdftomd\app.py

import streamlit as st
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import google.generativeai as genai
from dotenv import load_dotenv
from dropbox_handler import DropboxHandler

# Importar as funções do pipeline
from pdf_detector import is_digital_pdf, extract_structured_markitdown # RENOMEADO
from gcv_ocr import ocr_local_tesseract, extract_ocr_to_markdown_gemini
from youtube_handler import is_youtube_url, extract_youtube_transcript # NOVO

# --- Configuração da Interface ---
st.set_page_config(
    page_title="Processador de Documentos para Markdown",
    layout="wide"
)

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

def process_batch_directory(directory_path_str: str, gemini_key: str):
    """
    Varre um diretório recursivamente e converte arquivos suportados.
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
    errors_count = 0
    
    stop_button = st.button("🛑 Parar Processamento em Lote")
    
    for i, file_path in enumerate(files_to_process):
        if stop_button:
            st.warning("Processamento interrompido pelo usuário.")
            break
            
        rel_path = file_path.relative_to(root_dir)
        log_area.code(f"Processando [{i+1}/{len(files_to_process)}]: {rel_path}...")
        
        # Define saída: Nome_MD.md (na mesma pasta)
        output_path = file_path.parent / f"{file_path.stem}MD.md"
        
        # Pula se já existir (opcional, mas bom pra evitar loop se a extensão for igual, mas aqui a extensão é .md)
        if output_path.exists():
            # Opcional: pular ou sobrescrever. Vamos sobrescrever/processar de novo.
            pass

        try:
             # Chama Pipeline Silenciosamente (st.empty para não poluir, ou redirecionar logs se possível)
             # Como o pipeline usa st.success/st.error, isso vai aparecer na tela. 
             # No modo batch, seria ideal silenciar, mas vamos deixar rolar por enquanto.
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
    
    status_text.success(f"✅ Concluído! Processados: {processed_count}. Erros: {errors_count}.")
    st.balloons()

def process_dropbox_batch(folder_path_str: str, gemini_key: str):
    """
    Processamento em lote via Dropbox (Download -> Convert -> Upload).
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
    errors_count = 0
    
    for i, entry in enumerate(file_entries):
        if stop_button:
            st.warning("Interrompido.")
            break
            
        log_area.code(f"Baixando e Processando [{i+1}/{len(file_entries)}]: {entry.path_display}...")
        
        # Paths
        local_input = temp_dir / entry.name
        local_output_name = f"{Path(entry.name).stem}MD.md"
        local_output = temp_dir / local_output_name
        
        # Dropbox Output Path (Mesma pasta: /pasta/arquivo.pdf -> /pasta/arquivoMD.md)
        dropbox_output_path = f"{Path(entry.path_display).parent.as_posix()}/{local_output_name}"
        # Correção para root path '/' se parent for ''
        if dropbox_output_path.startswith("//"):
             dropbox_output_path = dropbox_output_path[1:]

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
        
    st.success(f"✅ Dropbox Batch Concluído! Sucessos: {processed_count}. Erros: {errors_count}.")
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


# --- Layout da Aplicação ---

st.title("📄 Processador de Documentos para Markdown")
st.markdown("---")

# 1. Entrada de Dados (MOVIDO PARA O TOPO)
st.subheader("1. Entrada de Dados")

col_input1, col_input2 = st.columns([1, 1])

# Nova Interface com Tabs: Arquivo Local, Pasta (Lote), Dropbox, YouTube
tab_local, tab_batch, tab_dropbox, tab_youtube = st.tabs(["📂 Arquivo Local", "📦 Pasta (Lote)", "☁️ Dropbox", "📺 YouTube"])

with tab_local:
    st.info("ℹ️ Selecione um arquivo para salvar a versão Markdown na **mesma pasta original**.")
    
    col_btn, col_txt = st.columns([1, 4], vertical_alignment="bottom")
    
    with col_btn:
        if st.button("📂 Selecionar Arquivo", use_container_width=True):
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1) 
            
            file_path = filedialog.askopenfilename(
                title="Selecione um arquivo para converter",
                filetypes=[
                    ("Todos os Suportados", "*.pdf *.docx *.pptx *.xlsx *.doc *.xls *.csv *.json *.xml *.html *.zip *.mp3 *.wav *.jpg *.png *.epub"),
                    ("Documentos PDF", "*.pdf"),
                    ("Todos os Arquivos", "*.*")
                ]
            )
            
            root.destroy()
            
            if file_path:
                st.session_state['selected_local_path'] = file_path
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
    st.info("ℹ️ Selecione uma **PASTA** para converter TODOS os arquivos contidos nela (Recursivo).")
    
    col_btn_batch, col_txt_batch = st.columns([1, 4], vertical_alignment="bottom")
    
    with col_btn_batch:
        if st.button("📂 Selecionar Pasta", use_container_width=True):
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            
            dir_path = filedialog.askdirectory(title="Selecione a Pasta para Processamento em Lote")
            
            root.destroy()
            
            if dir_path:
                st.session_state['selected_batch_dir'] = dir_path
                st.rerun()
                
    with col_txt_batch:
        current_dir = st.session_state.get('selected_batch_dir', '')
        if current_dir:
            st.code(current_dir, language=None)
        else:
            st.info("Nenhuma pasta selecionada.", icon="ℹ️")

with tab_dropbox:
    st.info("ℹ️ Navegue pelas pastas e clique em 'Selecionar Esta Pasta' para converter.")
    
    # Init State para Navegação
    if 'dbx_current_path' not in st.session_state:
        st.session_state['dbx_current_path'] = "" # Root
    if 'dbx_selected_for_processing' not in st.session_state:
        st.session_state['dbx_selected_for_processing'] = None # Pasta Escolhida

    # Validação Básica de Token
    if not st.session_state.get('dropbox_token'):
        st.warning("⚠️ Token do Dropbox não encontrado no .env (DROPBOX_ACCESS_TOKEN).")
    else:
        # Instancia Handler
        dbx = DropboxHandler(st.session_state['dropbox_token'])
        
        # --- Interface de Navegação ---
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
    # st.info("Modo: 100% Local (MarkItDown / Tesseract)")

st.markdown("---")


# Validação do trigger (qual tab tem input?)
has_input = False
input_name = "Desconhecido"
selected_local_path = st.session_state.get('selected_local_path')
selected_batch_dir = st.session_state.get('selected_batch_dir')
# Dropbox input (Seleção via Navegador)
dropbox_selected_processing = st.session_state.get('dbx_selected_for_processing')

if selected_local_path:
    has_input = True
    input_name = os.path.basename(selected_local_path)
elif selected_batch_dir:
    has_input = True
    input_name = f"Lote Local: {os.path.basename(selected_batch_dir)}"
elif selected_batch_dir:
    has_input = True
    input_name = f"Lote Local: {os.path.basename(selected_batch_dir)}"
elif dropbox_selected_processing is not None:
    has_input = True
    display_name = dropbox_selected_processing if dropbox_selected_processing else "Raiz (/)"
    input_name = f"Dropbox: {display_name}"
elif youtube_url:
    has_input = True
    input_name = youtube_url

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

        # 2. Arquivo Local (Via Dialogo Nativo)
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
             process_batch_directory(selected_batch_dir, st.session_state['api_key'])
        
        # 4. Dropbox Batch
        elif dropbox_selected_processing is not None:
             if st.session_state['api_key']:
                st.info("Modo Dropbox: Híbrido (Download -> Process -> Upload)")
             else:
                st.info("Modo Dropbox: 100% Local (Download -> Process -> Upload)")
             
             # Passa o path selecionado (pode ser "" para raiz)
             process_dropbox_batch(dropbox_selected_processing, st.session_state['api_key'])
            
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
    
    # Botão de Limpeza (Agora ocupa toda a largura, já que download foi removido)
    if st.button("🗑️ Limpar Arquivos de Saída Antigos", use_container_width=True):
        if clean_output_directory():
            st.success("Pasta de saída limpa com sucesso!")
        else:
            st.info("Nenhum arquivo para limpar na pasta de saída.")
        
        # Limpa o estado da sessão e inputs
        st.session_state['processed_file'] = None
        st.session_state['reset_counter'] += 1      # Incrementa contador para resetar TODOS os inputs
        st.session_state['selected_local_path'] = None # Limpa seleção de arquivo local
        st.session_state['selected_batch_dir'] = None # Limpa seleção de pasta
        st.rerun() 

    # Exibir o caminho de salvamento final
    st.caption(f"Arquivo salvo localmente em: {Path(st.session_state['processed_file']).resolve()}")


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