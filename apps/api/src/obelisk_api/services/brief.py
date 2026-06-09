"""Loads and indexes the Claude S&C Advisor Brief (the grounding source).

Sections 1-3 become the Block Coach system prompt; the full document is indexed
for keyword lookup by the ``lookup_advisor_principle`` tool.

Rewritten for the backend (ADR-003): the brief is now a versioned Markdown file
(``docs/advisor_brief.md``), not the original ``.docx``. Everything below the
``load_blocks`` parsing seam — ``system_prompt_source``, ``_chunks``, ``search`` —
is unchanged from the validated POC; only the source format differs.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

# Section 1-3 are the system-prompt-ready portion; section 4 begins reference material.
_SYSTEM_PROMPT_START = re.compile(r"^\s*1\.\s+Role and Mandate", re.IGNORECASE)
_SYSTEM_PROMPT_END = re.compile(r"^\s*4\.\s+Programming Decision Trees", re.IGNORECASE)

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _default_brief_path() -> Path:
    """Resolve the brief: env override, else the repo's docs/advisor_brief.md.

    Walks up from this module looking for ``docs/advisor_brief.md`` so the loader
    works from the monorepo checkout; the Docker image sets ``OBELISK_BRIEF_PATH``.
    """
    env = os.environ.get("OBELISK_BRIEF_PATH")
    if env:
        return Path(env)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "docs" / "advisor_brief.md"
        if candidate.exists():
            return candidate
    # Last resort: repo-root guess (5 levels up from services/brief.py).
    return Path(__file__).resolve().parents[5] / "docs" / "advisor_brief.md"


@dataclass(frozen=True)
class Chunk:
    """A heading plus the text/table content that follows it, for keyword search."""

    heading: str
    body: str
    keywords: frozenset[str] = field(default_factory=frozenset)


def _table_row_to_text(line: str) -> str | None:
    """A Markdown pipe row -> ' | '-joined cells, or None if it's a separator row."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if all(set(c) <= {"-", ":"} and c for c in cells):
        return None  # separator row (| --- | --- |)
    return " | ".join(cells)


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}


@lru_cache(maxsize=1)
def load_blocks(path_str: str | None = None) -> tuple[tuple[str, str, str], ...]:
    """Parse the brief into ordered (kind, level, text) tuples.

    kind is one of: 'heading', 'para', 'table'. Cached because the brief never
    changes during a session. Mirrors the POC docx parser's output shape.
    """
    path = Path(path_str) if path_str else _default_brief_path()
    if not path.exists():
        raise FileNotFoundError(f"Advisor Brief not found at {path}")
    raw = _COMMENT.sub("", path.read_text(encoding="utf-8"))

    blocks: list[tuple[str, str, str]] = []
    table_rows: list[str] = []

    def flush_table() -> None:
        if table_rows:
            blocks.append(("table", "", "\n".join(table_rows)))
            table_rows.clear()

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            row = _table_row_to_text(stripped)
            if row is not None:
                table_rows.append(row)
            continue
        flush_table()
        if not stripped:
            continue
        m = _HEADING.match(stripped)
        if m:
            level = str(len(m.group(1)))
            blocks.append(("heading", level, m.group(2).strip()))
        else:
            blocks.append(("para", "", stripped))
    flush_table()
    return tuple(blocks)


def system_prompt_source(path_str: str | None = None) -> str:
    """Return the verbatim text of sections 1-3 of the brief."""
    blocks = load_blocks(path_str)
    collecting = False
    parts: list[str] = []
    for kind, _level, text in blocks:
        if kind == "heading" and _SYSTEM_PROMPT_START.match(text):
            collecting = True
        elif kind == "heading" and _SYSTEM_PROMPT_END.match(text):
            break
        if collecting:
            parts.append(text)
    if not parts:
        raise ValueError("Could not locate sections 1-3 in the Advisor Brief.")
    return "\n".join(parts)


@lru_cache(maxsize=1)
def _chunks(path_str: str | None = None) -> tuple[Chunk, ...]:
    """Group the brief into searchable chunks keyed on each heading."""
    blocks = load_blocks(path_str)
    chunks: list[Chunk] = []
    current_heading = "Preamble"
    current_body: list[str] = []

    def flush() -> None:
        if current_body or current_heading != "Preamble":
            body = "\n".join(current_body).strip()
            kw = _tokenize(current_heading) | _tokenize(body)
            chunks.append(Chunk(heading=current_heading, body=body, keywords=frozenset(kw)))

    for kind, _level, text in blocks:
        if kind == "heading":
            flush()
            current_heading = text
            current_body = []
        else:
            current_body.append(text)
    flush()
    return tuple(chunks)


def search(topic: str, path_str: str | None = None) -> str:
    """Keyword search over the brief; returns the best-matching section."""
    query = _tokenize(topic)
    if not query:
        return "No searchable terms in query."
    chunks = _chunks(path_str)
    best: Chunk | None = None
    best_score = 0
    for chunk in chunks:
        score = len(query & chunk.keywords)
        # Heading matches are worth extra — they signal the section's topic.
        score += 2 * len(query & _tokenize(chunk.heading))
        if score > best_score:
            best_score = score
            best = chunk
    if best is None or best_score == 0:
        return (
            f"No Advisor Brief section strongly matched '{topic}'. "
            "Try a more specific term (e.g. 'hangboard', 'polarized', 'deload', 'macros')."
        )
    header = best.heading
    body = best.body if best.body else "(section heading only)"
    return f"## {header}\n{body}"
