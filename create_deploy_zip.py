# create_deploy_zip.py
import os
import zipfile
from pathlib import Path

def is_ignored(file_path: Path, project_dir: Path) -> bool:
    ignored_patterns = {
        "venv",
        ".git",
        "__pycache__",
        "markdown_output",
        "temp_uploads",
        "temp_dropbox",
        ".system_generated",
        "rlm_minimal_research",
        "pdftomd.zip",
        "pdftomd_clean.zip",
        ".env",
        "create_deploy_zip.py"
    }
    try:
        relative = file_path.relative_to(project_dir)
        for part in relative.parts:
            if part in ignored_patterns or part.startswith('.'):
                return True
    except Exception:
        return True
    return False

def create_zip():
    project_dir = Path(__file__).parent.resolve()
    zip_path = project_dir / "pdftomd_clean.zip"
    
    # Remove existing zip if it exists
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception:
            pass
            
    print("--- Iniciando compactacao limpa da aplicacao... ---")
    
    count = 0
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in project_dir.rglob("*"):
            if file_path.is_file():
                if is_ignored(file_path, project_dir):
                    continue
                    
                relative_path = file_path.relative_to(project_dir)
                zipf.write(file_path, relative_path)
                print(f"  + Adicionado: {relative_path}")
                count += 1
                
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n--- Concluido! {count} arquivos compactados com sucesso em '{zip_path.name}'. ---")
    print(f"Tamanho final do pacote: {size_mb:.2f} MB")

if __name__ == "__main__":
    create_zip()
