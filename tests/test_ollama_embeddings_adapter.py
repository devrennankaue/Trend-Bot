"""Testes do adaptador de embeddings sem PyTorch."""
import json
import os
import sys
import unittest
from unittest.mock import patch


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.ollama_embeddings import OllamaEmbeddings


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class TestOllamaEmbeddingsAdapter(unittest.TestCase):
    @patch("src.ollama_embeddings.urllib.request.urlopen")
    def test_adapta_documentos_e_consulta_para_api_do_ollama(self, mock_urlopen):
        mock_urlopen.return_value = _Response({"embeddings": [[0.1, 0.2], [0.3, 0.4]]})
        embeddings = OllamaEmbeddings(model="nomic-embed-text")

        self.assertEqual(embeddings.embed_documents(["a", "b"]), [[0.1, 0.2], [0.3, 0.4]])
        self.assertEqual(embeddings.embed_query("a"), [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
