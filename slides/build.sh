#!/usr/bin/env bash
# Render the supervisor deck: markdown -> beamer PDF.
#
#   bash slides/build.sh                        # all decks in slides/
#   bash slides/build.sh supervisor-2026-08-19  # just one
#
# Figures are regenerated first so the PDF can never carry stale numbers --
# every figure is re-derived from the panels in outputs/tables/ by
# scripts/analysis/slides_figures.py.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# pandoc: prefer one on PATH, else the binary bundled with the pypandoc_binary
# wheel in .venv (pip install pypandoc_binary).
PANDOC="$(command -v pandoc || true)"
if [ -z "$PANDOC" ]; then
  PANDOC="$(.venv/bin/python -c 'import pypandoc; print(pypandoc.get_pandoc_path())' 2>/dev/null || true)"
fi
if [ -z "$PANDOC" ]; then
  echo "no pandoc found: run  .venv/bin/pip install pypandoc_binary" >&2; exit 1
fi

.venv/bin/python scripts/analysis/slides_figures.py
PYTHONPATH=scripts/analysis .venv/bin/python scripts/analysis/slides_data_figures.py

shopt -s nullglob
if [ $# -gt 0 ]; then
  decks=("slides/${1%.md}.md")
else
  decks=(slides/*.md)
fi

for md in "${decks[@]}"; do
  out="${md%.md}.pdf"
  echo "rendering $md -> $out"
  "$PANDOC" "$md" \
    --from=markdown+tex_math_dollars+pipe_tables \
    --to=beamer \
    --pdf-engine=xelatex \
    --slide-level=1 \
    --resource-path="$ROOT/slides" \
    --include-in-header="$ROOT/slides/preamble.tex" \
    --variable=theme:default \
    --variable=colortheme:dove \
    --variable=fontsize:9pt \
    --variable=aspectratio:169 \
    --variable=mainfont:"Helvetica Neue" \
    --variable=sansfont:"Helvetica Neue" \
    --variable=mathfont:"STIX Two Math" \
    --variable=monofont:"Menlo" \
    --output="$out"
done

echo "done"
