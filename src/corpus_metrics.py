"""Consultas calculadas sobre todo o corpus de pesquisa selecionado."""
import csv
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from typing import Optional

from .config import DEFAULT_MODEL, DEFAULT_OLLAMA_URL
from .genre_analysis import classify_genres, compare_engagement


class CorpusMetrics:
    HUMOR_TERMS = re.compile(r"\b(humor\w*|comed\w*|comic\w*|piad\w*|engrac\w*)\b")
    TOPIC_ALIASES = {
        "beleza": "Beleza e moda",
        "esportes": "Esportes",
        "culinaria": "Culinária",
        "games": "Games",
        "saude": "Saúde",
        "animais": "Animais",
    }

    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.lower())
        return "".join(char for char in normalized if not unicodedata.combining(char))

    @staticmethod
    def _value(row, field):
        value = (row.get(field) or "").strip()
        return "" if value.upper() in {"NULL", "NAN", "NONE"} else value

    @classmethod
    def _number(cls, row, fields):
        for field in fields:
            raw = cls._value(row, field)
            if raw:
                try:
                    return float(raw.replace(",", "."))
                except ValueError:
                    continue
        return None

    @classmethod
    def _factual_summary(cls, row, focus_humor=False):
        source = cls._value(row, "resumo") or cls._value(row, "descricaoVideo")
        source = " ".join(source.split())
        source = re.sub(r"\b(Jr|Sr|Sra|Dr|Dra)\.", r"\1<dot>", source, flags=re.IGNORECASE)
        sentences = [sentence.replace("<dot>", ".")
                     for sentence in re.split(r"(?<=[.!?])\s+", source)]
        facts = []
        for sentence in sentences:
            if re.search(r"viraliz|potencial|apelo viral|capacidade de gerar", cls._normalize(sentence)):
                continue
            sentence = re.split(r",\s*(?:gerando|aumentando|potencializando|atraindo|incentivando)\b",
                                sentence, maxsplit=1)[0]
            if sentence.strip():
                facts.append(sentence.strip().rstrip(". !?") + ".")
        if focus_humor and facts:
            selected = [facts[0]]
            match = next((fact for fact in facts[1:] if cls.HUMOR_TERMS.search(cls._normalize(fact))), None)
            if match:
                selected.append(match)
            elif len(facts) > 1:
                selected.append(facts[1])
            return " ".join(selected)
        return " ".join(facts[:2])

    def example_summaries(self, video_ids):
        """Retorna frases completas dos resumos para vídeos já identificados pelo RAG."""
        wanted = set(map(str, video_ids))
        summaries = {}
        if not wanted:
            return summaries
        with open(self.csv_path, encoding="utf-8-sig", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                video_id = self._value(row, "IDPostagemFonte")
                if video_id in wanted:
                    summary = self._factual_summary(row)
                    if summary:
                        summaries[video_id] = summary
                if len(summaries) == len(wanted):
                    break
        return summaries

    def _humor_views_answer(self, rows, normalized):
        requested = re.search(r"\btop\s+(\d{1,2})\b", normalized)
        limit = min(int(requested.group(1)), 20) if requested else 5
        if limit < 1:
            return "O tamanho do ranking deve ser maior que zero."
        matches = []
        for row in rows:
            summary = self._value(row, "resumo") or self._value(row, "descricaoVideo")
            if not self.HUMOR_TERMS.search(self._normalize(summary[:400])):
                continue
            views = self._number(row, ("plays_mais_recente",))
            video_id = self._value(row, "IDPostagemFonte")
            if views is not None and video_id:
                matches.append((views, row))
        if not matches:
            return "Não encontrei vídeos com menção a humor no resumo e visualizações válidas no corpus selecionado."
        leaders = sorted(matches, key=lambda item: item[0], reverse=True)[:limit]
        lines = []
        for views, row in leaders:
            video_id = self._value(row, "IDPostagemFonte")
            count = f"{int(views):,}".replace(",", ".")
            summary = self._factual_summary(row, focus_humor=True) or "O resumo não descreve o conteúdo com detalhes suficientes."
            link = self._value(row, "URL")
            entry = f"- [Vídeo ID: {video_id}] {count} visualizações. {summary}"
            if link:
                entry += f" Link: {link}"
            lines.append(entry)
        return (f"Vídeos com menção a humor no início do resumo ou da descrição visual, ordenados por visualizações "
                f"({len(matches)} registros com métrica válida no corpus):\n" + "\n".join(lines) +
                "\nCritério provisório: termos ligados a humor no início do resumo ou da descrição visual; "
                "isso não é uma classificação revisada de conteúdo.")

    @staticmethod
    def _topic_from_question(normalized):
        match = re.search(r"\b(?:sobre|a respeito de)\s+(.+)", normalized)
        if match and not re.search(r"\b(o que|quais videos|que assuntos|que temas|falando|falam|"
                                   r"comentando|comentam|dizendo|dizem|mencionam)\b", normalized[:match.start()]):
            return None
        if not match:
            match = re.search(r"\b(?:falando|falam|comentando|comentam|dizendo|dizem)\s+"
                              r"(?:de|da|do|das|dos)\s+(.+)", normalized)
        if not match:
            return None
        topic = re.sub(r"\b(?:no|na|nos|nas)\s+(?:tiktok|corpus|dataset|csv|videos|postagens)\b.*$",
                       "", match.group(1)).strip(" ?!.")
        topic = re.sub(r"^(?:a|o|as|os|da|do|de|dos|das)\s+", "", topic)
        return topic if len(topic) >= 3 and len(topic.split()) <= 5 else None

    def _topic_answer(self, topic, rows):
        fields = ("postagem", "resumo", "descricaoVideo", "transcricaoVideo")
        matches = [row for row in rows if any(
            topic in self._normalize(self._value(row, field)) for field in fields
        )]
        if not matches:
            return f"Não encontrei menções a '{topic}' nos textos dos {len(rows)} vídeos do corpus selecionado."
        matches.sort(key=lambda row: self._number(row, ("plays_mais_recente",)) or 0, reverse=True)
        lines = []
        for row in matches[:5]:
            video_id = self._value(row, "IDPostagemFonte")
            if not video_id:
                continue
            summary = self._factual_summary(row) or "O corpus não traz um resumo descritivo para este vídeo."
            line = f"- [Vídeo ID: {video_id}] {summary}"
            caption = self._value(row, "postagem")
            if topic in self._normalize(caption):
                caption = " ".join(caption.split())
                if len(caption) > 180:
                    caption = caption[:180].rsplit(" ", 1)[0] + "…"
                line += f" Postagem: “{caption}”"
            link = self._value(row, "URL")
            if link:
                line += f" Link: {link}"
            lines.append(line)
        return (f"Encontrei {len(matches)} vídeos que mencionam '{topic}' nos textos do corpus selecionado. "
                "Exemplos entre os mais vistos:\n" + "\n".join(lines) +
                "\nA busca cobre postagens e descrições dos vídeos; não resume opiniões dos comentários.")

    @staticmethod
    def _associated_topic(normalized):
        if not (re.search(r"\b(?:que|quais)\s+(?:assuntos|temas|topicos|categorias)\b", normalized)
                and re.search(r"\b(?:junto|associ\w*|relacion\w*|acompanh\w*|combin\w*)\b", normalized)):
            return None
        match = re.search(r"\b(?:conteudo|videos?|postagens?)\s+(?:de|sobre)\s+(.+?)\s*\??$", normalized)
        if not match:
            match = re.search(r"\b(?:junto|associ\w*|relacion\w*|combin\w*)\s+"
                              r"(?:com|a|ao|aos|as)\s+(.+?)\s*\??$", normalized)
        if not match:
            return None
        topic = re.sub(r"^(?:conteudo|videos?|postagens?)\s+(?:de|sobre)\s+", "", match.group(1))
        topic = topic.strip(" ?.!")
        return topic if 3 <= len(topic) <= 40 and len(topic.split()) <= 4 else None

    def _associated_topic_answer(self, topic):
        """Conta categorias associadas em vídeos distintos do CSV, sem depender do top-k do RAG."""
        target_group = self.TOPIC_ALIASES.get(topic)
        subject_groups = set(classify_genres({"resumo": topic}))
        if target_group:
            subject_groups.add(target_group)
        grouped = {}
        target_ids = set()
        with open(self.csv_path, encoding="utf-8-sig", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                video_id = self._value(row, "IDPostagemFonte")
                if not video_id or video_id in target_ids:
                    continue
                groups = classify_genres(row)
                if target_group:
                    if target_group not in groups:
                        continue
                else:
                    evidence = " ".join(self._value(row, field) for field in
                                        ("assuntos_llm", "postagem", "resumo", "descricaoVideo"))
                    if not re.search(r"(?<!\w)" + re.escape(topic) + r"(?!\w)",
                                     self._normalize(evidence)):
                        continue
                target_ids.add(video_id)
                for group in groups:
                    if group not in subject_groups:
                        grouped.setdefault(group, []).append(row)

        if not target_ids:
            return f"Não encontrei vídeos classificados ou mencionando '{topic}' no corpus selecionado."
        leaders = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))[:5]
        if not leaders:
            return (f"Encontrei {len(target_ids)} vídeos relacionados a '{topic}', mas nenhum recebeu "
                    "uma segunda categoria pelas regras atuais de classificação.")
        lines = []
        for group, rows in leaders:
            exemplar = max(rows, key=lambda row: self._number(row, ("plays_mais_recente",)) or 0)
            video_id = self._value(exemplar, "IDPostagemFonte")
            lines.append(f"- {group}: {len(rows)} vídeo(s), por exemplo [Vídeo ID: {video_id}].")
        return (f"Nos {len(target_ids)} vídeos relacionados a '{topic}' no corpus selecionado, "
                "estas categorias também foram identificadas:\n" + "\n".join(lines) +
                "\nA contagem é por vídeo e as categorias podem se sobrepor. "
                "A classificação usa termos de assuntos, postagens e resumos; ela é exploratória "
                "e não confirma que os temas sejam centrais em cada vídeo.")

    @staticmethod
    def _people_topic(normalized):
        if not re.search(r"\bquem\b.*\b(costuma\w*|aparece\w*|mais)\b", normalized):
            return None
        match = re.search(r"\b(?:sobre|de|do|da)\s+([\w\s]+?)\s*\??$", normalized)
        if not match:
            return None
        topic = match.group(1).strip()
        return topic if 3 <= len(topic) <= 50 and len(topic.split()) <= 5 else None

    def _people_topic_answer(self, topic):
        fields = ("postagem", "resumo", "descricaoVideo", "transcricaoVideo")
        with open(self.csv_path, encoding="utf-8-sig", newline="") as csv_file:
            matches = [row for row in csv.DictReader(csv_file) if any(
                topic in self._normalize(self._value(row, field)) for field in fields
            )]
        described = [(self._value(row, "IDPostagemFonte"), self._value(row, "descricaoVideo"))
                     for row in matches if self._value(row, "IDPostagemFonte")
                     and self._value(row, "descricaoVideo")]
        if not matches:
            return f"Não encontrei vídeos com menção a '{topic}' no corpus selecionado."
        if not described:
            return (f"Encontrei {len(matches)} vídeos sobre '{topic}', mas nenhum tem descrição visual "
                    "com a qual identificar quem aparece.")

        counts = Counter()
        sources = {}
        try:
            for start in range(0, len(described), 6):
                batch = described[start:start + 6]
                prompt = (
                    "Extraia nomes de pessoas que a descrição visual afirma aparecer no vídeo. "
                    "Não inclua lugares, equipes, programas, obras ou pessoas apenas mencionadas como assunto. "
                    "Não infira identidades. Responda somente JSON no formato "
                    "{\"videos\":[{\"id\":\"...\",\"names\":[\"Nome exato\"]}]}. "
                    "Use uma lista vazia quando a descrição não identificar ninguém.\nDados:\n"
                    + json.dumps([{"id": video_id, "description": description}
                                  for video_id, description in batch], ensure_ascii=False)
                )
                payload = json.dumps({"model": DEFAULT_MODEL, "prompt": prompt, "stream": False,
                                      "format": "json", "options": {"temperature": 0}}).encode("utf-8")
                request = urllib.request.Request(f"{DEFAULT_OLLAMA_URL}/api/generate", data=payload,
                                                 headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=300) as response:
                    result = json.loads(response.read().decode("utf-8"))
                extracted = json.loads(result.get("response", "{}"))
                descriptions = dict(batch)
                for item in extracted.get("videos", []):
                    video_id = str(item.get("id", ""))
                    description = descriptions.get(video_id)
                    if not description:
                        continue
                    for name in item.get("names", []):
                        if not isinstance(name, str) or len(name) < 3:
                            continue
                        if not re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", description, re.IGNORECASE):
                            continue
                        key = self._normalize(name.strip())
                        sources.setdefault(key, {"name": name.strip(), "ids": set()})["ids"].add(video_id)
            for key, value in sources.items():
                counts[key] = len(value["ids"])
        except (OSError, ValueError, TypeError, KeyError):
            return "Não foi possível conferir os nomes nas descrições visuais. Verifique o Ollama e tente novamente."

        if not counts:
            return (f"Analisei as descrições visuais de {len(described)} dos {len(matches)} vídeos "
                    f"que mencionam '{topic}', mas não encontrei nomes de pessoas identificadas nelas.")
        leaders = counts.most_common(5)
        lines = []
        for key, count in leaders:
            ids = sorted(sources[key]["ids"])
            examples = ", ".join(f"[Vídeo ID: {video_id}]" for video_id in ids[:3])
            lines.append(f"- {sources[key]['name']}: {count} vídeo(s). Fontes: {examples}.")
        conclusion = ("Nenhum nome se repete nos vídeos analisados. " if leaders[0][1] == 1 else "")
        return (f"{conclusion}Nomes identificados nas descrições visuais de {len(described)} "
                f"dos {len(matches)} vídeos que mencionam '{topic}' no corpus selecionado:\n"
                + "\n".join(lines) +
                "\nA contagem é por vídeo, não por repetição do nome no texto. "
                "Ela depende da qualidade das descrições e não confirma identidade por imagem.")

    def _genre_engagement_answer(self):
        with open(self.csv_path, encoding="utf-8-sig", newline="") as csv_file:
            analysis = compare_engagement(list(csv.DictReader(csv_file)))
        groups = analysis["results"]
        if not groups:
            return "Não há grupos de conteúdo com pelo menos 40 vídeos e taxa de engajamento válida para comparar."
        lines = []
        for group in groups[:3]:
            median = f"{group['median']:.3f}".replace(".", ",")
            mean = f"{group['mean']:.3f}".replace(".", ",")
            lines.append(f"- {group['genre']}: {group['count']} vídeos; mediana {median}%; média {mean}%.")
        leader = groups[0]
        sources = ", ".join(f"[Vídeo ID: {video_id}]" for video_id in leader["examples"])
        return (f"Na classificação exploratória do corpus, o grupo com maior mediana de taxa de "
                f"engajamento é {leader['genre']}. Comparação dos três primeiros grupos:\n" +
                "\n".join(lines) +
                f"\nExemplos do primeiro grupo próximos à mediana: {sources}. "
                f"A classificação por termos em assuntos, postagem e resumo cobriu "
                f"{analysis['labeled']} de {analysis['total']} vídeos; grupos podem se sobrepor. "
                "Foram comparados grupos com pelo menos 40 vídeos. A taxa é calculada por "
                "(curtidas + comentários + compartilhamentos + salvamentos) / visualizações × 100. "
                "Aqui gênero ou estilo significa tema amplo do conteúdo, não formato audiovisual como POV ou tutorial. "
                "É uma associação observada, não uma prova de que o gênero causa engajamento.")

    @staticmethod
    def _is_population_question(question: str) -> bool:
        return bool(re.search(
            r"\b(mais|maior|menor|media|mediana|quantos|quantas|quanto|quantidade|total|ranking|top|frequente|"
            r"predomina|predominam|geram|gera|geral|padrao|tendencia|eficaz|funciona melhor)\b",
            question,
        ))

    def answer(self, question: str) -> Optional[str]:
        normalized = self._normalize(question)
        associated_topic = self._associated_topic(normalized)
        if associated_topic:
            return self._associated_topic_answer(associated_topic)
        people_topic = self._people_topic(normalized)
        if people_topic:
            return self._people_topic_answer(people_topic)
        type_question = bool(re.search(
            r"\b(tipo|tipos|categoria|categorias|formato|formatos|conteudo|conteudos|"
            r"tema|temas|estilo|estilos|genero|generos|assunto|assuntos)\b", normalized,
        ))
        comparison = bool(re.search(
            r"\b(mais|maior|menor|melhor|media|mediana|ranking|top|geram|gera|"
            r"rende\w*|perform\w*|viraliz\w*|lidera\w*|eficaz|sucesso)\b",
            normalized,
        ))
        views = bool(re.search(r"\b(visualizac\w*|vist[oa]s?|views|plays)\b", normalized))
        engagement = bool(re.search(r"\bengaj\w*\b", normalized))
        likes = bool(re.search(r"\b(curtid\w*|likes?)\b", normalized))
        comments = bool(re.search(r"\b(comentari\w*|comentad\w*)\b", normalized))
        shares = bool(re.search(r"\b(compartilhad\w*|compartilhament\w*)\b", normalized))
        metric_requested = any((views, engagement, likes, comments, shares))
        humor_ranking = (views and bool(re.search(r"\b(humor\w*|comed\w*|comic\w*|piad\w*|engrac\w*)\b", normalized))
                         and bool(re.search(r"\b(mais|maior|top|ranking)\b", normalized))
                         and not type_question)
        performance = metric_requested or bool(re.search(
            r"\b(interac\w*|envolviment\w*|resultado\w*|perform\w*|viraliz\w*|"
            r"sucesso|popularidade|alcance|repercussao)\b", normalized,
        ))
        requested_id = re.search(r"\b\d{15,20}\b", normalized)
        if type_question and comparison and performance:
            if engagement:
                return self._genre_engagement_answer()
            answer = ("Não é possível comparar tipos de vídeo no corpus atual: os registros "
                      "não têm uma classificação de conteúdo preenchida. As métricas dos vídeos "
                      "existem, mas não indicam a qual tipo cada vídeo pertence. "
                      "Para responder a essa pergunta, é preciso classificar os vídeos por tipo "
                      "e definir a métrica de comparação.")
            if engagement:
                answer += " Esses dados observacionais também não demonstram o que causa engajamento."
            return answer

        topic = self._topic_from_question(normalized) if not metric_requested and not requested_id else None
        if topic:
            with open(self.csv_path, encoding="utf-8-sig", newline="") as csv_file:
                return self._topic_answer(topic, list(csv.DictReader(csv_file)))

        if not self._is_population_question(normalized):
            return None

        if not any((metric_requested, "hashtag" in normalized,
                    "musica" in normalized, "audio" in normalized,
                    re.search(r"\b(quantos|quantidade|total|numero)\b.*\b(videos?|postagens?)\b", normalized))):
            return None

        with open(self.csv_path, encoding="utf-8-sig", newline="") as csv_file:
            rows = list(csv.DictReader(csv_file))
        total = len(rows)

        if humor_ranking:
            return self._humor_views_answer(rows, normalized)

        metric_specs = (
            (engagement, "taxa de engajamento", ("taxaEngajamento_mais_recente", "taxaEngajamento_da_ultima_coleta")),
            (views, "visualizações", ("plays_mais_recente", "plays_da_ultima_coleta")),
            (likes, "curtidas", ("curtidas_mais_recente", "curtidas_da_ultima_coleta")),
            (comments, "comentários", ("comentarios_mais_recente", "comentarios_da_ultima_coleta")),
            (shares, "compartilhamentos", ("compartilhamentos_mais_recente", "compartilhamentos_da_ultima_coleta")),
        )
        metric_label, fields = next(((label, columns) for selected, label, columns in metric_specs if selected), (None, ()))

        if requested_id and metric_requested:
            video = next((row for row in rows if self._value(row, "IDPostagemFonte") == requested_id.group()), None)
            if video is None:
                return f"O vídeo ID {requested_id.group()} não está no corpus selecionado."
            value = self._number(video, fields)
            if value is None:
                return f"O vídeo ID {requested_id.group()} não tem valor disponível para essa métrica."
            value_text = (f"{value:.3f}".replace(".", ",") if engagement
                          else f"{int(value):,}".replace(",", "."))
            return f"[Vídeo ID: {requested_id.group()}] tem {metric_label} de {value_text} no corpus selecionado."

        if re.search(r"\b(quantos|quantidade|total|numero)\b.*\b(videos?|postagens?)\b", normalized):
            return f"O corpus de pesquisa selecionado contém {total} vídeos."

        if metric_requested and any(term in normalized for term in ("hashtag", "musica", "audio")):
            return ("Essa comparação por hashtag ou música ainda não está definida para o corpus inteiro. "
                    "É necessário definir o agrupamento e conferir a cobertura dos campos antes do cálculo.")

        if "hashtag" in normalized:
            hashtags = Counter()
            covered = 0
            for row in rows:
                value = self._value(row, "hashtags_postagem")
                if value:
                    covered += 1
                    hashtags.update(set(re.findall(r"#[\w]+", value.lower())))
            if not hashtags:
                return f"Não há hashtags de postagens preenchidas nos {total} vídeos do corpus selecionado."
            items = ", ".join(f"{tag} ({count} vídeos)" for tag, count in hashtags.most_common(5))
            return f"Hashtags mais frequentes: {items}. Cobertura: {covered} de {total} vídeos."

        if "musica" in normalized or "audio" in normalized:
            songs = Counter(self._value(row, "nomeMusica") for row in rows)
            songs.pop("", None)
            if not songs:
                return f"Não há nomes de músicas preenchidos nos {total} vídeos do corpus selecionado."
            items = ", ".join(f"{song} ({count} vídeos)" for song, count in songs.most_common(5))
            return f"Músicas mais frequentes: {items}. Cobertura: {sum(songs.values())} de {total} vídeos."

        if metric_requested:
            average = bool(re.search(r"\b(media|medio)\b", normalized))
            ranking = bool(re.search(r"\b(mais|maior|top|ranking)\b", normalized))
            if not average and not ranking:
                return ("Essa pergunta exige uma análise do corpus inteiro que ainda não está definida "
                        "para esta métrica. Especifique um ranking de vídeos ou a medida desejada.")
            ranked = [(value, row) for row in rows if (value := self._number(row, fields)) is not None]
            if not ranked:
                return f"O corpus não possui valores válidos para essa métrica nos {total} vídeos."
            if average:
                mean = sum(value for value, _ in ranked) / len(ranked)
                mean_text = (f"{mean:.3f}".replace(".", ",") if engagement
                             else f"{mean:,.0f}".replace(",", "."))
                return (f"A média de {metric_label} no corpus selecionado é {mean_text}. "
                        f"Cálculo com {len(ranked)} de {total} vídeos com valor disponível.")

            requested = re.search(r"\btop\s+(\d{1,2})\b", normalized)
            plural = bool(re.search(r"\b(quais|videos)\b.*\b(mais|maior)\b", normalized))
            limit = min(int(requested.group(1)), 20) if requested else (5 if plural else 1)
            if limit < 1:
                return "O tamanho do ranking deve ser maior que zero."
            leaders = sorted(ranked, key=lambda item: item[0], reverse=True)[:limit]
            entries = []
            for value, row in leaders:
                video_id = self._value(row, "IDPostagemFonte") or "não informado"
                value_text = (f"{value:.3f}".replace(".", ",") if engagement
                              else f"{int(value):,}".replace(",", "."))
                metric_text = (f"taxa de engajamento de {value_text}" if engagement
                               else f"{value_text} {metric_label}")
                entry = f"[Vídeo ID: {video_id}], {metric_text}"
                date = self._value(row, "dataVisita_metricas_mais_recente")
                if date:
                    entry += f" (coleta: {date})"
                link = self._value(row, "URL")
                if link:
                    entry += f" ({link})"
                entries.append(entry)
            qualifier = "maior taxa de engajamento" if engagement else f"mais {metric_label}"
            subject = "Vídeo" if len(leaders) == 1 else "Vídeos"
            answer = (f"{subject} com {qualifier} no corpus selecionado: "
                      f"{'; '.join(entries)}. Valores disponíveis para {len(ranked)} de {total} vídeos.")
            if engagement:
                answer += " É uma comparação observacional; ela não demonstra o que causa engajamento."
            return answer

        return None
