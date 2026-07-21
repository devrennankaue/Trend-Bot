import json
import os
from typing import List, Dict, Any

# LangChain Imports
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

class TrendDataIngestor:
    """
    Responsável por carregar o JSON, realizar o chunking dos textos e salvar no banco de vetores com os metadados.
    """
    def _init_(self, json_path: str, persist_directory: str = "./chroma_db"):
        self.json_path = json_path
        self.persist_directory = persist_directory
        
        # 1. Definindo o modelo de embedding BERTimbau via HuggingFace
        self.embeddings = HuggingFaceEmbeddings(
            model_name="neuralmind/bert-base-portuguese-cased",
            model_kwargs={'device': 'cpu'}, # Mude para 'cuda' se tiver uma GPU dedicada
            encode_kwargs={'normalize_embeddings': False}
        )
        
        # 2. Configurando o splitter para o chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        
    def load_and_index(self):
        print("[Ingestor] Carregando os dados do JSON...")
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        docs = []
        for item in data:
            # Transformando as hashtags em uma string separada por vírgulas,
            # pois alguns vector stores lidam melhor com strings do que com listas
            hashtags_str = ", ".join(item.get('hashtags', []))
            
            doc = Document(
                page_content=item['transcription'],
                metadata={
                    "video_id": item['video_id'],
                    "hashtags": hashtags_str, 
                    "upload_date": item['upload_date'],
                    "play_count": item['play_count']
                }
            )
            docs.append(doc)
            
        print("[Ingestor] Realizando chunking dos documentos...")
        splits = self.text_splitter.split_documents(docs)
        
        print("[Ingestor] Salvando no ChromaDB...")
        vectorstore = Chroma.from_documents(
            documents=splits, 
            embedding=self.embeddings, 
            persist_directory=self.persist_directory
        )
        vectorstore.persist()
        print("[Ingestor] Indexação concluída com sucesso! 🚀")
        return vectorstore


class TrendRetriever:
    """
    Responsável por realizar a busca semântica baseada na query do usuário e nos metadados.
    """
    def _init_(self, persist_directory: str = "./chroma_db"):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="neuralmind/bert-base-portuguese-cased",
            model_kwargs={'device': 'cpu'}
        )
        # Carrega o banco de dados salvo
        self.vectorstore = Chroma(
            persist_directory=persist_directory, 
            embedding_function=self.embeddings
        )
        
    def get_retriever(self, k: int = 4, hashtag_filter: str = None):
        """
        Retorna o objeto retriever. 
        Implementa a busca "híbrida" (busca semântica com filtro de metadados).
        """
        search_kwargs = {"k": k}
        
        # Se uma hashtag foi providenciada, aplicamos o filtro no ChromaDB
        if hashtag_filter:
            # sintaxe de filtro do ChromaDB para substring ($contains)
            search_kwargs["filter"] = {"hashtags": {"$contains": hashtag_filter}}
            
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)


class TrendBot:
    """
    Integra o retriever, o prompt customizado e o Llama-3 para gerar a resposta.
    """
    def _init_(self, retriever):
        self.retriever = retriever
        
        # Integrando com Llama-3-8B-Instruct via Ollama
        # Certifique-se de que o modelo 'llama3' (ou 'llama3:8b') esteja baixado no Ollama rodando localmente
        self.llm = Ollama(model="llama3") 
        
        # Prompt de Sistema estruturado e com personalidade focada no TikTok BR
        self.prompt_template = """Você é o TrendBot-BR, um assistente AI especializado em analisar as grandes tendências do TikTok no Brasil.
Seu tom de voz deve ser sempre amigável, irreverente, autêntico, jovem e você deve estar por dentro da "internet culture". 
Use gírias brasileiras comuns do TikTok (ex: "tá flopado", "hitou", "entregou tudo", "trendzinha", "POV", "na fy") quando fizer sentido, mas sem forçar demais.
Sempre responda em português do Brasil (pt-BR).

Regra de ouro: Use APENAS o contexto fornecido abaixo para basear sua resposta. 
Se a informação não estiver no contexto, diga na lata e com bom humor que não encontrou nada sobre isso. (ex: "Putz cara, minha base de dados flopou nisso aí, não achei nada nas trends!").

Contexto recuperado dos vídeos:
{context}

Pergunta/Interação do usuário: {question}

Resposta(TrendBot-BR):"""
        
        self.prompt = PromptTemplate.from_template(self.prompt_template)
        
        # Montagem da pipeline RAG usando sintaxe LCEL (LangChain Expression Language)
        self.chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        
    def ask(self, question: str) -> str:
        return self.chain.invoke(question)


# ==========================================
# Exemplo de uso - Loop de Chat no Terminal
# ==========================================
if _name_ == "_main_":
    
    # Criando um arquivo JSON de exemplo temporário apenas para este script rodar a demonstração
    SAMPLE_JSON = "tiktok_trends_mock.json"
    if not os.path.exists(SAMPLE_JSON):
        sample_data = [
            {
                "video_id": "vid001",
                "transcription": "Gente, testei esse novo filtro de pó de café com base e, pelo amor de Deus, entregou tudo! A pele ficou de porcelana, me sigam para mais dicas de make.",
                "hashtags": ["makeup", "grwm", "dicas"],
                "upload_date": "2023-11-01",
                "play_count": 2500000
            },
            {
                "video_id": "vid002",
                "transcription": "POV: você é o funcionário que não entendeu o que o clente pediu e fica só concordando balançando a cabeça. Quem nunca passou por isso no trampo?",
                "hashtags": ["humor", "comedia", "pov", "clt"],
                "upload_date": "2023-11-02",
                "play_count": 800000
            }
        ]
        with open(SAMPLE_JSON, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f)
            
    print("\n--- INICIANDO SISTEMA TRENDBOT-BR ---")
    
    # 1. Faz a ingestão (idealmente rodaria apenas uma vez ou via cronjob)
    # ingestor = TrendDataIngestor(json_path=SAMPLE_JSON)
    # ingestor.load_and_index()
    
    # Para o exemplo rodar com fluidez a cada vez, vamos forçar a indexação na thread principal:
    ingestor = TrendDataIngestor(json_path=SAMPLE_JSON)
    ingestor.load_and_index()

    # 2. Configura a busca (com ou sem filtro de hashtag)
    retriever_system = TrendRetriever()
    
    # Você pode alterar get_retriever() para get_retriever(hashtag_filter="makeup") para testar os metadados!
    retriever = retriever_system.get_retriever(k=2) 
    
    # 3. Inicia a conversa com LLama 3
    bot = TrendBot(retriever=retriever)
    
    print("\n" + "="*60)
    print(" TrendBot-BR Online! 📱💃 (Digite 'sair' para encerrar) ")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input("Você: ")
            if user_input.lower() in ['sair', 'exit', 'quit']:
                print("\nTrendBot-BR: Falou, valeu pelo papo! Nos vemos na FY. 👋")
                break
                
            print("TrendBot-BR (Digitando...)")
            response = bot.ask(user_input)
            print(f"\nTrendBot-BR: {response}\n")
            
        except KeyboardInterrupt:
            print("\nEncerrando o loop.")
            break
        except Exception as e:
            print(f"\nOops, sistema crashou / Ollama não está rodando. Erro: {e}\n")