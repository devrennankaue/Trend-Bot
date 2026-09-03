import warnings
from typing import Optional

try:
    import torch
except ImportError:
    torch = None
import pandas as pd

# Supressão de avisos de depreciação para saída limpa no terminal
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Imports modernos do ecossistema LangChain com fallback resiliente
try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:
    from langchain_community.embeddings import HuggingFaceEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from .config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    resolver_caminho_csv,
    resolver_caminho_db
)


class TrendDataIngestor:
    """
    Responsável exclusivo por carregar os dados brutos (CSV), realizar chunking,
    tratar metadados e persistir os embeddings no banco vetorial ChromaDB.
    """
    def __init__(
        self, 
        csv_path: Optional[str] = None, 
        persist_directory: Optional[str] = None, 
        nrows: Optional[int] = 100
    ):
        self.csv_path = resolver_caminho_csv(csv_path)
        self.persist_directory = resolver_caminho_db(persist_directory)
        self.nrows = nrows
        
        self.device_type = 'cuda' if torch is not None and torch.cuda.is_available() else 'cpu'
        
        self.embeddings = HuggingFaceEmbeddings(
            model_name=DEFAULT_EMBEDDING_MODEL,
            model_kwargs={'device': self.device_type}, 
            encode_kwargs={'normalize_embeddings': False}
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP
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
        
        print(f"[Ingestor] Salvando no ChromaDB em '{self.persist_directory}' (usando {self.device_type.upper()})...")
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
