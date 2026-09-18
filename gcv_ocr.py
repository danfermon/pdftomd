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


def pdf_to_pil_images(pdf_path: str, dpi: int = 200) -> List[Image.Image]:
    """
    Converte um PDF em uma lista de imagens PIL usando pdf2image.
    Verifica previamente se o arquivo existe e tem conteúdo (> 0 bytes).
    Usa DPI 200 por padrão para excelente precisão de OCR com baixo consumo de memória RAM.
    """
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        print(f"[OCR] Arquivo inexistente ou vazio (0 bytes) ignorado: {pdf_path}")
        return []

    pdf_filename = os.path.basename(pdf_path)
    print(f"Convertendo PDF '{pdf_filename}' em imagens PIL (DPI {dpi})...")
    try:
        # Checa integridade antes da conversão
        pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
        
        # Converte páginas em imagens
        images_from_path = convert_from_path(pdf_path, poppler_path=POPPLER_PATH, dpi=dpi)
        
        if not images_from_path:
            print(f"Nenhuma imagem gerada a partir do PDF '{pdf_filename}'.")
            return []
        
        print(f"{len(images_from_path)} páginas convertidas para imagem.")
        return images_from_path
    except Exception as e:
        print(f"Erro ao converter PDF '{pdf_filename}' para imagens via Poppler: {e}")
        return []

def ocr_local_tesseract(pdf_path: str, output_md: str) -> bool:
    """
    Roda OCR em um PDF escaneado usando Tesseract (local) com gestão eficiente de memória.
    """
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        print(f"[Tesseract] Arquivo vazio ou inexistente ignorado: {pdf_path}")
        return False

    pdf_filename = os.path.basename(pdf_path)
    print(f"Iniciando OCR local com Tesseract para {pdf_filename}...")
    
    pil_images = pdf_to_pil_images(pdf_path, dpi=200)
    if not pil_images:
        return False
        
    full_markdown_content = []
    
    try:
        # Tesseract precisa saber onde está o tessdata (apenas se fornecido localmente em bin/tessdata)
        if (BIN_PATH / "tessdata").exists():
            os.environ['TESSDATA_PREFIX'] = str(BIN_PATH / "tessdata")
        
        for i, img in enumerate(pil_images):
            page_num = i + 1
            print(f"-> Tesseract processando página {page_num}/{len(pil_images)}...")
            
            try:
                # lang='por' para português
                text = pytesseract.image_to_string(img, lang='por')
                
                if text.strip():
                    full_markdown_content.append(f"\n\n# PÁGINA {page_num}\n\n{text.strip()}")
                else:
                    print(f"Alerta: Tesseract não encontrou texto na página {page_num}.")
                    full_markdown_content.append(f"\n\n# PÁGINA {page_num} (VAZIA)\n\n")
            finally:
                # Liberação de memória da imagem
                try:
                    img.close()
                except:
                    pass

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
        
        pil_images = pdf_to_pil_images(pdf_path, dpi=200)
        if not pil_images:
            return False

        full_markdown_content = []
        
        try:
            for i, img_page in enumerate(pil_images):
                page_num = i + 1
                print(f"-> Processando página {page_num}/{len(pil_images)} via OpenAI (gpt-4o-mini)...")
                
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

    pil_images = pdf_to_pil_images(pdf_path, dpi=200)
    if not pil_images:
        return False

    full_markdown_content = []
    
    try:
        for i, img_page in enumerate(pil_images):
            page_num = i + 1
            print(f"-> Processando página {page_num}/{len(pil_images)} via Gemini...")
            
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