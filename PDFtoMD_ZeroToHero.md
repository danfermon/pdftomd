# PDFtoMD: Guia Completo "Do Zero ao Funcionando" para Windows 11 🚀

> **Para quem é este guia?**
> Para **qualquer pessoa**, mesmo sem experiência em programação. Seguindo cada passo com atenção, você conseguirá instalar e rodar o sistema **Processador de Documentos para Markdown** partindo de um Windows 11 completamente novo.

---

## ⚠️ Antes de Começar: Leia com Atenção

Antes de iniciar, verifique os requisitos mínimos e entenda o que vai acontecer:

**O que vamos instalar (e por quê):**
| Programa | Para que serve |
|---|---|
| **Python 3.12** | É o "motor" que executa o sistema |
| **Git** | Ferramenta para baixar o código do GitHub |
| **Tesseract OCR** | Permite ler PDFs que são imagens escaneadas |
| **Bibliotecas Python** | Peças internas do sistema (instaladas automaticamente) |

**Requisitos mínimos:**
- Windows 11 (atualizado)
- Conexão com a internet estável
- Pelo menos **2 GB de espaço livre** no disco C:
- Cerca de **30 a 40 minutos** disponíveis (na primeira instalação)

---

## 🗺️ Visão Geral do Processo

O guia está dividido em **2 grandes partes**:

1. **Parte 1 – Configuração do Computador** *(feita uma única vez)*
   - Instalar Python, Git e Tesseract
   - Configurar o sistema para encontrar o Tesseract

2. **Parte 2 – Instalação e Execução do Sistema** *(a partir da segunda vez, começa direto no Passo 3)*
   - Baixar o projeto
   - Criar ambiente isolado
   - Instalar dependências
   - Executar o aplicativo

---

## 📋 PARTE 1: Preparando o Computador *(Feita uma única vez)*

### Passo 1.1 – Verificar se o `winget` está disponível

O `winget` é o instalador oficial da Microsoft. Verifique se ele está presente antes de continuar.

1. Clique no botão **Iniciar** do Windows (ícone da janela no canto inferior esquerdo).
2. Digite `PowerShell`.
3. Clique em **"Run as Administrator"** (Executar como Administrador) no painel da direita.
4. Clique em **"Yes"** (Sim) se o Windows perguntar se você permite alterações.
5. Na tela azul/preta que abrir, digite o comando abaixo e aperte `Enter`:

```powershell
winget --version
```

**O que deve aparecer:** algo como `v1.7.xxxxx` ou superior.

> ❌ **Se aparecer um erro dizendo que `winget` não foi reconhecido:**
> Abra a **Microsoft Store**, pesquise por **"App Installer"** e clique em **Instalar** ou **Atualizar**. Depois feche e reabra o PowerShell como Administrador e repita este passo.

---

### Passo 1.2 – Instalar Python, Git e Tesseract

> ⚠️ **ATENÇÃO:** Use o mesmo PowerShell como Administrador do passo anterior.

Copie o bloco abaixo **inteiro**, cole no PowerShell (clique com o botão direito do mouse para colar) e aperte `Enter`. Aguarde cada instalação terminar antes de continuar.

```powershell
# 1. Instalar Python 3.12
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements

# 2. Instalar o Git
winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements

# 3. Instalar o Tesseract OCR
winget install -e --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
```

> ⏳ Cada programa pode demorar de 2 a 5 minutos. Aguarde até aparecer a mensagem **"Successfully installed"** para cada um antes de prosseguir.

> ❌ **Se aparecer erro de rede ou "download failed":** Verifique sua conexão com a internet e execute o comando do programa que falhou novamente, individualmente.

> ❌ **Se aparecer "already installed" para algum deles:** Isso é normal. Significa que o programa já estava no seu computador. Continue para o próximo.

---

### Passo 1.3 – Verificar se o Python foi instalado corretamente

Antes de continuar, vamos confirmar que o Python foi instalado. Ainda no PowerShell como Administrador, execute:

```powershell
python --version
```

**O que deve aparecer:** `Python 3.12.x`

