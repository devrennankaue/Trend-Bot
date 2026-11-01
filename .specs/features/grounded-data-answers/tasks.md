# Grounded Data Answers Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill and its Execute flow.

**Design**: `.specs/features/grounded-data-answers/design.md`
**Status**: Approved

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: none - strong defaults applied.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Analytics domain logic | unit | Every supported intent, result ordering, empty value, and unreadable-source behavior maps to a requirement | `tests/test_analytics.py` | `python -m unittest discover -s tests -v` |
| Retrieval domain logic | unit | Threshold, lexical reranking, per-video diversity, and source metadata map 1:1 to P2 ACs | `tests/test_retriever.py` | `python -m unittest discover -s tests -v` |
| Bot orchestration | unit | Analytics precedence, RAG fallback, abstention, and rendered sources | `tests/test_bot_grounding.py` | `python -m unittest discover -s tests -v` |
| CLI indexing | unit | Full default, explicit limit, confirmed and declined reindex behavior | `tests/test_main_indexing.py` | `python -m unittest discover -s tests -v` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | After unit-only tasks | `python -m unittest discover -s tests -v` |
| Full | After integration work | `python -m unittest discover -s tests -v` |
| Build | After phase completion | `python -m unittest discover -s tests -v` |

## Execution Plan

### Phase 1: Deterministic facts

```
T1 → T2
```

### Phase 2: Grounded retrieval

```
T3 → T4
```

### Phase 3: Application integration

```
T5 → T6
```

## Task Breakdown

### T1: Create the local analytics service

**Status**: ✅ Done (`feat(analytics): add local corpus service`)

**What**: Add a CSV-backed analytics service that normalizes known TikTok columns and safely becomes unavailable when its source cannot be read.
**Where**: `src/analytics.py`, `tests/test_analytics.py`
**Depends on**: None
**Reuses**: `src/config.py:resolver_caminho_csv()` and Pandas use in `src/ingestor.py`.
**Requirement**: GDA-01

**Tools**:
- MCP: NONE
- Skill: codenavi

**Done when**:
- [ ] The service loads a fixture CSV and exposes its row count.
- [ ] An unreadable CSV disables analytics without raising from construction.
- [ ] The quick gate passes with the existing five tests plus new analytics tests.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(analytics): add local corpus service`

### T2: Implement deterministic factual intents

**Status**: ✅ Done (`feat(analytics): answer supported data questions`)

**What**: Parse supported Portuguese count and ranking questions and render calculated local-corpus answers.
**Where**: `src/analytics.py`, `tests/test_analytics.py`
**Depends on**: T1
**Reuses**: `TrendAnalytics` from T1.
**Requirement**: GDA-01, GDA-02

**Tools**:
- MCP: NONE
- Skill: codenavi

**Done when**:
- [ ] Count, hashtag, song, creator, and engagement ranking questions return exact fixture-derived results in descending order.
- [ ] A supported metric with no usable values returns the specified corpus-no-data result.
- [ ] Unsupported questions return `None` for RAG fallback.
- [ ] The quick gate passes.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(analytics): answer supported data questions`

### T3: Enrich ingestion metadata and indexing controls

**What**: Preserve creator and music metadata in vector documents and add configuration for relevance threshold and index limit.
**Where**: `src/config.py`, `src/ingestor.py`, `tests/test_ingestor_metadata.py`
**Depends on**: T2
**Reuses**: Existing document construction and configuration constants.
**Requirement**: GDA-03, GDA-05

**Tools**:
- MCP: NONE
- Skill: codenavi

**Done when**:
- [ ] Indexed documents contain creator, music, hashtags, publication date, and video ID metadata when supplied by a row.
- [ ] No default ingestion limit is applied when none is supplied.
- [ ] The quick gate passes.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(ingestion): preserve evidence metadata`

### T4: Add scored, diversified retrieval

**What**: Wrap semantic candidates with relevance thresholding, lexical reranking, and one-chunk-per-video selection.
**Where**: `src/retriever.py`, `tests/test_retriever.py`
**Depends on**: T3
**Reuses**: `TrendRetriever` embeddings and ChromaDB vector store.
**Requirement**: GDA-03, GDA-04

**Tools**:
- MCP: NONE
- Skill: codenavi

**Done when**:
- [ ] Documents below the configured threshold are excluded.
- [ ] Exact lexical matches improve candidate order without replacing semantic scoring.
- [ ] At most one document per `video_id` is returned.
- [ ] The quick gate passes.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(retriever): ground scored retrieval`

### T5: Route bot questions and render sources

**What**: Route supported factual questions to analytics, preserve RAG fallback, and append concise source evidence to generated responses.
**Where**: `src/bot.py`, `tests/test_bot_grounding.py`
**Depends on**: T2, T4
**Reuses**: Existing `TrendBot.ask()` history and prompt chain.
**Requirement**: GDA-01, GDA-03, GDA-04

**Tools**:
- MCP: NONE
- Skill: codenavi

**Done when**:
- [ ] A deterministic analytics result is returned without invoking the LLM path.
- [ ] Empty grounded retrieval produces the existing insufficient-information response.
- [ ] Generated response output includes only populated source fields from selected documents.
- [ ] The quick gate passes.

**Tests**: unit
**Gate**: quick
**Commit**: `feat(bot): route grounded data answers`

### T6: Make full indexing explicit in the CLI

**What**: Add CLI options for a development index limit and confirmed local vector-store rebuild, then wire analytics into startup.
**Where**: `main.py`, `tests/test_main_indexing.py`
**Depends on**: T1, T3, T5
**Reuses**: Existing path resolvers and CLI startup flow.
**Requirement**: GDA-05, GDA-06

**Tools**:
- MCP: NONE
- Skill: codenavi

**Done when**:
- [ ] Standard first-time startup constructs ingestion with no limit.
- [ ] `--limit` passes its positive integer value to ingestion.
- [ ] `--reindex` displays its target and leaves it untouched if confirmation is declined.
- [ ] The build gate passes.

**Tests**: unit
**Gate**: build
**Commit**: `feat(cli): add explicit corpus indexing controls`

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

T1 → T2
T2 → T3
T3 → T4
T2 → T5
T4 → T5
T1 → T6
T3 → T6
T5 → T6
```

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1 | Analytics service plus its unit contract | ✅ Granular |
| T2 | Analytics intent behavior plus its unit contract | ✅ Granular |
| T3 | Ingestion evidence representation plus its unit contract | ✅ Granular |
| T4 | Retrieval selection behavior plus its unit contract | ✅ Granular |
| T5 | Bot routing behavior plus its unit contract | ✅ Granular |
| T6 | CLI index lifecycle plus its unit contract | ✅ Granular |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | None | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T2, T4 | T2 → T5; T4 → T5 | ✅ Match |
| T6 | T1, T3, T5 | T1 → T6; T3 → T6; T5 → T6 | ✅ Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Analytics domain | unit | unit | ✅ OK |
| T2 | Analytics domain | unit | unit | ✅ OK |
| T3 | Ingestion domain | unit | unit | ✅ OK |
| T4 | Retrieval domain | unit | unit | ✅ OK |
| T5 | Bot orchestration | unit | unit | ✅ OK |
| T6 | CLI indexing | unit | unit | ✅ OK |
