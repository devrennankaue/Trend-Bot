# TrendBot-BR — Project Context & Architecture

Documento mestre de contexto, arquitetura e governança técnica do **TrendBot-BR** para o fluxo **TLC Spec-Driven Development**.

---

## 1. Visão Geral do Projeto

**TrendBot-BR** é um assistente analítico inteligente baseado em **RAG (Retrieval-Augmented Generation)** focado na análise de dados, tendências, áudios virais, hashtags, criadores e formatos de conteúdo do **TikTok no Brasil**.

### Objetivos Centrais
- **Inferência 100% Local**: Privacidade estrita de dados e custo zero por requisição utilizando LLMs executados via Ollama local.
- **Calibração Semântica para Português (Brasil)**: Indexação semântica de alta precisão através do modelo de embeddings BERTimbau (`neuralmind/bert-base-portuguese-cased`).
- **Recuperação Diversificada e Não-Redundante**: Busca semântica com Relevância Marginal Máxima (MMR) para evitar a concentração de respostas em múltiplos trechos do mesmo vídeo.
- **Gestão Proativa de Recursos de Hardware**: Monitoramento e liberação dinâmica de VRAM (NVIDIA GPU) e RAM entre trocas de modelos e execuções de benchmarks.
- **Avaliação Técnica e Benchmarking**: Suite integrada para medição de latência, consumo de memória, estabilidade e fidelidade das respostas entre múltiplos LLMs.

---

## 2. Stack Tecnológica e Decisões de Arquitetura

| Camada | Tecnologia / Padrão | Justificativa Técnica |
| :--- | :--- | :--- |
| **Linguagem** | Python 3.10+ | Ecossistema padrão de IA/ML e processamento de dados. |
| **Orquestração RAG** | LangChain / LCEL (*LangChain Expression Language*) | Chains declarativas, streaming, composição modular e desacoplamento de componentes. |
| **Modelos de Linguagem (LLM)** | Ollama (`llama3`, `mistral`, `gemma:7b`) | Execução local, troca dinâmica no runtime e controle de ciclo de vida (`keep_alive: 0`). |
| **Embeddings** | HuggingFace / BERTimbau (`neuralmind/bert-base-portuguese-cased`) | Embeddings de 768 dimensões com calibração semântica superior para o vocabulário e sintaxe do Português Brasileiro. |
| **Banco Vetorial** | ChromaDB (persistência local em disco) | Base vetorial serverless, leve, integrada ao LangChain e sem dependência de serviços em nuvem. |
| **Estratégia de Busca** | MMR (*Maximal Marginal Relevance*) | Balanceia similaridade semântica ($k=4$) com diversidade de conteúdo ($\text{fetch\_k}=25$). |
| **Processamento de Dados** | Pandas + `RecursiveCharacterTextSplitter` | ETL resiliente com chunking de 500 caracteres e overlap de 50 caracteres. |
| **Gestão de Hardware** | `nvidia-smi` + PyTorch CUDA API + `/proc/meminfo` / Win32 API | Telemetria contínua de VRAM/RAM e descarregamento forçado de modelos para prevenir OOM (*Out Of Memory*). |

---

## 3. Registro de Decisões Arquiteturais (ADRs)

