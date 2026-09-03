import os
import re
import gc
import time
import urllib.request
import urllib.error
import json
import warnings
from operator import itemgetter
from typing import List, Dict, Any, Optional

import torch
import pandas as pd

# Supressão de avisos de depreciação de bibliotecas externas para saída limpa no terminal
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Imports modernos do ecossistema LangChain com fallback resiliente para langchain_community
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

try:
    from langchain_ollama import OllamaLLM as Ollama
except ImportError:
    from langchain_community.llms import Ollama

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Modelos locais padrão suportados
MODELOS_PADRAO = {
    "1": ("llama3", "Meta LLaMA 3 (8B) - Alta fluidez e velocidade"),
    "2": ("mistral", "Mistral (7B) - Raciocínio conciso e analítico"),
    "3": ("gemma:7b", "Gemma (7B) - Modelo da Google DeepMind")
}


def limpar_memoria_gpu(model_name: Optional[str] = None, ollama_url: str = "http://localhost:11434"):
    """
    Otimização de Hardware para NVIDIA RTX 4060 Ti e Intel i5-11400F:
    1. Descarrega o modelo Ollama da VRAM via HTTP (keep_alive: 0).
    2. Consulta o endpoint /api/ps para descarregar qualquer modelo residual ativo.
    3. Executa coleta de lixo do Python (gc.collect).
    4. Esvazia o cache de tensores alocados no PyTorch (torch.cuda.empty_cache).
    """
    if model_name:
        try:
            req_data = json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8")
            req = urllib.request.Request(
                f"{ollama_url}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass

    try:
        req_ps = urllib.request.Request(f"{ollama_url}/api/ps", method="GET")
        with urllib.request.urlopen(req_ps, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("models", []):
                active_model = m.get("name") or m.get("model")
                if active_model:
                    req_data = json.dumps({"model": active_model, "keep_alive": 0}).encode("utf-8")
                    req = urllib.request.Request(
                        f"{ollama_url}/api/generate",
                        data=req_data,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=5):
                        pass
    except Exception:
        pass

    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        if hasattr(torch.cuda, "ipc_collect"):
            try:
                torch.cuda.ipc_collect()
            except Exception:
                pass

    time.sleep(0.5)


class TrendDataIngestor:
    """
    Responsável exclusivo por carregar os dados brutos (CSV), realizar chunking,
    tratar metadados e persistir os embeddings no banco vetorial ChromaDB.
    """
    def __init__(self, csv_path: str, persist_directory: str = "./chroma_db", nrows: Optional[int] = 100):
        self.csv_path = csv_path
        self.persist_directory = persist_directory
        self.nrows = nrows
        
        self.device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="neuralmind/bert-base-portuguese-cased",
            model_kwargs={'device': self.device_type}, 
            encode_kwargs={'normalize_embeddings': False}
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        
    def load_and_index(self):
        print(f"[Ingestor] Hardware detectado para processamento: {self.device_type.upper()}")
        print(f"[Ingestor] Carregando os dados do CSV: {self.csv_path} (amostra: {self.nrows or 'tudo'})...")
        
        try:
            df = pd.read_csv(self.csv_path, encoding='utf-8', nrows=self.nrows) 
        except UnicodeDecodeError:
            df = pd.read_csv(self.csv_path, encoding='latin1', nrows=self.nrows) 
            
        df = df.fillna('')
            
        docs = []
        colunas_texto = [
            'transcricaoVideo', 'transcription', 
            'descricaoVideo', 'descricao', 
            'resumo', 'textoVideo', 'texto', 
            'postagem', 'text', 'content'
        ]

        for index, row in df.iterrows():
            partes_conteudo = []

            for col in colunas_texto:
                val = str(row.get(col, '')).strip()
                if val and val.upper() != "NULL" and val.lower() != "nan":
                    partes_conteudo.append(f"Conteúdo: {val}")
                    break
                    
            musica = str(row.get('nomeMusica', '')).strip()
            autor_musica = str(row.get('autorMusica', '')).strip()
            if musica and musica.upper() != "NULL" and musica.lower() != "nan":
                info_musica = f"Música: {musica}"
                if autor_musica and autor_musica.upper() != "NULL" and autor_musica.lower() != "nan":
                    info_musica += f" ({autor_musica})"
                partes_conteudo.append(info_musica)

            topico = str(row.get('topico_principal', '')).strip()
            if topico and topico.upper() != "NULL" and topico.lower() != "nan":
                partes_conteudo.append(f"Tópico: {topico}")

            hashtags = str(row.get('hashtags_postagem', row.get('hashtags_topico_principal', row.get('hashtags', '')))).strip()
            if hashtags and hashtags.upper() != "NULL" and hashtags.lower() != "nan":
                partes_conteudo.append(f"Hashtags: {hashtags}")

            if partes_conteudo:
                text_content = "\n".join(partes_conteudo)
            else: 
                text_content = " ".join([str(val) for val in row.values if str(val).strip() and str(val).strip() != "NULL"])

            video_id = str(row.get('IDPostagem', row.get('IDPostagemFonte', row.get('video_id', f'video_{index}'))))
            upload_date = str(row.get('dataPublicacao', row.get('upload_date', row.get('data', 'N/A'))))
            
            raw_plays = row.get('plays_da_ultima_coleta', row.get('plays_mais_recente', row.get('play_count', 0)))
            try:
                play_count = int(raw_plays)
            except (ValueError, TypeError):
                try:
                    play_count = int(float(raw_plays))
                except (ValueError, TypeError):
                    play_count = 0
            
            doc = Document(
                page_content=text_content,
                metadata={
                    "video_id": str(video_id),
                    "hashtags": str(hashtags), 
                    "upload_date": str(upload_date),
                    "play_count": play_count
                }
            )
            docs.append(doc)
            
        print("[Ingestor] Realizando chunking dos documentos...")
        splits = self.text_splitter.split_documents(docs)
        
        print(f"[Ingestor] Salvando no ChromaDB (usando {self.device_type.upper()})...")
        vectorstore = Chroma.from_documents(
            documents=splits, 
            embedding=self.embeddings, 
            persist_directory=self.persist_directory
        )
        
        if hasattr(vectorstore, "persist") and callable(getattr(vectorstore, "persist")):
            try:
                vectorstore.persist()
            except Exception:
                pass

        print("[Ingestor] Indexação concluída com sucesso!")
        return vectorstore


class TrendRetriever:
    """
    Responsável exclusivo pela conexão com o ChromaDB e pela busca semântica,
    mantendo a base vetorial isolada da lógica de orquestração do LLM.
    """
    def __init__(self, persist_directory: str = "./chroma_db", embeddings: Optional[HuggingFaceEmbeddings] = None):
        self.device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.persist_directory = persist_directory
        
        if embeddings:
            self.embeddings = embeddings
        else:
            self.embeddings = HuggingFaceEmbeddings(
                model_name="neuralmind/bert-base-portuguese-cased",
                model_kwargs={'device': self.device_type},
                encode_kwargs={'normalize_embeddings': False}
            )
        self.vectorstore = Chroma(
            persist_directory=self.persist_directory, 
            embedding_function=self.embeddings
        )
        
    def get_retriever(self, k: int = 6, hashtag_filter: Optional[str] = None):
        """
        Retorna o retriever configurado com MMR (Maximal Marginal Relevance)
        para garantir que os chunks recuperados sejam diversos e não repitam o mesmo vídeo.
        """
        search_kwargs: Dict[str, Any] = {"k": k, "fetch_k": 25}
        if hashtag_filter:
            search_kwargs["filter"] = {"hashtags": {"$contains": hashtag_filter}}
            return self.vectorstore.as_retriever(search_kwargs=search_kwargs)
            
        return self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs
        )


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
        base_url: str = "http://localhost:11434", 
        temperature: float = 0.2,
        keep_alive: str = "0"
    ):
        self.retriever = retriever
        self.base_url = base_url
        self.temperature = temperature
        self.keep_alive = keep_alive
        
        self.model_name = model_name
        self.chat_history: List[str] = []
        
        self.prompt_template = """Você é o TrendBot-BR, um assistente analítico especializado em tendências do TikTok no Brasil.

REGRAS OBRIGATÓRIAS DE RESPOSTA:
1. Direto ao Ponto:
   - NUNCA repita ou parafraseie a pergunta do usuário (evite completamente frases como "Aqui vai a resposta para sua pergunta...").
   - NUNCA se apresente novamente nem dê saudações repetitivas (não diga "Olá! Sou o TrendBot-BR...").
   - NUNCA adicione frases clichês de despedida ao final (ex: "Se precisar de mais informações, estou aqui para ajudar").
   - Comece IMEDIATAMENTE respondendo à pergunta com os dados e a análise.

2. Factualidade Estrita (Sem Alucinações):
   - Responda EXCLUSIVAMENTE com base no "Contexto recuperado dos vídeos".
   - NUNCA invente criadores, hashtags, músicas ou métricas que não estejam no contexto.
   - Se os vídeos do contexto não trouxerem dados sobre o que foi perguntado, diga diretamente: "Com base no corpus atual de vídeos indexados, não foram encontradas informações suficientes sobre esse tópico."

3. Síntese Analítica e Evidências:
   - Destaque padrões observados: formatos visuais (POV, vlog, transições rápidas, legendas sobrepostas), tom do conteúdo (humor, informativo, etc.) e assuntos centrais.
   - Sempre que disponíveis no contexto, cite exemplos concretos: @criadores, #hashtags e músicas.
   - Organize a resposta de forma limpa e estruturada (use parágrafos curtos ou tópicos objetivos).

4. Idioma: Português do Brasil claro, correto e coeso.

Histórico recente:
{chat_history}

Contexto recuperado dos vídeos:
{context}

Pergunta: {question}

Resposta analítica direta:"""
        
        self.prompt = PromptTemplate.from_template(self.prompt_template)
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
        Alterna dinamicamente o modelo do bot liberando a VRAM da GPU RTX 4060 Ti
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


