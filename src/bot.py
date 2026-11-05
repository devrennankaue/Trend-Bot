"""Orquestrador do TrendBot usando a API local do Ollama."""
import json
import re
import urllib.request
from typing import Dict, List

from .config import (DEFAULT_RETRIEVAL_K, DEFAULT_KEEP_ALIVE, DEFAULT_MODEL, DEFAULT_OLLAMA_URL, DEFAULT_TEMPERATURE,
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
        self.base_k = getattr(retriever, "k", DEFAULT_RETRIEVAL_K)
        self.chat_history: List[str] = []

    def _answer(self, question: str, history: str) -> str:
        population_request = self._requires_population_comparison(question)
        pattern_request = self._is_pattern_request(question) or population_request
        if hasattr(self.retriever, "get_retriever"):
            target_k = max(self.base_k, DEFAULT_RETRIEVAL_K)
            self.retriever.get_retriever(k=target_k,
                                         hashtag_filter=getattr(self.retriever, "hashtag_filter", None))
        documents = self.retriever.search(question)
        terms = self._subject_terms(question)
        if terms and hasattr(self.retriever, "find_examples"):
            if "humor" in terms:
                terms.extend(["comédia", "engraçad", "piada"])
            if not any(any(term in document.get("page_content", "").lower() for term in terms)
                       for document in documents):
                documents = self.retriever.find_examples(terms) or documents
        video_ids = self._video_ids(documents)
        if not documents:
            return INSUFFICIENT_EVIDENCE_MESSAGE
        if population_request:
            examples = self._pattern_examples(question, documents)
            if not examples:
                return INSUFFICIENT_EVIDENCE_MESSAGE
            answer, cited_ids = examples
            sources = ", ".join(f"Vídeo ID: {video_id}" for video_id in cited_ids)
            return ("A busca encontrou estes exemplos relacionados à pergunta, mas não calculou "
                    "a frequência desse padrão no corpus inteiro:\n\n"
                    f"{answer}\n\nFontes do corpus: {sources}.")

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
        answer = self._generate(prompt)
        cited_ids = re.findall(r"\[Vídeo ID:\s*([^\]]+)\]", answer)
        model_abstained = answer.startswith("Com base no corpus atual") or answer == INSUFFICIENT_EVIDENCE_MESSAGE
        if not model_abstained and not self._claims_have_sources(answer, set(video_ids)):
            repair_prompt = (prompt + "\n\nRascunho a corrigir:\n" + answer +
                             "\n\nReescreva a resposta somente com fatos presentes no contexto. "
                             "Cite [Vídeo ID: ...] em cada frase factual. Exclua afirmações sem fonte. "
                             "Se nenhuma afirmação puder ser sustentada, responda que faltam evidências.")
            answer = self._generate(repair_prompt)
            cited_ids = re.findall(r"\[Vídeo ID:\s*([^\]]+)\]", answer)
        if (model_abstained or not cited_ids or
                not self._claims_have_sources(answer, set(video_ids))):
            examples = self._pattern_examples(question, documents)
            if not examples:
                return INSUFFICIENT_EVIDENCE_MESSAGE
            answer, cited_ids = examples
            sources = ", ".join(f"Vídeo ID: {video_id}" for video_id in cited_ids)
            return ("Não encontrei evidência suficiente para responder à pergunta inteira. "
                    "Estes registros do corpus tratam de termos relacionados:\n\n"
                    f"{answer}\n\nFontes do corpus: {sources}.")
        sources = ", ".join(f"Vídeo ID: {video_id}" for video_id in dict.fromkeys(cited_ids))
        if pattern_request:
            caveat = "Os exemplos recuperados não estabelecem um formato típico para todo o corpus."
            if "viral" in question.lower():
                caveat += " O projeto ainda não definiu um critério de viralidade."
            answer = f"{caveat} Nos exemplos recuperados:\n\n{answer}"
        return f"{answer}\n\nFontes do corpus: {sources}." if sources else answer

    def _generate(self, prompt: str) -> str:
        payload = json.dumps({"model": self.model_name, "prompt": prompt, "stream": False,
                              "keep_alive": self.keep_alive, "options": {"temperature": self.temperature}}).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/api/generate", data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8")).get("response", "").strip()

    @staticmethod
    def _video_ids(documents: List[Dict]) -> List[str]:
        return list(dict.fromkeys(
            str(document.get("metadata", {}).get("video_id"))
            for document in documents
            if document.get("metadata", {}).get("video_id") is not None
        ))

    @staticmethod
    def _claims_have_sources(answer: str, valid_ids: set) -> bool:
        """Exige uma fonte recuperada para cada afirmação factual da resposta."""
        for line in answer.splitlines():
            line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
            if not line or line.endswith(":"):
                continue
            for claim in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", line):
                if not claim.strip():
                    continue
                citations = re.findall(r"\[Vídeo ID:\s*([^\]]+)\]", claim)
                if not citations or any(video_id not in valid_ids for video_id in citations):
                    return False
        return True

    @staticmethod
    def _requires_population_comparison(question: str) -> bool:
        normalized = re.sub(r"[^\w\s]", "", question.lower())
        markers = ("mais frequente", "frequente", "predomina", "mais popular",
                   "mais usado", "mais eficaz", "funciona melhor", "gera mais",
                   "geram mais", "em geral", "de forma geral", "na maioria",
                   "costuma", "costumam", "normalmente", "geralmente",
                   "qual tipo", "quais tipos")
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _is_pattern_request(question: str) -> bool:
        normalized = re.sub(r"[^\w\s]", "", question.lower())
        return any(marker in normalized for marker in ("típico", "tipico", "padrão", "padrao", "comum"))

    @staticmethod
    def _subject_terms(question: str) -> List[str]:
        ignored = {"qual", "quais", "quem", "como", "costuma", "costumam", "normalmente",
                   "geralmente", "frequente", "aparecer", "aparecem", "aparece",
                   "criadores", "brasileiros", "brasileiras", "reagem", "reage", "notícias", "noticias",
                   "formato", "tipico", "típico", "padrao", "padrão",
                   "comum", "video", "vídeo", "videos", "vídeos", "viral", "virais",
                   "sobre", "entre", "corpus", "conteudo", "conteúdo"}
        return list(dict.fromkeys(
            word for word in re.findall(r"\b\w{5,}\b", question.lower()) if word not in ignored
        ))

    def _pattern_examples(self, question: str, documents: List[Dict]):
        terms = self._subject_terms(question)
        if not terms:
            return None
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
            summary = summaries.get(video_id, "")
            if not video_id or video_id in cited_ids or (not positions and not any(term in summary.lower() for term in terms)):
                continue
            if summary:
                examples.append(f"- [Vídeo ID: {video_id}] No resumo do CSV: {summary}")
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
