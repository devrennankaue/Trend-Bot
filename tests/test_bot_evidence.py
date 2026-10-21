"""Testes de evidência e recusa de generalizações do TrendBot."""
import json
import os
import sys
import unittest
from unittest.mock import patch


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.bot import TrendBot
from src.config import INSUFFICIENT_EVIDENCE_MESSAGE


class _Retriever:
    def __init__(self, documents):
        self.documents = documents

    def search(self, _question):
        return self.documents


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _document(video_id):
    return {"page_content": f"Evidência do vídeo {video_id}", "metadata": {"video_id": video_id}}


class TestBotEvidence(unittest.TestCase):
    def test_recusa_generalizacao_com_menos_de_tres_videos_distintos(self):
        bot = TrendBot(_Retriever([_document("1"), _document("2"), _document("1")]))

        answer = bot.ask("Qual é o formato típico de vídeo de humor?")

        self.assertEqual(answer, INSUFFICIENT_EVIDENCE_MESSAGE)

    @patch("src.bot.urllib.request.urlopen")
    def test_anexa_fontes_distintas_a_resposta(self, mock_urlopen):
        mock_urlopen.return_value = _Response({"response": "Achado confirmado."})
        bot = TrendBot(_Retriever([_document("1"), _document("2"), _document("3")]))

        answer = bot.ask("Quais vídeos mencionam humor?")

        self.assertEqual(answer, "Achado confirmado.\n\nFontes do corpus: Vídeo ID: 1, Vídeo ID: 2, Vídeo ID: 3.")
        request_payload = json.loads(mock_urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertIn("Vídeo ID: 1", request_payload["prompt"])


if __name__ == "__main__":
    unittest.main()
