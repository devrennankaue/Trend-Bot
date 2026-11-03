"""Testes da recuperação MMR com diversidade por vídeo."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.retriever import TrendRetriever


class _EmbeddingsFake:
    def embed_query(self, _question):
        return [1.0, 0.0]


class TestRetrieverMMR(unittest.TestCase):
    def test_prioriza_videos_distintos_quando_houver_candidatos(self):
        documents = [
            {"page_content": "primeiro", "metadata": {"video_id": "a"}, "embedding": [1.0, 0.0]},
            {"page_content": "repetido", "metadata": {"video_id": "a"}, "embedding": [0.99, 0.01]},
            {"page_content": "segundo", "metadata": {"video_id": "b"}, "embedding": [0.8, 0.6]},
            {"page_content": "terceiro", "metadata": {"video_id": "c"}, "embedding": [0.7, 0.7]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            with open(os.path.join(directory, "indice_ollama.json"), "w", encoding="utf-8") as index_file:
                json.dump(documents, index_file)
            retriever = TrendRetriever(persist_directory=directory, embeddings=_EmbeddingsFake())

            result = retriever.get_retriever(k=3).search("consulta")

        self.assertEqual([doc["metadata"]["video_id"] for doc in result], ["a", "b", "c"])

    def test_consulta_indice_sqlite_sem_carregar_json(self):
        documents = [
            {"page_content": "primeiro", "metadata": {"video_id": "a"}, "embedding": [1.0, 0.0]},
            {"page_content": "segundo", "metadata": {"video_id": "b"}, "embedding": [0.8, 0.6]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "indice_ollama.sqlite")
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE corpus (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("INSERT INTO corpus VALUES ('complete', '1')")
            connection.execute("CREATE TABLE documents (position INTEGER PRIMARY KEY, page_content TEXT, metadata TEXT, embedding TEXT)")
            connection.executemany(
                "INSERT INTO documents VALUES (?, ?, ?, ?)",
                [(i, doc["page_content"], json.dumps(doc["metadata"]), json.dumps(doc["embedding"]))
                 for i, doc in enumerate(documents)],
            )
            connection.commit()
            connection.close()
            result = TrendRetriever(persist_directory=directory, embeddings=_EmbeddingsFake()).get_retriever(k=2).search("consulta")
        self.assertEqual([doc["metadata"]["video_id"] for doc in result], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