> ❌ **Se aparecer erro ou uma versão diferente (ex: 3.9, 3.10):** O Windows pode ter o Python antigo instalado. Execute o comando abaixo para garantir que o Python 3.12 é o padrão:
> ```powershell
> py -3.12 --version
> ```
> Se aparecer `Python 3.12.x`, está correto. Use `py -3.12` no lugar de `python` em todos os próximos comandos que usarem `python`.

---

### Passo 1.4 – Configurar o Caminho do Tesseract no Windows

Para que o sistema encontre o Tesseract, precisamos informar ao Windows onde ele foi instalado. Cole o comando abaixo e aperte `Enter`:

```powershell
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$tesseractPath = "C:\Program Files\Tesseract-OCR"

if (Test-Path $tesseractPath) {
    if ($currentPath -notlike "*$tesseractPath*") {
        [Environment]::SetEnvironmentVariable("Path", $currentPath + ";" + $tesseractPath, "Machine")
        Write-Host "✅ Tesseract adicionado ao PATH com sucesso!" -ForegroundColor Green
    } else {
        Write-Host "✅ O Tesseract já estava no PATH. Nenhuma alteração necessária." -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ ERRO: A pasta do Tesseract não foi encontrada em C:\Program Files\Tesseract-OCR" -ForegroundColor Red
    Write-Host "Verifique se a instalação do Passo 1.2 foi concluída com sucesso." -ForegroundColor Red
}
```

**O que deve aparecer:** uma mensagem verde de confirmação.

> ❌ **Se aparecer a mensagem vermelha de ERRO:** Significa que o Tesseract não foi instalado na pasta padrão. Siga estes passos:
> 1. Abra o **Explorador de Arquivos** (atalho: `Win + E`)
> 2. Navegue até `C:\Program Files\` e procure uma pasta com o nome **Tesseract-OCR**
> 3. Se a pasta existir em outro local, anote o caminho completo e substitua `"C:\Program Files\Tesseract-OCR"` no comando acima pelo caminho correto

---

### Passo 1.5 – ⚠️ Fechar o PowerShell (obrigatório!)

**Feche COMPLETAMENTE a janela do PowerShell agora.** Isso é necessário para que as mudanças feitas no PATH sejam aplicadas ao sistema.

> ⚠️ Se você não fechar e reabrir o PowerShell, os próximos passos podem falhar com erros de "comando não encontrado".

---

## 🚀 PARTE 2: Baixando e Executando o Sistema

### Passo 2.1 – Abrir um Novo PowerShell (sem precisar ser Administrador)

1. Clique no **Iniciar** do Windows.
2. Digite `PowerShell`.
3. Aperte `Enter` *(desta vez **não** precisa clicar em "Run as Administrator")*.

> ✅ Uma nova tela azul/preta vai abrir. A diferença é que desta vez **não haverá** a palavra "Administrator" no título da janela.

---

### Passo 2.2 – Verificar se o Git está funcionando

```powershell
git --version
```

**O que deve aparecer:** `git version 2.xx.x.windows.x`

> ❌ **Se aparecer erro:** Feche e reabra o PowerShell. Se o erro persistir, repita o Passo 1.2 apenas para o Git.

---

### Passo 2.3 – Baixar o Projeto do GitHub

Vamos criar a pasta do projeto diretamente no disco `C:\`. Cole os três comandos abaixo **um de cada vez**, apertando `Enter` após cada um:

```powershell
# Ir para o disco C:
cd C:\
```

```powershell
# Baixar o código (isso cria a pasta C:\pdftomd automaticamente)
git clone https://github.com/danfermon/pdftomd.git
```

```powershell
# Entrar na pasta do projeto
cd pdftomd
```

> ⏳ O `git clone` pode demorar 1 a 2 minutos dependendo da velocidade da internet.

> ❌ **Se aparecer erro "repository not found" ou "could not resolve host":**
> - Verifique se sua internet está funcionando
> - Verifique se a URL digitada está correta: `https://github.com/danfermon/pdftomd.git`
> - Tente abrir esse endereço no navegador para confirmar que o repositório existe

