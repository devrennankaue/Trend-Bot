import re
from operator import itemgetter
from typing import List, Dict, Optional

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

try:
    from langchain_ollama import OllamaLLM as Ollama
except ImportError:
    from langchain_community.llms import Ollama

from .config import (
    DEFAULT_OLLAMA_URL,
    DEFAULT_TEMPERATURE,
    DEFAULT_KEEP_ALIVE,
    PROMPT_TEMPLATE
)
from .memory import limpar_memoria_gpu


class TrendBot:
    """
    Controlador de conversação do bot com suporte dinâmico a múltiplos modelos locais.
    Permite alternar entre modelos (llama3, mistral, gemma:7b) em tempo real no chat
    mantendo o histórico de conversação recente.
    """
    def __init__(
        self, 
        retriever, 
        model_name: str = "llama3", 
        base_url: str = DEFAULT_OLLAMA_URL, 
        temperature: float = DEFAULT_TEMPERATURE,
        keep_alive: str = DEFAULT_KEEP_ALIVE
    ):
        self.retriever = retriever
        self.base_url = base_url
        self.temperature = temperature
        self.keep_alive = keep_alive
        
        self.model_name = model_name
        self.chat_history: List[str] = []
        
        self.prompt = PromptTemplate.from_template(PROMPT_TEMPLATE)
        self._construir_chain()

    def _construir_chain(self):
        """Inicializa o LLM via Ollama e monta a chain LCEL com o modelo ativo."""
        self.llm = Ollama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
            keep_alive=self.keep_alive
        )

        def formatar_docs(docs: List[Document]) -> str:
            """Formata e deduplica os documentos recuperados para enriquecer a diversidade."""
            if not docs:
                return "Nenhum documento relevante encontrado na base."
            
            vistos = set()
            docs_unicos = []
            for doc in docs:
                conteudo_limpo = doc.page_content.strip()
                if conteudo_limpo and conteudo_limpo not in vistos:
                    vistos.add(conteudo_limpo)
                    docs_unicos.append(conteudo_limpo)
                    
            return "\n\n---\n\n".join(docs_unicos)

        self.chain = (
            {
                "context": itemgetter("question") | self.retriever | RunnableLambda(formatar_docs),
                "question": itemgetter("question"),
                "chat_history": itemgetter("chat_history")
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def trocar_modelo(self, novo_modelo: str):
        """
        Alterna dinamicamente o modelo do bot liberando a VRAM da GPU
        antes de inicializar o novo modelo.
        """
        print(f"\n[VRAM] Descarregando '{self.model_name}' da GPU...")
        limpar_memoria_gpu(model_name=self.model_name, ollama_url=self.base_url)
        
        antigo = self.model_name
        self.model_name = novo_modelo
        self._construir_chain()
        print(f"✅ Modelo alterado: [{antigo.upper()}] ➡️ [{novo_modelo.upper()}]!\n")

    def ask(self, question: str) -> str:
        """Executa a pergunta na chain LCEL com o modelo ativo e mantém o histórico."""
        # 1. Tratamento imediato de saudações e interações simples (evita busca desnecessária no banco vetorial)
        q_normalizada = re.sub(r'[^\w\s]', '', question.lower()).strip()
        saudacoes = {
            "oi", "ola", "olá", "opa", "e ai", "e aí", "fala", "salve", "oie", "hey",
            "bom dia", "boa tarde", "boa noite", "tudo bem", "tudo bom", "como vai",
            "quem e voce", "quem é você", "o que voce faz", "o que você faz"
        }
        
        if q_normalizada in saudacoes:
            resposta = (
                f"E aí! Eu sou o TrendBot-BR, seu assistente de tendências do TikTok no Brasil! 🔥📊\n"
                f"Estou rodando com o modelo [{self.model_name.upper()}].\n\n"
                f"Pode me perguntar sobre músicas virais, hashtags, criadores, challenges ou assuntos em alta. "
                f"O que você quer analisar hoje?"
            )
            self.chat_history.append(f"Usuário: {question}")
            self.chat_history.append(f"TrendBot ({self.model_name}): {resposta}")
            return resposta

        history_str = "\n".join(self.chat_history[-4:]) if self.chat_history else "Nenhuma conversa anterior."
        
        resposta = self.chain.invoke({
            "question": question, 
            "chat_history": history_str
        })
        resposta = resposta.strip()

        self.chat_history.append(f"Usuário: {question}")
        self.chat_history.append(f"TrendBot ({self.model_name}): {resposta}")

        return resposta

    def comparar(self, question: str, modelos: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Executa a mesma pergunta nos modelos disponíveis de forma isolada,
        garantindo que um modelo não leia a resposta do outro no histórico.
        """
        if modelos is None:
            modelos = ["llama3", "mistral", "gemma:7b"]

        modelo_original = self.model_name
        respostas = {}

        # Preserva o histórico antes da comparação para que os modelos não se contaminem mutuamente
        history_str = "\n".join(self.chat_history[-4:]) if self.chat_history else "Nenhuma conversa anterior."

        print(f"\n🔬 Consultando {len(modelos)} modelos para: \"{question}\"\n" + "-"*65)
        for mod in modelos:
            print(f"⏳ Processando no [{mod.upper()}]...")
            self.trocar_modelo(mod)
            try:
                # Invoca a chain isolada sem anexar respostas intermediárias ao chat_history
                resp = self.chain.invoke({
                    "question": question,
                    "chat_history": history_str
                })
                respostas[mod] = resp.strip()
            except Exception as e:
                respostas[mod] = f"Erro: {e}"

        # Restaura o modelo ativo original
        if self.model_name != modelo_original:
            self.trocar_modelo(modelo_original)

        # Registra apenas a resposta do modelo que estava ativo
        if modelo_original in respostas and not respostas[modelo_original].startswith("Erro:"):
            self.chat_history.append(f"Usuário: {question}")
            self.chat_history.append(f"TrendBot ({modelo_original}): {respostas[modelo_original]}")

        return respostas
