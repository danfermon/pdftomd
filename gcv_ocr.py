# C:\pdftomd\gcv_ocr.py

import os
import sys
import google.generativeai as genai
from pdf2image import convert_from_path, pdfinfo_from_path
import pytesseract
from PIL import Image
from typing import List
from pathlib import Path

# --- Configuração de Caminhos para Executáveis (Poppler e Tesseract) ---
# O PyInstaller define _MEIPASS para o caminho da pasta temporária de extração.
BASE_DIR = Path(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))))
BIN_PATH = BASE_DIR / "bin"

# Configuração do Poppler
# Se o executável pdfinfo.exe estiver na pasta bin, usamos esse caminho.
POPPLER_PATH = str(BIN_PATH) if (BIN_PATH / "pdfinfo.exe").exists() else None 

# Configuração do Tesseract
if (BIN_PATH / "tesseract.exe").exists():
    pytesseract.pytesseract.tesseract_cmd = str(BIN_PATH / "tesseract.exe")
# ----------------------------------------------------------------------


def pdf_to_pil_images(pdf_path: str) -> List[Image.Image]:
    """
    Converte um PDF em uma lista de imagens PIL usando pdf2image.
    Requer a instalação do Poppler no sistema ou no caminho POPPLER_PATH.
    """
    pdf_filename = os.path.basename(pdf_path)
    print(f"Convertendo PDF '{pdf_filename}' em imagens PIL (requer Poppler)...")
    try:
        # Tenta obter informações para checar se o PDF é válido
        pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
        
        # DPI 300 é um bom equilíbrio para OCR de documentos jurídicos
        images_from_path = convert_from_path(pdf_path, poppler_path=POPPLER_PATH, dpi=300)
        
        if not images_from_path:
            print(f"Nenhuma imagem gerada a partir do PDF '{pdf_filename}'.")
            return []
        
        print(f"{len(images_from_path)} páginas convertidas.")
        return images_from_path
    except Exception as e:
        print(f"Erro Crítico ao converter PDF '{pdf_filename}' para imagens. Verifique a instalação do Poppler e o caminho POPPLER_PATH.")
        print(f"Detalhe do erro: {e}")
        return []

def ocr_local_tesseract(pdf_path: str, output_md: str) -> bool:
    """
    Roda OCR em um PDF escaneado usando Tesseract (local).
    """
    pdf_filename = os.path.basename(pdf_path)
    print(f"Iniciando OCR local com Tesseract para {pdf_filename}...")
    
    # Reutilizamos a função de conversão para imagens
    pil_images = pdf_to_pil_images(pdf_path)
    if not pil_images:
        return False
        
    full_markdown_content = []
    
    try:
        # Tesseract precisa saber onde está o tessdata
        os.environ['TESSDATA_PREFIX'] = str(BIN_PATH / "tessdata")
        
        for i, img in enumerate(pil_images):
            page_num = i + 1
            print(f"-> Tesseract processando página {page_num}/{len(pil_images)}...")
            
            # lang='por' para português.
            text = pytesseract.image_to_string(img, lang='por')
            
            if text.strip():
                # Formatação simples em Markdown
                full_markdown_content.append(f"\n\n# PÁGINA {page_num}\n\n{text.strip()}")
            else:
                print(f"Alerta: Tesseract não encontrou texto na página {page_num}.")
                full_markdown_content.append(f"\n\n# PÁGINA {page_num} (VAZIA)\n\n")

        if full_markdown_content:
            final_output = "\n".join(full_markdown_content)
            with open(output_md, 'w', encoding='utf-8-sig') as f:
                f.write(final_output)
            print(f"OCR Local (Tesseract) concluído e salvo em: {output_md}")
            return True
        else:
            print("OCR Local falhou: Nenhuma página processada com sucesso.")
            return False
            
    except pytesseract.TesseractNotFoundError:
        print("Erro: Tesseract não encontrado. Verifique a instalação e o PATH.")
        return False
    except Exception as e:
        print(f"Erro durante o OCR local com Tesseract: {e}")
        return False

def extract_ocr_to_markdown_gemini(pdf_path: str, output_md: str, api_key: str):
    """
    Roda OCR e extração estruturada em um PDF escaneado usando Gemini Multimodal,
    processando uma página por vez para evitar bloqueios de conteúdo em documentos longos.
    """
    pdf_filename = os.path.basename(pdf_path)
    
    # 1. Configuração do Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    except Exception as e:
        print(f"Erro ao configurar SDK Gemini: {e}")
        return False

    # 2. Conversão para Imagens
    pil_images = pdf_to_pil_images(pdf_path)
    if not pil_images:
        return False

    full_markdown_content = []
    
    # 3. Processamento Página por Página
    for i, img_page in enumerate(pil_images):
        page_num = i + 1
        print(f"-> Processando página {page_num}/{len(pil_images)}...")
        
        prompt_text = f"""
        A imagem a seguir é a página {page_num} de um documento.
        
        Sua única tarefa é realizar o OCR e extrair todo o conteúdo textual desta imagem.
        
        Preserve a estrutura original (parágrafos, títulos, listas, tabelas, etc.).
        
        Formate a saída inteiramente em Markdown. Use cabeçalhos (#, ##, ###) para títulos e seções.
        
        Não inclua nenhuma explicação, introdução, ou texto adicional antes ou depois do conteúdo Markdown.
        
        Gere o conteúdo Markdown para a Página {page_num}:
        """
        
        content_parts = [prompt_text, img_page]
        
        try:
            generation_config = genai.types.GenerationConfig()
            
            response = model.generate_content(
                content_parts,
                generation_config=generation_config,
                request_options={"timeout": 120} # 2 minutos de timeout por página
            )
            
            markdown_content = response.text.strip()
            
            # Limpeza: Remove blocos de código Markdown (```markdown ... ```) se o Gemini os adicionar
            if markdown_content.lower().startswith("```markdown"):
                markdown_content = markdown_content[len("```markdown"):].strip()
            if markdown_content.endswith("```"):
                markdown_content = markdown_content[:-len("```")].strip()

            if not markdown_content:
                print(f"Alerta: Resposta do Gemini para a página {page_num} está vazia.")
                full_markdown_content.append(f"\n\n# ERRO DE EXTRAÇÃO NA PÁGINA {page_num}\n\n")
            else:
                # Adiciona um cabeçalho de página para estruturação
                full_markdown_content.append(f"\n\n# PÁGINA {page_num}\n\n{markdown_content}")

        except Exception as e:
            print(f"Erro ao chamar a API Gemini para a página {page_num}: {e}")
            # Se falhar, adiciona um placeholder de erro e continua para a próxima página
            full_markdown_content.append(f"\n\n# ERRO DE API NA PÁGINA {page_num}: {e}\n\n")
            
    # 4. Salvar o resultado concatenado
    if full_markdown_content:
        final_output = "\n".join(full_markdown_content)
        with open(output_md, 'w', encoding='utf-8-sig') as f:
            f.write(final_output)
            
        print(f"\nOCR e Extração (Gemini) concluídos e salvos em: {output_md}")
        return True
    else:
        print(f"Falha total: Nenhuma página foi processada com sucesso para {pdf_filename}.")
        return False