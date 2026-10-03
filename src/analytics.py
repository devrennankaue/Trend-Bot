"""Deterministic answers derived directly from the local TikTok corpus."""

from dataclasses import dataclass
from typing import Optional
import re
import unicodedata

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
        if self.dataframe is None:
            return None

        normalized = self._normalize(question)
        if self._is_count_question(normalized):
            return AnalyticsAnswer(
                title="Total de vídeos no corpus local:",
                lines=[f"- {self.row_count}"],
                source_count=self.row_count,
            )

        ranking = self._ranking_intent(normalized)
        if ranking is None:
            return None

        label, columns, split_values, numeric = ranking
        return self._ranking_answer(label, columns, split_values, numeric, self._requested_limit(normalized))

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value.lower())
        return "".join(char for char in decomposed if not unicodedata.combining(char))

    @staticmethod
    def _is_count_question(question: str) -> bool:
        return bool(re.search(r"\b(quantos|quantidade|numero|total)\b.*\b(videos?|postagens?)\b", question))

    @staticmethod
    def _requested_limit(question: str) -> int:
        match = re.search(r"\b(?:top|primeir[oa]s?)\s+(\d{1,2})\b", question)
        if match:
            return max(1, min(int(match.group(1)), 20))
        return 5

    @staticmethod
    def _ranking_intent(question: str):
        if "hashtag" in question:
            return "Hashtags mais frequentes:", ("hashtags_postagem", "hashtags_topico_principal", "hashtags"), True, False
        if any(term in question for term in ("musica", "audio")):
            return "Músicas mais frequentes:", ("nomeMusica", "musica"), False, False
        if any(term in question for term in ("criador", "criadores", "usuario", "autor")):
            return "Criadores mais frequentes:", ("usuario_apelido", "usuario_nome", "creator"), False, False
        if any(term in question for term in ("mais vistos", "maior numero de plays", "mais visualizados")):
            return "Vídeos com mais plays:", ("plays_mais_recente", "plays_da_ultima_coleta", "play_count"), False, True
        if "mais curtidos" in question:
            return "Vídeos com mais curtidas:", ("curtidas_mais_recente", "curtidas_da_ultima_coleta"), False, True
        if "mais comentados" in question:
            return "Vídeos com mais comentários:", ("comentarios_mais_recente", "comentarios_da_ultima_coleta"), False, True
        return None

    def _first_existing_column(self, columns: tuple[str, ...]) -> Optional[str]:
        assert self.dataframe is not None
        return next((column for column in columns if column in self.dataframe.columns), None)

    def _ranking_answer(
        self,
        label: str,
        columns: tuple[str, ...],
        split_values: bool,
        numeric: bool,
        limit: int,
    ) -> AnalyticsAnswer:
        assert self.dataframe is not None
        column = self._first_existing_column(columns)
        if column is None:
            return AnalyticsAnswer(label, ["- O corpus não possui dados para esta métrica."], 0)

        values = self.dataframe[column].dropna()
        if numeric:
            numeric_values = pd.to_numeric(values, errors="coerce").dropna()
            if numeric_values.empty:
                return AnalyticsAnswer(label, ["- O corpus não possui dados para esta métrica."], 0)
            video_ids = self.dataframe.get("IDPostagem", self.dataframe.index).astype(str)
            ranked = numeric_values.sort_values(ascending=False).head(limit)
            lines = [f"- Vídeo {video_ids.loc[index]}: {int(value)}" for index, value in ranked.items()]
            return AnalyticsAnswer(label, lines, len(numeric_values))

        text_values = values.astype(str).str.strip()
        text_values = text_values[(text_values != "") & (text_values.str.lower() != "nan") & (text_values.str.upper() != "NULL")]
        if split_values:
            text_values = text_values.str.split(r"[,;|\s]+", regex=True).explode().str.strip()
            text_values = text_values[text_values != ""]
        if text_values.empty:
            return AnalyticsAnswer(label, ["- O corpus não possui dados para esta métrica."], 0)

        ranked = text_values.value_counts().head(limit)
        lines = [f"- {value}: {count} vídeos" for value, count in ranked.items()]
        return AnalyticsAnswer(label, lines, len(text_values))
