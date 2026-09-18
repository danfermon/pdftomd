# pdf_detector.py

import os
import logging
import fitz # PyMuPDF
from markitdown import MarkItDown
from docx import Document # python-docx

# Silenciar warnings verbosos do pdfminer (como FontBBox e descritores fora de padrão)
logging.getLogger("pdfminer").setLevel(logging.ERROR)

def is_digital_pdf(pdf_path: str, min_text_chars: int = 30, threshold: float = 0.7, max_sample_pages: int = 15) -> bool:
    """
    Verifica se um PDF é predominantemente digital (texto extraível) ou escaneado (imagem).
    Usa amostragem rápida para documentos grandes (evitando travar em processos de centenas de páginas).

    Args:
        pdf_path: Caminho completo para o arquivo PDF.
        min_text_chars: Mínimo de caracteres para uma página ser considerada "com texto".
        threshold: Proporção mínima de páginas com texto para classificar o PDF como digital.
        max_sample_pages: Número máximo de páginas a inspecionar para decisão rápida.

    Returns:
        True se for digital, False se for escaneado ou vazio.
    """
    try:
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            return False

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            return False

        # Amostragem inteligente de páginas para alta performance
        if total_pages <= max_sample_pages:
            sample_indices = range(total_pages)
        else:
            sample_indices = sorted(list(set(
                int(i * (total_pages - 1) / (max_sample_pages - 1))
                for i in range(max_sample_pages)
            )))

        pages_with_text = 0
        for idx in sample_indices:
            page = doc[idx]
            text = page.get_text()
            if len(text.strip()) >= min_text_chars:
                pages_with_text += 1

        doc.close()
        ratio = pages_with_text / len(sample_indices)
        return ratio >= threshold

    except Exception as e:
        print(f"Erro na detecção do PDF {pdf_path}: {e}")
        return False

def extract_digital_pdf_pymupdf(pdf_path: str, output_md: str) -> bool:
    """
    Extrai texto de PDF digital de forma ultra-rápida usando PyMuPDF (fitz em C/C++),
    preservando paginação ('## PÁGINA X') e ordenação espacial.
    """
    try:
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            print(f"[ERRO] Arquivo vazio ou inexistente: {pdf_path}")
            return False

        print(f"Iniciando extração ultra-rápida (PyMuPDF) de {os.path.basename(pdf_path)}...")
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        with open(output_md, 'w', encoding='utf-8-sig') as f:
            for i, page in enumerate(doc):
                # Extrai texto preservando ordem natural de leitura
                text = page.get_text("text", sort=True)
                page_header = f"## PÁGINA {i+1}\n\n"
                if text.strip():
                    f.write(f"{page_header}{text.strip()}\n\n")
                else:
                    f.write(f"{page_header}*(Página sem texto digital identificável)*\n\n")

        doc.close()
        print(f"Extração ultra-rápida concluída ({total_pages} páginas): {output_md}")
        return True
    except Exception as e:
        print(f"Erro na extração PyMuPDF de {pdf_path}: {e}")
        return False

def preprocess_docx_with_pagination(docx_path: str) -> str:
    """
    Lê um arquivo DOCX, detecta quebras de página manuais e insere marcadores '## PÁGINA X'.
    Retorna o caminho de um arquivo temporário modificado.
    """
    try:
        doc = Document(docx_path)
        page_count = 1
        
        # Inserir marcador da página 1 no início
        if doc.paragraphs:
            doc.paragraphs[0].insert_paragraph_before(f"## PÁGINA {page_count}")
        else:
            doc.add_paragraph(f"## PÁGINA {page_count}")

        for para in doc.paragraphs:
            for run in para.runs:
                if '<w:br w:type="page"/>' in run._element.xml or '<w:lastRenderedPageBreak/>' in run._element.xml:
                    page_count += 1
                    para.insert_paragraph_before(f"\n\n## PÁGINA {page_count}")
                    break 
        
        temp_path = docx_path.replace(".docx", "_paginated_temp.docx")
        doc.save(temp_path)
        return temp_path
    except Exception as e:
        print(f"Aviso: Falha ao processar paginação do DOCX ({e}). Usando arquivo original.")
        return docx_path

