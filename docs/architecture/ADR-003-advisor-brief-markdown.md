# ADR-003: Advisor Brief as a versioned Markdown source

**Status:** Accepted · **Date:** 2026-06-09

## Context

The POC's `brief.py` read `Claude_SC_Advisor_Brief.docx` at runtime via `python-docx`.
The mission requires the brief be read from a versioned file (`docs/advisor_brief.md`),
not inlined and not a binary blob the deploy image must parse. `system_prompt_source()`
extracts sections 1–3 by regex-matching the headings `1. Role and Mandate` and
`4. Programming Decision Trees`; `search()` keyword-indexes the whole document.

## Decision

- Extract the `.docx` once (`_extract.py`) into `docs/advisor_brief.md`, preserving
  **heading text verbatim** (so the section regexes still match) and rendering Word
  tables as Markdown pipe tables.
- Rewrite `brief.py` to parse Markdown into the same `(kind, level, text)` block
  stream the docx parser produced: `#`-prefixed lines → `heading` (text stripped of
  `#`), consecutive `|`-rows → `table`, everything else → `para`. `system_prompt_source`,
  `_chunks`, and `search` are unchanged below that parsing seam.
- Path resolution: `OBELISK_BRIEF_PATH` env override → else walk up from the package
  to the repo `docs/advisor_brief.md`. The Docker image `COPY`s the file in and sets
  the env var, so the deployed backend has no dependency on repo layout.

## Consequences

- The grounding source is now human-diffable in PRs; no `python-docx` at runtime.
- `docs/advisor_brief.md` is the single source of truth. Re-running `_extract.py`
  regenerates it from the `.docx` if the original is edited.
- Risk: a parsing difference could change the system prompt. Mitigated by
  `test_system_prompt_includes_brief_and_athlete`, which asserts `Role and Mandate`
  survives end-to-end.
