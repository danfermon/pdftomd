#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificação de Conversão de Arquivos (PDF -> MD) no Dropbox.

Permite fornecer as credenciais (chave API do LLM e token do Dropbox),
valida ambas as conexões e varre a pasta indicada para apresentar
quantos arquivos foram convertidos e quantos ainda faltam converter.
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Forçar UTF-8 no terminal Windows para evitar caracteres corrompidos
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Carregar variáveis de ambiente do .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Suporte a cores no terminal Windows/Linux
try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    BLUE = Fore.BLUE
    WHITE = Fore.WHITE
    BOLD = Style.BRIGHT
    DIM = Style.DIM
    RESET = Style.RESET_ALL
except Exception:
    GREEN = RED = YELLOW = CYAN = MAGENTA = BLUE = WHITE = BOLD = DIM = RESET = ""

import dropbox
from dropbox.exceptions import AuthError, ApiError
from dropbox.common import PathRoot

# Extensões suportadas pelo ecossistema pdftomd
SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.pptx', '.xlsx', '.doc', '.xls', 
    '.csv', '.json', '.xml', '.html', '.zip', '.mp3', 
    '.wav', '.jpg', '.png', '.epub'
}

SYSTEM_FILE_PREFIXES = ("._", ".~$", "~$")
SYSTEM_FILE_NAMES = (".ds_store", "thumbs.db")


def is_system_file(file_name: str) -> bool:
    """Ignora arquivos de metadados ocultos de SO (macOS, Windows locks)."""
    name_lower = file_name.lower()
    if name_lower in SYSTEM_FILE_NAMES:
        return True
    for prefix in SYSTEM_FILE_PREFIXES:
        if file_name.startswith(prefix):
            return True
    return False


def with_retry(api_func, max_retries=5, initial_delay=2.0):
    """Executa chamadas da API do Dropbox com backoff exponencial contra Rate Limit."""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return api_func()
        except ApiError as err:
            is_rate_limit = False
            retry_after = delay
            if hasattr(err, 'error') and hasattr(err.error, 'is_rate_limit') and err.error.is_rate_limit():
                is_rate_limit = True
                if hasattr(err.error, 'get_rate_limit_reason') and hasattr(err.error.get_rate_limit_reason(), 'retry_after'):
                    retry_after = max(err.error.get_rate_limit_reason().retry_after, delay)
            
            if is_rate_limit and attempt < max_retries - 1:
                print(f"{YELLOW}[RATE LIMIT] Aguardando {retry_after:.1f}s antes da tentativa {attempt + 2}/{max_retries}...{RESET}")
                time.sleep(retry_after)
                delay *= 2
            elif attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise err
        except AuthError as err:
            raise err
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise e


def validate_llm_key(api_key: str) -> Tuple[bool, str]:
    """
    Valida a chave do LLM (Google Gemini ou OpenAI).
    Retorna (is_valid, message).
    """
    if not api_key or not api_key.strip():
        return False, "Chave API do LLM não fornecida."
    
    api_key = api_key.strip()
    
    # 1. Se for OpenAI (chave começa com 'sk-')
    if api_key.startswith("sk-"):
        try:
            import requests
            headers = {"Authorization": f"Bearer {api_key}"}
            res = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=8)
            if res.status_code == 200:
                return True, "OpenAI API Key validada com sucesso!"
            else:
                return False, f"Falha na validação OpenAI (HTTP {res.status_code})."
        except Exception as e:
            return False, f"Erro ao contatar OpenAI: {e}"
            
    # 2. Google Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # Tenta listar os modelos para confirmar autenticação
        models = list(genai.list_models())
        count = len(models)
        return True, f"Google Gemini API Key validada com sucesso! ({count} modelos acessíveis)"
    except Exception as e:
        return False, f"Falha na validação Gemini: {e}"


