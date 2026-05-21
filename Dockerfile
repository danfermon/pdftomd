# Dockerfile
FROM python:3.11-slim

# Evita que o Python grave arquivos .pyc em disco e faz o buffering de log imediato
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RUNNING_IN_DOCKER=true
ENV USERS_DB_PATH=/data/users.db

# Configura o diretório de trabalho
WORKDIR /app

# Instala dependências de sistema necessárias (Tesseract OCR com suporte a Português e Poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de requisitos e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Cria os diretórios necessários para volumes e permissões
RUN mkdir -p /data /app/markdown_output /app/temp_uploads /app/temp_dropbox && \
    chmod -R 777 /data /app/markdown_output /app/temp_uploads /app/temp_dropbox

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Comando de inicialização do Streamlit com configurações recomendadas para produção
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