> ❌ **Se aparecer erro "destination path 'pdftomd' already exists":**
> A pasta já foi baixada antes. Execute o comando abaixo para entrar nela diretamente:
> ```powershell
> cd C:\pdftomd
> ```

---

### Passo 2.4 – Criar o Ambiente Virtual (A "bolha de proteção")

O ambiente virtual isola as bibliotecas do projeto, sem interferir no resto do seu computador. Execute os dois comandos abaixo:

```powershell
# Criar o ambiente virtual (demora ~10 segundos)
python -m venv venv
```

> ❌ **Se aparecer erro "python was not found" ou similar:** Use `py -3.12` no lugar de `python`:
> ```powershell
> py -3.12 -m venv venv
> ```

Agora **ative** o ambiente virtual:

```powershell
# Ativar o ambiente virtual
.\venv\Scripts\activate
```

> ✅ **Como saber se deu certo:** O início da linha de comando vai mostrar **`(venv)`** em verde, assim:
> ```
> (venv) PS C:\pdftomd>
> ```

> ❌ **Se aparecer erro "cannot be loaded because running scripts is disabled":**
> Execute o comando abaixo para liberar a execução de scripts e tente ativar novamente:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Depois execute `.\venv\Scripts\activate` novamente.

---

### Passo 2.5 – Atualizar o pip e Instalar as Dependências

> ⚠️ **IMPORTANTE:** Certifique-se de que o `(venv)` ainda aparece no início da linha antes de continuar.

```powershell
# Atualizar o instalador interno do Python
python -m pip install --upgrade pip
```

```powershell
# Instalar todas as dependências do projeto
pip install -r requirements.txt
```

> ⏳ Este passo pode demorar de **5 a 15 minutos**. Muitos arquivos serão baixados. Isso é normal — pode tomar um café! ☕

> ❌ **Se aparecer erro "No such file or directory: requirements.txt":**
> Você pode não estar dentro da pasta correta. Verifique com:
> ```powershell
> pwd
> ```
> O resultado deve ser `C:\pdftomd`. Se não for, execute `cd C:\pdftomd` e tente novamente.

> ❌ **Se aparecer erro durante a instalação de alguma biblioteca específica:**
> Anote o nome da biblioteca que falhou e execute individualmente:
> ```powershell
> pip install nome-da-biblioteca
> ```

---

### Passo 2.6 – 🎉 Ligar o Sistema!

Com tudo instalado (e o `(venv)` ainda ativo), execute:

```powershell
streamlit run app.py
```

> ✅ **O que vai acontecer:**
> 1. O terminal vai exibir mensagens de inicialização
> 2. O **seu navegador padrão** (Chrome, Edge, etc.) vai **abrir automaticamente**
> 3. Você verá a tela do **Processador de Documentos para Markdown** no endereço `http://localhost:8501`

> 🔒 **Se o Windows Defender (firewall) perguntar se deve permitir acesso à rede:** Clique em **"Allow access"** (Permitir acesso). Isso é necessário para o sistema funcionar localmente.

> ❌ **Se o navegador não abrir automaticamente:** Abra manualmente o Chrome ou Edge e acesse: `http://localhost:8501`

> ❌ **Se aparecer erro "streamlit: command not found":** O ambiente virtual pode ter se desativado. Execute:
> ```powershell
> cd C:\pdftomd
> .\venv\Scripts\activate
> streamlit run app.py
> ```

---

## 🔑 Configurando as Chaves de API (Inteligência Artificial e Nuvem)

Para usar os recursos de IA (Gemini) e integração com a nuvem (Dropbox), o sistema precisa de **chaves de API** — que funcionam como senhas de acesso a esses serviços.

Você tem **duas opções**:

### Opção A – Via Tela do Aplicativo *(Mais fácil, ideal para testar)*

1. Com o sistema aberto no navegador, olhe para a **barra lateral esquerda**
2. Localize os campos **"(Opcional) Chave API do Gemini"** e **"Token do Dropbox"**
3. Cole suas chaves nesses campos
4. As chaves ficam ativas apenas durante aquela sessão — ao fechar o navegador, precisará colar novamente

