"""
TrendBot-BR: Assistente Inteligente de Tendências do TikTok no Brasil
Arquitetura RAG com índice JSON e modelos locais via Ollama
"""

from .config import (
    DEFAULT_MODEL,
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
from .memory import limpar_memoria_gpu, obter_metricas_memoria, checar_conexao_ollama
from .ingestor import TrendDataIngestor
from .retriever import TrendRetriever
from .bot import TrendBot

__all__ = [
    "TrendBot",
    "TrendRetriever",
    "TrendDataIngestor",
    "limpar_memoria_gpu",
    "obter_metricas_memoria",
    "checar_conexao_ollama",
    "DEFAULT_MODEL",
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
