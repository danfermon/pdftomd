@echo off
REM Renomeado para pdftomd.bat

REM 1. Ativa o ambiente virtual
call C:\pdftomd\venv\Scripts\activate

REM 2. Inicia o Streamlit e abre o navegador
streamlit run app.py

REM 3. Desativa o ambiente virtual após o Streamlit ser fechado
deactivate

REM Mantém a janela aberta após o processo (opcional, remova se quiser que feche imediatamente)
