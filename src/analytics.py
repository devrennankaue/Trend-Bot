"""Deterministic answers derived directly from the local TikTok corpus."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from .config import resolver_caminho_csv


@dataclass(frozen=True)
class AnalyticsAnswer:
    """A calculated answer that does not require language-model generation."""

    title: str
    lines: list[str]
    source_count: int

    def render(self) -> str:
        body = "\n".join(self.lines)
        return f"{self.title}\n{body}\n\nCalculado a partir do corpus local ({self.source_count} vídeos)."


class TrendAnalytics:
    """Loads the CSV once and exposes deterministic corpus facts."""

    def __init__(self, csv_path: Optional[str] = None, dataframe: Optional[pd.DataFrame] = None):
        self.csv_path = resolver_caminho_csv(csv_path)
        self.dataframe: Optional[pd.DataFrame] = dataframe
        self.error: Optional[str] = None

        if self.dataframe is None:
            try:
                self.dataframe = self._read_csv(self.csv_path)
            except (OSError, UnicodeDecodeError, pd.errors.ParserError) as exc:
                self.error = str(exc)

    @staticmethod
    def _read_csv(csv_path: str) -> pd.DataFrame:
        try:
            return pd.read_csv(csv_path, encoding="utf-8")
        except UnicodeDecodeError:
            return pd.read_csv(csv_path, encoding="latin1")

    @property
    def available(self) -> bool:
        return self.dataframe is not None

    @property
    def row_count(self) -> int:
        return 0 if self.dataframe is None else len(self.dataframe.index)

    def answer(self, question: str) -> Optional[AnalyticsAnswer]:
        """Return a deterministic result for a supported question, otherwise None."""
        return None