Decisões de nível de projeto registradas em [`.specs/STATE.md`](file:///home/renan/LSI/Trend-Bot/.specs/STATE.md):

- **AD-001 (LLMs Locais via Ollama)**: Uso exclusivo de LLMs locais com `keep_alive: 0` para garantir privacidade e liberação imediata de VRAM.
- **AD-002 (BERTimbau + ChromaDB)**: Embeddings especializados em PT-BR persistidos em disco local sem dependência de nuvem.
- **AD-003 (Recuperação MMR com k=4 e fetch_k=25)**: Eliminação de chunks redundantes do mesmo vídeo no prompt do modelo.
- **AD-004 (Pipeline de Ingestão Resiliente)**: Normalização automática de esquemas de CSV de TikTok com metadados estruturados (`video_id`, `hashtags`, `upload_date`, `play_count`).
- **AD-005 (Gestão Ativa de VRAM/RAM)**: Coleta de métricas de hardware e rotinas de descarte de tensores/processos na GPU em trocas de modelo e benchmarks.

---

## 4. Estrutura do Repositório e Módulos

```
Trend-Bot/
├── .specs/                           # Memória e governança do TLC Spec-Driven
│   ├── STATE.md                      # Log de decisões (AD-NNN) e snapshot de Handoff
│   ├── LESSONS.md                    # Playbook de lições aprendidas (gerado por script)
│   ├── lessons.json                  # Estado canônico de lições aprendidas
│   └── features/                     # Especificações de features por pasta
│       └── core-rag-assistant/       # Feature core do assistente RAG
│           ├── spec.md               # Requisitos e critérios de aceitação em EARS
│           ├── design.md             # Arquitetura e componentes técnicos
│           └── validation.md         # Relatório de validação e evidências do Verifier
│
├── benchmark/                        # Módulo de avaliação comparativa
│   ├── benchmark.py                  # Execução de testes de inferência, latência e hardware
│   ├── perguntas_teste.json          # Perguntas padrão de teste técnico
│   └── reports/                      # Relatórios estruturados em Markdown (.md)
│
├── data/                             # Armazenamento de dados
│   ├── raw/                          # CSVs de postagens brutas (ex: postagens_tiktok.csv)
│   ├── chroma_db/                    # Diretório persistido do banco vetorial ChromaDB
│   └── perguntas.txt                 # Lista de perguntas temáticas para testes manuais
│
├── docs/                             # Documentação técnica e relatórios
│   ├── assets/                       # Diagramas de arquitetura e fluxo
│   ├── Métricas técnicas de avaliação.pdf
│   ├── projeto.docx
│   └── trendbot_exemplo_fluxo_rag.pdf
│
├── src/                              # Código-fonte modularizado
│   ├── __init__.py                   # Exportação do pacote
│   ├── bot.py                        # Orquestrador TrendBot (LCEL + histórico + prompt)
│   ├── config.py                     # Constantes globais, caminhos, templates e fallbacks
│   ├── ingestor.py                   # Ingestão de CSV, chunking e indexação no ChromaDB
│   ├── memory.py                     # Telemetria e limpeza de VRAM (NVIDIA) e RAM
│   └── retriever.py                  # Conexão com ChromaDB e busca semântica MMR
│
├── main.py                           # CLI interativa principal com menu e troca de modelo
├── tests/                            # Testes unitários e de integração
├── requirements.txt                  # Dependências do projeto
├── README.md                         # Documentação pública de apresentação
└── PROJECT.md                        # Contexto mestre do projeto (este arquivo)
```

---

## 5. Fluxo de Desenvolvimento: TLC Spec-Driven

O projeto adota a metodologia **TLC Spec-Driven Development** para qualquer nova funcionalidade ou refatoração:

```
┌──────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐
│ SPECIFY  │ → │  DESIGN  │ → │  TASKS  │ → │ EXECUTE │
└──────────┘   └──────────┘   └─────────┘   └─────────┘
```

### 1. Fase Specify (`spec.md`)
- Requisitos rastreáveis (`[FEAT]-NN`).
- Critérios de aceitação formatados na notação **EARS** (*Easy Approach to Requirements Syntax*):
  - **Ubiquitous**: `The system SHALL [response]`
  - **Event-driven**: `WHEN [trigger] THEN the system SHALL [response]`
  - **State-driven**: `WHILE [state] the system SHALL [response]`
  - **Optional**: `WHERE [feature] the system SHALL [response]`
  - **Unwanted-behavior**: `IF [error] THEN the system SHALL [response]`
- Portão de fechamento obrigatório antes da aprovação via `scripts/validate_spec.py`.

### 2. Fase Design (`design.md`)
- Verificação de conformidade com decisões ativas em [`.specs/STATE.md`](file:///home/renan/LSI/Trend-Bot/.specs/STATE.md).
- Definição de interfaces, reutilização de código existente e mapeamento de riscos/mitigações.

### 3. Fase Tasks (`tasks.md`)
- Divisão em tarefas atômicas e sequenciais.
- Cada tarefa deve conter arquivo-alvo, testes e critério de passagem (*Gate*).
- Validação estrutural via `scripts/validate_tasks.py`.

### 4. Fase Execute e Verifier
- **Commits Atômicos**: 1 commit por tarefa com padrão Conventional Commits verificado por `scripts/check_commit.py`.
- **Integridade dos Testes**: Testes derivam dos critérios da especificação e nunca são enfraquecidos ou pulados.
- **Verifier Independente**: Ao concluir as tarefas, o Verifier executa a validação formal gerando `validation.md` com evidências `file:line`, aprovado via `scripts/validate_state.py`.
- **Destilação de Lições**: Falhas identificadas são registradas via `scripts/lessons.py` para alimentar [`.specs/LESSONS.md`](file:///home/renan/LSI/Trend-Bot/.specs/LESSONS.md).

---

## 6. Comandos e Operação

### Execução da Aplicação
```bash
# Iniciar o chatbot interativo
python main.py

# Executar benchmark comparativo entre modelos
python benchmark/benchmark.py
```

### Validações Spec-Driven (a partir do diretório do skill)
```bash
# Validar estrutura de uma especificação
python3 .agents/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/core-rag-assistant/spec.md

# Validar tarefas
python3 .agents/skills/tlc-spec-driven/scripts/validate_tasks.py .specs/features/core-rag-assistant/tasks.md

# Validar mensagem de commit
python3 .agents/skills/tlc-spec-driven/scripts/check_commit.py --message "feat(retriever): add hashtag filter to MMR search"

# Validar fechamento da feature (Verifier PASS com evidências)
python3 .agents/skills/tlc-spec-driven/scripts/validate_state.py core-rag-assistant
```
