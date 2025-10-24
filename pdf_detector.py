# C:\pdftomd\pdf_detector.py

import fitz # PyMuPDF
from markitdown import MarkItDown
import os

def is_digital_pdf(pdf_path: str, min_text_chars: int = 30, threshold: float = 0.7) -> bool:
    """
    Verifica se um PDF é predominantemente digital (texto extraível) ou escaneado (imagem).

    Args:
        pdf_path: Caminho completo para o arquivo PDF.
        min_text_chars: Mínimo de caracteres para uma página ser considerada "com texto".
        threshold: Proporção mínima de páginas com texto para classificar o PDF como digital.

    Returns:
        True se for digital, False se for escaneado (imagem).
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if total_pages == 0:
            return False

        pages_with_text = 0
        for page in doc:
            # Extrai texto simples
            text = page.get_text()
            if len(text.strip()) >= min_text_chars:
                pages_with_text += 1

        ratio = pages_with_text / total_pages
        return ratio >= threshold

    except Exception as e:
        print(f"Erro na detecção do PDF {pdf_path}: {e}")
        return False

def extract_structured_markitdown(file_path: str, output_md: str):
    """
    Extrai o texto de qualquer arquivo suportado (PDF digital, DOCX, XLSX, etc.) 
    usando MarkItDown para preservar a estrutura.
    Em caso de falha no PDF, tenta um fallback simples com PyMuPDF.
    """
    if not os.path.exists(file_path):
        print(f"Erro: Arquivo não encontrado em {file_path}")
        return

    # --- Tentativa 1: MarkItDown ---
    try:
        md_converter = MarkItDown()
        print(f"Iniciando conversão estruturada de {os.path.basename(file_path)} para Markdown (MarkItDown)...")
        
        result = md_converter.convert(file_path)
        markdown_content = result.text_content
        
        # Verificação simples para PDFs (se o MarkItDown falhar na tabela, tentamos o fallback)
        if markdown_content and (file_path.lower().endswith('.pdf') and "|---|---" not in markdown_content):
            raise Exception("MarkItDown não gerou tabelas ou falhou na estrutura do PDF. Tentando fallback.")
        
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"Extração estruturada (MarkItDown) concluída: {output_md}")
        return

    except Exception as e:
        print(f"Erro ao usar MarkItDown para extração: {e}")
        
        # --- Tentativa 2: Fallback PyMuPDF (Apenas para PDFs) ---
        if file_path.lower().endswith('.pdf'):
            print("Tentando fallback com PyMuPDF (layout) para PDF...")
            try:
                doc = fitz.open(file_path)
                with open(output_md, 'w', encoding='utf-8') as f:
                    for i, page in enumerate(doc):
                        # Usamos 'text' com o parâmetro 'layout' para tentar preservar o espaçamento
                        text = page.get_text("text", sort=True) 
                        f.write(f"\n\n## Página {i+1}\n\n{text.strip()}\n")
                print(f"Extração digital (Fallback PyMuPDF com layout) concluída: {output_md}")
            except Exception as e_f:
                print(f"Falha total na extração digital de PDF: {e_f}")
        else:
            print("Nenhum fallback disponível para este tipo de arquivo.")