"""Testes de indexacao em lotes para o Ollama."""
import csv
import json
import os
import sys
import tempfile
import unittest


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.config import DEFAULT_EMBEDDING_BATCH_SIZE
from src.ingestor import TrendDataIngestor


class _EmbeddingsFake:
    def __init__(self):
        self.batch_sizes = []

    def embed_documents(self, texts):
        self.batch_sizes.append(len(texts))
        return [[float(index)] for index in range(len(texts))]


class TestIngestorBatching(unittest.TestCase):
    def test_indexa_todos_os_chunks_em_lotes_limitados(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = os.path.join(directory, "videos.csv")
            index_dir = os.path.join(directory, "index")
            with open(csv_path, "w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=["descricaoVideo"])
                writer.writeheader()
                writer.writerows({"descricaoVideo": f"video {index}"} for index in range(11))

            ingestor = TrendDataIngestor(csv_path=csv_path, persist_directory=index_dir, nrows=None)
            embeddings = _EmbeddingsFake()
            ingestor.embeddings = embeddings

            documents = ingestor.load_and_index()

            self.assertEqual(len(documents), 11)
            self.assertEqual(embeddings.batch_sizes, [DEFAULT_EMBEDDING_BATCH_SIZE, 1])
            with open(os.path.join(index_dir, "indice_ollama.json"), encoding="utf-8") as index_file:
                self.assertEqual(len(json.load(index_file)), 11)


if __name__ == "__main__":
    unittest.main()
