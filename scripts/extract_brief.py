"""Regenerate docs/advisor_brief.md from the source .docx (ADR-003).

The Markdown is the canonical grounding source at runtime; this script only needs
to run if the original .docx is edited. Requires python-docx (a dev-only tool, not
a backend runtime dependency):

    uv run --with python-docx python scripts/extract_brief.py

Preserves heading TEXT verbatim (so brief.py's section regexes still match) and
renders Word tables as Markdown pipe tables.
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "reference" / "Claude_SC_Advisor_Brief.docx"
DST = ROOT / "docs" / "advisor_brief.md"


def iter_block_items(document):  # type: ignore[no-untyped-def]
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def table_to_md(table: Table) -> list[str]:
    rows = []
    for row in table.rows:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        if any(cells):
            rows.append(cells)
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return out


def main() -> None:
    doc = Document(str(SRC))
    lines: list[str] = [
        "<!-- GENERATED from Claude_SC_Advisor_Brief.docx by scripts/extract_brief.py.",
        "     Canonical grounding source for the Block Coach system prompt (sections 1-3)",
        "     and lookup_advisor_principle search. Edit the .docx and re-run, or edit here",
        "     directly — this .md is the source of truth read by obelisk_api. -->",
        "",
    ]
    for item in iter_block_items(doc):
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if not text:
                continue
            style = item.style.name if item.style else ""
            if style.startswith("Heading"):
                level_str = style.replace("Heading ", "").strip()
                level = int(level_str) if level_str.isdigit() else 1
                lines.extend(["", f"{'#' * level} {text}", ""])
            elif style == "Title":
                lines.extend([f"# {text}", ""])
            else:
                lines.append(text)
        elif isinstance(item, Table):
            lines.append("")
            lines.extend(table_to_md(item))
            lines.append("")
    DST.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {DST} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
