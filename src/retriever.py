"""Busca semântica local sem dependências nativas."""
import json
import heapq
import math
import os
import re
import sqlite3
import unicodedata
from contextlib import closing
from typing import Any, Dict, List, Optional

from .config import (DEFAULT_EMBEDDING_MODEL, DEFAULT_FETCH_K, DEFAULT_MMR_LAMBDA,
                     DEFAULT_OLLAMA_URL, DEFAULT_RETRIEVAL_K, resolver_caminho_db)
from .ollama_embeddings import OllamaEmbeddings


class TrendRetriever:
    QUERY_STOPWORDS = {"qual", "quais", "quanto", "quantos", "quantas", "como", "onde",
                       "quem", "video", "videos", "sobre", "para", "pela", "pelo",
                       "estao", "esse", "essa", "esses", "essas", "diante", "entre"}

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

    def find_examples(self, terms: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """Encontra trechos textuais com os termos, sem gerar novos embeddings."""
        if not terms:
            return []
        terms = [self._normalize(term) for term in terms]
        if self.documents is not None:
            candidates = ((doc["page_content"], doc["metadata"]) for doc in self.documents)
        else:
            connection = sqlite3.connect(self.index_path)
            candidates = ((content, json.loads(metadata)) for content, metadata in connection.execute(
                "SELECT page_content, metadata FROM documents"
            ))
        best_by_video = {}
        try:
            for content, metadata in candidates:
                video_id = metadata.get("video_id")
                if not video_id:
                    continue
                lowered = self._normalize(content)
                score = sum(min(lowered.count(term), 2) * (1 + (len(term) >= 7) + (len(term) >= 10))
                            for term in terms)
                if score:
                    score += 4 * ("resumo:" in lowered) + 2 * ("descricao visual:" in lowered)
                if score > 0 and (video_id not in best_by_video or score > best_by_video[video_id][0]):
                    best_by_video[video_id] = (score, {"page_content": content, "metadata": metadata})
        finally:
            if self.documents is None:
                connection.close()
        return [document for _, document in heapq.nlargest(
            limit, best_by_video.values(), key=lambda item: item[0]
        )]

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.lower())
        return "".join(char for char in decomposed if not unicodedata.combining(char))

    @classmethod
    def _query_terms(cls, question: str) -> List[str]:
        return list(dict.fromkeys(
            word for word in re.findall(r"\b\w{4,}\b", cls._normalize(question))
            if word not in cls.QUERY_STOPWORDS
        ))

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

        terms = self._query_terms(question)
        lexical = self.find_examples(terms, limit=min(self.k, 3))
        direct = [doc for doc in lexical
                  if sum(term in self._normalize(doc["page_content"]) for term in terms) >= 2]
        if direct:
            direct_ids = {doc["metadata"].get("video_id") for doc in direct[:2]}
            selected = direct[:2] + [doc for doc in selected
                                     if doc["metadata"].get("video_id") not in direct_ids]
        return selected[:self.k]
