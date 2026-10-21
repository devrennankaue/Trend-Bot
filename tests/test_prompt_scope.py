"""Testes de contrato do escopo factual do TrendBot-BR."""
import os
import sys
import unittest


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.config import PROMPT_TEMPLATE


class TestPromptScope(unittest.TestCase):
    """Garante que o prompt mantenha o TrendBot no escopo do corpus."""

    def test_restringe_respostas_ao_corpus_do_tiktok(self):
        self.assertIn("não é um assistente geral", PROMPT_TEMPLATE.lower())
        self.assertIn("Contexto recuperado dos vídeos", PROMPT_TEMPLATE)
        self.assertIn("O histórico da conversa não é evidência", PROMPT_TEMPLATE)

    def test_define_recusa_para_perguntas_subjetivas_e_fora_do_escopo(self):
        self.assertIn("Não responda perguntas subjetivas", PROMPT_TEMPLATE)
        self.assertIn("pedidos de opinião", PROMPT_TEMPLATE)
        self.assertIn(
            "O TrendBot analisa exclusivamente dados do corpus de vídeos do TikTok.",
            PROMPT_TEMPLATE,
        )

    def test_exige_evidencias_concretas(self):
        self.assertIn("hashtags, músicas, criadores, datas, métricas", PROMPT_TEMPLATE)
        self.assertIn("não apresente interpretações como certezas", PROMPT_TEMPLATE)
        self.assertIn("Vídeo ID", PROMPT_TEMPLATE)
        self.assertIn("três vídeos distintos", PROMPT_TEMPLATE)


if __name__ == "__main__":
    unittest.main()
