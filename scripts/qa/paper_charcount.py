"""Count the thesis's main-text characters against the 60,000-120,000 limit.

The rule counts characters including spaces, excluding the outline (table of
contents), sources, footnotes and appendices. This script reads the chapter
sources in paper/chapters/, strips comments, \\plan boxes, footnotes, figure and
table environments, citations and references, and LaTeX markup, and counts what
is left with whitespace collapsed. It is an approximation of the printed text
(equations are counted as their source); check against the PDF near the limits.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHAPTERS = ROOT / "paper" / "chapters"

LIMIT_LOW, LIMIT_HIGH = 60_000, 120_000
# Budget per chapter (characters), from paper/revision.md Part 2.
BUDGET = {
    "01-introduction": 9_000,
    "02-setting": 11_000,
    "03-market": 11_000,
    "04-framework": 8_000,
    "05-data-method": 11_000,
    "06-households": 13_000,
    "07-firms": 15_000,
    "08-planned-vs-hourly": 9_000,
    "09-validity": 7_000,
    "10-conclusion": 5_000,
}

DROP_ENVS = ("figure", "figure*", "table", "table*")
DROP_CMDS_WITH_ARG = ("plan", "footnote", "label", "cite", "textcite", "parencite",
                      "citet", "citep", "ref", "cref", "Cref", "eqref", "fig")


def strip_braced(text: str, cmd: str) -> str:
    """Remove \\cmd[opt]{...}{...}... with balanced braces (all following brace groups)."""
    out, i = [], 0
    pat = re.compile(r"\\" + re.escape(cmd) + r"(?![A-Za-z])")
    while True:
        m = pat.search(text, i)
        if not m:
            out.append(text[i:])
            return "".join(out)
        out.append(text[i:m.start()])
        j = m.end()
        while True:
            while j < len(text) and text[j] in " \t":
                j += 1
            if j < len(text) and text[j] == "[":
                j = text.index("]", j) + 1
                continue
            if j < len(text) and text[j] == "{":
                depth = 0
                while j < len(text):
                    depth += {"{": 1, "}": -1}.get(text[j], 0)
                    j += 1
                    if depth == 0:
                        break
                continue
            break
        i = j


def clean(tex: str) -> str:
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    for env in DROP_ENVS:
        e = re.escape(env)
        tex = re.sub(r"\\begin\{" + e + r"\}.*?\\end\{" + e + r"\}", "", tex, flags=re.S)
    for cmd in DROP_CMDS_WITH_ARG:
        tex = strip_braced(tex, cmd)
    tex = re.sub(r"\\(begin|end)\{[^}]*\}", "", tex)
    tex = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?", "", tex)   # command names; keep their {text}
    tex = tex.replace("{", "").replace("}", "").replace("~", " ").replace("$", "")
    return re.sub(r"\s+", " ", tex).strip()


def main() -> int:
    total = 0
    print(f"{'chapter':<24}{'chars':>8}{'budget':>9}")
    for f in sorted(CHAPTERS.glob("*.tex")):
        n = len(clean(f.read_text(encoding="utf-8")))
        total += n
        print(f"{f.stem:<24}{n:>8,}{BUDGET.get(f.stem, 0):>9,}")
    status = "below minimum" if total < LIMIT_LOW else "over limit" if total > LIMIT_HIGH else "within limits"
    print(f"{'total':<24}{total:>8,}{sum(BUDGET.values()):>9,}   ({LIMIT_LOW:,}-{LIMIT_HIGH:,}: {status})")
    return 1 if total > LIMIT_HIGH else 0


if __name__ == "__main__":
    sys.exit(main())
