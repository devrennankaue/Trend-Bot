"""Testes de contrato do caminho de embeddings sem PyTorch."""
import os
import sys
import unittest


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.config import DEFAULT_CHROMA_DIR, DEFAULT_EMBEDDING_MODEL


class TestOllamaEmbeddings(unittest.TestCase):
    def test_configura_embeddings_locais_do_ollama(self):
        self.assertEqual(DEFAULT_EMBEDDING_MODEL, "nomic-embed-text")
        self.assertTrue(DEFAULT_CHROMA_DIR.endswith("chroma_ollama_db"))

    def test_codigo_de_execucao_nao_importa_torch(self):
        for module in ("src/ingestor.py", "src/retriever.py", "src/memory.py"):
            with open(os.path.join(ROOT_DIR, module), encoding="utf-8") as source_file:
                self.assertNotIn("import torch", source_file.read())


if __name__ == "__main__":
    unittest.main()
