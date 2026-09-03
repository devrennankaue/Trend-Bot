# Benchmark Markdown Reports Specification

## Problem Statement

Atualmente, o módulo de benchmark do TrendBot-BR exporta os resultados consolidados apenas para um arquivo CSV (`benchmark/resultados_benchmark.csv`). Embora útil para análise tabular, o formato CSV dificulta a leitura humana direta, a auditoria qualitativa das respostas geradas pelo LLM em conjunto com os chunks de contexto RAG recuperados, e a rastreabilidade histórica visual de cada bateria de testes executada. É necessário gerar relatórios individuais e estruturados em formato Markdown (`.md`) a cada execução de benchmark, contendo metadados de hardware, tabelas comparativas consolidadas, detalhamento por pergunta/resposta com contexto colapsável e espaço para anotações humanas.

## Goals

- [ ] Gerar automaticamente um arquivo de log Markdown (`.md`) com timestamp único a cada execução de benchmark em `benchmark/reports/`.
- [ ] Incluir metadados completos do ambiente de execução (hardware detectado, VRAM/RAM, versão Ollama, parâmetros RAG e embeddings).
- [ ] Apresentar tabela comparativa de performance (latência média/mín/máx, throughput estimado, pico de VRAM, RAM média e taxa de sucesso).
- [ ] Detalhar cada iteração de pergunta/resposta por modelo, exibindo o contexto recuperado do ChromaDB de forma colapsável (`<details>`) e campos de avaliação humana (fidelidade e eficácia).
- [ ] Manter um arquivo de índice `benchmark/reports/latest.md` (ou link simbólico/atalho) apontando para o relatório mais recente.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| ------- | ------ |
| Dashboard Web Interativo (HTML/React) | Os relatórios devem ser gerados em Markdown estático versionável no repositório |
| Avaliação automática por LLM-as-a-Judge | Avaliação de fidelidade/eficácia neste escopo permanece manual/humana no template gerado |
| Envio de relatórios para endpoints externos ou Webhooks | Armazenamento exclusivamente local no sistema de arquivos |
| Modificação do algoritmo central de RAG no bot | O foco da feature é puramente telemetria, estruturação de métricas e exportação de logs do benchmark |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here - nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Diretório padrão de saída | `benchmark/reports/` | Isola relatórios da raiz do módulo `benchmark/` e evita poluição de arquivos | y |
| Padrão de nomenclatura de arquivos | `benchmark_report_YYYYMMDD_HHMMSS.md` | Garante ordenação cronológica natural e previne sobrescrita de logs anteriores | y |
| Contexto RAG colapsável | Tags HTML `<details><summary>` | Melhora a legibilidade do relatório sem poluir visualmente a visualização principal | y |
| Manutenção do CSV legado | Exportação simultânea para CSV e Markdown | Garante retrocompatibilidade para quem usa planilhas sem quebrar fluxos existentes | y |
| Atualização de link do último relatório | Atualização automática de `benchmark/reports/latest.md` | Facilita acesso imediato ao relatório mais recente sem precisar inspecionar timestamps | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Automated Markdown Benchmark Report Generation ⭐ MVP

**User Story**: As a machine learning engineer, I want a complete Markdown report generated automatically after each benchmark execution so that I can inspect model outputs, hardware usage, and RAG context in a clean, human-readable format.

**Why P1**: É o núcleo da funcionalidade solicitada, transformando os dados brutos de execução em um artefato estruturado e legível.

**Acceptance Criteria**:

1. WHEN a benchmark run completes THEN the system SHALL create a timestamped Markdown report file in `benchmark/reports/benchmark_report_YYYYMMDD_HHMMSS.md`.
2. The system SHALL include execution metadata comprising start/end timestamps, duration, host hardware specs (CPU, RAM, GPU VRAM), Ollama endpoint, embedding model name, and RAG parameters (k, fetch_k).
3. The system SHALL generate a consolidated summary table comparing all evaluated models across average latency, min/max latency, peak VRAM, average RAM, word count, and success rate.
4. The system SHALL output a detailed section for each model containing every tested question, execution status, technical metrics, generated LLM response, retrieved RAG context in `<details>` blocks, and blank fields for human evaluation (fidelity 1-5, effectiveness 1-5, observations).
5. The system SHALL write the identical content of the newest report to `benchmark/reports/latest.md` to serve as an instant reference.
6. IF the `benchmark/reports/` directory does not exist WHEN exporting logs THEN the system SHALL create the target directory automatically.

**Independent Test**: Executar `python benchmark/benchmark.py` e validar a criação de `benchmark/reports/benchmark_report_<timestamp>.md` e `benchmark/reports/latest.md` contendo todas as seções, tabelas e dados das perguntas.

---

### P2: Automated Highlights & Performance Badging

**User Story**: As an evaluator, I want the Markdown log to highlight the best performing models across different dimensions (speed, memory efficiency, completeness) so that I can quickly draw conclusions without manually parsing the table.

**Why P2**: Fornece síntese imediata de insights analíticos no topo do relatório para tomada de decisão ágil.

**Acceptance Criteria**:

1. WHEN compiling the summary section THEN the system SHALL compute and highlight key takeaways including fastest model (lowest average latency), most memory-efficient model (lowest peak VRAM/RAM), and highest throughput model (words per second).
2. IF a model fails on one or more test questions THEN the system SHALL flag the failure count prominently in the highlights and summary table with warning indicators.

**Independent Test**: Executar benchmark com 2 ou mais modelos e verificar no Markdown gerado a presença da seção "Destaques e Recomendações" com os badges calculados corretamente.

---

## Edge Cases

- IF an LLM call throws an exception or times out THEN the system SHALL log the exact error traceback in the question's detail block and record the status as ERROR without stopping subsequent model benchmarks.
- IF GPU VRAM telemetry is unavailable (e.g., CPU-only environment or no NVIDIA GPU) THEN the system SHALL record "N/A (CPU-only)" in the hardware metadata and metrics tables without throwing an exception.
- IF retrieved context from ChromaDB is empty or fails during vector query THEN the system SHALL output "Nenhum contexto recuperado" in the details block.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| BMD-01 | P1: Automated Markdown Benchmark Report Generation | Execute | Verified |
| BMD-02 | P1: Automated Markdown Benchmark Report Generation | Execute | Verified |
| BMD-03 | P1: Automated Markdown Benchmark Report Generation | Execute | Verified |
| BMD-04 | P1: Automated Markdown Benchmark Report Generation | Execute | Verified |
| BMD-05 | P1: Automated Markdown Benchmark Report Generation | Execute | Verified |
| BMD-06 | P1: Automated Markdown Benchmark Report Generation | Execute | Verified |
| BMD-07 | P2: Automated Highlights & Performance Badging | Execute | Verified |
| BMD-08 | P2: Automated Highlights & Performance Badging | Execute | Verified |

**Coverage:** 8 total, 8 mapped to user stories, 0 unmapped

---

## Success Criteria

- [x] Todo benchmark executado gera um arquivo `.md` correspondente e atualiza `latest.md` sem intervenção manual.
- [x] O relatório em Markdown é renderizado perfeitamente no GitHub, VS Code e visualizadores Markdown padrão.
- [x] O arquivo CSV (`resultados_benchmark.csv`) continua sendo gerado normalmente em paralelo.
- [x] Contexto de cada pergunta é inspecionável individualmente via blocos colapsáveis sem poluir o documento.
