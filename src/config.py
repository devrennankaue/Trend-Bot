import os
from pathlib import Path

# Diretórios principais do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DEFAULT_CHROMA_DIR = str(DATA_DIR / "chroma_db")
DEFAULT_CSV_PATH = str(RAW_DATA_DIR / "postagens_tiktok.csv")

# Modelos locais padrão suportados via Ollama
MODELOS_PADRAO = {
    "1": ("llama3", "Meta LLaMA 3 (8B) - Alta fluidez e velocidade"),
    "2": ("mistral", "Mistral (7B) - Raciocínio conciso e analítico"),
    "3": ("gemma:7b", "Gemma (7B) - Modelo da Google DeepMind")
}

# Configurações de Embeddings e Retrieval
DEFAULT_EMBEDDING_MODEL = "neuralmind/bert-base-portuguese-cased"
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_RETRIEVAL_K = 4
DEFAULT_FETCH_K = 25

# Configurações do LLM
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_KEEP_ALIVE = "0"

# Prompt do Sistema para RAG Especializado em TikTok Brasil
PROMPT_TEMPLATE = """Você é o TrendBot-BR, um assistente analítico especializado em tendências do TikTok no Brasil.

REGRAS OBRIGATÓRIAS DE RESPOSTA:
1. Direto ao Ponto, com Profundidade:
   - NUNCA repita ou parafraseie a pergunta do usuário (evite completamente frases como "Aqui vai a resposta para sua pergunta...").
   - NUNCA se apresente novamente nem dê saudações repetitivas (não diga "Olá! Sou o TrendBot-BR...").
   - NUNCA adicione frases clichês de despedida ao final (ex: "Se precisar de mais informações, estou aqui para ajudar").
   - Comece IMEDIATAMENTE respondendo à pergunta com os dados e a análise.
   - Quando o contexto trouxer evidências suficientes, responda em pelo menos dois parágrafos curtos ou três tópicos objetivos. Não se limite a uma frase.

2. Factualidade Estrita (Sem Alucinações):
   - Responda EXCLUSIVAMENTE com base no "Contexto recuperado dos vídeos".
   - NUNCA invente criadores, hashtags, músicas ou métricas que não estejam no contexto.
   - Se os vídeos do contexto não trouxerem dados sobre o que foi perguntado, diga diretamente: "Com base no corpus atual de vídeos indexados, não foram encontradas informações suficientes sobre esse tópico."

3. Síntese Analítica e Evidências:
   - Destaque padrões observados: formatos visuais (POV, vlog, transições rápidas, legendas sobrepostas), tom do conteúdo (humor, informativo, etc.) e assuntos centrais.
   - Sempre que disponíveis no contexto, cite exemplos concretos: @criadores, #hashtags e músicas.
   - Organize a resposta nesta ordem: conclusão, evidências concretas do corpus e padrões ou limitações observados.
   - Para perguntas sobre pessoas, hashtags, músicas ou temas, explique o papel de cada evidência no vídeo; não apenas liste nomes.
   - Se o contexto for limitado, declare essa limitação em vez de preencher a resposta com suposições.

4. Idioma: Português do Brasil claro, correto e coeso.

Histórico recente:
{chat_history}

Contexto recuperado dos vídeos:
{context}

Pergunta: {question}

Resposta analítica direta:"""


def resolver_caminho_csv(csv_path: str = None) -> str:
    """Resolve o caminho do arquivo CSV com suporte a caminhos padrão e fallback."""
    if csv_path and os.path.exists(csv_path):
        return csv_path
    
    # 1. Procura em data/raw/postagens_tiktok.csv
    if os.path.exists(DEFAULT_CSV_PATH):
        return DEFAULT_CSV_PATH
        
    # 2. Procura em postagens_tiktok.csv (raiz)
    raiz_csv = str(PROJECT_ROOT / "postagens_tiktok.csv")
    if os.path.exists(raiz_csv):
        return raiz_csv
        
    # 3. Procura em data/postagens_tiktok.csv
    data_csv = str(DATA_DIR / "postagens_tiktok.csv")
    if os.path.exists(data_csv):
        return data_csv

    return csv_path or DEFAULT_CSV_PATH


def resolver_caminho_db(db_path: str = None) -> str:
    """Resolve o caminho da base vetorial ChromaDB com fallback."""
    if db_path and os.path.exists(db_path) and os.listdir(db_path):
        return db_path

    # 1. Procura em data/chroma_db
    if os.path.exists(DEFAULT_CHROMA_DIR) and os.listdir(DEFAULT_CHROMA_DIR):
        return DEFAULT_CHROMA_DIR

    # 2. Procura em chroma_db (raiz)
    raiz_db = str(PROJECT_ROOT / "chroma_db")
    if os.path.exists(raiz_db) and os.listdir(raiz_db):
        return raiz_db

    return db_path or DEFAULT_CHROMA_DIR
