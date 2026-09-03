# Benchmark Markdown Reports Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/benchmark-markdown-reports/design.md`
**Status**: Done

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: none - strong defaults applied.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Benchmark Reporting / Logic | unit | All formatting branches, EARS ACs, hardware metadata, and edge cases | `tests/test_*.py` | `python3 -m unittest discover -s tests` |
| Benchmark Integration | integration | End-to-end report generation and file persistence verification | `tests/test_*.py` | `python3 -m unittest discover -s tests` |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | After tasks with unit tests only | `python3 -m unittest discover -s tests` |
| Full | After tasks with integration tests | `python3 -m unittest discover -s tests` |
| Build | After phase completion | `python3 -m unittest discover -s tests` |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Benchmark Markdown Reporting Engine

Complete implementation and integration of the Markdown reporting engine.

```
T1 → T2 → T3 → T4 → T5
```

---

## Task Breakdown

### T1: Implement Metadata and Environment Header Formatter

**What**: Implement function to format host hardware, environment specs, and RAG configuration into Markdown header.
**Where**: `benchmark/benchmark.py`
**Depends on**: None
**Reuses**: `src/config.py` constants and `src/memory.py` telemetry structure
**Requirement**: BMD-02

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Header includes execution timestamps, duration, host hardware (GPU/RAM), Ollama URL, and RAG parameters
- [x] Handles fallback gracefully if GPU telemetry is unavailable (CPU-only)
- [x] Gate check passes: `python3 -m unittest discover -s tests`
- [x] Test count: 1 tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

---

### T2: Implement Consolidated Summary Table & Highlights Generator

**What**: Implement function to calculate automated performance highlights and format the comparative summary table.
**Where**: `benchmark/benchmark.py`
**Depends on**: T1
**Reuses**: Aggregated metrics calculation loop
**Requirement**: BMD-03, BMD-07, BMD-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Computes and renders fastest model, lowest VRAM/RAM consumer, and highest throughput
- [x] Formats full Markdown table with latencies, throughput, VRAM peak, RAM average, and success rate
- [x] Flags model failure counts prominently if errors occur
- [x] Gate check passes: `python3 -m unittest discover -s tests`
- [x] Test count: 2 tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

---

### T3: Implement Question Iteration & Collapsible RAG Context Formatter

**What**: Implement detailed per-model and per-question formatter with `<details>` tags and human rating checkboxes.
**Where**: `benchmark/benchmark.py`
**Depends on**: T2
**Reuses**: `todos_resultados` dictionaries from test run
**Requirement**: BMD-04

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Formats each question with status, latency, RAM, VRAM, and generated response
- [x] Encapsulates retrieved ChromaDB context in `<details><summary>` blocks
- [x] Includes blank human evaluation fields for fidelity (1-5), effectiveness (1-5), and observations
- [x] Gate check passes: `python3 -m unittest discover -s tests`
- [x] Test count: 3 tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

---

### T4: Implement Persistent Markdown File Exporter and Pointer

**What**: Implement `exportar_para_markdown` to save timestamped unique file in `benchmark/reports/` and update `latest.md`.
**Where**: `benchmark/benchmark.py`
**Depends on**: T3
**Reuses**: Python standard library `os` and `datetime`
**Requirement**: BMD-01, BMD-05, BMD-06

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] Automatically creates `benchmark/reports/` if it does not exist
- [x] Generates unique file `benchmark_report_YYYYMMDD_HHMMSS.md` without overwriting existing files
- [x] Writes identical copy to `benchmark/reports/latest.md`
- [x] Gate check passes: `python3 -m unittest discover -s tests`
- [x] Test count: 4 tests pass (no silent deletions)

**Tests**: unit
**Gate**: quick

---

### T5: Wire Exporter into Benchmark Pipeline and Add Automated Tests

**What**: Integrate `exportar_para_markdown` into `executar_benchmark_tecnico` and create comprehensive test suite.
**Where**: `benchmark/benchmark.py`
**Depends on**: T4
**Reuses**: `executar_benchmark_tecnico` workflow
**Requirement**: BMD-01, BMD-02, BMD-03, BMD-04, BMD-05, BMD-06, BMD-07, BMD-08

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [x] `executar_benchmark_tecnico` calls `exportar_para_markdown` alongside `exportar_para_csv`
- [x] Unit & integration tests in `tests/test_benchmark_reports.py` verify complete generation workflow
- [x] Gate check passes: `python3 -m unittest discover -s tests`
- [x] Test count: 5 tests pass (no silent deletions)

**Tests**: integration
**Gate**: full

---

## Phase Execution Map

```
Phase 1

Phase 1:  T1 ------→ T2 ------→ T3 ------→ T4 ------→ T5
```

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1: Implement Metadata Header Formatter | 1 function | ✅ Granular |
| T2: Implement Summary Table & Highlights | 1 function | ✅ Granular |
| T3: Implement Question Detail Formatter | 1 function | ✅ Granular |
| T4: Implement Persistent File Exporter | 1 function | ✅ Granular |
| T5: Wire Pipeline & Integration Tests | 1 integration | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | None | ✅ Match |
| T2 | T1 | T1 -> T2 | ✅ Match |
| T3 | T2 | T2 -> T3 | ✅ Match |
| T4 | T3 | T3 -> T4 | ✅ Match |
| T5 | T4 | T4 -> T5 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1: Metadata Header Formatter | Benchmark Reporting | unit | unit | ✅ OK |
| T2: Summary Table & Highlights | Benchmark Reporting | unit | unit | ✅ OK |
| T3: Question Detail Formatter | Benchmark Reporting | unit | unit | ✅ OK |
| T4: Persistent File Exporter | Benchmark Reporting | unit | unit | ✅ OK |
| T5: Wire Pipeline & Integration Tests | Benchmark Integration | integration | integration | ✅ OK |
