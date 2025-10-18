==================================================
--- Conversor de PDF para Markdown (pdftomd) ---
==================================================

Este utilitário de linha de comando converte documentos PDF em arquivos Markdown (.md) limpos e legíveis. Ele é projetado para lidar com PDFs baseados em texto e PDFs baseados em imagem (escaneados), selecionando automaticamente a melhor estratégia de extração.

[*] Visão Geral do Projeto
--------------------------
O objetivo principal é automatizar a extração de conteúdo de PDFs, transformando-os em um formato de texto estruturado (Markdown) que é fácil de editar, versionar e usar em outras plataformas.

O pipeline funciona da seguinte forma:
1.  Análise do PDF: O script `pdf_detector.py` examina o PDF para determinar se ele contém texto extraível ou se é primariamente uma imagem.
2.  Extração de Conteúdo:
    - Para PDFs com texto, ele usa a biblioteca `PyMuPDF` para uma extração rápida e precisa.
    - Para PDFs baseados em imagem, ele utiliza `pdf2image` para converter as páginas em imagens e, em seguida, envia essas imagens para a API Google Cloud Vision (`gcv_ocr.py`) para realizar o Reconhecimento Óptico de Caracteres (OCR).
3.  Conversão para Markdown: O texto extraído é então processado e convertido para o formato Markdown usando a biblioteca `markdownify`.
4.  Saída: O resultado é salvo como um arquivo `.md`.


[*] Pré-requisitos
------------------
> Python 3.9 ou superior.
> Acesso a um projeto Google Cloud com a API "Cloud Vision AI" ativada.
> Credenciais de autenticação do Google Cloud (um arquivo JSON de conta de serviço).


[*] Instalação e Configuração
-----------------------------
Siga estes passos para configurar o ambiente de desenvolvimento:

1.  Clone este repositório (ou certifique-se de estar no diretório do projeto).

2.  Crie e ative um ambiente virtual Python. Isso isola as dependências do projeto.
    ```sh
    # Cria o ambiente virtual
    python -m venv venv

    # Ativa o ambiente no Windows
    .\venv\Scripts\activate
    ```

3.  Instale todas as dependências necessárias a partir do arquivo `requirements.txt`.
    ```sh
    pip install -r requirements.txt
    ```

4.  Configure suas credenciais do Google Cloud.
    - Renomeie o arquivo `.env.example` para `.env` (ou crie um novo arquivo `.env`).
    - Dentro do arquivo `.env`, adicione a seguinte linha, substituindo pelo caminho para o seu arquivo de credenciais JSON:
      ```
      GOOGLE_APPLICATION_CREDENTIALS="C:\caminho\para\sua\chave-gcp.json"
      ```
    - Certifique-se de que o caminho para o arquivo JSON usa barras duplas (`\\`) se estiver no Windows.


[*] Como Usar
-------------
O script principal que orquestra todo o processo é o `pipeline_master.py`. Para executar a conversão, use o seguinte comando no seu terminal, passando o caminho do arquivo PDF como argumento.

Exemplo de uso:
```sh
python pipeline_master.py --input "caminho/para/seu/documento.pdf"
```
O arquivo de saída `.md` será gerado no mesmo diretório.


[*] Estrutura do Projeto
------------------------
  .
  ├── .env                  # Arquivo para variáveis de ambiente (credenciais, etc.)
  ├── gcv_ocr.py            # Módulo responsável pela comunicação com a API Google Cloud Vision OCR.
  ├── pdf_detector.py       # Módulo para detectar o tipo de PDF (texto vs. imagem).
  ├── pipeline_master.py    # Script principal que executa o pipeline de conversão.
  ├── requirements.txt      # Lista de todas as dependências Python do projeto.
  └── venv/                 # Diretório do ambiente virtual Python.


[*] Principais Dependências
---------------------------
- `PyMuPDF`: Para extração de texto de alta performance de PDFs.
- `google-cloud-vision`: Cliente da API para OCR de imagens.
- `pdf2image`: Converte páginas de PDF em objetos de imagem.
- `markdownify`: Converte HTML (ou texto simples) em Markdown.
- `python-dotenv`: Para carregar variáveis de ambiente a partir de um arquivo `.env`.

