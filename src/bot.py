"""Orquestrador do TrendBot usando a API local do Ollama."""
import json
import re
import urllib.request
from typing import Dict, List

from .config import (DEFAULT_KEEP_ALIVE, DEFAULT_MODEL, DEFAULT_OLLAMA_URL, DEFAULT_TEMPERATURE,
                     INSUFFICIENT_EVIDENCE_MESSAGE, MIN_DISTINCT_VIDEOS_FOR_GENERALIZATION,
                     PROMPT_TEMPLATE)


class TrendBot:
    def __init__(self, retriever, base_url: str = DEFAULT_OLLAMA_URL,
                 temperature: float = DEFAULT_TEMPERATURE, keep_alive: str = DEFAULT_KEEP_ALIVE):
        self.retriever = retriever
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.keep_alive = keep_alive
        self.model_name = DEFAULT_MODEL
        self.chat_history: List[str] = []

    def _answer(self, question: str, history: str) -> str:
        documents = self.retriever.search(question)
        video_ids = self._video_ids(documents)
        if self._is_generalization_request(question) and len(video_ids) < MIN_DISTINCT_VIDEOS_FOR_GENERALIZATION:
            return INSUFFICIENT_EVIDENCE_MESSAGE

        context = "\n\n---\n\n".join(
            f"Vídeo ID: {document['metadata'].get('video_id', 'N/A')}\n{document['page_content']}"
            for document in documents
        ) or "Nenhum documento relevante encontrado na base."
        prompt = PROMPT_TEMPLATE.format(chat_history=history, context=context, question=question)
        payload = json.dumps({"model": self.model_name, "prompt": prompt, "stream": False,
                              "keep_alive": self.keep_alive, "options": {"temperature": self.temperature}}).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/api/generate", data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=300) as response:
            answer = json.loads(response.read().decode("utf-8")).get("response", "").strip()
        sources = ", ".join(f"Vídeo ID: {video_id}" for video_id in video_ids)
        return f"{answer}\n\nFontes do corpus: {sources}." if sources else answer

    @staticmethod
    def _video_ids(documents: List[Dict]) -> List[str]:
        return list(dict.fromkeys(
            str(document.get("metadata", {}).get("video_id"))
            for document in documents
            if document.get("metadata", {}).get("video_id") is not None
        ))

    @staticmethod
    def _is_generalization_request(question: str) -> bool:
        normalized = re.sub(r"[^\w\s]", "", question.lower())
        markers = ("típico", "tipico", "comum", "geralmente", "padrão", "padrao", "mais frequente")
        return any(marker in normalized for marker in markers)

    def ask(self, question: str) -> str:
        normalized = re.sub(r"[^\w\s]", "", question.lower()).strip()
        if normalized in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "quem e voce", "quem é você"}:
            return "TrendBot-BR: análise factual do corpus de vídeos do TikTok no Brasil."
        history = "\n".join(self.chat_history[-4:]) or "Nenhuma conversa anterior."
        answer = self._answer(question, history)
        self.chat_history.extend([f"Usuário: {question}", f"TrendBot ({self.model_name}): {answer}"])
        return answer
