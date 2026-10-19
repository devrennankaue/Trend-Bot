"""Indexação do corpus usando Python padrão e Ollama."""
import csv
import json
import os
from typing import Dict, List, Optional

from .config import (DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, DEFAULT_EMBEDDING_BATCH_SIZE,
                     DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_URL, resolver_caminho_csv,
                     resolver_caminho_db)
from .ollama_embeddings import OllamaEmbeddings


class TrendDataIngestor:
    """Lê o CSV, gera embeddings no Ollama e salva um índice JSON local."""
    def __init__(self, csv_path: Optional[str] = None, persist_directory: Optional[str] = None,
                 nrows: Optional[int] = 100):
        self.csv_path = resolver_caminho_csv(csv_path)
        self.persist_directory = resolver_caminho_db(persist_directory)
        self.nrows = nrows
        self.embeddings = OllamaEmbeddings(DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_URL)

    @staticmethod
    def _value(row: Dict[str, str], *fields: str, default: str = "") -> str:
        for field in fields:
            value = str(row.get(field, "")).strip()
            if value and value.upper() != "NULL" and value.lower() != "nan":
                return value
        return default

    @staticmethod
    def _split(text: str) -> List[str]:
        if len(text) <= DEFAULT_CHUNK_SIZE:
            return [text]
        step = DEFAULT_CHUNK_SIZE - DEFAULT_CHUNK_OVERLAP
        return [text[index:index + DEFAULT_CHUNK_SIZE] for index in range(0, len(text), step)]

    def _rows(self) -> List[Dict[str, str]]:
        for encoding in ("utf-8", "latin1"):
            try:
                with open(self.csv_path, encoding=encoding, newline="") as csv_file:
                    rows = list(csv.DictReader(csv_file))
                return rows[:self.nrows] if self.nrows else rows
            except UnicodeDecodeError:
                pass
        return []

    def load_and_index(self):
        print("[Ingestor] Gerando embeddings localmente pelo Ollama...")
        documents = []
        for index, row in enumerate(self._rows()):
            content = self._value(row, "transcricaoVideo", "transcription", "descricaoVideo", "descricao",
                                  "resumo", "textoVideo", "texto", "postagem", "text", "content")
            music = self._value(row, "nomeMusica")
            author = self._value(row, "autorMusica")
            topic = self._value(row, "topico_principal")
            hashtags = self._value(row, "hashtags_postagem", "hashtags_topico_principal", "hashtags")
            parts = []
            if content:
                parts.append(f"Conteúdo: {content}")
            if music:
                parts.append(f"Música: {music}" + (f" ({author})" if author else ""))
            if topic:
                parts.append(f"Tópico: {topic}")
            if hashtags:
                parts.append(f"Hashtags: {hashtags}")
            text = "\n".join(parts) or " ".join(str(value) for value in row.values() if str(value).strip())
            if not text.strip():
                continue
            metadata = {
                "video_id": self._value(row, "IDPostagem", "IDPostagemFonte", "video_id", default=f"video_{index}"),
                "hashtags": hashtags,
                "upload_date": self._value(row, "dataPublicacao", "upload_date", "data", default="N/A"),
                "play_count": self._value(row, "plays_da_ultima_coleta", "plays_mais_recente", "play_count", default="0"),
            }
            documents.extend({"page_content": chunk, "metadata": metadata} for chunk in self._split(text))
        if not documents:
            raise RuntimeError("O CSV não contém registros textuais válidos para indexação.")
        vectors = []
        texts = [doc["page_content"] for doc in documents]
        for start in range(0, len(texts), DEFAULT_EMBEDDING_BATCH_SIZE):
            vectors.extend(self.embeddings.embed_documents(texts[start:start + DEFAULT_EMBEDDING_BATCH_SIZE]))
        for document, vector in zip(documents, vectors):
            document["embedding"] = vector
        os.makedirs(self.persist_directory, exist_ok=True)
        index_path = os.path.join(self.persist_directory, "indice_ollama.json")
        with open(index_path, "w", encoding="utf-8") as index_file:
            json.dump(documents, index_file, ensure_ascii=False)
        print(f"[Ingestor] Indexação concluída em '{index_path}'.")
        return documents
