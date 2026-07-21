import os
import torch
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
    Responsável por carregar o CSV, realizar o chunking dos textos e salvar no banco de vetores.
    """
    def __init__(self, csv_path: str, persist_directory: str = "./chroma_db"):
        self.csv_path = csv_path
        self.persist_directory = persist_directory
        
        # Detecção Inteligente: Roda na Placa de Vídeo (CUDA) ou Processador (CPU)
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
        print(f"[Ingestor] Carregando os dados do CSV: {self.csv_path}...")
        
        # Lendo as 100 primeiras linhas para teste (remover nrows=100 depois para ler tudo)
        try:
            df = pd.read_csv(self.csv_path, encoding='utf-8', nrows=100) 
        except UnicodeDecodeError:
            df = pd.read_csv(self.csv_path, encoding='latin1', nrows=100) 
            
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
        
        print(f"[Ingestor] Salvando no ChromaDB (usando {self.device_type.upper()})...")
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
        self.device_type = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name="neuralmind/bert-base-portuguese-cased",
            model_kwargs={'device': self.device_type} 
        )
        self.vectorstore = Chroma(
            persist_directory=persist_directory, 
            embedding_function=self.embeddings
        )
        
    def get_retriever(self, k: int = 4, hashtag_filter: str = None):
        search_kwargs = {"k": k}
        if hashtag_filter:
            search_kwargs["filter"] = {"hashtags": {"$contains": hashtag_filter}}
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)


class TrendBot:
    """
    Integra o retriever, o prompt customizado e o Llama-3 com Memória de Conversa!
    """
    def __init__(self, retriever):
        self.retriever = retriever
        self.llm = Ollama(model="llama3") 
        
        self.chat_history = []
        
        self.prompt_template = """Você é o TrendBot-BR, um assistente AI focado nas tendências do TikTok no Brasil.
Seu tom é jovem e descontraído, mas você é um analista SÉRIO de dados.

Regra de Ouro Inquebrável: 
1. Responda APENAS com base no "Contexto recuperado". 
2. Se a resposta exata para a pergunta não estiver no contexto, diga APENAS "Não encontrei essa informação na minha base de dados". 
3. NUNCA tente compensar oferecendo informações sobre outros assuntos que estão no contexto, mas que não foram perguntados pelo usuário.
4. NUNCA invente fatos, nomes ou misture assuntos.
5. Responda sempre em Português do Brasil.

Histórico da nossa conversa recente:
{chat_history}

Contexto recuperado dos vídeos:
{context}

Pergunta atual do usuário: {question}

Resposta(TrendBot-BR):"""
        
        self.prompt = PromptTemplate.from_template(self.prompt_template)
        
        # AQUI ESTAVA O PROBLEMA: A chain precisa receber o chat_history explicitamente
        self.chain = (
            {
                "context": lambda x: "\n".join([doc.page_content for doc in self.retriever.invoke(x["question"])]),
                "question": lambda x: x["question"],
                "chat_history": lambda x: x["chat_history"]
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
        
    def ask(self, question: str) -> str:
        # Se não houver histórico, manda uma string vazia
        history_str = "\n".join(self.chat_history[-4:]) if self.chat_history else "Nenhuma conversa anterior."
        
        # O método invoke agora envia um dicionário com a pergunta e o histórico
        resposta = self.chain.invoke({
            "question": question, 
            "chat_history": history_str
        })
        
        self.chat_history.append(f"Usuário: {question}")
        self.chat_history.append(f"TrendBot: {resposta}")
        
        return resposta

# ==========================================
# Execução Principal com Dados Reais
# ==========================================
if __name__ == "__main__":
    print("\n--- INICIANDO SISTEMA TRENDBOT-BR COM DADOS REAIS ---")
    
    csv_path = "postagens_tiktok.csv"

    if not os.path.exists(csv_path):
        print(f"❌ Arquivo {csv_path} não encontrado. Certifique-se de que ele está na mesma pasta do script.")
        exit()

    # 1. Faz a ingestão do CSV
    ingestor = TrendDataIngestor(csv_path=csv_path)
    # DICA: Comente a linha abaixo com um '#' se o ChromaDB já estiver gerado, 
    # para não recriar a base toda vez que ligar o bot.
    ingestor.load_and_index()

    # 2. Configura a busca
    retriever_system = TrendRetriever()
    retriever = retriever_system.get_retriever(k=4) 
    
    # 3. Inicia o Bot
    bot = TrendBot(retriever=retriever)
    
    # 4. Loop do Chat Interativo
    print("\n" + "="*60)
    print(" TrendBot-BR Online! (Digite 'sair' para encerrar) ")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input("Você: ")
            if user_input.lower() in ['sair', 'exit', 'quit']:
                print("\nTrendBot-BR: Falou, valeu pelo papo! Nos vemos na FY. 👋\n")
                break
                
            print("TrendBot-BR (Pesquisando as trends...)")
            response = bot.ask(user_input)
            print(f"\nTrendBot-BR:\n{response}\n")
            
        except KeyboardInterrupt:
            print("\nEncerrando o loop.")
            break
        except Exception as e:
            print(f"\nOops, sistema crashou. Erro: {e}\n")