"""Busca semântica local sem dependências nativas."""
import json
import heapq
import math
import os
import sqlite3
from contextlib import closing
from typing import Any, Dict, List, Optional

from .config import (DEFAULT_EMBEDDING_MODEL, DEFAULT_FETCH_K, DEFAULT_MMR_LAMBDA,
                     DEFAULT_OLLAMA_URL, DEFAULT_RETRIEVAL_K, resolver_caminho_db)
from .ollama_embeddings import OllamaEmbeddings


class TrendRetriever:
    def __init__(self, persist_directory: Optional[str] = None, embeddings: Optional[Any] = None):
        self.persist_directory = resolver_caminho_db(persist_directory)
        self.embeddings = embeddings or OllamaEmbeddings(DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_URL)
        self.index_path = os.path.join(self.persist_directory, "indice_ollama.sqlite")
        self.documents = None
        if os.path.exists(self.index_path):
            if not self.index_complete(self.persist_directory):
                raise RuntimeError(f"Indexação incompleta em '{self.index_path}'.")
        else:
            legacy_path = os.path.join(self.persist_directory, "indice_ollama.json")
            if not os.path.exists(legacy_path):
                raise RuntimeError(f"Índice não encontrado em '{self.index_path}'.")
            with open(legacy_path, encoding="utf-8") as index_file:
                self.documents = json.load(index_file)
        self.k = DEFAULT_RETRIEVAL_K
        self.hashtag_filter = None

    @staticmethod
    def index_complete(persist_directory: str) -> bool:
        index_path = os.path.join(persist_directory, "indice_ollama.sqlite")
        if not os.path.exists(index_path):
            return False
        with closing(sqlite3.connect(index_path)) as connection:
            try:
                row = connection.execute("SELECT value FROM corpus WHERE key = 'complete'").fetchone()
            except sqlite3.OperationalError:
                return False
        return row is not None and row[0] == "1"

    def _iter_documents(self):
        if self.documents is not None:
            yield from self.documents
            return
        with closing(sqlite3.connect(self.index_path)) as connection:
            for content, metadata, embedding in connection.execute(
                "SELECT page_content, metadata, embedding FROM documents"
            ):
                yield {"page_content": content, "metadata": json.loads(metadata),
                       "embedding": json.loads(embedding)}

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
        candidates = self._iter_documents()
        if self.hashtag_filter:
            filter_text = self.hashtag_filter.lower()
            candidates = (doc for doc in candidates
                          if filter_text in doc["metadata"].get("hashtags", "").lower())

        ranked = heapq.nlargest(
            DEFAULT_FETCH_K,
            ((doc, self._similarity(query_vector, doc["embedding"])) for doc in candidates),
            key=lambda item: item[1],
        )
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
