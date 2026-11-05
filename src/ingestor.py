"""Indexação do corpus usando Python padrão e Ollama."""
import csv
import hashlib
import json
import os
import sqlite3
from typing import Dict, List, Optional

from .config import (DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, DEFAULT_EMBEDDING_BATCH_SIZE,
                     DEFAULT_EMBEDDING_MODEL, DEFAULT_OLLAMA_URL, resolver_caminho_csv,
                     resolver_caminho_db)
from .ollama_embeddings import OllamaEmbeddings


class TrendDataIngestor:
    """Lê o CSV, gera embeddings no Ollama e salva um índice JSON local."""
    def __init__(self, csv_path: Optional[str] = None, persist_directory: Optional[str] = None,
                 nrows: Optional[int] = None):
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
        print("[Ingestor] Preparando documentos do corpus...", flush=True)
        documents = []
        for index, row in enumerate(self._rows()):
            transcription = self._value(row, "transcricaoVideo", "transcription")
            visual = self._value(row, "descricaoVideo", "descricao")
            summary = self._value(row, "resumo")
            other_text = self._value(row, "textoVideo", "texto", "postagem", "text", "content")
            music = self._value(row, "nomeMusica")
            author = self._value(row, "autorMusica")
            topic = self._value(row, "topico_principal")
            hashtags = self._value(row, "hashtags_postagem", "hashtags_topico_principal", "hashtags")
            parts = []
            if transcription:
                parts.append(f"Transcrição: {transcription}")
            if visual:
                parts.append(f"Descrição visual: {visual}")
            if summary:
                parts.append(f"Resumo: {summary}")
            if other_text and not parts:
                parts.append(f"Conteúdo: {other_text}")
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
                "video_id": self._value(row, "IDPostagemFonte", "video_id", default=f"video_{index}"),
                "internal_id": self._value(row, "IDPostagem"),
                "hashtags": hashtags,
                "upload_date": self._value(row, "dataPublicacao", "upload_date", "data", default="N/A"),
                "play_count": self._value(row, "plays_da_ultima_coleta", "plays_mais_recente", "play_count", default="0"),
            }
            documents.extend({"page_content": chunk, "metadata": metadata} for chunk in self._split(text))
        if not documents:
            raise RuntimeError("O CSV não contém registros textuais válidos para indexação.")
        os.makedirs(self.persist_directory, exist_ok=True)
        corpus_hash = hashlib.sha256()
        with open(self.csv_path, "rb") as csv_file:
            for block in iter(lambda: csv_file.read(1024 * 1024), b""):
                corpus_hash.update(block)
        signature = hashlib.sha256(
            f"{corpus_hash.hexdigest()}:{self.nrows}:{DEFAULT_CHUNK_SIZE}:"
            f"{DEFAULT_CHUNK_OVERLAP}:{DEFAULT_EMBEDDING_MODEL}".encode("utf-8")
        ).hexdigest()[:16]
        index_path = os.path.join(self.persist_directory, "indice_ollama.sqlite")
        connection = sqlite3.connect(index_path)
        connection.execute("CREATE TABLE IF NOT EXISTS corpus (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS documents (position INTEGER PRIMARY KEY, page_content TEXT NOT NULL, metadata TEXT NOT NULL, embedding TEXT NOT NULL)")
        previous_signature = connection.execute("SELECT value FROM corpus WHERE key = 'signature'").fetchone()
        if previous_signature is None or previous_signature[0] != signature:
            connection.execute("DELETE FROM documents")
            connection.execute("INSERT OR REPLACE INTO corpus VALUES ('signature', ?)", (signature,))
            connection.execute("INSERT OR REPLACE INTO corpus VALUES ('complete', '0')")
            connection.commit()
        total = len(documents)
        print(f"[Ingestor] {total} trechos; gerando embeddings em lotes de "
              f"{DEFAULT_EMBEDDING_BATCH_SIZE}.", flush=True)

        for start in range(0, total, DEFAULT_EMBEDDING_BATCH_SIZE):
            batch = documents[start:start + DEFAULT_EMBEDDING_BATCH_SIZE]
            saved = connection.execute("SELECT COUNT(*) FROM documents WHERE position >= ? AND position < ?",
                                       (start, start + len(batch))).fetchone()[0]
            if saved == len(batch):
                continue
            try:
                vectors = self.embeddings.embed_documents(
                    [document["page_content"] for document in batch]
                )
            except Exception:
                connection.close()
                raise
            if len(vectors) != len(batch):
                connection.close()
                raise RuntimeError("O Ollama retornou menos embeddings que trechos no lote.")
            with connection:
                connection.executemany(
                    "INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?)",
                    ((start + offset, document["page_content"],
                      json.dumps(document["metadata"], ensure_ascii=False), json.dumps(vector))
                     for offset, (document, vector) in enumerate(zip(batch, vectors))),
                )
            print(f"[Ingestor] {min(start + len(batch), total)}/{total} trechos concluídos.", flush=True)

        with connection:
            connection.execute("INSERT OR REPLACE INTO corpus VALUES ('complete', '1')")
        connection.close()
        print(f"[Ingestor] Indexação concluída em '{index_path}'.")
        return documents
