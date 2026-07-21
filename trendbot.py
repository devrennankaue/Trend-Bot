import os
import pandas as pd
from typing import List, Dict, Any

# LangChain Imports
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class TrendDataIngestor:
    """
    Responsável por carregar o CSV, realizar o chunking dos textos e salvar no banco de vetores com os metadados.
    """
    def __init__(self, csv_path: str, persist_directory: str = "./chroma_db"):
        self.csv_path = csv_path
        self.persist_directory = persist_directory
        
        # 1. Definindo o modelo de embedding BERTimbau via HuggingFace
        self.embeddings = HuggingFaceEmbeddings(
            model_name="neuralmind/bert-base-portuguese-cased",
            model_kwargs={'device': 'cpu'}, 
            encode_kwargs={'normalize_embeddings': False}
        )
        
        # 2. Configurando o splitter para o chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        
    def load_and_index(self):
        print(f"[Ingestor] Carregando os dados do CSV: {self.csv_path}...")
        
        try:
            df = pd.read_csv(self.csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(self.csv_path, encoding='latin1')
            
        df = df.fillna('')
            
        docs = []
        for index, row in df.iterrows():
            text_content = ""
            for col in ['transcription', 'descricao', 'texto', 'text', 'content', 'resumo']:
                if col in df.columns:
                    text_content = str(row[col])
                    break
                    
            if not text_content: 
                 text_content = " ".join([str(val) for val in row.values if str(val).strip()])

            video_id = row.get('video_id', row.get('id', f'video_{index}'))
            hashtags = row.get('hashtags', '')
            upload_date = row.get('upload_date', row.get('data', 'N/A'))
            play_count = row.get('play_count', row.get('views', 0))
            
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
    def __init__(self, persist_directory: str = "./chroma_db"):
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
            search_kwargs["filter"] = {"hashtags": {"$contains": hashtag_filter}}
            
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)


class TrendBot:
    """
    Integra o retriever, o prompt customizado e o Llama-3 para gerar a resposta.
    """
    def __init__(self, retriever):
        self.retriever = retriever
        
        # Integrando com Llama-3-8B-Instruct via Ollama
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
        
        # Montagem da pipeline RAG usando sintaxe LCEL
        self.chain = (
            {"context": self.retriever, "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        
    def ask(self, question: str) -> str:
        return self.chain.invoke(question)


# ==========================================
# Execução Principal com Arquivos Reais
# ==========================================
if __name__ == "__main__":
    print("\n--- INICIANDO SISTEMA TRENDBOT-BR COM DADOS REAIS ---")
    
    csv_path = "postagens_tiktok.csv"
    txt_path = "perguntas.txt"

    if not os.path.exists(csv_path):
        print(f"❌ Arquivo {csv_path} não encontrado. Certifique-se de que ele está na mesma pasta.")
        exit()

    # 1. Faz a ingestão do CSV
    ingestor = TrendDataIngestor(csv_path=csv_path)
    # IMPORTANTE: Você pode comentar a linha abaixo (adicionar um # no início) 
    # nas próximas execuções para não recriar o banco de dados toda vez.
    ingestor.load_and_index()

    # 2. Configura a busca
    retriever_system = TrendRetriever()
    retriever = retriever_system.get_retriever(k=4) 
    
    # 3. Inicia o Bot
    bot = TrendBot(retriever=retriever)
    
    # 4. Lê e processa as perguntas do arquivo txt
    if os.path.exists(txt_path):
        print(f"\nLendo perguntas do arquivo {txt_path}...")
        with open(txt_path, 'r', encoding='utf-8') as f:
            perguntas = f.readlines()
            
        for linha in perguntas:
            pergunta = linha.strip()
            if pergunta:  
                print(f"\n{'='*60}")
                print(f"🗣️  Pergunta: {pergunta}")
                print(f"{'='*60}")
                print("TrendBot-BR (Pensando...)\n")
                
                try:
                    resposta = bot.ask(pergunta)
                    print(f"🤖 Resposta:\n{resposta}\n")
                except Exception as e:
                    print(f"❌ Erro ao processar pergunta: {e}\n")
    else:
        print(f"❌ Arquivo {txt_path} não encontrado.")
        print("\nIniciando chat interativo em vez disso...\n")
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