import os
import textwrap
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
# Import RLM
from rlm.rlm_repl import RLM_REPL

def generate_index_for_folder(folder_path_str: str, api_key: str, recursive: bool = True):
    """
    Gera um índice semântico em PDF para a pasta especificada.
    Analisa arquivos .md, gera resumos e keywords usando RLM.
    Se recursive=True, processa subpastas também.
    """
    folder_path = Path(folder_path_str)
    if not folder_path.exists():
        print(f"Erro: Pasta não encontrada: {folder_path}")
        return

    print(f"📍 Iniciando indexação de: {folder_path.name}")

    # 1. Identificar arquivos Markdown na raiz desta pasta
    # Ignora arquivos que começam com ponto ou underscore (como _INDEX, .git)
    md_files = [
        f for f in folder_path.glob("*.md") 
        if not f.name.startswith("_") and not f.name.startswith(".")
    ]

    index_data = []
    
    # 2. Processar Arquivos
    if md_files:
        # Inicializa RLM (Gemini)
        # Usamos flash para velocidade, ou pro para qualidade se necessário.
        try:
            rlm = RLM_REPL(model="gemini-2.0-flash", enable_logging=True)
            
            for md_file in md_files:
                print(f"  📖 Analisando com RLM: {md_file.name}")
                try:
                    with open(md_file, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                    
                    if not content.strip():
                        continue

                    # Otimização: Se for muito grande, pegamos os primeiros 30k chars para o índice
                    truncated_content = content[:30000] 
                    
                    query = f"""
                    Analyze the following text from file '{md_file.name}'.
                    1. Provide a concise summary of the document (max 3 sentences).
                    2. Extract 5 relevant keywords or tags.
                    
                    Format your answer EXACTLY like this:
                    Summary: [Your summary here]
                    Keywords: [Tag1, Tag2, Tag3, Tag4, Tag5]
                    """
                    
                    # Call RLM
                    analysis = rlm.completion(context=truncated_content, query=query)
                    
                    # Parse simples
                    summary = "Resumo não disponível."
                    keywords = "Tags não disponíveis."
                    
                    if "Summary:" in analysis:
                        # Tenta extrair Summary e Keywords
                        try:
                            parts = analysis.split("Keywords:")
                            summary_part = parts[0].replace("Summary:", "").strip()
                            keywords_part = parts[1].strip() if len(parts) > 1 else ""
                            
                            summary = summary_part.replace("*", "") # Remove markdown bold
                            keywords = keywords_part.replace("[", "").replace("]", "")
                        except:
                            summary = analysis[:200] + "..."
                    else:
                        summary = analysis[:300].replace("\n", " ") + "..." # Fallback
                    
                    index_data.append({
                        "filename": md_file.name,
                        "summary": summary,
                        "keywords": keywords
                    })
                    
                except Exception as e:
                    print(f"  ❌ Erro ao analisar {md_file.name}: {e}")
        except Exception as e_init:
            print(f"Erro ao inicializar RLM: {e_init}")

        # 3. Gerar PDF se houver dados
        if index_data:
            pdf_filename = f"_INDEX_CONTENT_{folder_path.name}.pdf"
            pdf_path = folder_path / pdf_filename
            try:
                create_pdf_report(str(pdf_path), folder_path.name, index_data)
                print(f"  ✅ Índice PDF Criado: {pdf_path}")
            except Exception as e_pdf:
                print(f"Erro ao gerar PDF: {e_pdf}")

    # 4. Recursividade (Depth First)
    if recursive:
        # Pega todas as subpastas diretias
        subfolders = [d for d in folder_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
        for sub in subfolders:
            generate_index_for_folder(str(sub), api_key, recursive=True)

def create_pdf_report(output_path, folder_name, data):
    """
    Cria o arquivo PDF visual usando ReportLab com quebra de linha manual.
    """
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    margin_left = 2 * cm
    margin_right = 2 * cm
    max_width = width - margin_left - margin_right
    
    # Header da Primeira Página
    draw_header(c, folder_name, height)
    y = height - 4 * cm
    
    for item in data:
        # Verifica se cabe o item (estimativa: Título + Keywords + 3 linhas resumo + separador ~= 5cm)
        if y < 6 * cm: 
            c.showPage()
            draw_header(c, folder_name, height)
            y = height - 4 * cm
            
        # Filename
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.darkblue)
        c.drawString(margin_left, y, item['filename'])
        y -= 0.6 * cm
        
        # Keywords
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(colors.darkgreen)
        c.drawString(margin_left, y, f"Tags: {item['keywords']}")
        y -= 0.8 * cm
        
        # Summary (Wrap text)
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        
        summary_text = item['summary']
        # Wrap usando textwrap para caber na largura
        # Aproximação: Helvetica 10pt ~= 60-80 chars por linha em A4
        wrapper = textwrap.TextWrapper(width=90) 
        lines = wrapper.wrap(summary_text)
        
        text_obj = c.beginText(margin_left, y)
        for line in lines:
            text_obj.textLine(line)
            y -= 0.5 * cm # Line height
        
        c.drawText(text_obj)
        y -= 0.5 * cm # Padding
        
        # Separator
        c.setStrokeColor(colors.lightgrey)
        c.line(margin_left, y, width - margin_right, y)
        y -= 1 * cm # Margin bottom

    c.save()

def draw_header(c, folder_name, height):
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.black)
    c.drawString(2 * cm, height - 2 * cm, f"Índice Semântico: {folder_name}")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.grey)
    c.drawString(2 * cm, height - 2.5 * cm, "Gerado por RLM (Recursive Language Model) & Gemini")
    c.line(2 * cm, height - 2.8 * cm, 19 * cm, height - 2.8 * cm)
