"""Mede se os vídeos de referência aparecem entre os recuperados pelo RAG."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DEFAULT_CHROMA_DIR
from src.retriever import TrendRetriever


def main():
    questions = Path(__file__).with_name("perguntas_referencia.csv")
    retriever = TrendRetriever(persist_directory=DEFAULT_CHROMA_DIR).get_retriever(k=4)
    hits = 0
    total = 0
    with questions.open(encoding="utf-8", newline="") as question_file:
        for row in csv.DictReader(question_file):
            if not row["ids_fonte"].strip():
                continue
            expected = set(row["ids_fonte"].split(";"))
            found = {str(document["metadata"]["video_id"])
                     for document in retriever.search(row["pergunta"])}
            hit = bool(expected & found)
            hits += hit
            total += 1
            print(f"{'ACERTO' if hit else 'FALHA'}: {row['pergunta']}")
            print(f"  Esperados: {sorted(expected)}; recuperados: {sorted(found)}")
    print(f"Acerto de fonte em pelo menos um dos 4 resultados: {hits}/{total}")


if __name__ == "__main__":
    main()
