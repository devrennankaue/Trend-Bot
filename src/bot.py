"""Orquestrador do TrendBot usando a API local do Ollama."""
import json
import re
import urllib.request
from typing import Dict, List

from .config import (DEFAULT_KEEP_ALIVE, DEFAULT_MODEL, DEFAULT_OLLAMA_URL, DEFAULT_TEMPERATURE,
                     INSUFFICIENT_EVIDENCE_MESSAGE, PROMPT_TEMPLATE)


class TrendBot:
    def __init__(self, retriever, base_url: str = DEFAULT_OLLAMA_URL,
                 temperature: float = DEFAULT_TEMPERATURE, keep_alive: str = DEFAULT_KEEP_ALIVE,
                 metrics=None):
        self.retriever = retriever
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.keep_alive = keep_alive
        self.model_name = DEFAULT_MODEL
        self.metrics = metrics
        self.chat_history: List[str] = []

    def _answer(self, question: str, history: str) -> str:
        pattern_request = self._is_pattern_request(question)
        documents = self.retriever.search(question)
        if pattern_request and hasattr(self.retriever, "find_examples"):
            terms = self._subject_terms(question)
            if "humor" in terms:
                terms.extend(["comédia", "engraçad", "piada"])
            if not any(any(term in document.get("page_content", "").lower() for term in terms)
                       for document in documents):
                documents = self.retriever.find_examples(terms) or documents
        video_ids = self._video_ids(documents)
        if not documents or self._requires_population_comparison(question):
            return INSUFFICIENT_EVIDENCE_MESSAGE

        context = "\n\n---\n\n".join(
            f"Vídeo ID: {document['metadata'].get('video_id', 'N/A')}\n{document['page_content']}"
            for document in documents
        ) or "Nenhum documento relevante encontrado na base."
        scoped_question = question
        if pattern_request:
            subject = ", ".join(self._subject_terms(question)) or "o assunto perguntado"
            scoped_question = (f"Descreva apenas características observáveis nos vídeos recuperados "
                               f"relacionadas a {subject}. Cite o ID de cada exemplo. "
                               "Não afirme que são um formato típico do corpus nem que "
                               "a viralidade foi comprovada.")
        prompt = PROMPT_TEMPLATE.format(chat_history=history, context=context, question=scoped_question)
        payload = json.dumps({"model": self.model_name, "prompt": prompt, "stream": False,
                              "keep_alive": self.keep_alive, "options": {"temperature": self.temperature}}).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/api/generate", data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=300) as response:
            answer = json.loads(response.read().decode("utf-8")).get("response", "").strip()
        cited_ids = re.findall(r"\[Vídeo ID:\s*([^\]]+)\]", answer)
        model_abstained = answer.startswith("Com base no corpus atual") or answer == INSUFFICIENT_EVIDENCE_MESSAGE
        if (model_abstained or not cited_ids or any(video_id not in video_ids for video_id in cited_ids)):
            if pattern_request:
                examples = self._pattern_examples(question, documents)
                if examples:
                    answer, cited_ids = examples
                else:
                    return INSUFFICIENT_EVIDENCE_MESSAGE
            else:
                return INSUFFICIENT_EVIDENCE_MESSAGE
        sources = ", ".join(f"Vídeo ID: {video_id}" for video_id in dict.fromkeys(cited_ids))
        if pattern_request:
            caveat = "Os exemplos recuperados não estabelecem um formato típico para todo o corpus."
            if "viral" in question.lower():
                caveat += " O projeto ainda não definiu um critério de viralidade."
            answer = f"{caveat} Nos exemplos recuperados:\n\n{answer}"
        return f"{answer}\n\nFontes do corpus: {sources}." if sources else answer

    @staticmethod
    def _video_ids(documents: List[Dict]) -> List[str]:
        return list(dict.fromkeys(
            str(document.get("metadata", {}).get("video_id"))
            for document in documents
            if document.get("metadata", {}).get("video_id") is not None
        ))

    @staticmethod
    def _requires_population_comparison(question: str) -> bool:
        normalized = re.sub(r"[^\w\s]", "", question.lower())
        markers = ("mais frequente", "predomina", "mais popular",
                   "mais usado", "mais eficaz", "funciona melhor", "gera mais",
                   "geram mais", "em geral", "na maioria", "qual tipo", "quais tipos")
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _is_pattern_request(question: str) -> bool:
        normalized = re.sub(r"[^\w\s]", "", question.lower())
        return any(marker in normalized for marker in ("típico", "tipico", "padrão", "padrao", "comum"))

    @staticmethod
    def _subject_terms(question: str) -> List[str]:
        ignored = {"qual", "quais", "formato", "tipico", "típico", "padrao", "padrão",
                   "comum", "video", "vídeo", "videos", "vídeos", "viral", "virais",
                   "sobre", "entre", "corpus", "conteudo", "conteúdo"}
        return list(dict.fromkeys(
            word for word in re.findall(r"\b\w{5,}\b", question.lower()) if word not in ignored
        ))

    def _pattern_examples(self, question: str, documents: List[Dict]):
        terms = self._subject_terms(question)
        if "humor" in terms:
            terms.extend(["comédia", "engraçad", "piada"])
        source_ids = self._video_ids(documents)
        summaries = (self.metrics.example_summaries(source_ids)
                     if self.metrics is not None and hasattr(self.metrics, "example_summaries") else {})
        examples = []
        cited_ids = []
        for document in documents:
            raw_id = document.get("metadata", {}).get("video_id")
            video_id = str(raw_id) if raw_id is not None else ""
            content = " ".join(document.get("page_content", "").split())
            lowered = content.lower()
            positions = [lowered.find(term) for term in terms if term in lowered]
            if not video_id or video_id in cited_ids or (not positions and video_id not in summaries):
                continue
            if video_id in summaries:
                examples.append(f"- [Vídeo ID: {video_id}] No resumo do CSV: {summaries[video_id]}")
                cited_ids.append(video_id)
                if len(examples) == 3:
                    break
                continue
            summary_start = lowered.find("resumo:")
            start = summary_start if summary_start >= 0 else max(0, min(positions) - 40)
            excerpt = content[start:start + 260].strip()
            if start and summary_start < 0:
                excerpt = "…" + excerpt
            if start + 260 < len(content):
                excerpt += "…"
            examples.append(f"- [Vídeo ID: {video_id}] {excerpt}")
            cited_ids.append(video_id)
            if len(examples) == 3:
                break
        return ("\n".join(examples), cited_ids) if examples else None

    def ask(self, question: str) -> str:
        normalized = re.sub(r"[^\w\s]", "", question.lower()).strip()
        if normalized in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "quem e voce", "quem é você"}:
            return "TrendBot-BR: análise factual do corpus de vídeos do TikTok no Brasil."
        if self.metrics is not None:
            metric_answer = self.metrics.answer(question)
            if metric_answer is not None:
                self.chat_history.extend([f"Usuário: {question}", f"TrendBot: {metric_answer}"])
                return metric_answer
        history = "\n".join(self.chat_history[-4:]) or "Nenhuma conversa anterior."
        answer = self._answer(question, history)
        self.chat_history.extend([f"Usuário: {question}", f"TrendBot ({self.model_name}): {answer}"])
        return answer
