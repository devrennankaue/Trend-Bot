#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para garantir imports consistentes
DIRETORIO_RAIZ = Path(__file__).resolve().parent
if str(DIRETORIO_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIRETORIO_RAIZ))

from src import (
    TrendBot,
    TrendRetriever,
    TrendDataIngestor,
    limpar_memoria_gpu,
    MODELOS_PADRAO,
    resolver_caminho_csv,
    resolver_caminho_db,
    DEFAULT_CHROMA_DIR,
    DEFAULT_CSV_PATH
)


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


def main():
    print("\n" + "="*65)
    print("       TRENDBOT-BR - ASSISTENTE INTELIGENTE DO TIKTOK        ")
    print("="*65 + "\n")
    
    csv_path = resolver_caminho_csv()
    db_dir = resolver_caminho_db()

    # 1. Ingestão Inteligente: indexa apenas se a base ChromaDB não existir
    if not os.path.exists(db_dir) or not os.listdir(db_dir):
        if not os.path.exists(csv_path):
            print(f"❌ Arquivo de dados não encontrado em '{csv_path}'.")
            print(f"💡 Dica: Adicione 'postagens_tiktok.csv' na pasta 'data/raw/' ou na raiz.")
            sys.exit(1)

        print(f"[Setup] Criando base vetorial a partir de '{csv_path}'...")
        ingestor = TrendDataIngestor(csv_path=csv_path, persist_directory=DEFAULT_CHROMA_DIR, nrows=100)
        ingestor.load_and_index()
        db_dir = DEFAULT_CHROMA_DIR
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
    print(" Comandos úteis:")
    print("   - 'sair', 'exit' ou 'quit' : Encerra a conversa")
    print("   - '/modelo'                : Troca o modelo ativo durante o chat")
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

            if user_input.lower() in ['/modelo', '/model', '/trocar']:
                novo_modelo = menu_selecao_modelo()
                bot.trocar_modelo(novo_modelo)
                continue

            print(f"TrendBot-BR [{bot.model_name}] (Pesquisando as trends...)")
            response = bot.ask(user_input)
            print(f"\nTrendBot-BR [{bot.model_name}]:\n{response}\n")
            
        except KeyboardInterrupt:
            print("\nEncerrando o chat...")
            limpar_memoria_gpu(bot.model_name)
            break
        except Exception as e:
            print(f"\n❌ Erro durante a execução: {e}\n")


if __name__ == "__main__":
    main()