def init_dropbox_client(token: str = None, refresh_token: str = None, app_key: str = None, app_secret: str = None) -> Tuple[dropbox.Dropbox, dict]:
    """
    Inicializa o cliente do Dropbox com suporte a Team Spaces / Business.
    Detecta automaticamente se o valor informado é um Access Token ou Refresh Token.
    Retorna o cliente configurado e os dados da conta.
    """
    refresh_token = refresh_token or os.environ.get("DROPBOX_REFRESH_TOKEN")
    app_key = app_key or os.environ.get("DROPBOX_APP_KEY")
    app_secret = app_secret or os.environ.get("DROPBOX_APP_SECRET")

    # Se o token informado for na verdade um Refresh Token (não começa com 'sl.')
    if token and not token.strip().startswith("sl.") and not refresh_token:
        refresh_token = token.strip()
        token = None

    if refresh_token:
        refresh_token = refresh_token.strip().strip('"').strip("'")
    if app_key:
        app_key = app_key.strip().strip('"').strip("'")
    if app_secret:
        app_secret = app_secret.strip().strip('"').strip("'")

    if refresh_token and app_key and app_secret:
        base_dbx = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
    elif token and token.strip():
        try:
            base_dbx = dropbox.Dropbox(token.strip())
            # Testa rápido se o token funciona
            with_retry(lambda: base_dbx.users_get_current_account())
        except AuthError:
            # Se falhou como access token, tenta como refresh token com as chaves do app
            if app_key and app_secret:
                base_dbx = dropbox.Dropbox(
                    oauth2_refresh_token=token.strip(),
                    app_key=app_key.strip(),
                    app_secret=app_secret.strip()
                )
            else:
                raise
    else:
        raise ValueError("Nenhuma credencial do Dropbox fornecida.")
    
    account = with_retry(lambda: base_dbx.users_get_current_account())
    
    active_dbx = base_dbx
    if hasattr(account, 'root_info') and account.root_info:
        root_ns = account.root_info.root_namespace_id
        candidate = base_dbx.with_path_root(PathRoot.root(root_ns))
        try:
            with_retry(lambda: candidate.files_list_folder("", limit=1))
            active_dbx = candidate
        except Exception:
            active_dbx = base_dbx
            
    account_info = {
        "display_name": account.name.display_name,
        "email": getattr(account, 'email', 'N/A'),
        "account_type": type(account.account_type).__name__ if hasattr(account, 'account_type') else 'Standard'
    }
    return active_dbx, account_info


def list_top_folders(dbx: dropbox.Dropbox) -> List[str]:
    """Lista pastas de primeiro nível para facilitar escolha do usuário."""
    folders = []
    try:
        res = with_retry(lambda: dbx.files_list_folder("", limit=50))
        for entry in res.entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                folders.append(entry.path_display)
    except Exception:
        pass
    return sorted(folders)


def scan_folder(dbx: dropbox.Dropbox, folder_path: str, only_pdf: bool = False):
    """
    Varre recursivamente a pasta informada e mapeia:
    1. Arquivos fonte suportados
    2. Arquivos .md já existentes
    """
    path_param = folder_path.strip()
    if path_param == "/" or path_param == "":
        path_param = ""
    elif path_param.endswith("/"):
        path_param = path_param[:-1]
        
    print(f"\n{CYAN}Iniciando varredura recursiva em:{RESET} {BOLD}{path_param or '/'}{RESET}")
    print(f"{DIM}Aguarde, listando arquivos via API do Dropbox...{RESET}")
    
    allowed_exts = {'.pdf'} if only_pdf else SUPPORTED_EXTENSIONS
    
    source_files = [] # List of FileMetadata
    existing_md_set = set() # Set of lowercased posix paths
    
    res = with_retry(lambda: dbx.files_list_folder(path_param, recursive=True))
    
    count_scanned = 0
    
    def process_entries(entries):
        nonlocal count_scanned
        for entry in entries:
            if isinstance(entry, dropbox.files.FileMetadata):
                count_scanned += 1
                if count_scanned % 100 == 0:
                    print(f"  {DIM}... {count_scanned} arquivos verificados{RESET}", end="\r")
                    
                if is_system_file(entry.name):
                    continue
                
                path_lower = entry.path_display.lower()
                ext = os.path.splitext(entry.name)[1].lower()
                
                if ext == '.md':
                    existing_md_set.add(path_lower)
                elif ext in allowed_exts:
                    source_files.append(entry)
                    
    process_entries(res.entries)
    
    while res.has_more:
        cursor = res.cursor
        res = with_retry(lambda: dbx.files_list_folder_continue(cursor))
        process_entries(res.entries)
        
    print(f"\r  {GREEN}[OK]{RESET} Varredura concluída: {BOLD}{count_scanned}{RESET} arquivos inspecionados.               ")
    return source_files, existing_md_set


