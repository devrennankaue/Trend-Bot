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
