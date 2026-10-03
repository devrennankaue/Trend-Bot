# STATE

## Decisions

### AD-001
- **Decision**: Utilização de modelos de linguagem locais (LLMs) executados via Ollama (Llama 3, Mistral, Gemma 7b) com parâmetro keep_alive configurado para 0.
- **Reason**: Garantir privacidade dos dados de análise, custo zero de inferência e capacidade de descarregar modelos da VRAM imediatamente após a execução ou troca de modelo.
- **Trade-off**: Requer hardware local compatível com inferência (GPU/CPU) e setup prévio do Ollama pelo usuário.
- **Scope**: Camada de inferência e orquestração do LLM (`src/bot.py`, `src/config.py`).
- **Date**: 2026-09-03
- **Status**: active

### AD-002
- **Decision**: Uso do modelo de embeddings BERTimbau (`neuralmind/bert-base-portuguese-cased`) com banco vetorial persistido localmente via ChromaDB.
- **Reason**: Calibração semântica superior para a língua portuguesa (Brasil) em comparação a modelos genéricos multilíngues, com persistência em disco local sem dependência de nuvem.
- **Trade-off**: Embeddings exigem memória dedicada durante ingestão e não realizam normalização nativa nos vetores de busca.
- **Scope**: Camada de indexação vetorial e recuperação (`src/ingestor.py`, `src/retriever.py`).
- **Date**: 2026-09-03
- **Status**: active

### AD-003
- **Decision**: Estratégia de recuperação por Relevância Marginal Máxima (MMR - Maximal Marginal Relevance) com k=4 e fetch_k=25.
- **Reason**: Evitar redundância de múltiplos chunks oriundos do mesmo vídeo ou de vídeos com legendas similares na janela de contexto do LLM.
- **Trade-off**: Custo computacional ligeiramente superior ao cálculo simples de similaridade por cosseno.
- **Scope**: Camada de busca e recuperação semântica (`src/retriever.py`).
- **Date**: 2026-09-03
- **Status**: active

### AD-004
- **Decision**: Pipeline de ingestão modularizado com extração resiliente de colunas textuais e enriquecimento de metadados tabulares (video_id, hashtags, upload_date, play_count).
- **Reason**: Padronizar bases CSV de postagens do TikTok com múltiplos formatos de schema possíveis, gerando chunks de 500 caracteres com overlap de 50 caracteres.
- **Trade-off**: Reindexação requer leitura síncrona do CSV bruto e recriação da pasta do ChromaDB.
- **Scope**: Ingestão e ETL de dados (`src/ingestor.py`).
- **Date**: 2026-09-03
- **Status**: active

### AD-005
- **Decision**: Gestão proativa de hardware (VRAM da GPU NVIDIA e RAM do sistema) integrada ao ciclo de vida da aplicação e dos benchmarks.
- **Reason**: Prevenir estouro de memória (OOM) na GPU durante alternância de modelos ou execuções longas de benchmarks comparativos.
- **Trade-off**: Chamadas HTTP para `/api/generate` (keep_alive: 0), `/api/ps` e chamadas de subprocess para `nvidia-smi` adicionam leve overhead de I/O.
- **Scope**: Gestão de memória e telemetria (`src/memory.py`, `benchmark/benchmark.py`).
- **Date**: 2026-09-03
- **Status**: active

### AD-006
- **Decision**: Geração automatizada de relatórios individuais de benchmark em Markdown (`benchmark/reports/benchmark_report_YYYYMMDD_HHMMSS.md`) com histórico imutável e ponteiro `latest.md`.
- **Reason**: Prover auditoria visual, qualitativa e comparativa de respostas e chunks RAG colapsáveis sem perder histórico de baterias de testes anteriores.
- **Trade-off**: Gera novos arquivos Markdown em disco a cada execução de benchmark.
- **Scope**: Módulo de benchmark e telemetria (`benchmark/benchmark.py`, `benchmark/reports/`).
- **Date**: 2026-09-03
- **Status**: active

### AD-007
- **Decision**: Consultas factuais suportadas serão resolvidas localmente por uma camada determinística de analytics antes do fallback RAG.
- **Reason**: Contagens, rankings e filtros precisam refletir os dados tabulares, não uma síntese probabilística de poucos chunks.
- **Trade-off**: A primeira versão aceita apenas intenções explícitas e auditáveis, em vez de SQL produzido livremente por LLM.
- **Scope**: Roteamento de perguntas e acesso ao corpus (`src/analytics.py`, `src/bot.py`).
- **Date**: 2026-10-03
- **Status**: active

## Handoff

- **Feature**: benchmark-markdown-reports (.specs/features/benchmark-markdown-reports/)
- **Phase / Task**: Execute - Implementação, testes e validação concluídos com sucesso (PASS)
- **Completed**: T1 a T5 implementados, 5/5 testes unitários e de integração passando, `spec.md`, `design.md`, `tasks.md` e `validation.md` validados
- **In-progress**: Nenhum
- **Next step**: Pronto para uso nos benchmarks do TrendBot-BR
- **Blockers**: none
- **Uncommitted files**: `benchmark/benchmark.py`, `src/memory.py`, `src/ingestor.py`, `src/retriever.py`, `src/__init__.py`, `tests/test_benchmark_reports.py`, `.specs/`
- **Branch**: main
