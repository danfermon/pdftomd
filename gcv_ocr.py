# gcv_ocr.py

import os
import sys
import gc
import google.generativeai as genai
from pdf2image import convert_from_path, pdfinfo_from_path
import pytesseract
from PIL import Image
from typing import List
from pathlib import Path

# --- Configuração de Caminhos para Executáveis (Poppler e Tesseract) ---
BASE_DIR = Path(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))))
BIN_PATH = BASE_DIR / "bin"

# Configuração do Poppler
POPPLER_PATH = str(BIN_PATH) if (BIN_PATH / "pdfinfo.exe").exists() else None 

# Configuração do Tesseract
if (BIN_PATH / "tesseract.exe").exists():
    pytesseract.pytesseract.tesseract_cmd = str(BIN_PATH / "tesseract.exe")
# ----------------------------------------------------------------------

def iter_pdf_pages_as_images(pdf_path: str, dpi: int = 150):
    """
    Gera imagens PIL página por página (streaming), liberando memória a cada página.
    Garante consumo de RAM quase ZERO (< 100 MB) mesmo para PDFs gigantes de centenas de páginas.
    """
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        return
    
    pdf_filename = os.path.basename(pdf_path)
    
    # 1. Tenta usar PyMuPDF (fitz) - extremamente rápido e uso mínimo de RAM
    try:
        import fitz
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        print(f"[Streaming OCR] Processando {total_pages} página(s) de '{pdf_filename}' via PyMuPDF...")
        for i in range(total_pages):
            page = doc[i]
            pix = page.get_pixmap(dpi=dpi)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            yield i + 1, total_pages, img
            try:
                img.close()
            except Exception:
                pass
            del pix
            del img
            gc.collect()
        doc.close()
        return
    except Exception as e:
        print(f"[PyMuPDF Fallback] Erro fitz ({e}). Usando pdf2image...")

    # 2. Fallback via pdf2image página a página
    try:
        from pdf2image import pdfinfo_from_path, convert_from_path
        info = pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
        total_pages = info.get("Pages", 1)
        print(f"[Streaming OCR] Processando {total_pages} página(s) de '{pdf_filename}' via pdf2image...")
        for page_num in range(1, total_pages + 1):
            imgs = convert_from_path(pdf_path, first_page=page_num, last_page=page_num, poppler_path=POPPLER_PATH, dpi=dpi)
            if imgs:
                img = imgs[0]
                yield page_num, total_pages, img
                try:
                    img.close()
                except Exception:
                    pass
                del imgs
                gc.collect()
    except Exception as err:
        print(f"[Streaming OCR Erro] Falha ao processar páginas de {pdf_filename}: {err}")


def pdf_to_pil_images(pdf_path: str, dpi: int = 150) -> List[Image.Image]:
    """Retorna lista de imagens PIL (mantido por compatibilidade retroativa)."""
    return [img for _, _, img in iter_pdf_pages_as_images(pdf_path, dpi=dpi)]


def ocr_local_tesseract(pdf_path: str, output_md: str) -> bool:
    """
    Roda OCR em um PDF escaneado usando Tesseract (local) em modo STREAMING página a página.
    Consumo de memória ultra-baixo para não estourar os limites do Docker.
    """
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        print(f"[Tesseract] Arquivo vazio ou inexistente ignorado: {pdf_path}")
        return False

    pdf_filename = os.path.basename(pdf_path)
    print(f"Iniciando OCR local com Tesseract (Streaming) para {pdf_filename}...")
    
    full_markdown_content = []
    
    try:
        if (BIN_PATH / "tessdata").exists():
            os.environ['TESSDATA_PREFIX'] = str(BIN_PATH / "tessdata")
            
        page_count = 0
        for page_num, total_pages, img in iter_pdf_pages_as_images(pdf_path, dpi=150):
            page_count += 1
            print(f"-> Tesseract processando página {page_num}/{total_pages}...")
            
            try:
                text = pytesseract.image_to_string(img, lang='por')
                if text.strip():
                    full_markdown_content.append(f"\n\n# PÁGINA {page_num}\n\n{text.strip()}")
                else:
                    full_markdown_content.append(f"\n\n# PÁGINA {page_num} (VAZIA)\n\n")
            except Exception as page_err:
                print(f"Alerta: Erro no OCR da página {page_num}: {page_err}")
                full_markdown_content.append(f"\n\n# PÁGINA {page_num} (ERRO NA EXTRAÇÃO)\n\n")

        if full_markdown_content:
            final_output = "\n".join(full_markdown_content)
            with open(output_md, 'w', encoding='utf-8-sig') as f:
                f.write(final_output)
            print(f"OCR Local (Tesseract) concluído com sucesso ({page_count} páginas): {output_md}")
            return True
        else:
            print("OCR Local falhou: Nenhuma página processada.")
            return False
            
    except pytesseract.TesseractNotFoundError:
        print("Erro: Tesseract não encontrado. Verifique a instalação e o PATH.")
        return False
    except Exception as e:
        print(f"Erro durante o OCR local com Tesseract: {e}")
        return False
    finally:
        gc.collect()

