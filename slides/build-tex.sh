#!/usr/bin/env bash
# Render the LaTeX supervisor deck.
#
#   bash slides/build-tex.sh
#
# Figures are regenerated first so the PDF can never carry stale numbers --
# every figure is re-derived from the panels in outputs/tables/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

XELATEX="$(command -v xelatex || echo /Library/TeX/texbin/xelatex)"
[ -x "$XELATEX" ] || { echo "no xelatex found (install MacTeX)" >&2; exit 1; }

.venv/bin/python scripts/analysis/slides_figures.py
PYTHONPATH=scripts/analysis .venv/bin/python scripts/analysis/slides_data_figures.py

TEX="${1:-supervisor-2026-08-19-data-and-designs}"
echo "rendering slides/${TEX}.tex -> slides/${TEX}.pdf"
cd slides
# Twice: the second pass settles the PDF outline.
for _ in 1 2; do
  "$XELATEX" -interaction=batchmode -halt-on-error "${TEX}.tex" >/dev/null
done
rm -f "${TEX}".{aux,log,nav,out,snm,toc,vrb}
echo "done"
