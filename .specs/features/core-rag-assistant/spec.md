# Core RAG Assistant Specification

## Problem Statement

Analisar grandes volumes de dados de postagens e tendências do TikTok no Brasil exige um assistente analítico capaz de responder perguntas factuais (criadores, hashtags, músicas e formatos) sem alucinações. O TrendBot-BR resolve essa necessidade operando de forma 100% local com LLMs via Ollama, garantindo baixo custo, privacidade de dados e gestão eficiente de memória de hardware (GPU VRAM / RAM).

## Goals

- [ ] Prover um assistente conversacional RAG com busca semântica MMR e embeddings calibrados para português brasileiro (BERTimbau).
- [ ] Permitir alternância dinâmica de modelos locais em tempo real com liberação de VRAM.
- [ ] Garantir ingestão automatizada e resiliente de dados tabulares (CSV) no ChromaDB.
- [ ] Fornecer módulo automatizado de benchmark para mensurar tempo de inferência, uso de memória e exportação para CSV.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| ------- | ------ |
| Interface gráfica Web / Frontend | O escopo do core é restrito à CLI interativa e biblioteca Python modular |
| Treinamento e Fine-Tuning de LLMs | O sistema utiliza LLMs pré-treinados via Ollama para inferência direta |
| Coleta em tempo real via Scraping | A ingestão opera sobre bases de dados CSV já exportadas |
| Integração com provedores de nuvem pagos (OpenAI/Anthropic) | A arquitetura do core é estritamente voltada a modelos locais |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Endpoint padrão do Ollama | `http://localhost:11434` | Padrão da instalação local do servidor Ollama | y |
| Tamanho de chunk e overlap | 500 caracteres / 50 de overlap | Otimizado para legendas e descrições curtas de vídeos do TikTok | y |
| Quantidade de documentos recuperados (k) | k=4 com fetch_k=25 via MMR | Maximiza a diversidade de vídeos sem saturar a janela de contexto do LLM | y |
| Modelo de embeddings padrão | `neuralmind/bert-base-portuguese-cased` | Calibrado especificamente para a sintaxe e semântica do português do Brasil | y |
| Política de keep_alive do Ollama | `keep_alive: 0` | Garante descarregamento imediato da VRAM ao trocar de modelo ou finalizar sessão | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: RAG Query & Grounded Analysis ⭐ MVP

**User Story**: As a content strategist, I want to ask questions about Brazilian TikTok trends so that I receive factual answers based strictly on indexed video data.

**Why P1**: É a função essencial do sistema (responder perguntas sobre tendências baseando-se no corpus).

**Acceptance Criteria**:

1. WHEN the user submits a question about TikTok trends THEN the system SHALL retrieve relevant video context using MMR (k=4) and generate an analytical factual response in Brazilian Portuguese.
2. IF no relevant information is found in the indexed corpus THEN the system SHALL output "Com base no corpus atual de vídeos indexados, não foram encontradas informações suficientes sobre esse tópico."
3. WHILE answering user questions the system SHALL maintain recent conversation history and format responses without repeating the question or adding polite clichés.
4. The system SHALL restrict factual assertions strictly to the retrieved context to prevent hallucinations.

**Independent Test**: Executar `python main.py`, fazer perguntas sobre músicas e hashtags presentes no CSV e validar que a resposta cita os dados reais sem inventar informações.

---

### P2: Dynamic Model Switching & VRAM Management

**User Story**: As a researcher running on limited hardware, I want to switch between different local LLMs on the fly so that I can compare responses without running out of GPU memory.

**Why P2**: Permite comparar modelos (LLaMA 3, Mistral, Gemma 7b) dinamicamente sem reiniciar a aplicação ou causar Out-Of-Memory (OOM).

**Acceptance Criteria**:

1. WHEN the user executes '/modelo' during the interactive session THEN the system SHALL display the model selection menu and switch the active LLM without losing recent chat history.
2. WHEN a model switch or session exit occurs THEN the system SHALL unload Ollama models from VRAM via keep_alive=0 and clear PyTorch CUDA tensor caches.
3. The system SHALL support LLaMA 3, Mistral, and Gemma 7b as standard selectable local models.

**Independent Test**: Iniciar chat com LLaMA 3, digitar `/modelo`, trocar para Mistral e verificar no `nvidia-smi` que a VRAM foi desalocada antes do novo modelo subir.

---

### P3: Automated Ingestion & Vector Indexing

**User Story**: As a developer, I want the system to automatically build the vector database from a CSV file so that I do not need manual database setup.

**Why P3**: Assegura inicialização "plug-and-play" do banco vetorial ChromaDB com fallback automático de paths.

**Acceptance Criteria**:

1. WHEN the application starts and the ChromaDB vectorstore does not exist THEN the system SHALL load postagens_tiktok.csv, generate 500-char chunks with 50-char overlap, and index embeddings with BERTimbau.
2. IF the input CSV file is missing during first-time setup THEN the system SHALL display a descriptive error message and exit with non-zero status code.

**Independent Test**: Excluir a pasta `data/chroma_db/`, executar `python main.py` e verificar a criação automática da base vetorial a partir de `data/raw/postagens_tiktok.csv`.

---

### P4: Benchmark Execution & Metrics Export

**User Story**: As an evaluator, I want to run standardized benchmarks across multiple models so that I can compare inference latency, memory usage, and export results for human evaluation.

**Why P4**: Provê rigor técnico e métricas empíricas para a escolha do melhor modelo local para cada cenário.

**Acceptance Criteria**:

1. WHEN the benchmark script is executed THEN the system SHALL run standardized test questions across configured models, measure inference time and RAM/VRAM consumption, and export results to CSV with blank columns for human rating.

**Independent Test**: Executar `python benchmark/benchmark.py` e verificar a geração do arquivo `benchmark/resultados_benchmark.csv` com métricas completas.

---

## Edge Cases

- IF the user enters an empty prompt THEN the system SHALL ignore the empty input and prompt again without error.
- IF Ollama is not running or unreachable at the configured URL THEN the system SHALL report the connection error gracefully without crashing the process unhandled.
- WHEN a question does not match any indexed documents with sufficient relevance THEN the system SHALL declare insufficient context rather than hallucinating answers.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| CORE-01 | P1: RAG Query & Grounded Analysis | Design | Verified |
| CORE-02 | P1: RAG Query & Grounded Analysis | Design | Verified |
| CORE-03 | P1: RAG Query & Grounded Analysis | Design | Verified |
| CORE-04 | P2: Dynamic Model Switching & VRAM Management | Design | Verified |
| CORE-05 | P2: Dynamic Model Switching & VRAM Management | Design | Verified |
| CORE-06 | P3: Automated Ingestion & Vector Indexing | Design | Verified |
| CORE-07 | P3: Automated Ingestion & Vector Indexing | Design | Verified |
| CORE-08 | P4: Benchmark Execution & Metrics Export | Design | Verified |

**Coverage:** 8 total, 8 mapped to tasks/components, 0 unmapped

---

## Success Criteria

- [ ] Respostas do RAG fundamentadas exclusivamente nos chunks retornados pelo ChromaDB.
- [ ] Alternância entre modelos executada em tempo real com consumo estável de VRAM.
- [ ] Ingestão de CSV executada com sucesso criando coleções no ChromaDB com BERTimbau.
- [ ] Exportação de benchmark gerando arquivo CSV com latência e uso de memória estruturados.