def extract_ocr_to_markdown_gemini(pdf_path: str, output_md: str, api_key: str) -> bool:
    """
    Roda OCR e extração estruturada em um PDF escaneado usando Gemini Multimodal ou OpenAI,
    processando uma página por vez para evitar bloqueios de conteúdo em documentos longos.
    """
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        print(f"[IA OCR] Arquivo vazio ou inexistente ignorado: {pdf_path}")
        return False

    pdf_filename = os.path.basename(pdf_path)
    is_openai = api_key.startswith("sk-")
    
    if is_openai:
        import base64
        import io
        import requests
        
        full_markdown_content = []
        
        try:
            for page_num, total_pages, img_page in iter_pdf_pages_as_images(pdf_path, dpi=150):
                print(f"-> Processando página {page_num}/{total_pages} via OpenAI (gpt-4o-mini)...")
                
                prompt_text = f"""
                A imagem a seguir é a página {page_num} de um documento.
                Sua única tarefa é realizar o OCR e extrair todo o conteúdo textual desta imagem.
                Preserve a estrutura original (parágrafos, títulos, listas, tabelas, etc.).
                Formate a saída inteiramente em Markdown. Use cabeçalhos (#, ##, ###) para títulos e seções.
                Não inclua nenhuma explicação, introdução, ou texto adicional antes ou depois do conteúdo Markdown.
                Gere o conteúdo Markdown para a Página {page_num}:
                """
                
                buffered = io.BytesIO()
                img_page.save(buffered, format="JPEG")
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
                
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                            ]
                        }
                    ],
                    "max_tokens": 4096
                }
                
                try:
                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=120
                    )
                    response.raise_for_status()
                    res_data = response.json()
                    markdown_content = res_data["choices"][0]["message"]["content"].strip()
                    
                    if markdown_content.lower().startswith("```markdown"):
                        markdown_content = markdown_content[len("```markdown"):].strip()
                    if markdown_content.endswith("```"):
                        markdown_content = markdown_content[:-len("```")].strip()

                    if not markdown_content:
                        full_markdown_content.append(f"\n\n# ERRO DE EXTRAÇÃO NA PÁGINA {page_num}\n\n")
                    else:
                        full_markdown_content.append(f"\n\n# PÁGINA {page_num}\n\n{markdown_content}")
                        
                except Exception as e:
                    print(f"Erro ao chamar a API OpenAI para a página {page_num}: {e}")
                    full_markdown_content.append(f"\n\n# ERRO DE API NA PÁGINA {page_num}: {e}\n\n")
                finally:
                    try:
                        img_page.close()
                    except:
                        pass
                    buffered.close()
        finally:
            gc.collect()
                
        if full_markdown_content:
            final_output = "\n".join(full_markdown_content)
            with open(output_md, 'w', encoding='utf-8-sig') as f:
                f.write(final_output)
            print(f"\nOCR e Extração (OpenAI) concluídos e salvos em: {output_md}")
            return True
        else:
            print(f"Falha total: Nenhuma página foi processada com sucesso para {pdf_filename}.")
            return False

    # Configuração do Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    except Exception as e:
        print(f"Erro ao configurar SDK Gemini: {e}")
        return False

    full_markdown_content = []
    
    try:
        for page_num, total_pages, img_page in iter_pdf_pages_as_images(pdf_path, dpi=150):
            print(f"-> Processando página {page_num}/{total_pages} via Gemini...")
            
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
                    request_options={"timeout": 120}
                )
                
                markdown_content = response.text.strip()
                
                if markdown_content.lower().startswith("```markdown"):
                    markdown_content = markdown_content[len("```markdown"):].strip()
                if markdown_content.endswith("```"):
                    markdown_content = markdown_content[:-len("```")].strip()

                if not markdown_content:
                    full_markdown_content.append(f"\n\n# ERRO DE EXTRAÇÃO NA PÁGINA {page_num}\n\n")
                else:
                    full_markdown_content.append(f"\n\n# PÁGINA {page_num}\n\n{markdown_content}")

            except Exception as e:
                print(f"Erro ao chamar a API Gemini para a página {page_num}: {e}")
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key:
                    print(f"-> Tentando fallback para OpenAI (gpt-4o-mini) na página {page_num}...")
                    try:
                        import base64
                        import io
                        import requests
                        
                        buffered = io.BytesIO()
                        img_page.save(buffered, format="JPEG")
                        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        
                        headers = {
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {openai_key}"
                        }
                        
                        payload = {
                            "model": "gpt-4o-mini",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": prompt_text},
                                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                                    ]
                                }
                            ],
                            "max_tokens": 4096
                        }
                        
                        response = requests.post(
                            "https://api.openai.com/v1/chat/completions",
                            headers=headers,
                            json=payload,
                            timeout=120
                        )
                        response.raise_for_status()
                        res_data = response.json()
                        markdown_content = res_data["choices"][0]["message"]["content"].strip()
                        
                        if markdown_content.lower().startswith("```markdown"):
                            markdown_content = markdown_content[len("```markdown"):].strip()
                        if markdown_content.endswith("```"):
                            markdown_content = markdown_content[:-len("```")].strip()
                            
                        if not markdown_content:
                            full_markdown_content.append(f"\n\n# ERRO DE EXTRAÇÃO NA PÁGINA {page_num}\n\n")
                        else:
                            full_markdown_content.append(f"\n\n# PÁGINA {page_num} (OpenAI Fallback)\n\n{markdown_content}")
                            continue
                    except Exception as e_fallback:
                        print(f"Erro no fallback da OpenAI para a página {page_num}: {e_fallback}")
                
                full_markdown_content.append(f"\n\n# ERRO DE API NA PÁGINA {page_num}: {e}\n\n")
            finally:
                try:
                    img_page.close()
                except:
                    pass
    finally:
        gc.collect()
            
    if full_markdown_content:
        final_output = "\n".join(full_markdown_content)
        with open(output_md, 'w', encoding='utf-8-sig') as f:
            f.write(final_output)
        print(f"\nOCR e Extração (Gemini) concluídos e salvos em: {output_md}")
        return True
    else:
        print(f"Falha total: Nenhuma página foi processada com sucesso para {pdf_filename}.")
        return False