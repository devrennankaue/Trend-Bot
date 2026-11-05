#!/usr/bin/env python3
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

# Adiciona a raiz do projeto ao sys.path para garantir imports consistentes
DIRETORIO_RAIZ = Path(__file__).resolve().parent
if str(DIRETORIO_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIRETORIO_RAIZ))

from src import (
    TrendBot,
    TrendRetriever,
    TrendDataIngestor,
    limpar_memoria_gpu,
    checar_conexao_ollama,
    resolver_caminho_csv,
    resolver_caminho_db
)
from src.corpus_metrics import CorpusMetrics


def main():
    print("\n" + "="*65)
    print("       TRENDBOT-BR - ASSISTENTE INTELIGENTE DO TIKTOK        ")
    print("="*65 + "\n")
    
    csv_path = str(DIRETORIO_RAIZ / "data" / "corpus_pesquisa_5000.csv")
    db_dir = resolver_caminho_db()

    # 1. Indexa apenas o corpus selecionado e auditado.
    index_path = os.path.join(db_dir, "indice_ollama.sqlite")
    if not os.path.exists(index_path) or not TrendRetriever.index_complete(db_dir):
        if not os.path.exists(csv_path):
            print(f"Corpus selecionado não encontrado em '{csv_path}'.")
            print("Execute scripts/preparar_corpus.ps1 antes de iniciar o TrendBot.")
            sys.exit(1)

        print(f"[Setup] Criando base vetorial a partir de '{csv_path}'...")
        ingestor = TrendDataIngestor(csv_path=csv_path, persist_directory=db_dir, nrows=None)
        ingestor.load_and_index()
    else:
        print(f"[Setup] Banco vetorial detectado em '{db_dir}'. Inicializando...")

    # 2. Configura a busca semântica
    retriever_system = TrendRetriever(persist_directory=db_dir)
    retriever = retriever_system.get_retriever(k=4) 

    # 3. Verificação de Conectividade com o Ollama
    if not checar_conexao_ollama():
        print("⚠️  Aviso: O serviço do Ollama não está ativo em http://localhost:11434.")
        print("💡 Para iniciar o Ollama no Windows:")
        print("   - Abra o aplicativo 'Ollama' pelo Menu Iniciar, OU")
        print("   - Em um terminal, execute: ollama serve\n")

    # 4. Inicia o bot com o único modelo configurado
    bot = TrendBot(retriever=retriever, keep_alive="0", metrics=CorpusMetrics(csv_path))

    # 6. Loop do Chat Interativo
    print("="*65)
    print(f" TrendBot-BR Online com [{bot.model_name.upper()}]!")
    print(" Comandos úteis:")
    print("   - 'sair', 'exit' ou 'quit' : Encerra a conversa")
    print("="*65 + "\n")
    
    while True:
        try:
            prompt_str = f"Você [{bot.model_name}]: "
            user_input = input(prompt_str).strip()

            if not user_input:
                continue

            if user_input.lower() in ['sair', 'exit', 'quit']:
                print("\nTrendBot-BR: Falou, valeu pelo papo! Nos vemos na FY.\n")
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
            msg = str(e)
            if "10061" in msg or "Failed to establish a new connection" in msg or "Connection refused" in msg:
                print(f"\n❌ Erro de conexão com o Ollama: O serviço não está respondendo em http://localhost:11434.")
                print("💡 Certifique-se de que o Ollama está rodando (`ollama serve` ou abra o app Ollama).\n")
            else:
                print(f"\n❌ Erro durante a execução: {e}\n")


if __name__ == "__main__":
    main()
