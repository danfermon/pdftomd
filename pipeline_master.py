# C:\pdftomd\pipeline_master.py

import os
import sys
from pdf_detector import is_digital_pdf, extract_text_digital_markitdown
from gcv_ocr import extract_ocr_to_markdown_gemini, ocr_local_tesseract
import google.generativeai as genai
from pathlib import Path

# --- Funções de Utilidade ---

def validate_gemini_api_key(api_key: str) -> bool:
    """
    Tenta configurar o SDK e listar modelos para validar a chave API.
    """
    if not api_key:
        print("Chave API vazia.")
        return False
    try:
        genai.configure(api_key=api_key)
        # Tenta listar modelos para garantir que a chave é válida
        list(genai.list_models())
        print("Chave API Gemini validada com sucesso.")
        return True
    except Exception as e:
        print(f"Erro ao validar a chave API Gemini. Verifique a chave ou as permissões. Erro: {e}")
        return False

def get_user_input(prompt: str, is_file: bool = False) -> str:
    """
    Solicita entrada do usuário e garante que não esteja vazia.
    Se is_file for True, verifica a existência do arquivo.
    """
    while True:
        user_input = input(prompt).strip().strip('"').strip("'")
        if not user_input:
            print("Entrada não pode ser vazia. Tente novamente.")
            continue
        
        if is_file:
            if not os.path.exists(user_input):
                print(f"Arquivo não encontrado em: {user_input}. Tente novamente.")
                continue
            if not user_input.lower().endswith('.pdf'):
                print("O arquivo deve ser um PDF (.pdf). Tente novamente.")
                continue
        
        return user_input

# --- Função Principal do Pipeline ---

def run_pipeline():
    print("--- Pipeline de Processamento de Documentos Jurídicos ---")
    
    # 1. Autenticação Gemini
    gemini_key = get_user_input("Por favor, insira sua chave API do GEMINI: ")
    if not validate_gemini_api_key(gemini_key):
        print("Falha na autenticação. Encerrando o pipeline.")
        sys.exit(1)
        
    # 2. Solicitar o Documento
    pdf_path_str = get_user_input("Insira o caminho completo do arquivo PDF a ser processado: ", is_file=True)
    pdf_path = Path(pdf_path_str)
    
    # 3. Definir Caminho de Saída
    output_dir = pdf_path.parent / "markdown_output"
    output_dir.mkdir(exist_ok=True)
    
    output_md_path = output_dir / f"{pdf_path.stem}_output.md"
    
    print(f"\nArquivo de saída será salvo em: {output_md_path}")
    
    # 4. Triagem e Processamento
    
    is_digital = is_digital_pdf(pdf_path_str)
    
    if is_digital:
        print("\n[DETECÇÃO] PDF digital detectado. Usando MarkItDown/Fallback para extração estruturada.")
        extract_text_digital_markitdown(pdf_path_str, str(output_md_path))
        
    else:
        print("\n[DETECÇÃO] PDF escaneado detectado. Tentando OCR local (Tesseract) primeiro.")
        
        # TENTATIVA 1: OCR LOCAL (Tesseract)
        tesseract_success = ocr_local_tesseract(pdf_path_str, str(output_md_path))
        
        if tesseract_success:
            print("\n[SUCESSO] OCR local concluído. Verifique a qualidade do arquivo de saída.")
            
            # Pergunta ao usuário se a qualidade é suficiente, ou se deve usar Gemini
            use_gemini = get_user_input("A qualidade do OCR Tesseract é suficiente? (s/n): ").lower()
            
            if use_gemini != 's':
                print("\n[UPGRADE] Qualidade insuficiente. Iniciando OCR e estruturação via Gemini (custo/nuvem).")
                
                # TENTATIVA 2: OCR EM NUVEM (Gemini)
                success = extract_ocr_to_markdown_gemini(pdf_path_str, str(output_md_path), gemini_key)
                
                if not success:
                    print("\n[ERRO] O processamento via Gemini falhou. O bloqueio de conteúdo pode estar ativo.")
            
        else:
            print("\n[FALHA LOCAL] OCR Tesseract falhou. Tentando OCR e estruturação via Gemini (custo/nuvem).")
            
            # TENTATIVA 2: OCR EM NUVEM (Gemini)
            success = extract_ocr_to_markdown_gemini(pdf_path_str, str(output_md_path), gemini_key)
            
            if not success:
                print("\n[ERRO] O processamento via Gemini falhou. O bloqueio de conteúdo pode estar ativo.")
            
    print("\n--- Pipeline concluído. ---")
    
if __name__ == "__main__":
    run_pipeline()