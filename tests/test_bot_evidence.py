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
    @patch("src.bot.urllib.request.urlopen")
    def test_pergunta_de_visualizacoes_usa_calculo_sem_chamar_llm(self, mock_urlopen):
        class _Metrics:
            def answer(self, _question):
                return "Vídeo ID: 10, 58.600.000 visualizações."

        bot = TrendBot(_Retriever([]), metrics=_Metrics())
        self.assertEqual(bot.ask("Qual tipo de vídeo tem mais visualizações?"),
                         "Vídeo ID: 10, 58.600.000 visualizações.")
        mock_urlopen.assert_not_called()

    @patch("src.bot.urllib.request.urlopen")
    def test_formato_tipico_descreve_exemplos_sem_afirmar_padrao(self, mock_urlopen):
        mock_urlopen.return_value = _Response({"response": "Há uma brincadeira visual [Vídeo ID: 1]."})
        bot = TrendBot(_Retriever([_document("1"), _document("2"), _document("1")]))

        answer = bot.ask("Qual é o formato típico de um vídeo viral de humor?")

        self.assertIn("não estabelecem um formato típico", answer)
        self.assertIn("não definiu um critério de viralidade", answer)
        self.assertIn("brincadeira visual [Vídeo ID: 1]", answer)
        prompt = json.loads(mock_urlopen.call_args.args[0].data.decode("utf-8"))["prompt"]
        self.assertIn("Descreva apenas características observáveis", prompt)

    @patch("src.bot.urllib.request.urlopen")
    def test_formato_tipico_mostra_trechos_quando_llm_recusa_sem_citar(self, mock_urlopen):
        mock_urlopen.return_value = _Response({"response": INSUFFICIENT_EVIDENCE_MESSAGE})
        documents = [{"page_content": "Humor autodepreciativo com a surpresa de um cachorro.",
                      "metadata": {"video_id": "123"}}]
        bot = TrendBot(_Retriever(documents))

        answer = bot.ask("Qual é o formato típico de um vídeo viral de humor?")

        self.assertIn("não estabelecem um formato típico", answer)
        self.assertIn("[Vídeo ID: 123] Humor autodepreciativo", answer)
        self.assertIn("Fontes do corpus: Vídeo ID: 123.", answer)

    @patch("src.bot.urllib.request.urlopen")
    def test_formato_tipico_busca_exemplos_textuais_se_semantica_falhar(self, mock_urlopen):
        class _RetrieverComFallback(_Retriever):
            def find_examples(self, _terms):
                return [{"page_content": "Piada visual de humor com reação inesperada.",
                         "metadata": {"video_id": "456"}}]

        mock_urlopen.return_value = _Response({"response": INSUFFICIENT_EVIDENCE_MESSAGE})
        bot = TrendBot(_RetrieverComFallback([_document("1")]))

        answer = bot.ask("Qual é o formato típico de um vídeo viral de humor?")

        self.assertIn("[Vídeo ID: 456] Piada visual de humor", answer)
        self.assertIn("Fontes do corpus: Vídeo ID: 456.", answer)

    @patch("src.bot.urllib.request.urlopen")
    def test_fallback_usa_resumo_completo_do_csv(self, mock_urlopen):
        class _Metrics:
            def answer(self, _question):
                return None

            def example_summaries(self, _ids):
                return {"123": "Homem conta uma piada. O vídeo tem cortes rápidos."}

        mock_urlopen.return_value = _Response({"response": INSUFFICIENT_EVIDENCE_MESSAGE})
        documents = [{"page_content": "…humor com cortes…", "metadata": {"video_id": "123"}}]
        bot = TrendBot(_Retriever(documents), metrics=_Metrics())

        answer = bot.ask("Qual é o formato típico de um vídeo viral de humor?")

        self.assertIn("No resumo do CSV: Homem conta uma piada. O vídeo tem cortes rápidos.", answer)
        self.assertNotIn("…humor com cortes…", answer)

    @patch("src.bot.urllib.request.urlopen")
    def test_anexa_fontes_distintas_a_resposta(self, mock_urlopen):
        mock_urlopen.return_value = _Response({"response": "Achado confirmado [Vídeo ID: 1]."})
        bot = TrendBot(_Retriever([_document("1"), _document("2"), _document("3")]))

        answer = bot.ask("Quais vídeos mencionam humor?")

        self.assertEqual(answer, "Achado confirmado [Vídeo ID: 1].\n\nFontes do corpus: Vídeo ID: 1.")
        request_payload = json.loads(mock_urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertIn("Vídeo ID: 1", request_payload["prompt"])

    @patch("src.bot.urllib.request.urlopen")
    def test_recusa_citacao_de_video_nao_recuperado(self, mock_urlopen):
        mock_urlopen.return_value = _Response({"response": "Tem 123.456 visualizações [Vídeo ID: 999]."})
        bot = TrendBot(_Retriever([_document("1")]))

        self.assertEqual(bot.ask("O que mostra o vídeo?"), INSUFFICIENT_EVIDENCE_MESSAGE)

    @patch("src.bot.urllib.request.urlopen")
    def test_pergunta_sobre_tipo_que_gera_engajamento_nao_usa_quatro_exemplos(self, mock_urlopen):
        bot = TrendBot(_Retriever([_document(str(i)) for i in range(4)]))

        self.assertEqual(bot.ask("Qual tipo de vídeo gera mais engajamento no TikTok?"),
                         INSUFFICIENT_EVIDENCE_MESSAGE)
        mock_urlopen.assert_not_called()

    @patch("src.bot.urllib.request.urlopen")
    def test_pergunta_descritiva_sobre_tendencias_pode_usar_fontes(self, mock_urlopen):
        mock_urlopen.return_value = _Response({"response": "Um vídeo mostra humor [Vídeo ID: 1]."})
        bot = TrendBot(_Retriever([_document("1")]))

        answer = bot.ask("Quais tendências aparecem nos vídeos recuperados?")

        self.assertIn("Um vídeo mostra humor [Vídeo ID: 1].", answer)
        self.assertIn("Fontes do corpus: Vídeo ID: 1.", answer)

    @patch("src.bot.urllib.request.urlopen")
    def test_sem_documentos_nao_aciona_llm(self, mock_urlopen):
        bot = TrendBot(_Retriever([]))

        self.assertEqual(bot.ask("O que mostra o vídeo?"), INSUFFICIENT_EVIDENCE_MESSAGE)
        mock_urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
