"""Orquestrador do TrendBot usando a API local do Ollama."""
import json
import re
import urllib.request
from typing import Dict, List, Optional

from .config import DEFAULT_KEEP_ALIVE, DEFAULT_OLLAMA_URL, DEFAULT_TEMPERATURE, PROMPT_TEMPLATE
from .memory import limpar_memoria_gpu


class TrendBot:
    def __init__(self, retriever, model_name: str = "llama3", base_url: str = DEFAULT_OLLAMA_URL,
                 temperature: float = DEFAULT_TEMPERATURE, keep_alive: str = DEFAULT_KEEP_ALIVE):
        self.retriever = retriever
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.keep_alive = keep_alive
        self.model_name = model_name
        self.chat_history: List[str] = []

    def _answer(self, question: str, history: str) -> str:
        documents = self.retriever.search(question)
        context = "\n\n---\n\n".join(doc["page_content"] for doc in documents) or "Nenhum documento relevante encontrado na base."
        prompt = PROMPT_TEMPLATE.format(chat_history=history, context=context, question=question)
        payload = json.dumps({"model": self.model_name, "prompt": prompt, "stream": False,
                              "keep_alive": self.keep_alive, "options": {"temperature": self.temperature}}).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/api/generate", data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8")).get("response", "").strip()

    def trocar_modelo(self, novo_modelo: str):
        limpar_memoria_gpu(self.model_name, self.base_url)
        self.model_name = novo_modelo

    def ask(self, question: str) -> str:
        normalized = re.sub(r"[^\w\s]", "", question.lower()).strip()
        if normalized in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "quem e voce", "quem é você"}:
            return "TrendBot-BR: análise factual do corpus de vídeos do TikTok no Brasil."
        history = "\n".join(self.chat_history[-4:]) or "Nenhuma conversa anterior."
        answer = self._answer(question, history)
        self.chat_history.extend([f"Usuário: {question}", f"TrendBot ({self.model_name}): {answer}"])
        return answer

    def comparar(self, question: str, modelos: Optional[List[str]] = None) -> Dict[str, str]:
        original = self.model_name
        history = "\n".join(self.chat_history[-4:]) or "Nenhuma conversa anterior."
        answers = {}
        for model in modelos or ["llama3", "mistral"]:
            self.trocar_modelo(model)
            answers[model] = self._answer(question, history)
        self.trocar_modelo(original)
        return answers