def extract_structured_markitdown(file_path: str, output_md: str) -> bool:
    """
    Extrai o texto e estrutura de qualquer arquivo suportado.
    - PDFs digitais: Roteados diretamente para PyMuPDF (ultra-rápido, segundos em vez de minutos).
    - DOCX: Pré-processamento de paginação + MarkItDown.
    - PPTX, XLSX, CSV, EPUB, JSON, HTML: MarkItDown.
    - DOC (Word 97-2003 legado): Tratamento específico e mensagem orientando salvar como .docx.
    """
    if not os.path.exists(file_path):
        print(f"Erro: Arquivo não encontrado em {file_path}")
        return False

    if os.path.getsize(file_path) == 0:
        print(f"[PULADO] Arquivo vazio (0 bytes): {file_path}")
        return False

    file_ext = os.path.splitext(file_path)[1].lower()

    # --- 1. Rota Ultra-Rápida para PDF Digital (PyMuPDF) ---
    if file_ext == '.pdf':
        success = extract_digital_pdf_pymupdf(file_path, output_md)
        if success:
            return True
        print("Aviso: Falha no motor primário PyMuPDF. Tentando MarkItDown como fallback...")

    # --- 2. Tratamento para arquivos .doc legados ---
    if file_ext == '.doc':
        print(f"Arquivo legado Word 97-2003 (.doc) detectado: {os.path.basename(file_path)}")
        # Tenta MarkItDown caso haja suporte de plugins
        try:
            md_converter = MarkItDown()
            result = md_converter.convert(file_path)
            if result and result.text_content:
                with open(output_md, 'w', encoding='utf-8-sig') as f:
                    f.write(result.text_content)
                print(f"Extração (.doc via MarkItDown) concluída: {output_md}")
                return True
        except Exception as e:
            print(f"Erro: Formato .doc legado não suportado diretamente pelo MarkItDown: {e}")
            print(f"[DICA] Para arquivos .doc legados, converta-os para .docx antes de processar.")
            return False

    # --- 3. Motor Geral MarkItDown (DOCX, PPTX, XLSX, CSV, etc.) ---
    processing_path = file_path
    is_temp_docx = False

    if file_ext == '.docx':
        print("Pré-processando DOCX para inserir marcadores de página...")
        processing_path = preprocess_docx_with_pagination(file_path)
        if processing_path != file_path:
            is_temp_docx = True

    try:
        md_converter = MarkItDown()
        print(f"Iniciando conversão estruturada de {os.path.basename(file_path)} para Markdown (MarkItDown)...")
        
        result = md_converter.convert(processing_path)
        markdown_content = result.text_content
        
        with open(output_md, 'w', encoding='utf-8-sig') as f:
            f.write(markdown_content)
        print(f"Extração estruturada (MarkItDown) concluída: {output_md}")
        return True
        
    except Exception as e:
        print(f"Erro ao usar MarkItDown para extração: {e}")
        
        # Fallback PyMuPDF caso seja PDF
        if file_ext == '.pdf':
            print("Tentando fallback com PyMuPDF (layout) para PDF...")
            return extract_digital_pdf_pymupdf(file_path, output_md)
        else:
            print(f"Nenhum fallback disponível para formato {file_ext}.")
            return False
            
    finally:
        if is_temp_docx and os.path.exists(processing_path):
            try:
                os.remove(processing_path)
            except Exception as e:
                print(f"Aviso: Não foi possível remover o arquivo temporário DOCX {processing_path}: {e}")

# Alias para compatibilidade retroativa
extract_text_digital_markitdown = extract_structured_markitdown
