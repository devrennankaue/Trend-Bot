import time
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate

# IMPORTANTE: Substitua 'bot' pelo nome do seu arquivo original, se for diferente.
# Isso importa as suas classes prontas para usarmos aqui!
from bot import TrendRetriever, TrendBot 

class AvaliadorDeRAG:
    def __init__(self, modelo_juiz="llama3"):
        self.juiz = Ollama(model=modelo_juiz)
        
        self.prompt_avaliacao = PromptTemplate.from_template("""
        Você é um juiz imparcial avaliando um sistema de IA.
        Sua tarefa é dar uma nota de 1 a 5 para a resposta gerada, baseada em duas métricas:
        1. Fidelidade: A resposta usa APENAS a informação do Contexto? (Se inventar, nota baixa).
        2. Relevância: A resposta responde diretamente à Pergunta?

        Pergunta do Usuário: {pergunta}
        Contexto Recuperado: {contexto}
        Resposta Gerada: {resposta}

        Responda APENAS com um número de 1 a 5.
        """)
        
    def avaliar(self, pergunta: str, contexto: str, resposta: str) -> int:
        prompt_formatado = self.prompt_avaliacao.format(
            pergunta=pergunta, 
            contexto=contexto, 
            resposta=resposta
        )
        nota = self.juiz.invoke(prompt_formatado)
        try:
            return int(nota.strip())
        except ValueError:
            return 0 

def executar_teste_de_benchmark(bot, retriever):
    avaliador = AvaliadorDeRAG(modelo_juiz="llama3")
    
    # 📝 Coloque aqui perguntas que você SABE que estão no CSV
    perguntas_teste = [
        "Quais são as principais hashtags usadas?",
        "Qual é o vídeo com mais visualizações?",
        "Qual a capital do Brasil?" 
    ]
    
    resultados = []
    
    print("\n--- INICIANDO BENCHMARK DO TRENDBOT ---")
    for pergunta in perguntas_teste:
        print(f"Testando: '{pergunta}'...")
        
        inicio = time.time()
        
        # O Bot gera a resposta
        resposta = bot.ask(pergunta)
        tempo_resposta = time.time() - inicio
        
        # Pegamos o contexto para o Juiz poder comparar
        docs_recuperados = retriever.invoke(pergunta)
        contexto = "\n".join([doc.page_content for doc in docs_recuperados])
        
        # O Juiz dá a nota final
        nota = avaliador.avaliar(pergunta, contexto, resposta)
        
        resultados.append({
            "Pergunta": pergunta,
            "Nota": nota,
            "Tempo": round(tempo_resposta, 2)
        })
    
    print("\n" + "="*50)
    print(" RESULTADO FINAL DO TESTE ")
    print("="*50)
    
    media_notas = sum(r["Nota"] for r in resultados) / len(resultados)
    media_tempo = sum(r["Tempo"] for r in resultados) / len(resultados)
    
    for r in resultados:
        print(f"⭐ Nota: {r['Nota']}/5 | ⏱️ Tempo: {r['Tempo']}s | ❓ Pergunta: {r['Pergunta']}")
        
    print("-" * 50)
    print(f"📊 MÉDIA GERAL -> Nota: {media_notas:.1f}/5.0 | Latência: {media_tempo:.2f}s")
    print("="*50 + "\n")

# ==========================================
# Execução Isolada do Teste
# ==========================================
if __name__ == "__main__":
    # Inicia os seus sistemas silenciosamente
    print("Carregando o banco de dados...")
    retriever_system = TrendRetriever()
    retriever = retriever_system.get_retriever(k=4) 
    meu_bot = TrendBot(retriever=retriever)
    
    # Roda a avaliação
    executar_teste_de_benchmark(meu_bot, retriever)