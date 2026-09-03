import os
import sys
import time
import json
import csv
import ctypes
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

# Adiciona o diretório raiz ao path para importar as classes do trendbot
DIRETORIO_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if DIRETORIO_RAIZ not in sys.path:
    sys.path.insert(0, DIRETORIO_RAIZ)

from trendbot import TrendRetriever, TrendBot, limpar_memoria_gpu


def obter_metricas_memoria() -> Dict[str, float]:
    """Retorna o consumo atual de RAM do sistema e VRAM da GPU NVIDIA em GB."""
    ram_usada_gb = 0.0
    ram_total_gb = 0.0
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        ram_usada_gb = round((stat.ullTotalPhys - stat.ullAvailPhys) / (1024**3), 2)
        ram_total_gb = round(stat.ullTotalPhys / (1024**3), 2)
    except Exception:
        pass

    vram_usada_mb = 0.0
    vram_total_mb = 0.0
    try:
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            encoding="utf-8",
            startupinfo=startupinfo
        )
        parts = out.strip().split(",")
        if len(parts) == 2:
            vram_usada_mb = float(parts[0].strip())
            vram_total_mb = float(parts[1].strip())
    except Exception:
        pass

    return {
        "ram_usada_gb": ram_usada_gb,
        "ram_total_gb": ram_total_gb,
        "vram_usada_gb": round(vram_usada_mb / 1024, 2),
        "vram_total_gb": round(vram_total_mb / 1024, 2)
    }


def carregar_perguntas_teste(arquivo_perguntas: str = "perguntas_teste.json") -> List[str]:
    """Carrega a lista de perguntas fixas do arquivo JSON."""
    caminho = os.path.join(os.path.dirname(__file__), arquivo_perguntas)
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao ler '{arquivo_perguntas}': {e}. Usando perguntas padrão.")
    
    return [
        "Quais são as principais músicas e áudios em alta nos vídeos?",
        "Qual é o vídeo com o maior número de visualizações registrado?",
        "Quais são as hashtags mais frequentes associadas aos conteúdos?",
        "Qual a capital da França?"  # Pergunta controle fora do escopo
    ]


