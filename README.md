# 📊 TrendBot-BR — Assistente Inteligente de Tendências do TikTok

**TrendBot-BR** é um assistente analítico baseado em **RAG (Retrieval-Augmented Generation)** projetado para analisar e responder a perguntas sobre tendências, áudios virais, hashtags, criadores e formatos de conteúdo do TikTok no Brasil.

O sistema opera com **modelos de linguagem locais (LLMs)** executados via [Ollama](https://ollama.ai/), garantindo privacidade, baixo custo e controle sobre a inferência, além de gerenciamento proativo de memória VRAM (GPU) e RAM.

---

## 🏗️ Arquitetura do Projeto

```
Trend-Bot/
├── benchmark/                      # Módulo de avaliação técnica e benchmarks
│   ├── benchmark.py                # Script de execução de testes de inferência e hardware
│   ├── perguntas_teste.json        # Perguntas de validação técnica padronizadas
│   └── reports/                    # Relatórios estruturados em Markdown (.md)
│
├── data/                           # Armazenamento de dados e bases vetoriais
│   ├── raw/                        # Dados brutos (ex: postagens_tiktok.csv)
│   ├── chroma_db/                  # Banco vetorial persistido pelo ChromaDB
│   └── perguntas.txt               # Banco temático de perguntas para testes
│
├── docs/                           # Documentação e relatórios do projeto
│   ├── assets/                     # Diagramas e recursos visuais
│   │   └── trendbot_arquitetura_rag.png
│   ├── Métricas técnicas de avaliação.pdf
│   ├── projeto.docx
│   └── trendbot_exemplo_fluxo_rag.pdf
│
├── src/                            # Código-fonte modularizado
│   ├── __init__.py                 # Exportação do pacote
│   ├── bot.py                      # Orquestrador TrendBot (LCEL + histórico + prompt)
│   ├── config.py                   # Configurações globais, paths e prompts
│   ├── ingestor.py                 # Pipeline de ETL, chunking e indexação vetorial
│   ├── memory.py                   # Gestão de VRAM GPU (NVIDIA) e RAM do sistema
│   └── retriever.py                # Recuperação semântica com MMR (Maximal Marginal Relevance)
│
├── .gitignore                      # Regras de exclusão do Git
├── main.py                         # Ponto de entrada da CLI interativa
├── requirements.txt                # Dependências do ecossistema Python
└── README.md                       # Documentação principal
```

---

## ⚙️ Pré-requisitos

1. **Python 3.10+**
2. **[Ollama](https://ollama.ai/)** instalado e em execução no endereço padrão `http://localhost:11434`.
3. **Modelos locais do Ollama** baixados:
   ```bash
   ollama pull llama3
   ollama pull mistral
   ollama pull gemma:7b
   ```
4. *(Opcional, recomendado)*: GPU NVIDIA com suporte a CUDA para aceleração de embeddings e inferência.

---

## 🚀 Instalação e Configuração

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/devrennankaue/Trend-Bot.git
   cd Trend-Bot
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python3 -m venv meu_ambiente
   source meu_ambiente/bin/activate   # Linux/macOS
   # ou meu_ambiente\Scripts\activate # Windows
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Prepare os dados:**
   - Coloque o arquivo de postagens em `data/raw/postagens_tiktok.csv`.
   - Na primeira execução, o sistema criará automaticamente a base vetorial em `data/chroma_db/`.

---

## 💻 Como Usar

### 1. Iniciar o Chatbot Interativo
Execute o ponto de entrada principal:
```bash
python main.py
```

**Funcionalidades no chat:**
- **Menu interativo** de escolha do LLM na inicialização (`llama3`, `mistral`, `gemma:7b`).
- **`/modelo`**: Alterne o modelo ativo a qualquer momento no meio da conversa sem perder o histórico recente.
- **`sair`**, **`exit`** ou **`quit`**: Encerra a sessão liberando a VRAM da GPU.

### 2. Executar o Benchmark Técnico
Para medir tempo de inferência, uso de RAM/VRAM, taxa de sucesso e gerar relatórios estruturados em Markdown:
```bash
python benchmark/benchmark.py
```

Os resultados serão gravados em:
* `benchmark/reports/benchmark_report_YYYYMMDD_HHMMSS.md` (relatório individual estruturado com histórico imutável)
* `benchmark/reports/latest.md` (atalho para a última execução)

---

## 🧠 Detalhes Técnicos

- **Modelo de Embeddings:** `neuralmind/bert-base-portuguese-cased` (BERTimbau), calibrado para semântica do português brasileiro.
- **Banco Vetorial:** `ChromaDB` persistido localmente.
- **Estratégia de Recuperação:** `MMR` (*Maximal Marginal Relevance*) com $k=4$ e $\text{fetch\_k}=25$, evitando redundância de vídeos na mesma resposta.
- **Gerenciamento de VRAM:** Descarregamento forçado de modelos do Ollama (`keep_alive: 0`), limpeza de cache PyTorch (`torch.cuda.empty_cache()`) e coleta de lixo Python (`gc.collect()`).
