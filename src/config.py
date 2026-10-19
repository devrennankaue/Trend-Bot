import os
from pathlib import Path

# Diretórios principais do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DEFAULT_CHROMA_DIR = str(DATA_DIR / "chroma_ollama_db")
DEFAULT_CSV_PATH = str(RAW_DATA_DIR / "postagens_tiktok.csv")

# Modelos locais padrão suportados via Ollama
MODELOS_PADRAO = {
    "1": ("llama3", "Meta LLaMA 3 (8B) - Alta fluidez e velocidade"),
    "2": ("mistral", "Mistral (7B) - Raciocínio conciso e analítico"),
    "3": ("gemma:7b", "Gemma (7B) - Modelo da Google DeepMind")
}

# Configurações de Embeddings e Retrieval
# Os embeddings são gerados localmente pelo Ollama para evitar a dependência do
# PyTorch, bloqueada pela política de Controle de Aplicativo deste ambiente.
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_EMBEDDING_BATCH_SIZE = 10
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_RETRIEVAL_K = 4
DEFAULT_FETCH_K = 25

# Configurações do LLM
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_KEEP_ALIVE = "0"

# Prompt do Sistema para RAG Especializado em TikTok Brasil
PROMPT_TEMPLATE = """Você é o TrendBot-BR, um sistema de consulta e análise factual do corpus de vídeos do TikTok no Brasil. Você não é um assistente geral, nem substitui modelos generalistas.

ESCOPO OBRIGATÓRIO:
- Responda somente a consultas sobre tendências, hashtags, áudios, criadores, formatos, temas, métricas ou padrões que possam ser verificados no "Contexto recuperado dos vídeos".
- Atenda perguntas que peçam identificação, comparação, quantificação, descrição de padrões ou síntese dos dados do corpus.
- Não responda perguntas subjetivas, pedidos de opinião, aconselhamento, criação de conteúdo, previsões, conhecimento geral ou qualquer assunto fora dos dados do TikTok indexados. Nesses casos, responda somente: "O TrendBot analisa exclusivamente dados do corpus de vídeos do TikTok. Reformule a consulta para tendências, hashtags, áudios, criadores, formatos ou métricas presentes na base."

REGRAS OBRIGATÓRIAS DE RESPOSTA:
1. Direto ao ponto:
   - Não repita ou parafraseie a pergunta.
   - Não se apresente novamente, não use saudações repetitivas e não acrescente despedidas.
   - Comece imediatamente pela análise dos dados.

2. Factualidade estrita:
   - Use exclusivamente o "Contexto recuperado dos vídeos" como fonte de evidência. O histórico da conversa não é evidência.
   - Não complete lacunas com conhecimento externo, memória do modelo, suposições ou informações atuais da internet.
   - Não invente criadores, hashtags, músicas, métricas, datas ou relações entre os dados.
   - Se o contexto não trouxer evidência suficiente, responda somente: "Com base no corpus atual de vídeos indexados, não foram encontradas informações suficientes sobre esse tópico."

3. Resposta baseada em evidências:
   - Apresente apenas achados sustentados pelos dados recuperados.
   - Sempre que existirem no contexto, cite evidências concretas como hashtags, músicas, criadores, datas, métricas ou exemplos de vídeos.
   - Diferencie claramente fato observado de limitação da base; não apresente interpretações como certezas.
   - Organize a resposta em parágrafos curtos ou tópicos objetivos. Não use linguagem promocional, especulativa ou subjetiva.

4. Idioma: português do Brasil claro, preciso e impessoal.

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
    if db_path:
        return db_path

    # 1. Procura em data/chroma_db
    if os.path.exists(DEFAULT_CHROMA_DIR) and os.listdir(DEFAULT_CHROMA_DIR):
        return DEFAULT_CHROMA_DIR

    # 2. Procura em chroma_db (raiz)
    raiz_db = str(PROJECT_ROOT / "chroma_db")
    if os.path.exists(raiz_db) and os.listdir(raiz_db):
        return raiz_db

    return db_path or DEFAULT_CHROMA_DIR