def analyze_conversion_status(source_files: List, existing_md_set: Set[str]) -> Tuple[List[dict], List[dict], Dict[str, dict]]:
    """
    Compara cada arquivo fonte com a presença do Markdown correspondente.
    Padrão principal: {stem}MD.md
    Padrões secundários aceitos: {stem}_MD.md, {stem}.md
    """
    converted = []
    pending = []
    stats_by_ext = {}
    
    for entry in source_files:
        stem = Path(entry.name).stem
        parent = Path(entry.path_display).parent.as_posix()
        ext = os.path.splitext(entry.name)[1].lower()
        
        if ext not in stats_by_ext:
            stats_by_ext[ext] = {"total": 0, "converted": 0, "pending": 0}
        stats_by_ext[ext]["total"] += 1
        
        # Possíveis nomes do arquivo Markdown gerado
        candidates = [
            f"{parent}/{stem}MD.md".lower(),
            f"{parent}/{stem}_MD.md".lower(),
            f"{parent}/{stem}.md".lower(),
            f"{parent}/{stem}md.md".lower(),
            f"{parent}/{stem}_md.md".lower()
        ]
        
        # Remove barras duplas se houver
        candidates = [c.replace("//", "/") for c in candidates]
        
        is_converted = any(c in existing_md_set for c in candidates)
        
        file_info = {
            "name": entry.name,
            "path": entry.path_display,
            "size_kb": entry.size / 1024,
            "ext": ext,
            "expected_md": f"{parent}/{stem}MD.md".replace("//", "/")
        }
        
        if is_converted:
            converted.append(file_info)
            stats_by_ext[ext]["converted"] += 1
        else:
            pending.append(file_info)
            stats_by_ext[ext]["pending"] += 1
            
    return converted, pending, stats_by_ext


def print_progress_bar(percentage: float, length: int = 30):
    """Exibe barra de progresso visual colorida."""
    filled = int(length * (percentage / 100))
    bar = "█" * filled + "░" * (length - filled)
    color = GREEN if percentage == 100 else (YELLOW if percentage >= 50 else RED)
    return f"{color}[{bar}] {percentage:.1f}%{RESET}"


