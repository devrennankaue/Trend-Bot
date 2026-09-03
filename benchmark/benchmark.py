import os
import sys
import time
import json
import platform
from datetime import datetime
from typing import List, Dict, Any, Optional

# Adiciona o diretório raiz ao path para importar o módulo src
DIRETORIO_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if DIRETORIO_RAIZ not in sys.path:
    sys.path.insert(0, DIRETORIO_RAIZ)

from src.config import (
    resolver_caminho_db,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_KEEP_ALIVE
)
from src.memory import (
    limpar_memoria_gpu,
    obter_metricas_memoria
)


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


def formatar_cabecalho_markdown(metadados: Dict[str, Any]) -> str:
    """Gera a seção de cabeçalho e metadados de hardware/RAG em Markdown."""
    data_inicio = metadados.get("data_inicio", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    duracao = metadados.get("duracao_total_segundos", 0.0)
    so = metadados.get("sistema_operacional", platform.system())
    gpu = metadados.get("gpu_info", "N/A (CPU-only)")
    ram_total = metadados.get("ram_total_gb", "N/A")
    ram_str = f"{ram_total} GB" if isinstance(ram_total, (int, float)) and ram_total > 0 else str(ram_total)
    
    ollama_url = metadados.get("ollama_url", DEFAULT_OLLAMA_URL)
    embedding = metadados.get("modelo_embedding", DEFAULT_EMBEDDING_MODEL)
    caminho_db = metadados.get("caminho_db", "data/chroma_db")
    k = metadados.get("k_retrieval", 4)
    fetch_k = metadados.get("fetch_k", 25)
    keep_alive = metadados.get("keep_alive", DEFAULT_KEEP_ALIVE)
    modelos_str = ", ".join(f"`{m}`" for m in metadados.get("modelos", []))

    linhas = [
        "# 📊 Relatório de Benchmark — TrendBot-BR",
        f"**Data da Execução:** {data_inicio}  ",
        f"**Duração Total:** {duracao}s  ",
        f"**Ambiente:** SO: {so} | GPU: {gpu} | RAM Total: {ram_str}  ",
        f"**Configurações RAG:** ChromaDB (MMR, k={k}, fetch_k={fetch_k}) | Embeddings: `{embedding}` | Ollama: `{ollama_url}` (`keep_alive: {keep_alive}`)  ",
        f"**Modelos Avaliados:** {modelos_str}  ",
        f"**Base Vetorial:** `{caminho_db}`",
        "\n---"
    ]
    return "\n".join(linhas)


def formatar_resumo_e_destaques_markdown(resumo_modelos: List[Dict[str, Any]]) -> str:
    """Gera o resumo consolidado em tabela e calcula os destaques de performance."""
    if not resumo_modelos:
        return "## 🏆 Resumo Consolidado de Performance\n\nNenhum dado de modelo disponível.\n"

    linhas = [
        "## 🏆 Resumo Consolidado de Performance",
        "",
        "| Modelo | Tempo Médio | Min / Máx | Throughput Est. | Pico VRAM | RAM Média | Taxa Sucesso |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    modelo_mais_rapido = None
    menor_tempo = float("inf")
    modelo_menor_vram = None
    menor_vram = float("inf")
    modelo_maior_throughput = None
    maior_throughput = 0.0
    erros_totais = 0

    for r in resumo_modelos:
        modelo = r.get("modelo", "")
        t_med = r.get("tempo_medio", 0.0)
        t_min = r.get("tempo_min", 0.0)
        t_max = r.get("tempo_max", 0.0)
        med_palavras = r.get("media_palavras", 0.0)
        ram_med = r.get("ram_media", 0.0)
        vram_pico = r.get("vram_pico", 0.0)
        sucesso = r.get("taxa_sucesso", "0/0")
        
        throughput = round(med_palavras / t_med, 1) if t_med > 0 else 0.0

        linhas.append(
            f"| **{modelo}** | {t_med:.2f}s | {t_min:.2f}s / {t_max:.2f}s | {throughput:.1f} pal/s | {vram_pico:.2f} GB | {ram_med:.2f} GB | {sucesso} |"
        )

        if t_med > 0 and t_med < menor_tempo:
            menor_tempo = t_med
            modelo_mais_rapido = modelo

        if vram_pico >= 0 and vram_pico < menor_vram:
            menor_vram = vram_pico
            modelo_menor_vram = modelo

        if throughput > maior_throughput:
            maior_throughput = throughput
            modelo_maior_throughput = modelo

        if "/" in sucesso:
            partes = sucesso.split("/")
            if len(partes) == 2:
                try:
                    s_count = int(partes[0])
                    t_count = int(partes[1])
                    if s_count < t_count:
                        erros_totais += (t_count - s_count)
                except ValueError:
                    pass

    linhas.extend([
        "",
        "### 💡 Destaques da Rodada"
    ])

    if modelo_mais_rapido:
        linhas.append(f"- 🚀 **Modelo Mais Rápido:** `{modelo_mais_rapido}` (Média de {menor_tempo:.2f}s por inferência)")
    if modelo_menor_vram:
        linhas.append(f"- 🧠 **Menor Consumo de VRAM:** `{modelo_menor_vram}` (Pico de {menor_vram:.2f} GB)")
    if modelo_maior_throughput:
        linhas.append(f"- ⚡ **Maior Throughput:** `{modelo_maior_throughput}` ({maior_throughput:.1f} palavras/segundo)")

    if erros_totais == 0:
        linhas.append("- 🎯 **Estabilidade:** 100% de sucesso nas perguntas avaliadas sem falhas de execução.")
    else:
        linhas.append(f"- ⚠️ **Atenção:** Foram detectadas {erros_totais} falhas durante a execução.")

    linhas.append("\n---")
    return "\n".join(linhas)


def formatar_detalhes_perguntas_markdown(
    modelos: List[str],
    todos_resultados: List[Dict[str, Any]]
) -> str:
    """Gera a seção detalhada por modelo e pergunta com blocos colapsáveis e campos de avaliação humana."""
    linhas = [
        "## 🔍 Detalhamento das Avaliações por Pergunta",
        ""
    ]

    for modelo in modelos:
        resultados_mod = [r for r in todos_resultados if r.get("modelo") == modelo]
        linhas.append(f"### 🤖 Modelo: `{modelo}`\n")

        for idx, r in enumerate(resultados_mod, 1):
            pergunta = r.get("pergunta", "")
            resposta = r.get("resposta", "")
            contexto = r.get("contexto", "Nenhum contexto recuperado.")
            tempo = r.get("tempo_segundos", 0.0)
            ram = r.get("ram_usada_gb", 0.0)
            vram = r.get("vram_usada_gb", 0.0)
            palavras = r.get("qtd_palavras", 0)
            caracteres = r.get("qtd_caracteres", 0)
            status = "✅ Sucesso" if not resposta.startswith("Erro:") else "❌ Erro"

            qtd_chunks = len(contexto.split("---")) if "---" in contexto else 1

            linhas.append(f"#### [Q{idx}/{len(resultados_mod)}] \"{pergunta}\"")
            linhas.append(f"- **Status:** {status}")
            linhas.append(f"- **Telemetria:** ⏱️ {tempo}s | 🧠 RAM: {ram} GB | 🎮 VRAM: {vram} GB | 📏 {palavras} palavras ({caracteres} caracteres)")
            linhas.append("")
            linhas.append("> **Resposta Gerada:**")
            for line in resposta.splitlines():
                linhas.append(f"> {line}" if line else ">")
            linhas.append("")
            linhas.append("<details>")
            linhas.append(f"<summary>📂 Ver Contexto RAG Recuperado ({qtd_chunks} Chunks)</summary>\n")
            linhas.append(f"```text\n{contexto.strip()}\n```")
            linhas.append("</details>")
            linhas.append("")
            linhas.append("**Avaliação Humana / Auditoria:**")
            linhas.append("- [ ] Fidelidade (1-5): `___`")
            linhas.append("- [ ] Eficácia (1-5): `___`")
            linhas.append("- [ ] Observações: `_____________________________________________`")
            linhas.append("")
            linhas.append("---")
            linhas.append("")

    return "\n".join(linhas)


def gerar_conteudo_markdown(
    metadados_execucao: Dict[str, Any],
    resumo_modelos: List[Dict[str, Any]],
    todos_resultados: List[Dict[str, Any]]
) -> str:
    """Monta o documento completo em Markdown a partir de todas as seções."""
    cabecalho = formatar_cabecalho_markdown(metadados_execucao)
    resumo = formatar_resumo_e_destaques_markdown(resumo_modelos)
    modelos = metadados_execucao.get("modelos", [])
    if not modelos:
        modelos = list(dict.fromkeys(r.get("modelo", "") for r in todos_resultados if r.get("modelo")))
    detalhes = formatar_detalhes_perguntas_markdown(modelos, todos_resultados)
    
    return f"{cabecalho}\n\n{resumo}\n\n{detalhes}"


def exportar_para_markdown(
    metadados_execucao: Dict[str, Any],
    resumo_modelos: List[Dict[str, Any]],
    todos_resultados: List[Dict[str, Any]],
    pasta_reports: str = "reports"
) -> str:
    """
    Gera o arquivo de log individual em Markdown com timestamp único em benchmark/reports/
    e atualiza a cópia do benchmark mais recente em latest.md.
    Garante que nenhum relatório anterior seja substituído.
    """
    if os.path.isabs(pasta_reports):
        caminho_pasta_reports = pasta_reports
    else:
        diretorio_modulo = os.path.dirname(__file__)
        caminho_pasta_reports = os.path.join(diretorio_modulo, pasta_reports)

    os.makedirs(caminho_pasta_reports, exist_ok=True)

    timestamp_arquivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"benchmark_report_{timestamp_arquivo}.md"
    caminho_relatorio = os.path.join(caminho_pasta_reports, nome_arquivo)
    caminho_latest = os.path.join(caminho_pasta_reports, "latest.md")

    conteudo_md = gerar_conteudo_markdown(metadados_execucao, resumo_modelos, todos_resultados)

    # 1. Salva o relatório com timestamp único (imutável)
    with open(caminho_relatorio, "w", encoding="utf-8") as f:
        f.write(conteudo_md)

    # 2. Atualiza o ponteiro latest.md
    with open(caminho_latest, "w", encoding="utf-8") as f:
        f.write(conteudo_md)

    print(f"📝 Relatório Markdown individual gerado: {caminho_relatorio}")
    print(f"📌 Relatório mais recente atualizado em: {caminho_latest}")
    return caminho_relatorio


def executar_benchmark_tecnico(
    modelos: List[str],
    caminho_db: Optional[str] = None,
    k_retrieval: int = 4
):
    """
    Executa testes técnicos de performance de inferência, recuperação vetorial e
    consumo de memória RAM e VRAM nos modelos locais, com gestão de VRAM da GPU.
    Gera exportações em CSV e relatórios estruturados individuais em Markdown (.md).
    """
    inicio_benchmark = time.time()
    data_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    caminho_db_resolvido = resolver_caminho_db(caminho_db)
    
    if not os.path.exists(caminho_db_resolvido) or not os.listdir(caminho_db_resolvido):
        print(f"❌ Banco vetorial não encontrado em '{caminho_db_resolvido}'. Execute o main.py primeiro.")
        return

    perguntas = carregar_perguntas_teste()
    print("\n" + "="*70)
    print("      BENCHMARK TÉCNICO DE HARDWARE E RAG (TRENDBOT-BR)       ")
    print("="*70)
    print(f"📁 Banco Vetorial: {caminho_db_resolvido}")
    print(f"📋 Total de Perguntas de Validação: {len(perguntas)}")
    print(f"🤖 Modelos Selecionados: {', '.join(modelos)}")
    print("="*70 + "\n")

    from src.retriever import TrendRetriever
    from src.bot import TrendBot

    retriever_system = TrendRetriever(persist_directory=caminho_db_resolvido)
    retriever = retriever_system.get_retriever(k=k_retrieval)

    todos_resultados = []
    resumo_modelos = []

    for modelo in modelos:
        print(f"\n" + "-"*70)
        print(f"⚙️ Testando Modelo: [{modelo.upper()}]")
        print("-"*70)

        # 1. Limpeza de VRAM preventiva na GPU
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

    duracao_total = round(time.time() - inicio_benchmark, 2)
    data_fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mem_final = obter_metricas_memoria()

    gpu_label = f"NVIDIA GPU ({mem_final['vram_total_gb']} GB VRAM)" if mem_final.get("vram_total_gb", 0) > 0 else "N/A (CPU-only)"

    metadados_execucao = {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "duracao_total_segundos": duracao_total,
        "gpu_info": gpu_label,
        "ram_total_gb": mem_final.get("ram_total_gb", 0.0),
        "sistema_operacional": platform.system(),
        "ollama_url": DEFAULT_OLLAMA_URL,
        "modelo_embedding": DEFAULT_EMBEDDING_MODEL,
        "caminho_db": caminho_db_resolvido,
        "k_retrieval": k_retrieval,
        "fetch_k": 25,
        "keep_alive": DEFAULT_KEEP_ALIVE,
        "total_perguntas": len(perguntas),
        "modelos": modelos
    }

    # Tabela Resumo no Terminal
    print("\n" + "="*80)
    print("           RESUMO CONSOLIDADO DE PERFORMANCE TÉCNICA E MEMÓRIA           ")
    print("="*80)
    print(f"{'Modelo':<12} | {'Tempo Médio':<12} | {'VRAM Pico':<11} | {'RAM Média':<11} | {'Média Palavras':<14} | {'Sucesso'}")
    print("-"*80)
    for res in resumo_modelos:
        print(f"{res['modelo']:<12} | {res['tempo_medio']:>5.2f}s       | {res['vram_pico']:>5.2f} GB    | {res['ram_media']:>5.2f} GB   | {res['media_palavras']:>6.1f}         | {res['taxa_sucesso']}")
    print("="*80 + "\n")

    # Exportação do relatório estruturado em Markdown com histórico permanente
    exportar_para_markdown(metadados_execucao, resumo_modelos, todos_resultados)


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