### Opção B – Via Arquivo `.env` *(Recomendado para uso diário)*

1. Abra o **Explorador de Arquivos** (atalho: `Win + E`)
2. Navegue até `C:\pdftomd`
3. Clique com o botão direito em uma área vazia da pasta → **Novo** → **Documento de Texto**
4. Nomeie o arquivo como `.env` *(com o ponto no início)*
   > ⚠️ Se o Windows não deixar criar um arquivo começando com ponto, crie como `env.txt`, abra-o, e ao salvar use **"Salvar como"**, escolha "Todos os arquivos (*.*)" no tipo e nomeie como `.env`
5. Abra o arquivo `.env` com o **Bloco de Notas** e escreva exatamente:
   ```
   GOOGLE_GEMINI_API_KEY=cole_aqui_sua_chave_do_gemini
   DROPBOX_ACCESS_TOKEN=cole_aqui_seu_token_do_dropbox
   ```
6. Salve e feche o arquivo. Na próxima vez que o sistema iniciar, ele lerá as chaves automaticamente.

> 🔒 **Segurança:** Nunca compartilhe o arquivo `.env` com outras pessoas. Ele contém suas senhas de acesso aos serviços de IA.

---

## 🔄 Como Usar o Sistema nas Próximas Vezes

Após a configuração inicial, para abrir o sistema basta:

1. Abrir o **PowerShell** (sem precisar ser Administrador)
2. Executar os três comandos abaixo:

```powershell
cd C:\pdftomd
.\venv\Scripts\activate
streamlit run app.py
```

> 💡 **Dica:** Você pode criar um atalho com esses comandos. Crie um arquivo de texto em `C:\pdftomd` chamado `iniciar.bat` com o seguinte conteúdo:
> ```bat
> @echo off
> cd /d C:\pdftomd
> call .\venv\Scripts\activate
> streamlit run app.py
> ```
> Clicando duas vezes nesse arquivo, o sistema abre automaticamente!

---

## 🆘 Tabela de Erros Comuns e Soluções

| Erro | Causa provável | Solução |
|---|---|---|
| `winget não reconhecido` | App Installer desatualizado | Atualizar "App Installer" na Microsoft Store |
| `python não reconhecido` | Python não foi ao PATH | Fechar e reabrir o PowerShell; ou usar `py -3.12` |
| `git não reconhecido` | Git não instalado corretamente | Fechar e reabrir o PowerShell; reinstalar o Git |
| `cannot be loaded, scripts disabled` | Política de execução bloqueada | Executar `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `(venv) sumiu da tela` | Ambiente virtual desativado | Executar `.\venv\Scripts\activate` novamente |
| `No module named 'streamlit'` | Dependências não instaladas no venv ativo | Ativar o venv e rodar `pip install -r requirements.txt` |
| `Port 8501 is in use` | Sistema já está rodando em segundo plano | Fechar outras janelas do PowerShell ou reiniciar o computador |
| Página em branco no navegador | Sistema ainda carregando | Aguardar 10 segundos e recarregar a página (`F5`) |

---

## ✅ Resumo Visual do Processo

```
[Início]
   │
   ▼
Abrir PowerShell como Administrador
   │
   ▼
Instalar Python 3.12 + Git + Tesseract (winget)
   │
   ▼
Configurar PATH do Tesseract
   │
   ▼
FECHAR o PowerShell ← (obrigatório!)
   │
   ▼
Abrir novo PowerShell (normal)
   │
   ▼
git clone → cd pdftomd
   │
   ▼
python -m venv venv → .\venv\Scripts\activate
   │
   ▼
pip install -r requirements.txt
   │
   ▼
streamlit run app.py
   │
   ▼
🎉 Sistema aberto no navegador!
```

---

*Pronto! Você configurou do zero um sistema completo de inteligência artificial. Nas próximas vezes, são apenas 3 comandos para colocar tudo a funcionar novamente.*
