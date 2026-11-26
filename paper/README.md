# Thesis (LaTeX)

- `revision.md` — triage of every research thread and the outline the chapters follow.
- `main.tex` — the document; `chapters/` main text (counted), `appendix/` (not counted).
- `numbers.tex` — headline numbers as macros, each with its source spec. Change a number only when its source changes.
- `figures/` — figures used by the text. `\fig{file}{caption}{label}` shows a placeholder until the file exists.
- `references.bib` — biblatex/biber, author–year.

```bash
make            # build/main.pdf, with the grey plan boxes
make count      # main-text characters vs the 60,000–120,000 limit and per-chapter budgets
make submission MATRIKEL=12345678 NAME=First-Last   # ISC-named PDF, plan boxes hidden, warns above 11 MB
```

**Overleaf:** zip this folder (without `build/`) and upload it as a new project; `latexmkrc` and biber work there.
Deadline: 9 February 2027, 12 noon, through the ISC web form.
