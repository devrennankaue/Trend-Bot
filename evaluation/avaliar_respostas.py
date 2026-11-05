"""Executa as perguntas de referência e registra medidas automáticas e revisão humana."""
import csv
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bot import TrendBot
from src.corpus_metrics import CorpusMetrics
from src.config import DEFAULT_CHROMA_DIR
from src.retriever import TrendRetriever


def rouge_l(reference: str, answer: str) -> float:
    first = re.findall(r"\w+", reference.lower())
    second = re.findall(r"\w+", answer.lower())
    if not first or not second:
        return 0.0
    previous = [0] * (len(second) + 1)
    for word in first:
        current = [0]
        for index, candidate in enumerate(second, 1):
            current.append(previous[index - 1] + 1 if word == candidate
                           else max(previous[index], current[-1]))
        previous = current
    overlap = previous[-1]
    return 2 * overlap / (len(first) + len(second))


def main():
    questions_path = Path(__file__).with_name("perguntas_referencia.csv")
    output_path = Path(__file__).with_name("resultados_respostas.csv")
    retriever = TrendRetriever(persist_directory=DEFAULT_CHROMA_DIR).get_retriever(k=4)
    bot = TrendBot(retriever=retriever, metrics=CorpusMetrics(str(ROOT / "data" / "corpus_pesquisa_5000.csv")))
    with questions_path.open(encoding="utf-8", newline="") as question_file:
        questions = list(csv.DictReader(question_file))
    fields = ["categoria", "pergunta", "resposta_referencia", "ids_fonte", "ids_recuperados",
              "acerto_fonte", "acerto_resposta_deterministica", "resposta", "rouge_l_f1", "tempo_segundos",
              "relevancia_1a5", "factualidade_1a5", "coerencia_1a5", "utilidade_1a5", "observacoes"]
    with output_path.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fields)
        writer.writeheader()
        for question in questions:
            start = time.perf_counter()
            expected = set(filter(None, question["ids_fonte"].split(";")))
            documents = retriever.search(question["pergunta"]) if expected else []
            found = {str(document["metadata"].get("video_id")) for document in documents}
            answer = bot.ask(question["pergunta"])
            elapsed = time.perf_counter() - start
            deterministic = question["categoria"] in {"contagem", "ranking", "sem_resposta", "tema", "genero"}
            writer.writerow({
                "categoria": question["categoria"], "pergunta": question["pergunta"],
                "resposta_referencia": question["resposta_referencia"],
                "ids_fonte": question["ids_fonte"], "ids_recuperados": ";".join(sorted(found)),
                "acerto_fonte": int(bool(expected & found)) if expected else "",
                "acerto_resposta_deterministica": (int(question["resposta_referencia"].casefold() in answer.casefold())
                                                   if deterministic else ""),
                "resposta": answer,
                "rouge_l_f1": round(rouge_l(question["resposta_referencia"], answer), 4),
                "tempo_segundos": round(elapsed, 2),
            })
            output_file.flush()
            print(f"{question['categoria']}: {elapsed:.1f}s; fonte encontrada: "
                  f"{bool(expected & found) if expected else 'não se aplica'}", flush=True)
    print(f"Resultados para revisão humana: {output_path}")


if __name__ == "__main__":
    main()
