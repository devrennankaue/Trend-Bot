"""Comparação exploratória de grupos de conteúdo definidos por termos do CSV."""
import re
import statistics
import unicodedata
from collections import defaultdict


GENRE_RULES = (
    ("Humor e memes", r"\b(?:humor\w*|comed\w*|comic\w*|piad\w*|meme\w*|engrac\w*)\b"),
    ("Esportes", r"\b(?:esport\w*|futebol|atleta\w*|copa do mundo|basquete|volei|corrida)\b"),
    ("Culinária", r"\b(?:receit\w*|culinari\w*|cozinh\w*|bolo\w*|prato\w*|ingrediente\w*)\b"),
    ("Beleza e moda", r"\b(?:maquiagem|makeup|skincare|cosmetic\w*|batom|blush|"
     r"hidratante\w*|moda|look\w*|cabelo\w*|roupa\w*)\b"),
    ("Música e dança", r"\b(?:cantor\w*|cantora\w*|cantando|danc\w*|coreografi\w*|clipe\w*|show musical)\b"),
    ("Cinema e séries", r"\b(?:filme\w*|serie\w*|novela\w*|cinema|kdrama|netflix)\b"),
    ("Notícias e política", r"\b(?:notici\w*|politic\w*|governo|eleic\w*|congresso|stf|presidente\w*)\b"),
    ("Games", r"\b(?:game\w*|gamer\w*|gameplay|minecraft|free fire|videogame\w*)\b"),
    ("Saúde", r"\b(?:saude|medic\w*|doenc\w*|vacina\w*|hospital\w*|tratamento\w*)\b"),
    ("Animais", r"\b(?:cachorro\w*|gato\w*|pet\w*|cao|caes|animal\w*|cavalo\w*)\b"),
)
MIN_GROUP_SIZE = 40


def _normalize(text):
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _value(row, field):
    value = (row.get(field) or "").strip()
    return "" if value.upper() in {"NULL", "NAN", "NONE"} else value


def classify_genres(row):
    """Um vídeo pode pertencer a mais de um grupo; os rótulos são provisórios."""
    summary = _value(row, "resumo") or _value(row, "descricaoVideo")
    evidence = _normalize(" ".join((_value(row, "assuntos_llm"), _value(row, "postagem")[:250],
                                    summary[:400])))
    return [name for name, pattern in GENRE_RULES if re.search(pattern, evidence)]


def compare_engagement(rows):
    groups = defaultdict(list)
    valid_metrics = 0
    labeled = 0
    for row in rows:
        raw = _value(row, "taxaEngajamento_mais_recente")
        try:
            rate = float(raw.replace(",", "."))
        except ValueError:
            continue
        if rate < 0:
            continue
        valid_metrics += 1
        genres = classify_genres(row)
        if genres:
            labeled += 1
        for genre in genres:
            groups[genre].append((rate, _value(row, "IDPostagemFonte")))
    results = []
    for genre, videos in groups.items():
        if len(videos) < MIN_GROUP_SIZE:
            continue
        median = statistics.median(rate for rate, _ in videos)
        examples = [video_id for _, video_id in sorted(videos, key=lambda item: abs(item[0] - median))
                    if video_id][:3]
        results.append({"genre": genre, "count": len(videos), "median": median,
                        "mean": statistics.mean(rate for rate, _ in videos),
                        "examples": examples})
    results.sort(key=lambda item: (-item["median"], -item["count"], item["genre"]))
    return {"results": results, "valid_metrics": valid_metrics, "labeled": labeled,
            "total": len(rows)}