def menu_selecao_modelo() -> str:
    """Exibe o menu interativo inicial para escolha do modelo local."""
    print(" Escolha o modelo local para esta sessão:")
    print(" -------------------------------------------------------------")
    for key, (nome, desc) in MODELOS_PADRAO.items():
        marcador = " [PADRÃO]" if key == "1" else ""
        print(f" [{key}] {nome:<10} - {desc}{marcador}")
    print(" -------------------------------------------------------------")

    escolha = input(" Digite o número da opção (Pressione Enter para [1] llama3): ").strip()
    
    if escolha in MODELOS_PADRAO:
        modelo_selecionado = MODELOS_PADRAO[escolha][0]
    else:
        modelo_selecionado = "llama3"

    print(f"\n🚀 Modelo ativo selecionado: [{modelo_selecionado.upper()}]\n")
    return modelo_selecionado


# ==========================================
# Execução Principal do Chatbot Interativo
# ==========================================
if __name__ == "__main__":
    print("\n" + "="*65)
    print("       TRENDBOT-BR - ASSISTENTE INTELIGENTE DO TIKTOK        ")
    print("="*65 + "\n")
    
    csv_path = "postagens_tiktok.csv"
    db_dir = "./chroma_db"

    # 1. Ingestão Inteligente: indexa apenas se o banco ChromaDB não existir
    if not os.path.exists(db_dir) or not os.listdir(db_dir):
        if not os.path.exists(csv_path):
            print(f"❌ Arquivo {csv_path} não encontrado. Certifique-se de que ele está na mesma pasta do script.")
            exit()

        print("[Setup] Criando base vetorial a partir do CSV...")
        ingestor = TrendDataIngestor(csv_path=csv_path, persist_directory=db_dir, nrows=100)
        ingestor.load_and_index()
    else:
        print(f"[Setup] Banco vetorial detectado em '{db_dir}'. Inicializando...")

    # 2. Configura a busca semântica
    retriever_system = TrendRetriever(persist_directory=db_dir)
    retriever = retriever_system.get_retriever(k=4) 

    # 3. Menu Interativo de Seleção do Modelo Inicial
    modelo_inicial = menu_selecao_modelo()

    # 4. Inicia o Bot
    bot = TrendBot(retriever=retriever, model_name=modelo_inicial, keep_alive="0")

    # 5. Loop do Chat Interativo
    print("="*65)
    print(f" TrendBot-BR Online com [{bot.model_name.upper()}]!")
    print(" Digite sua pergunta ou 'sair' para encerrar.")
    print("="*65 + "\n")
    
    while True:
        try:
            prompt_str = f"Você [{bot.model_name}]: "
            user_input = input(prompt_str).strip()

            if not user_input:
                continue

            if user_input.lower() in ['sair', 'exit', 'quit']:
                print(f"\nTrendBot-BR: Falou, valeu pelo papo! Nos vemos na FY. 👋\n")
                limpar_memoria_gpu(bot.model_name)
                break

            print(f"TrendBot-BR [{bot.model_name}] (Pesquisando as trends...)")
            response = bot.ask(user_input)
            print(f"\nTrendBot-BR [{bot.model_name}]:\n{response}\n")
            
        except KeyboardInterrupt:
            print("\nEncerrando o chat...")
            limpar_memoria_gpu(bot.model_name)
            break
        except Exception as e:
            print(f"\n❌ Erro durante a execução: {e}\n")