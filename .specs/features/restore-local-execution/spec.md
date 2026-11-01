# Restore Local Execution Specification

## Problem Statement

The project cannot start because its virtual environment refers to a removed Python 3.12 executable. The current local source changes use Ollama embeddings and a JSON index, so the legacy ChromaDB directory cannot satisfy the active runtime.

## Goals

- [ ] Restore an isolated Python runtime that can execute the project and its tests.
- [ ] Prove that the current local implementation can index the supplied CSV and initialize a retriever through the running Ollama service.
- [ ] Preserve all pre-existing local source changes.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Revert or commit the existing Ollama/JSON migration | It is pre-existing user work and changes the documented architecture. |
| Change the documented BERTimbau/Chroma/MMR architecture | Requires an explicit architectural decision. |
| Publish, push, or deploy | Not authorized. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Python installation scope | Install or repair Python 3.12 for the current user, then create `.venv` | The prior virtual environment was created with Python 3.12 and is broken; a new environment leaves it untouched. | y |
| Active runtime architecture | Validate the current Ollama + JSON-index implementation | Ollama and `nomic-embed-text` are running locally, and the user requested a safe recovery without overwriting changes. | y |
| Legacy ChromaDB directory | Preserve it without using or deleting it | Its format is incompatible with the active JSON-index implementation. | y |
| Index scope | Create the application's configured 100-row startup index if absent | This is the current behavior of `main.py`. | y |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Run the local assistant

**User Story**: As the project maintainer, I want the TrendBot to initialize on this computer so that I can use the local TikTok corpus assistant.

**Why P1**: The application currently cannot execute at all.

**Acceptance Criteria**:

1. WHEN the recovery is complete THEN the system SHALL provide an isolated `.venv` whose Python executable starts successfully.
2. WHEN the repository test suite runs in `.venv` THEN the system SHALL complete all discovered tests without failures or skips.
3. WHEN the current local implementation starts with its supplied CSV and Ollama service THEN the system SHALL create `data/chroma_ollama_db/indice_ollama.json` and initialize `TrendRetriever` successfully.
4. WHILE recovery is performed THEN the system SHALL preserve the pre-existing local source diff and the legacy `data/chroma_db` directory.
5. IF the startup corpus creates more than 10 text chunks THEN the system SHALL request embeddings in batches of at most 10 chunks until every chunk is indexed.

**Independent Test**: Create the environment, run `unittest discover`, index the supplied corpus, initialize the retriever, and compare the source diff to its pre-recovery baseline.

---

## Edge Cases

- IF Python cannot be installed or repaired THEN the system SHALL stop without modifying source files and report the failed installer command.
- IF Ollama or `nomic-embed-text` is unavailable THEN the system SHALL stop before creating a partial index and report the unavailable dependency.
- IF the legacy ChromaDB directory exists THEN the system SHALL leave it intact and create the active JSON index in `data/chroma_ollama_db`.

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| RUN-01 | P1: Run the local assistant | Execute | Implementing |
| RUN-02 | P1: Run the local assistant | Execute | Implementing |
| RUN-03 | P1: Run the local assistant | Execute | Implementing |
| RUN-04 | P1: Run the local assistant | Execute | Implementing |
| RUN-05 | P1: Run the local assistant | Execute | Implementing |

**Coverage:** 5 total, 5 mapped to execution checks, 0 unmapped.

## Success Criteria

- [ ] The application runtime and test suite work from a new isolated environment.
- [ ] The current implementation indexes the supplied corpus and can retrieve local documents.
- [ ] No pre-existing local source modification is overwritten.
