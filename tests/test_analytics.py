import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.analytics import TrendAnalytics


class TestTrendAnalyticsLoading(unittest.TestCase):
    def test_loads_fixture_csv_and_exposes_exact_row_count(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fixture:
            fixture.write("video_id,hashtags\n1,#tiktok\n2,#brasil\n")
            fixture_path = fixture.name

        try:
            analytics = TrendAnalytics(csv_path=fixture_path)
        finally:
            os.unlink(fixture_path)

        self.assertTrue(analytics.available)
        self.assertEqual(analytics.row_count, 2)


class TestTrendAnalyticsAnswers(unittest.TestCase):
    def setUp(self):
        self.analytics = TrendAnalytics(dataframe=pd.DataFrame({
            "IDPostagem": ["v1", "v2", "v3"],
            "hashtags_postagem": ["#moda #brasil", "#moda", "#brasil"],
            "nomeMusica": ["Som A", "Som A", "Som B"],
            "usuario_apelido": ["ana", "bia", "ana"],
            "plays_mais_recente": [10, 30, 20],
        }))

    def test_count_question_returns_exact_corpus_row_count(self):
        answer = self.analytics.answer("Quantos vídeos existem no corpus?")

        self.assertIsNotNone(answer)
        self.assertIn("- 3", answer.render())
        self.assertIn("Calculado a partir do corpus local (3 vídeos).", answer.render())

    def test_hashtag_ranking_is_calculated_in_descending_frequency(self):
        answer = self.analytics.answer("Quais são as top 2 hashtags mais frequentes?")

        self.assertEqual(answer.lines, ["- #moda: 2 vídeos", "- #brasil: 2 vídeos"])

    def test_song_creator_and_engagement_rankings_use_their_data_columns(self):
        song_answer = self.analytics.answer("Quais músicas são mais frequentes?")
        creator_answer = self.analytics.answer("Quais criadores aparecem mais?")
        plays_answer = self.analytics.answer("Quais são os vídeos mais vistos?")

        self.assertEqual(song_answer.lines[0], "- Som A: 2 vídeos")
        self.assertEqual(creator_answer.lines[0], "- ana: 2 vídeos")
        self.assertEqual(plays_answer.lines[0], "- Vídeo v2: 30")

    def test_supported_metric_without_values_does_not_invent_a_ranking(self):
        analytics = TrendAnalytics(dataframe=pd.DataFrame({"nomeMusica": ["", None]}))

        answer = analytics.answer("Quais músicas são mais frequentes?")

        self.assertEqual(answer.lines, ["- O corpus não possui dados para esta métrica."])

    def test_unsupported_question_returns_none_for_rag_fallback(self):
        self.assertIsNone(self.analytics.answer("Explique o tom dos vídeos sobre moda"))

    def test_unreadable_csv_disables_analytics_without_raising(self):
        with patch("src.analytics.pd.read_csv", side_effect=OSError("arquivo indisponível")):
            analytics = TrendAnalytics(csv_path="missing-fixture.csv")

        self.assertFalse(analytics.available)
        self.assertEqual(analytics.row_count, 0)
        self.assertIsNotNone(analytics.error)

    def test_render_labels_result_as_calculated_from_local_corpus(self):
        analytics = TrendAnalytics(dataframe=pd.DataFrame({"video_id": ["1", "2"]}))
        answer = analytics.answer("pergunta não suportada")

        self.assertIsNone(answer)
        self.assertEqual(analytics.row_count, 2)


if __name__ == "__main__":
    unittest.main()
