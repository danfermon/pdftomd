
import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

def extract_youtube_transcript(url: str, output_md: str) -> bool:
    """
    Extrai a transcrição de um vídeo do YouTube.
    Estratégia Cascata:
    1. Tenta listar e traduzir para Português (Ideal).
    2. Tenta obter legenda em Português nativa.
    3. Tenta obter legenda em Inglês nativa.
    4. Fallback: Obtém qualquer legenda disponível (comportamento original do MarkItDown).
    """
    print(f"Iniciando extração de transcrição YouTube (Cascata): {url}")
    
    try:
        # Extrair Video ID
        video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
        if not video_id_match:
            print("Erro: Não foi possível extrair o ID do vídeo.")
            return False
            
        video_id = video_id_match.group(1)
        transcript = None
        source_infos = "N/A"

        # Instanciar a API (Necessário nesta versão da biblioteca)
        yt_api = YouTubeTranscriptApi()

        # --- Estratégia: NATIVO (Sem Tradução) ---
        # 1. Tenta listar e pegar legendas em PT ou EN (Nativas)
        # 2. Se não achar, pega QUALQUER UMA Disponível (Nativa)
        
        try:
            transcript_list = yt_api.list(video_id)
            
            # Tenta encontrar PT ou EN (Manual ou Gerada)
            try:
                # Preferência: Português > Inglês
                t = transcript_list.find_transcript(['pt', 'pt-BR', 'en', 'en-US'])
                transcript = t.fetch()
                source_infos = f"Nativo ({t.language_code})"
            except:
                # Se não encontrar PT/EN específico, pega a primeira disponível
                print("PT/EN não encontrados explicitamente. Pegando a primeira disponível.")
                first = next(iter(transcript_list))
                transcript = first.fetch()
                source_infos = f"Nativo - Fallback ({first.language_code})"
                
        except Exception as e_list:
            print(f"Erro ao listar legendas ({e_list}). Tentando fetch direto...")
            
            # Se a listagem falhar, tentamos fetch direto (cego)
            try:
                # Primeiro tenta PT
                transcript = yt_api.fetch(video_id, languages=['pt', 'pt-BR'])
                source_infos = "Nativo (PT) - Fetch Direto"
            except:
                try:
                    # Depois tenta EN
                    transcript = yt_api.fetch(video_id, languages=['en', 'en-US'])
                    source_infos = "Nativo (EN) - Fetch Direto"
                except:
                    # Por último, tenta o default (geralmente EN ou o idioma do vídeo)
                    try:
                        transcript = yt_api.fetch(video_id)
                        source_infos = "Nativo (Default) - Fetch Direto"
                    except Exception as e_final:
                        print(f"Falha total youtube: {e_final}")
                        return False

        if not transcript:
            return False

        # Formata para texto contínuo
        # CORREÇÃO: 'transcript' é um objeto FetchedTranscript iterável de objetos Snippet.
        # Devemos acessar .text (atributo), não ['text'] (dicionário).
        text_parts = []
        for t in transcript:
            # Verifica se é objeto ou dict (para compatibilidade/segurança)
            if isinstance(t, dict):
                text_parts.append(t['text'].replace('\n', ' '))
            else:
                text_parts.append(t.text.replace('\n', ' '))
                
        text_formatted = " ".join(text_parts)
        
        final_content = f"# Transcrição YouTube\n**URL:** {url}\n**Video ID:** {video_id}\n**Info:** {source_infos}\n\n---\n\n{text_formatted}"
        
        with open(output_md, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        print(f"Sucesso: {source_infos}")
        return True
        
    except Exception as e:
        print(f"Erro Genérico YouTube: {e}")
        return False

def is_youtube_url(url: str) -> bool:
    """
    Valida se uma string é uma URL do YouTube.
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return bool(re.match(youtube_regex, url))
