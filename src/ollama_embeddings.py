"""Adaptador mínimo de embeddings para a API local do Ollama."""
import json
import urllib.error
import urllib.request
from typing import List


class OllamaEmbeddings:
    """Fornece a interface de embeddings esperada pelo Chroma sem PyTorch."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def _embed(self, inputs):
        payload = json.dumps({"model": self.model, "input": inputs}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as error:
            raise RuntimeError(
                "Não foi possível gerar embeddings no Ollama. Confirme que o serviço está em execução "
                "e que o modelo 'nomic-embed-text' foi baixado."
            ) from error

        embeddings = data.get("embeddings")
        if not embeddings:
            raise RuntimeError("O Ollama não retornou embeddings para o modelo configurado.")
        return embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)[0]
