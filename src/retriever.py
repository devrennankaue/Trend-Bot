import warnings
from typing import Dict, Any, Optional

try:
    import torch
except ImportError:
    torch = None

# Supressão de avisos de depreciação para saída limpa
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Imports modernos do ecossistema LangChain com fallback resiliente
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from .config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_RETRIEVAL_K,
    DEFAULT_FETCH_K,
    resolver_caminho_db
)


class TrendRetriever:
    """
    Responsável exclusivo pela conexão com o ChromaDB e pela busca semântica,
    mantendo a base vetorial isolada da lógica de orquestração do LLM.
    """
    def __init__(
        self, 
        persist_directory: Optional[str] = None, 
        embeddings: Optional[HuggingFaceEmbeddings] = None
    ):
        self.device_type = 'cuda' if torch is not None and torch.cuda.is_available() else 'cpu'
        self.persist_directory = resolver_caminho_db(persist_directory)
        
        if embeddings:
            self.embeddings = embeddings
        else:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=DEFAULT_EMBEDDING_MODEL,
                model_kwargs={'device': self.device_type},
                encode_kwargs={'normalize_embeddings': False}
            )
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory, 
            embedding_function=self.embeddings
        )
        
    def get_retriever(self, k: int = DEFAULT_RETRIEVAL_K, hashtag_filter: Optional[str] = None):
        """
        Retorna o retriever configurado com MMR (Maximal Marginal Relevance)
        para garantir que os chunks recuperados sejam diversos e não repitam o mesmo vídeo.
        """
        search_kwargs: Dict[str, Any] = {"k": k, "fetch_k": DEFAULT_FETCH_K}
        if hashtag_filter:
            search_kwargs["filter"] = {"hashtags": {"$contains": hashtag_filter}}
            return self.vectorstore.as_retriever(search_kwargs=search_kwargs)
            
        return self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs
        )
