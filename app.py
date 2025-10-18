# C:\pdftomd\app.py

import streamlit as st
import os
import sys
from pathlib import Path
import google.generativeai as genai

# Importar as funções do pipeline
from pdf_detector import is_digital_pdf, extract_text_digital_markitdown
from gcv_ocr import ocr_local_tesseract, extract_ocr_to_markdown_gemini

# --- Configuração da Interface ---
st.set_page_config(
    page_title="Processador de Documentos Jurídicos para Markdown",
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
    </style>
    """, unsafe_allow_html=True)

# --- Variáveis de Estado ---
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = None
if 'processed_file' not in st.session_state:
    st.session_state['processed_file'] = None

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

def process_uploaded_pdf(uploaded_file, gemini_key):
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
    
    pdf_path_str = str(pdf_path)
    
    # 2. Definir Caminho de Saída
    output_dir = Path("markdown_output")
    output_dir.mkdir(exist_ok=True)
    output_md_path = output_dir / f"{pdf_path.stem}_output.md"
    
    st.info(f"Arquivo de saída será salvo temporariamente em: {output_md_path.resolve()}")
    
    # 3. Triagem
    is_digital = is_digital_pdf(pdf_path_str)
    
    if is_digital:
        st.success("✅ PDF digital detectado. Usando MarkItDown/Fallback para extração estruturada (Local).")
        extract_text_digital_markitdown(pdf_path_str, str(output_md_path))
        
    else:
        st.warning("⚠️ PDF escaneado detectado. Tentando OCR local (Tesseract) primeiro.")
        
        # TENTATIVA 1: OCR LOCAL (Tesseract)
        tesseract_success = ocr_local_tesseract(pdf_path_str, str(output_md_path))
        
        if tesseract_success:
            st.success("✅ OCR Local (Tesseract) concluído. Verifique a qualidade.")
            
            # Se o usuário forneceu a chave Gemini, damos a opção de upgrade
            if gemini_key:
                # Nota: O botão de upgrade deve ser fora da função de processamento para Streamlit
                # Mas para manter a lógica sequencial, vamos forçar a decisão aqui.
                # Em uma aplicação Streamlit ideal, isso seria um checkbox/radio button antes do processamento.
                
                # Para fins de empacotamento, vamos assumir que se a chave está presente, o usuário
                # quer a melhor qualidade, a menos que ele explicitamente diga o contrário.
                # Como não podemos ter input dentro do st.spinner, vamos perguntar antes.
                
                # Para simplificar o empacotamento, se a chave está presente, perguntamos:
                if st.session_state.get('force_gemini', False):
                    st.info("Iniciando OCR e estruturação via Gemini (custo/nuvem).")
                    success = extract_ocr_to_markdown_gemini(pdf_path_str, str(output_md_path), gemini_key)
                    if success:
                        st.success("✅ Processamento Gemini concluído.")
                    else:
                        st.error("❌ Processamento Gemini falhou (Bloqueio de Conteúdo ou Erro de API).")
                
            
        else:
            st.error("❌ OCR Tesseract falhou.")
            if gemini_key:
                st.info("Tentando OCR e estruturação via Gemini (custo/nuvem) como fallback.")
                success = extract_ocr_to_markdown_gemini(pdf_path_str, str(output_md_path), gemini_key)
                if success:
                    st.success("✅ Processamento Gemini concluído.")
                else:
                    st.error("❌ Processamento Gemini falhou (Bloqueio de Conteúdo ou Erro de API).")
            else:
                st.error("❌ Não foi possível processar o PDF. Chave Gemini não fornecida para fallback.")

    # 4. Limpeza e Retorno
    os.remove(pdf_path)
    return output_md_path

# --- Layout da Aplicação ---

st.title("📄 Processador de Documentos Jurídicos para Markdown")
st.markdown("---")

# 1. Configuração da API
with st.expander("🔑 Configuração da Chave API Gemini (Opcional)", expanded=True):
    st.markdown("""
    A chave API do Gemini é **opcional**. Se você não a fornecer, o sistema usará apenas o OCR local (Tesseract), que é gratuito, mas menos preciso para documentos escaneados.
    """)
    
    gemini_key_input = st.text_input("Chave API Gemini:", type="password", key="gemini_key_input")
    
    if gemini_key_input:
        if validate_gemini_api_key(gemini_key_input):
            st.session_state['api_key'] = gemini_key_input
            st.success("Chave Gemini validada.")
        else:
            st.session_state['api_key'] = None
            st.error("Chave inválida. O processamento será limitado ao modo local.")
    else:
        st.session_state['api_key'] = None
        st.warning("Modo 100% Local (Tesseract) ativado.")

    # Opção para forçar o Gemini mesmo se o Tesseract funcionar (apenas se a chave estiver presente)
    if st.session_state['api_key']:
        st.session_state['force_gemini'] = st.checkbox(
            "Forçar Gemini (Alta Qualidade) mesmo se o Tesseract funcionar?", 
            value=False,
            help="Se marcado, o Gemini será usado para PDFs escaneados, ignorando o resultado do Tesseract."
        )


st.markdown("---")

# 2. Upload do Arquivo
uploaded_file = st.file_uploader("Selecione o arquivo PDF para processamento:", type="pdf")

if uploaded_file is not None:
    
    # Botão de Processamento
    if st.button("🚀 Iniciar Processamento"):
        st.session_state['processed_file'] = None
        
        # Exibe o modo de processamento
        if st.session_state['api_key']:
            st.info("Modo de Processamento: Híbrido (Local + Nuvem Gemini)")
        else:
            st.info("Modo de Processamento: 100% Local (Tesseract)")
            
        # Executa o pipeline
        with st.spinner("Processando... Isso pode levar alguns minutos para PDFs grandes ou escaneados."):
            output_path = process_uploaded_pdf(uploaded_file, st.session_state['api_key'])
            st.session_state['processed_file'] = output_path
            
        # A mensagem de sucesso/erro final é dada dentro da função process_uploaded_pdf

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
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Botão de Download
        st.download_button(
            label="⬇️ Baixar Arquivo Markdown (.md)",
            data=md_content.encode('utf-8'),
            file_name=os.path.basename(st.session_state['processed_file']),
            mime="text/markdown"
        )
    
    with col2:
        # Botão de Limpeza
        if st.button("🗑️ Limpar Arquivos de Saída Antigos"):
            if clean_output_directory():
                st.success("Pasta de saída limpa com sucesso!")
            else:
                st.info("Nenhum arquivo para limpar na pasta de saída.")
            # Limpa o estado da sessão para forçar o Streamlit a recarregar
            st.session_state['processed_file'] = None
            st.rerun() # Recarrega a página para refletir a limpeza

    # Exibir o caminho de salvamento final
    st.caption(f"Arquivo salvo localmente em: {Path(st.session_state['processed_file']).resolve()}")