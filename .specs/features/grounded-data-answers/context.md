# Grounded Data Answers Context

**Gathered:** 2026-10-03
**Spec:** `.specs/features/grounded-data-answers/spec.md`
**Status:** Ready for design

## Feature Boundary

Deliver deterministic local answers for supported corpus facts and evidence-grounded semantic answers for all remaining questions, without changing the local-only model policy.

## Implementation Decisions

### Direct answers

- Use Pandas over the existing CSV, not LLM-generated SQL.
- Support exact corpus counts and top rankings for hashtags, songs, creators, and engagement.
- Use a clear calculated-from-local-corpus label in every deterministic response.

### RAG evidence

- Threshold weak semantic results before invoking the LLM.
- Retain at most one chunk from each video and include concise source metadata in prompt context and the final response.
- Apply lexical token overlap as a deterministic reranking signal after semantic candidate retrieval.

### Index lifecycle

- Default to all rows; retain a CLI limit for development.
- Require an interactive confirmation before deleting and rebuilding a local vector store.

### Agent's Discretion

- Exact Portuguese intent phrases and response formatting, provided tests preserve the specified outcomes.
- Exact ranking length default, provided it is configurable and deterministic.

### Declined / Undiscussed Gray Areas → Assumptions

- Concurrent indexing is N/A because the CLI has one interactive process and index writes occur only before chat startup.
- Data expiry is N/A because the CSV is a user-managed research corpus; this feature neither uploads nor deletes source data.
- External-dependency failure is limited to the pre-existing Ollama path; analytics remains local and RAG errors retain the existing CLI handling.

## Specific References

No specific UI requirements; the existing CLI remains the interface.

## Deferred Ideas

- Natural-language filtering beyond supported analytics intents.
- A historical trend-growth model based on successive collection snapshots.
