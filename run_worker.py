#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Worker Autônomo de Conversão em Background para o PDFtoMD.

Executa de forma 100% independente do navegador:
1. Conecta ao Dropbox via Refresh Token permanente.
2. Varre a pasta especificada e identifica arquivos pendentes.
3. Baixa, converte (MarkItDown / OCR Streaming / OpenAI) e faz upload do .md.
4. Grava logs detalhados em 'worker.log'.
5. Ao concluir o último arquivo, FINALIZA O PROCESSO AUTOMATICAMENTE,
   liberando totalmente os recursos de CPU e memória da VPS!
"""

import os
import sys
import gc
import time
import argparse
from pathlib import Path
from datetime import datetime

# Garante UTF-8 no stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Carrega variáveis de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from dropbox_handler import DropboxHandler
from pdf_detector import is_digital_pdf, extract_structured_markitdown
from gcv_ocr import ocr_local_tesseract, extract_ocr_to_markdown_gemini

LOG_FILE = "worker.log"
SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.pptx', '.xlsx', '.doc', '.xls', 
    '.csv', '.json', '.xml', '.html', '.zip', '.mp3', 
    '.wav', '.jpg', '.png', '.epub'
}


def log(msg: str):
    """Grava log com timestamp tanto no stdout quanto no arquivo worker.log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass


def run_headless_conversion(input_path_str: str, output_path_str: str, api_key: str) -> bool:
    """
    Executa o pipeline de conversão de um arquivo de forma headless (sem Streamlit).
    """
    input_path = Path(input_path_str)
    if not input_path.exists() or input_path.stat().st_size == 0:
        log(f"  [PULADO] Arquivo vazio ou inexistente: {input_path.name}")
        return False

    ext = input_path.suffix.lower()

    if ext == '.pdf':
        is_digital = is_digital_pdf(input_path_str)
        if is_digital:
            log(f"  [PDF Digital] Extraindo texto via MarkItDown/PyMuPDF...")
            success = extract_structured_markitdown(input_path_str, output_path_str)
            return success and Path(output_path_str).exists()
        else:
            log(f"  [PDF Escaneado] Tentando OCR local com Tesseract (Streaming)...")
            tesseract_success = ocr_local_tesseract(input_path_str, output_path_str)
            if tesseract_success and Path(output_path_str).exists():
                return True
            elif api_key:
                log(f"  [OCR Fallback] Tesseract falhou. Chamando OCR via IA (OpenAI/Gemini)...")
                return extract_ocr_to_markdown_gemini(input_path_str, output_path_str, api_key)
            else:
                log(f"  [FALHA] PDF escaneado sem chave de IA configurada para fallback.")
                return False

    elif ext == '.doc':
        log(f"  [DOC Legado] Extraindo com MarkItDown...")
        success = extract_structured_markitdown(input_path_str, output_path_str)
        return success and Path(output_path_str).exists()

    elif ext in SUPPORTED_EXTENSIONS:
        log(f"  [{ext.upper()}] Extraindo conteúdo estruturado com MarkItDown...")
        success = extract_structured_markitdown(input_path_str, output_path_str)
        return success and Path(output_path_str).exists()

    return False


