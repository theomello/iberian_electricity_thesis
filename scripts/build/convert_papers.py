#!/usr/bin/env python3
"""Convert the PDFs in papers/ to Markdown for reading and search.

    .venv/bin/python scripts/build/convert_papers.py

Writes papers/md/<slug>.md, one file per PDF. The PDFs are opened read-only and
are never modified -- same rule as raw data: re-run the conversion rather than
editing the output.

The conversion is structural, not just a text dump:

* Headings come from the PDF's own outline (62 and 83 entries in the two
  chapters), so the Markdown has the chapter's real section tree rather than a
  flat wall of text.
* Each page emits an HTML-comment anchor carrying the *printed* page number
  (the chapters start at 649 and 429, not 1), so a note can cite `p. 655` and
  point at the paper's own numbering.
* Text is taken block-by-block in reading order, which recovers paragraphs;
  line-broken hyphens are rejoined and ligatures normalised.

Known limits, none of which matter for reading: displayed equations extract as
run-together symbols, footnotes appear inline at the foot of their page, and
table layout is lost.
"""

from __future__ import annotations

import collections
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent.parent
PAPERS = ROOT / "papers"
OUT = PAPERS / "md"

LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
             "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}


def clean(text: str) -> str:
    """Normalise ligatures and unicode dashes without touching maths."""
    for lig, rep in LIGATURES.items():
        text = text.replace(lig, rep)
    # NFC only: NFKC would rewrite superscripts and fractions inside equations.
    return unicodedata.normalize("NFC", text)


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    # Zotero-style names ("Author - 2021 - Title") collapse to "--" separators.
    return re.sub(r"-{2,}", "-", s)


def running_headers(pages: list[list[str]], threshold: float = 0.2) -> set[str]:
    """Lines repeated across many pages are running heads, not content."""
    seen: collections.Counter[str] = collections.Counter()
    for lines in pages:
        for ln in set(lines[:2] + lines[-1:]):
            if len(ln) < 90:
                seen[ln] += 1
    cut = max(3, int(len(pages) * threshold))
    return {ln for ln, n in seen.items() if n >= cut}


def block_text(block) -> str:
    """Join the hard-wrapped lines of one block back into a paragraph."""
    raw = clean(block[4]).strip()
    if not raw:
        return ""
    # A hyphen at end of line is a syllable break in justified text: join it.
    raw = re.sub(r"(\w)-\n(\w)", r"\1\2", raw)
    return re.sub(r"\s*\n\s*", " ", raw).strip()


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(s).lower())


def convert(pdf_path: Path) -> Path:
    doc = pymupdf.open(pdf_path)
    toc = doc.get_toc()

    # Headings that begin on each 0-indexed page.
    starts: dict[int, list[tuple[int, str]]] = collections.defaultdict(list)
    for level, title, page in toc:
        starts[page - 1].append((level, clean(title).strip()))

    page_lines = [p.get_text("text").split("\n") for p in doc]
    heads = running_headers(page_lines)

    # The printed page number is a bare-number line near the top or bottom of
    # the page, but a stray number ("Chapter 17") can be picked up instead. So
    # take the most common printed-minus-physical offset across the whole
    # document and apply it uniformly -- page citations have to be trustworthy.
    offsets: collections.Counter[int] = collections.Counter()
    for i, lines in enumerate(page_lines):
        for ln in lines[:3] + lines[-3:]:
            s = ln.strip()
            if s.isdecimal() and 1 <= int(s) <= 9999:
                offsets[int(s) - (i + 1)] += 1
    offset = offsets.most_common(1)[0][0] if offsets else 0

    body: list[str] = []

    for i, page in enumerate(doc):
        pending = list(starts.get(i, []))
        body.append(f"\n<!-- pdf page {i + 1} | printed p. {i + 1 + offset} -->\n")

        blocks = [b for b in page.get_text("blocks", sort=True) if b[6] == 0]
        for b in blocks:
            para = block_text(b)
            if not para:
                continue
            if para in heads or para.strip().isdigit():
                continue
            # If this block *is* one of the headings starting on this page,
            # emit it as a heading instead of as body text.
            matched = None
            for level, title in pending:
                if norm(para).startswith(norm(title)[:40]) and len(para) < len(title) + 60:
                    matched = (level, title)
                    break
            if matched:
                pending.remove(matched)
                level, title = matched
                body.append(f"\n{'#' * min(level + 1, 6)} {title}\n")
                continue
            body.append(para)

        # Headings whose text did not surface as its own block (usually run
        # into the following paragraph) still get anchored to the right page.
        for level, title in pending:
            body.insert(len(body), f"\n{'#' * min(level + 1, 6)} {title}\n")

    meta = doc.metadata or {}
    title = clean(meta.get("title") or pdf_path.stem)
    author = clean(meta.get("author") or "")
    pages_note = f"{1 + offset}-{doc.page_count + offset}"

    header = [
        "---",
        f'title: "{title}"',
        f'authors: "{author}"' if author else 'authors: ""',
        f'source_pdf: "{pdf_path.name}"',
        f"pdf_pages: {doc.page_count}",
        f'printed_pages: "{pages_note}"',
        "converted_by: scripts/build/convert_papers.py",
        "---",
        "",
        f"# {title}",
        "",
        "> Converted from PDF for reading and search. The PDF in `papers/` is",
        "> authoritative; equations, tables and footnote placement are lossy here.",
        "> Page anchors give the paper's own printed page numbers.",
        "",
        "## Contents",
        "",
    ]
    for level, t, p in toc:
        header.append(f"{'  ' * (level - 1)}- {clean(t).strip()}  ·  p{p}")

    out_path = OUT / f"{slugify(pdf_path.stem)}.md"
    text = "\n".join(header) + "\n" + "\n\n".join(body) + "\n"
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    out_path.write_text(text, encoding="utf-8")
    doc.close()
    return out_path


def main() -> int:
    if not PAPERS.is_dir():
        print(f"no papers/ directory at {PAPERS}", file=sys.stderr)
        return 1
    pdfs = sorted(PAPERS.glob("*.pdf"))
    if not pdfs:
        print("no PDFs found in papers/", file=sys.stderr)
        return 1
    OUT.mkdir(exist_ok=True)
    for pdf in pdfs:
        before = pdf.stat().st_mtime_ns
        out = convert(pdf)
        assert pdf.stat().st_mtime_ns == before, f"{pdf.name} was modified"
        kb = out.stat().st_size / 1024
        print(f"  {pdf.name}\n    -> {out.relative_to(ROOT)}  ({kb:,.0f} KB)")
    print(f"\n{len(pdfs)} converted. Originals untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
