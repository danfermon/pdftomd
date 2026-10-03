@echo off
chcp 65001 > nul
echo Iniciando verificador de status PDFtoMD...
if exist ".\venv\Scripts\python.exe" (
    .\venv\Scripts\python.exe check_status.py %*
) else (
    python check_status.py %*
)
pause