def main():
    parser = argparse.ArgumentParser(description="Worker em segundo plano para o PDFtoMD.")
    parser.add_argument("--folder", "-f", default=None, help="Pasta do Dropbox a ser processada (ex: / ou /Documentos)")
    parser.add_argument("--api-key", "-k", default=None, help="Chave API do LLM (OpenAI ou Gemini)")
    parser.add_argument("--overwrite", action="store_true", help="Se definido, sobrescreve arquivos já convertidos")
    args = parser.parse_args()

    log("=" * 70)
    log("INICIANDO WORKER AUTÔNOMO PDFTOMD (BACKGROUND)")
    log("=" * 70)

    # 1. Credenciais do Dropbox
    try:
        dbx = DropboxHandler()
        status, msg = dbx.check_connection()
        if not status:
            log(f"[ERRO CRÍTICO] Falha ao conectar ao Dropbox: {msg}")
            sys.exit(1)
        log(f"[✓] Conexão com Dropbox estabelecida: {msg}")
    except Exception as e:
        log(f"[ERRO CRÍTICO] Erro ao inicializar DropboxHandler: {e}")
        sys.exit(1)

    # 2. Chave de IA (Prioriza OpenAI se configurada, senão Gemini)
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GOOGLE_GEMINI_API_KEY")
    if api_key:
        provider = "OpenAI" if api_key.startswith("sk-") else "Gemini"
        log(f"[✓] Chave LLM detectada: Provedor {provider}")
    else:
        log("[AVISO] Nenhuma chave LLM configurada. Documentos escaneados dependerão exclusivamente do Tesseract.")

    # 3. Pasta Alvo
    folder_path = args.folder if args.folder is not None else "/"
    if folder_path == "":
        folder_path = "/"
    log(f"[*] Varrendo pasta: {folder_path} ...")

    # 4. Varredura
    try:
        file_entries, existing_md_set, _ = dbx.scan_folder_tree(folder_path, SUPPORTED_EXTENSIONS)
    except Exception as e:
        log(f"[ERRO CRÍTICO] Falha na varredura: {e}")
        sys.exit(1)

    total_scanned = len(file_entries)
    log(f"[*] Total de arquivos compatíveis encontrados: {total_scanned}")

    # Filtrar pendentes
    pending_entries = []
    for entry in file_entries:
        stem = Path(entry.name).stem
        parent = Path(entry.path_display).parent.as_posix()
        output_name = f"{stem}MD.md"
        output_path = f"{parent}/{output_name}".replace("//", "/")
        
        candidates = [
            output_path.lower(),
            f"{parent}/{stem}_MD.md".lower().replace("//", "/"),
            f"{parent}/{stem}.md".lower().replace("//", "/")
        ]
        
        is_already_done = any(c in existing_md_set for c in candidates)
        if args.overwrite or not is_already_done:
            pending_entries.append((entry, output_path))

    total_pending = len(pending_entries)
    already_done = total_scanned - total_pending
    log(f"[*] Já convertidos: {already_done} | Restantes para converter: {total_pending}")

    if total_pending == 0:
        log("=" * 70)
        log("[CONCLUÍDO] Todos os arquivos da pasta já possuem suas versões Markdown (.md)!")
        log("Liberando recursos da VPS. Até logo!")
        log("=" * 70)
        sys.exit(0)

    # 5. Diretório temporário local
    temp_dir = Path("temp_dropbox") / "worker_session"
    temp_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    errors = 0
    start_time = time.time()

    log(f"\nIniciando conversão de {total_pending} arquivos...")
    log("-" * 70)

    for idx, (entry, dbx_output_path) in enumerate(pending_entries, 1):
        item_start = time.time()
        log(f"[{idx}/{total_pending}] Processando: {entry.path_display} ({entry.size / 1024:.1f} KB)...")

        local_input = temp_dir / entry.name
        local_output = temp_dir / f"{Path(entry.name).stem}MD.md"

        success = False
        try:
            # Download
            if dbx.download_file(entry.path_display, str(local_input)):
                # Converte
                if run_headless_conversion(str(local_input), str(local_output), api_key):
                    if local_output.exists() and local_output.stat().st_size > 0:
                        # Upload
                        if dbx.upload_file(str(local_output), dbx_output_path):
                            elapsed = time.time() - item_start
                            log(f"  [✓] Convertido e enviado com sucesso em {elapsed:.1f}s -> {dbx_output_path}")
                            processed += 1
                            success = True
                        else:
                            log(f"  [X] Falha no upload para o Dropbox: {dbx_output_path}")
                    else:
                        log(f"  [X] Conversão finalizada mas arquivo de saída está vazio ou não existe.")
                else:
                    log(f"  [X] Falha na conversão do arquivo.")
            else:
                log(f"  [X] Falha no download do Dropbox.")
        except Exception as err:
            log(f"  [EXCEÇÃO] Erro ao processar {entry.name}: {err}")
        finally:
            if not success:
                errors += 1
            # Limpeza rigorosa de arquivos temporários e lixo de memória RAM
            if local_input.exists():
                try: os.remove(local_input)
                except: pass
            if local_output.exists():
                try: os.remove(local_output)
                except: pass
            gc.collect()

        # Log de progresso a cada 10 arquivos
        if idx % 10 == 0 or idx == total_pending:
            pct = (idx / total_pending) * 100
            total_elapsed_min = (time.time() - start_time) / 60
            log(f"--- Progresso do Lote: {idx}/{total_pending} ({pct:.1f}%) | Concluídos: {processed} | Falhas: {errors} | Tempo corrido: {total_elapsed_min:.1f} min ---")

    total_time_min = (time.time() - start_time) / 60
    log("=" * 70)
    log(f"LOTE FINALIZADO COM SUCESSO!")
    log(f"Total processados com sucesso: {processed}/{total_pending}")
    log(f"Total de falhas/erros: {errors}")
    log(f"Tempo total gasto: {total_time_min:.1f} minutos.")
    log("O worker terminou todas as tarefas e está se encerrando para liberar a VPS.")
    log("=" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
