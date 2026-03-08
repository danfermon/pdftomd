# Processador de Documentos para Markdown 📄➡️📝

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-UI-FF4B4B.svg)
![Gemini](https://img.shields.io/badge/AI-Google_Gemini-orange.svg)

Uma plataforma web robusta desenvolvida em Streamlit para converter múltiplos formatos de documentos em texto estruturado **Markdown (`.md`)** limpo e legível. O sistema é ideal para criar bases de conhecimento (RAG), com suporte a extração multimodal e indexação semântica inteligente usando IA.

---

## 🚀 Principais Funcionalidades

### 1. Extração Multimodal Universal
*   **Documentos Digitais:** Conversão impecável de `.pdf` (textuais), `.docx`, `.pptx`, `.xlsx`, `.csv`, `.epub` e arquivos de dados (JSON, XML, HTML) usando o motor estruturado `MarkItDown`.
*   **PDFs Escaneados & Imagens:** OCR avançado combinando a velocidade local do **Tesseract** com a precisão estruturadora da IA **Google Gemini Vision**.
*   **Áudio:** Transcrição e formatação de arquivos `.mp3` e `.wav`.
*   **Vídeo (YouTube):** Extração direta de transcrições a partir de URLs do YouTube.

### 2. Fluxos de Trabalho Automatizados (Batch & Nuvem)
*   **Lote Local (Batch):** Selecione uma pasta no seu computador para varrer e converter recursivamente dezenas de documentos ignorando os já processados.
*   **Integração Dropbox:** Conecte-se via token OAuth2, navegue pelas suas pastas na nuvem diretamente pela interface do app, baixe lote de arquivos, converta e faça o upload automático do Markdown estruturado de volta para o Dropbox.

### 3. Índice Semântico Inteligente (RLM) 🧠
Geração automática de "Catálogos de Arquivos" para pastas. Após a conversão para `.md`, o sistema utiliza uma versão adaptada do **Recursive Language Model (RLM)** alimentada pelo *Gemini 2.0 Flash* para:
*   Ler e analisar todos os Markdowns de uma pasta.
*   Gerar Resumos Concisos (max. 3 linhas) por documento.
*   Extrair Tags e Palavras-chave relevantes.
*   Compilar tudo em um único arquivo PDF (`_INDEX_CONTENT.pdf`) visualmente organizado para fácil navegação humana usando a biblioteca `reportlab`.

---

## 🛠️ Arquitetura e Engenharia

A aplicação foi migrada de scripts via CLI para uma interface visual completa.

### Estrutura do Projeto
```text
C:\pdftomd
├── app.py                  # Entrypoint principal (Interface Streamlit)
├── index_generator.py      # Motor de indexação semântica (Geração de resumos e PDF)
├── dropbox_handler.py      # Integração com a API do Dropbox (OAuth, navegação, I/O)
├── pdf_detector.py         # Pipeline core de extração (MarkItDown, classificação de PDF)
├── gcv_ocr.py              # Integração OCR (Tesseract local + Fallback/Agent Gemini Vision)
├── youtube_handler.py      # Extração de legendas
├── rlm/                    # Módulo Recursive Language Model adaptado para Google Gemini
├── requirements.txt        # Dependências do projeto
└── venv/                   # Ambiente virtual recomendado
```

---

## ⚙️ Pré-requisitos e Setup

### 1. Dependências do Sistema
*   **Python 3.9+**
*   **Tesseract OCR:** Deve estar instalado no sistema operacional e no `PATH` para OCR rápido em imagens simples.

### 2. Configuração do Ambiente e Instalação

```bash
# Clone o repositório ou acesse a pasta raiz
cd C:\pdftomd

# Crie um ambiente virtual (Recomendado)
python -m venv venv

# Ative o ambiente (Windows)
.\venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt
```

### 3. Variáveis de Ambiente e Chaves API
O sistema pode carregar chaves do arquivo `.env` na raiz do projeto ou podem ser injetadas diretamente via interface UI.

1.  **Google Gemini API Key:** Necessária para fluxos de OCR difíceis e essencial para a **Geração do Índice Semântico RLM**. Obtenha no Google AI Studio. (`GOOGLE_GEMINI_API_KEY=sua_chave`)
2.  **Dropbox Access Token:** Necessário apenas se for usar a aba Nuvem. Deve possuir permissões de `files.content.read` e `files.content.write`. (`DROPBOX_ACCESS_TOKEN=seu_token`)

---

## 💻 Como Executar

Para iniciar a interface web, garanta que seu ambiente virtual esteja ativo e rode:

```bash
streamlit run app.py
```

O painel será aberto no seu navegador padrão (geralmente `http://localhost:8501`). A interface é dividida em **Abas:**
1.  **Arquivo Local:** Processamento 1:1 salvando na mesma pasta do PC.
2.  **Pasta (Lote):** Processamento recursivo em massa. Inclui Botão para **Gerar Índice Semântico**.
3.  **Dropbox:** Navegação remota, batch download/upload e **Índice Semântico na nuvem**.
4.  **YouTube:** Útil para converter áudios de aulas e palestras.

---
*Documentação atualizada de acordo com a versão unificada Multimodal v2.0.*