def exportar_para_csv(resultados: List[Dict[str, Any]], arquivo_csv: str = "resultados_benchmark.csv"):
    """
    Exporta os dados técnicos e respostas para uma planilha CSV,
    incluindo colunas de consumo de memória RAM/VRAM e colunas em branco para avaliação humana.
    """
    caminho_csv = os.path.join(os.path.dirname(__file__), arquivo_csv)
    colunas = [
        "Data_Hora",
        "Modelo",
        "Pergunta",
        "Resposta_Gerada",
        "Contexto_Recuperado",
        "Tempo_Inferência_Segundos",
        "RAM_Usada_GB",
        "VRAM_GPU_GB",
        "Qtd_Palavras",
        "Qtd_Caracteres",
        "Avaliacao_Humana_Fidelidade (1-5)",
        "Avaliacao_Humana_Eficacia (1-5)",
        "Observacoes_Humano"
    ]

    linhas_existentes = []
    if os.path.exists(caminho_csv):
        try:
            with open(caminho_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    row.setdefault("RAM_Usada_GB", "N/A")
                    row.setdefault("VRAM_GPU_GB", "N/A")
                    linhas_existentes.append(row)
        except Exception:
            linhas_existentes = []

    for r in resultados:
        linhas_existentes.append({
            "Data_Hora": r.get("timestamp", ""),
            "Modelo": r.get("modelo", ""),
            "Pergunta": r.get("pergunta", ""),
            "Resposta_Gerada": r.get("resposta", ""),
            "Contexto_Recuperado": r.get("contexto", ""),
            "Tempo_Inferência_Segundos": r.get("tempo_segundos", ""),
            "RAM_Usada_GB": r.get("ram_usada_gb", ""),
            "VRAM_GPU_GB": r.get("vram_usada_gb", ""),
            "Qtd_Palavras": r.get("qtd_palavras", ""),
            "Qtd_Caracteres": r.get("qtd_caracteres", ""),
            "Avaliacao_Humana_Fidelidade (1-5)": "",
            "Avaliacao_Humana_Eficacia (1-5)": "",
            "Observacoes_Humano": ""
        })

    with open(caminho_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=colunas, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas_existentes)

    print(f"💾 Dados exportados com sucesso para: {caminho_csv}")
    print("📋 Dica: Abra o CSV no Excel/Google Sheets para realizar a avaliação humana de fidelidade e eficácia.")


def executar_benchmark_tecnico(
    modelos: List[str],
    caminho_db: str = "./chroma_db",
    k_retrieval: int = 4
):
    """
    Executa testes técnicos de performance de inferência, recuperação vetorial e
    consumo de memória RAM e VRAM nos modelos locais, com gestão de VRAM da GPU.
    """
    caminho_absoluto_db = os.path.abspath(os.path.join(DIRETORIO_RAIZ, caminho_db))
    
    if not os.path.exists(caminho_absoluto_db):
        print(f"❌ Banco vetorial não encontrado em '{caminho_absoluto_db}'. Execute o trendbot.py primeiro.")
        return

    perguntas = carregar_perguntas_teste()
    print("\n" + "="*70)
    print("      BENCHMARK TÉCNICO DE HARDWARE E RAG (TRENDBOT-BR)       ")
    print("="*70)
    print(f"📁 Banco Vetorial: {caminho_absoluto_db}")
    print(f"📋 Total de Perguntas de Validação: {len(perguntas)}")
    print(f"🤖 Modelos Selecionados: {', '.join(modelos)}")
    print("="*70 + "\n")

    retriever_system = TrendRetriever(persist_directory=caminho_absoluto_db)
    retriever = retriever_system.get_retriever(k=k_retrieval)

    todos_resultados = []
    resumo_modelos = []

    for modelo in modelos:
        print(f"\n" + "-"*70)
        print(f"⚙️ Testando Modelo: [{modelo.upper()}]")
        print("-"*70)

        # 1. Limpeza de VRAM preventiva na RTX 4060 Ti
        limpar_memoria_gpu()
        
        bot = TrendBot(retriever=retriever, model_name=modelo, keep_alive="0")
        tempos = []
        palavras = []
        rams = []
        vrams = []
        sucessos = 0

        for idx, pergunta in enumerate(perguntas, 1):
            print(f"\n[Q{idx}/{len(perguntas)}] Pergunta: \"{pergunta}\"")
            
            # Medição exata do tempo de inferência
            inicio = time.time()
            try:
                resposta = bot.ask(pergunta)
                tempo_gasto = round(time.time() - inicio, 2)
                sucessos += 1
                status = "OK"
            except Exception as e:
                resposta = f"Erro: {e}"
                tempo_gasto = 0.0
                status = "Erro"

            # Coleta métricas de consumo de memória em tempo real
            mem = obter_metricas_memoria()
            rams.append(mem["ram_usada_gb"])
            vrams.append(mem["vram_usada_gb"])

            # Coleta do contexto recuperado para conferência humana
            try:
                docs = retriever.invoke(pergunta)
                contexto_str = "\n\n---\n\n".join(d.page_content for d in docs)
            except Exception:
                contexto_str = "Erro ao recuperar contexto."

            qtd_palavras = len(resposta.split())
            qtd_caracteres = len(resposta)

            tempos.append(tempo_gasto)
            palavras.append(qtd_palavras)

            print(f"   ⏱️ Tempo: {tempo_gasto}s | 🧠 RAM: {mem['ram_usada_gb']} GB | 🎮 VRAM GPU: {mem['vram_usada_gb']} GB | 📏 {qtd_palavras} palavras ({qtd_caracteres} carac.) | Status: {status}")
            print(f"   💬 Resposta ({modelo}): {resposta[:130]}...")

            todos_resultados.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "modelo": modelo,
                "pergunta": pergunta,
                "resposta": resposta,
                "contexto": contexto_str,
                "tempo_segundos": tempo_gasto,
                "ram_usada_gb": mem["ram_usada_gb"],
                "vram_usada_gb": mem["vram_usada_gb"],
                "qtd_palavras": qtd_palavras,
                "qtd_caracteres": qtd_caracteres
            })

        # 2. Liberação de VRAM após o modelo
        limpar_memoria_gpu(model_name=modelo)

        # Métricas agregadas do modelo
        tempo_medio = round(sum(tempos) / len(tempos), 2) if tempos else 0.0
        tempo_min = min(tempos) if tempos else 0.0
        tempo_max = max(tempos) if tempos else 0.0
        media_palavras = round(sum(palavras) / len(palavras), 1) if palavras else 0.0
        ram_media = round(sum(rams) / len(rams), 2) if rams else 0.0
        vram_pico = max(vrams) if vrams else 0.0

        resumo_modelos.append({
            "modelo": modelo,
            "tempo_medio": tempo_medio,
            "tempo_min": tempo_min,
            "tempo_max": tempo_max,
            "media_palavras": media_palavras,
            "ram_media": ram_media,
            "vram_pico": vram_pico,
            "taxa_sucesso": f"{sucessos}/{len(perguntas)}"
        })

    # Tabela Resumo no Terminal
    print("\n" + "="*80)
    print("           RESUMO CONSOLIDADO DE PERFORMANCE TÉCNICA E MEMÓRIA           ")
    print("="*80)
    print(f"{'Modelo':<12} | {'Tempo Médio':<12} | {'VRAM Pico':<11} | {'RAM Média':<11} | {'Média Palavras':<14} | {'Sucesso'}")
    print("-"*80)
    for res in resumo_modelos:
        print(f"{res['modelo']:<12} | {res['tempo_medio']:>5.2f}s       | {res['vram_pico']:>5.2f} GB    | {res['ram_media']:>5.2f} GB   | {res['media_palavras']:>6.1f}         | {res['taxa_sucesso']}")
    print("="*80 + "\n")

    # Exportação dos resultados em CSV para avaliação humana
    exportar_para_csv(todos_resultados)


if __name__ == "__main__":
    print("\n" + "="*65)
    print("          PAINEL DE BENCHMARK TÉCNICO - TRENDBOT-BR          ")
    print("="*65 + "\n")
    print("Iniciando avaliação comparativa completa em todos os modelos:")
    print("  • Meta LLaMA 3 (8B)")
    print("  • Mistral (7B)")
    print("  • Gemma (7B)")
    print("-------------------------------------------------------------")

    modelos_alvo = ["llama3", "mistral", "gemma:7b"]
    executar_benchmark_tecnico(modelos=modelos_alvo)
