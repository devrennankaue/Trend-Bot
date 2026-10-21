"""Busca semântica local sem dependências nativas."""
import json
import math
import os
from typing import Any, Dict, List, Optional

from .config import (DEFAULT_EMBEDDING_MODEL, DEFAULT_FETCH_K, DEFAULT_MMR_LAMBDA,
                     DEFAULT_OLLAMA_URL, DEFAULT_RETRIEVAL_K, resolver_caminho_db)
from .ollama_embeddings import OllamaEmbeddings


class TrendRetriever:
    def __init__(self, persist_directory: Optional[str] = None, embeddings: Optional[Any] = None):
        self.persist_directory = resolver_caminho_db(persist_directory)
        self.embeddings = embeddings or OllamaEmbeddings(DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_URL)
        index_path = os.path.join(self.persist_directory, "indice_ollama.json")
        if not os.path.exists(index_path):
            raise RuntimeError(f"Índice não encontrado em '{index_path}'.")
        with open(index_path, encoding="utf-8") as index_file:
            self.documents = json.load(index_file)
        self.k = DEFAULT_RETRIEVAL_K
        self.hashtag_filter = None

    def get_retriever(self, k: int = DEFAULT_RETRIEVAL_K, hashtag_filter: Optional[str] = None):
        self.k = k
        self.hashtag_filter = hashtag_filter
        return self

    @staticmethod
    def _similarity(first: List[float], second: List[float]) -> float:
        product = sum(a * b for a, b in zip(first, second))
        norm_first = math.sqrt(sum(a * a for a in first))
        norm_second = math.sqrt(sum(b * b for b in second))
        return product / (norm_first * norm_second) if norm_first and norm_second else 0.0

    def search(self, question: str) -> List[Dict[str, Any]]:
        query_vector = self.embeddings.embed_query(question)
        candidates = self.documents
        if self.hashtag_filter:
            filter_text = self.hashtag_filter.lower()
            candidates = [doc for doc in candidates if filter_text in doc["metadata"].get("hashtags", "").lower()]

        ranked = sorted(
            ((doc, self._similarity(query_vector, doc["embedding"])) for doc in candidates),
            key=lambda item: item[1],
            reverse=True,
        )[:DEFAULT_FETCH_K]
        selected: List[Dict[str, Any]] = []
        selected_video_ids = set()

        while ranked and len(selected) < self.k:
            distinct_candidates = [
                item for item in ranked
                if item[0]["metadata"].get("video_id") not in selected_video_ids
            ]
            pool = distinct_candidates or ranked

            def mmr_score(item):
                document, relevance = item
                redundancy = max(
                    (self._similarity(document["embedding"], chosen["embedding"]) for chosen in selected),
                    default=0.0,
                )
                return DEFAULT_MMR_LAMBDA * relevance - (1 - DEFAULT_MMR_LAMBDA) * redundancy

            chosen, _ = max(pool, key=mmr_score)
            selected.append(chosen)
            selected_video_ids.add(chosen["metadata"].get("video_id"))
            ranked = [item for item in ranked if item[0] is not chosen]

        return selected
