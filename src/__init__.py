"""
TrendBot-BR: Assistente Inteligente de Tendências do TikTok no Brasil
Arquitetura RAG com LangChain, ChromaDB e Modelos Locais via Ollama
"""

from .config import (
    MODELOS_PADRAO,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_TEMPERATURE,
    DEFAULT_KEEP_ALIVE,
    DEFAULT_RETRIEVAL_K,
    PROJECT_ROOT,
    DATA_DIR,
    RAW_DATA_DIR,
    DEFAULT_CHROMA_DIR,
    DEFAULT_CSV_PATH,
    PROMPT_TEMPLATE,
    resolver_caminho_csv,
    resolver_caminho_db
)
from .memory import limpar_memoria_gpu, obter_metricas_memoria
try:
    from .ingestor import TrendDataIngestor
except ImportError:
    TrendDataIngestor = None

try:
    from .retriever import TrendRetriever
except ImportError:
    TrendRetriever = None

try:
    from .bot import TrendBot
except ImportError:
    TrendBot = None

__all__ = [
    "TrendBot",
    "TrendRetriever",
    "TrendDataIngestor",
    "limpar_memoria_gpu",
    "obter_metricas_memoria",
    "MODELOS_PADRAO",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_OLLAMA_URL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_KEEP_ALIVE",
    "DEFAULT_RETRIEVAL_K",
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "DEFAULT_CHROMA_DIR",
    "DEFAULT_CSV_PATH",
    "PROMPT_TEMPLATE",
    "resolver_caminho_csv",
    "resolver_caminho_db"
]