def export_report_file(output_path: str, folder_path: str, converted: List[dict], pending: List[dict]):
    """Exporta lista de arquivos pendentes para conferência."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"=== RELATORIO DE CONVERSAO PDFTOMD ===\n")
            f.write(f"Data/Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Pasta Dropbox: {folder_path}\n")
            f.write(f"Total Arquivos: {len(converted) + len(pending)}\n")
            f.write(f"Convertidos: {len(converted)}\n")
            f.write(f"Faltam Converter: {len(pending)}\n")
            pct = (len(converted) / (len(converted) + len(pending)) * 100) if (len(converted) + len(pending)) > 0 else 0
            f.write(f"Progresso: {pct:.1f}%\n\n")
            
            f.write("=" * 60 + "\n")
            f.write("ARQUIVOS PENDENTES (FALTANDO CONVERTER):\n")
            f.write("=" * 60 + "\n")
            if pending:
                for item in pending:
                    f.write(f"- {item['path']} ({item['size_kb']:.1f} KB) -> Esperado: {item['expected_md']}\n")
            else:
                f.write("Nenhum arquivo pendente! Todos foram convertidos.\n")
                
            f.write("\n" + "=" * 60 + "\n")
            f.write("ARQUIVOS JA CONVERTIDOS:\n")
            f.write("=" * 60 + "\n")
            for item in converted:
                f.write(f"- {item['path']}\n")
                
        print(f"\n{GREEN}[✓] Relatório detalhado exportado com sucesso para:{RESET} {BOLD}{output_path}{RESET}")
    except Exception as e:
        print(f"{RED}[X] Erro ao exportar relatório: {e}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Verifica status de conversão de documentos (PDF -> MD) em pastas do Dropbox.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python check_status.py
  python check_status.py --folder "/Documentos"
  python check_status.py --only-pdf
  python check_status.py --token "sl.u...." --api-key "AIza..." --folder "/Juridico" --export "pendentes.txt"
        """
    )
    parser.add_argument("--token", "-t", help="Token de acesso do Dropbox", default=None)
    parser.add_argument("--api-key", "-k", help="Chave API do LLM (Gemini ou OpenAI)", default=None)
    parser.add_argument("--folder", "-f", help="Caminho da pasta no Dropbox (ex: /Processos ou /)", default=None)
    parser.add_argument("--only-pdf", action="store_true", help="Filtrar apenas arquivos PDF")
    parser.add_argument("--export", "-e", help="Salvar lista de pendentes em arquivo (ex: pendentes.txt)", default=None)
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print(f" {BOLD}{CYAN}PDFtoMD — Verificador de Status de Conversão{RESET}")
    print("=" * 70)
    
    # -------------------------------------------------------------
    # 1. Obter e validar Chave API do LLM
    # -------------------------------------------------------------
    env_gemini = os.environ.get("GOOGLE_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    env_openai = os.environ.get("OPENAI_API_KEY")
    default_llm = env_gemini or env_openai
    
    llm_key = args.api_key
    if not llm_key:
        if default_llm:
            masked = default_llm[:8] + "..." + default_llm[-4:]
            print(f"\n{WHITE}[1/3] Chave API do LLM:{RESET}")
            resp = input(f"Chave detectada no .env ({CYAN}{masked}{RESET}).\nUsar esta chave? [Enter para Sim, ou cole nova chave]: ").strip()
            llm_key = default_llm if not resp else resp
        else:
            print(f"\n{WHITE}[1/3] Chave API do LLM:{RESET}")
            llm_key = input("Cole a chave da API do Gemini ou OpenAI: ").strip()
            
    print(f"{DIM}Validando chave LLM...{RESET}", end=" ")
    is_llm_valid, llm_msg = validate_llm_key(llm_key)
    if is_llm_valid:
        print(f"{GREEN}[✓] {llm_msg}{RESET}")
    else:
        print(f"{RED}[X] {llm_msg}{RESET}")
        resp = input(f"{YELLOW}Deseja continuar mesmo sem validar a chave LLM? (s/N): {RESET}").strip().lower()
        if resp not in ('s', 'sim', 'y', 'yes'):
            print(f"{RED}Operação cancelada pelo usuário.{RESET}")
            sys.exit(1)

    # -------------------------------------------------------------
    # 2. Obter e validar Token do Dropbox
    # -------------------------------------------------------------
    env_refresh = os.environ.get("DROPBOX_REFRESH_TOKEN")
    env_app_key = os.environ.get("DROPBOX_APP_KEY")
    env_app_sec = os.environ.get("DROPBOX_APP_SECRET")
    env_dbx = os.environ.get("DROPBOX_ACCESS_TOKEN")
    dbx_token = args.token
    
    dbx_client = None
    account_info = None
    
    # Se existe Refresh Token configurado com app key/secret no .env
    if not dbx_token and env_refresh and env_app_key and env_app_sec:
        print(f"\n{WHITE}[2/3] Conexão do Dropbox:{RESET}")
        print(f"  {GREEN}[✓] Refresh Token permanente detectado no .env!{RESET}")
        resp = input("Usar Refresh Token permanente (sem expiração de 4h)? [Enter para Sim, ou 'n' para colar outro]: ").strip().lower()
        if resp not in ('n', 'nao', 'não', 'no'):
            print(f"{DIM}Conectando ao Dropbox via Refresh Token...{RESET}", end=" ")
            try:
                dbx_client, account_info = init_dropbox_client(refresh_token=env_refresh, app_key=env_app_key, app_secret=env_app_sec)
                print(f"{GREEN}[✓] Conectado permanentemente!{RESET}")
                print(f"  {CYAN}Usuário:{RESET} {account_info['display_name']} ({account_info['account_type']})")
                if account_info['email'] != 'N/A':
                    print(f"  {CYAN}Email:{RESET} {account_info['email']}")
            except Exception as e:
                print(f"{RED}[X] Falha com Refresh Token: {e}{RESET}")
                dbx_client = None

    while not dbx_client:
        if not dbx_token:
            if env_dbx:
                masked_dbx = env_dbx[:10] + "..." + env_dbx[-6:]
                print(f"\n{WHITE}[2/3] Token do Dropbox:{RESET}")
                resp = input(f"Token detectado no .env ({CYAN}{masked_dbx}{RESET}).\nUsar este token? [Enter para Sim, ou cole novo token]: ").strip()
                dbx_token = env_dbx if not resp else resp
            else:
                print(f"\n{WHITE}[2/3] Token do Dropbox:{RESET}")
                dbx_token = input("Cole o token de acesso do Dropbox (inicia com sl. ou token): ").strip()
                
        print(f"{DIM}Conectando ao Dropbox e verificando token...{RESET}", end=" ")
        try:
            dbx_client, account_info = init_dropbox_client(token=dbx_token)
            print(f"{GREEN}[✓] Conectado com sucesso!{RESET}")
            print(f"  {CYAN}Usuário:{RESET} {account_info['display_name']} ({account_info['account_type']})")
            if account_info['email'] != 'N/A':
                print(f"  {CYAN}Email:{RESET} {account_info['email']}")
        except AuthError:
            print(f"{RED}[X] Erro de Autenticação:{RESET} Token inválido ou expirado.")
            print(f"{YELLOW}Dica: Tokens 'sl.' expiram em 4 horas. Para obter um token permanente que nunca expira, execute: python get_dropbox_refresh_token.py{RESET}")
            dbx_token = None
            env_dbx = None
            resp = input("\nDeseja tentar outro token? (S/n): ").strip().lower()
            if resp in ('n', 'nao', 'não', 'no'):
                sys.exit(1)
        except Exception as e:
            print(f"{RED}[X] Erro ao conectar ao Dropbox: {e}{RESET}")
            dbx_token = None
            env_dbx = None
            resp = input("\nDeseja tentar novamente? (S/n): ").strip().lower()
            if resp in ('n', 'nao', 'não', 'no'):
                sys.exit(1)

    # -------------------------------------------------------------
    # 3. Escolha da pasta a ser varrida
    # -------------------------------------------------------------
    folder_path = args.folder
    if folder_path is None:
        print(f"\n{WHITE}[3/3] Seleção da Pasta do Dropbox:{RESET}")
        
        # Exibe pastas raízes para facilitar
        top_folders = list_top_folders(dbx_client)
        if top_folders:
            print(f"{DIM}Pastas encontradas na raiz:{RESET}")
            for idx, tf in enumerate(top_folders[:12], 1):
                print(f"  {CYAN}{idx}.{RESET} {tf}")
            print(f"  {DIM}(ou digite qualquer subpasta como '/MinhaPasta/Subpasta'){RESET}")
            
        prompt_txt = "Informe o caminho da pasta a ser varrida (Enter para varrer a Raiz '/'): "
        user_choice = input(prompt_txt).strip()
        
        # Se o usuário digitou apenas um número da lista
        if user_choice.isdigit() and 1 <= int(user_choice) <= len(top_folders):
            folder_path = top_folders[int(user_choice) - 1]
        elif user_choice == "" or user_choice == "/":
            folder_path = "/"
        else:
            folder_path = user_choice if user_choice.startswith("/") else f"/{user_choice}"

    # -------------------------------------------------------------
    # 4. Executar Varredura e Análise
    # -------------------------------------------------------------
    try:
        source_files, existing_md_set = scan_folder(dbx_client, folder_path, only_pdf=args.only_pdf)
    except Exception as e:
        print(f"\n{RED}[X] Falha durante a varredura da pasta '{folder_path}': {e}{RESET}")
        sys.exit(1)
        
    total_docs = len(source_files)
    if total_docs == 0:
        print(f"\n{YELLOW}Nenhum arquivo compatível encontrado na pasta especificada.{RESET}")
        sys.exit(0)
        
    converted, pending, stats_by_ext = analyze_conversion_status(source_files, existing_md_set)
    
    total_conv = len(converted)
    total_pend = len(pending)
    pct = (total_conv / total_docs * 100) if total_docs > 0 else 0
    
    # -------------------------------------------------------------
    # 5. Exibir Relatório Formatado
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print(f" {BOLD}RESUMO DO STATUS DE CONVERSÃO{RESET}")
    print("=" * 70)
    print(f" Pasta analisada:  {BOLD}{folder_path}{RESET}")
    print(f" Total de arquivos: {BOLD}{total_docs}{RESET}")
    print(f" Convertidos (MD):  {BOLD}{GREEN}{total_conv}{RESET}")
    print(f" Faltam converter:  {BOLD}{RED if total_pend > 0 else GREEN}{total_pend}{RESET}")
    print(f" Progresso geral:   {print_progress_bar(pct)}")
    print("-" * 70)
    
    # Detalhamento por formato
    print(f" {BOLD}Detalhamento por extensão:{RESET}")
    print(f"  {'Extensão':<10} | {'Total':<8} | {'Convertidos':<12} | {'Faltam':<8} | {'Status'}")
    print("  " + "-" * 55)
    for ext, stats in sorted(stats_by_ext.items()):
        sub_pct = (stats['converted'] / stats['total'] * 100) if stats['total'] > 0 else 0
        pend_color = RED if stats['pending'] > 0 else GREEN
        print(f"  {ext:<10} | {stats['total']:<8} | {GREEN}{stats['converted']:<12}{RESET} | {pend_color}{stats['pending']:<8}{RESET} | {sub_pct:.0f}% concluído")
        
    print("=" * 70)
    
    # -------------------------------------------------------------
    # 6. Listagem ou exportação dos pendentes
    # -------------------------------------------------------------
    if total_pend > 0:
        print(f"\n{YELLOW}Há {total_pend} arquivo(s) aguardando conversão.{RESET}")
        
        # Se passou o argumento --export
        export_file = args.export
        if not export_file:
            resp = input("\nDeseja ver a lista dos primeiros 15 arquivos pendentes no terminal? (s/N): ").strip().lower()
            if resp in ('s', 'sim', 'y', 'yes'):
                print(f"\n{CYAN}Arquivos pendentes:{RESET}")
                for idx, p in enumerate(pending[:15], 1):
                    print(f" {idx:2d}. {p['path']} ({p['size_kb']:.1f} KB)")
                if len(pending) > 15:
                    print(f" ... e mais {len(pending) - 15} arquivos.")
                    
            resp_exp = input("\nDeseja salvar a lista completa de pendentes em um arquivo de texto? (s/N): ").strip().lower()
            if resp_exp in ('s', 'sim', 'y', 'yes'):
                export_file = input("Nome do arquivo [pendentes.txt]: ").strip()
                if not export_file:
                    export_file = "pendentes.txt"
                    
        if export_file:
            export_report_file(export_file, folder_path, converted, pending)
    else:
        print(f"\n{GREEN}{BOLD}[PARABÉNS!]{RESET} Todos os arquivos da pasta já possuem suas versões Markdown (.md) geradas!")
        if args.export:
            export_report_file(args.export, folder_path, converted, pending)
            
    print(f"\n{DIM}Finalizado.{RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Operação interrompida pelo usuário.{RESET}")
        sys.exit(0)
