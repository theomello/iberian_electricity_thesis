"""Figure: Spain's access tariffs by connection voltage, who is on each, and which demand series the thesis uses.

Voltage and power conditions: CNMC Circular 3/2020, art. 6.2 (a-f) and art. 3.b (tariff voltage levels NT0-NT4);
see docs/tou-policy-sources.md. Demand series: ESIOS 1201 (E0, below 1 kV), 1202+1203 (E1+E2, 1-36 kV, about 80%
6.1TD), 1216-1218 (tariffs 6.2-6.4). Writes paper/figures/tariff_voltages.pdf (and a .png preview).
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_style as S  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
FIG = ROOT / "paper" / "figures"

ROWS = [  # tariff, voltage, contracted power, who
    ("2.0TD", "up to 1 kV", "up to 15 kW", "Households, small shops"),
    ("3.0TD", "up to 1 kV", "above 15 kW", "Small/medium firms"),
    ("6.1TD", "1 – 30 kV", "any", "Medium firms"),
    ("6.2TD", "30 – 72.5 kV", "any", "Large industry"),
    ("6.3TD", "72.5 – 145 kV", "any", "Large industry"),
    ("6.4TD", "145 kV or more", "any", "Largest industrial sites"),
]
SERIES = [  # (first row, last row, label)
    (0, 1, "E0: one series for both"),
    (2, 2, "E1+E2 (mostly 6.1TD)"),
    (3, 3, "Tariff series 6.2"),
    (4, 4, "Tariff series 6.3"),
    (5, 5, "Tariff series 6.4"),
]
COLS = [("Tariff", 0.00), ("Voltage", 0.135), ("Contracted power", 0.345), ("Customers", 0.555),
        ("Hourly demand series", 0.815)]
LOW, HIGH = S.RAMP6[5], S.RAMP6[4]   # band colours: low voltage, high voltage


def main():
    S.apply()
    n = len(ROWS)
    fig, ax = plt.subplots(figsize=(7.8, 2.6))
    ax.set_xlim(0, 1.13)
    ax.set_ylim(n + 0.15, -1.1)
    ax.axis("off")
    for name, x in COLS:
        ax.text(x, -0.55, name, fontweight="bold", color=S.INK, va="center", fontsize=8)
    ax.plot([0, 1.13], [-0.1, -0.1], color=S.INK3, lw=0.6)
    for i, (tar, volt, pw, who) in enumerate(ROWS):
        y = i + 0.4
        band = LOW if i < 2 else HIGH
        ax.add_patch(plt.Rectangle((0, i - 0.02), 0.105, 0.84, color=band, lw=0))
        ax.text(0.012, y, tar, fontweight="bold", color=S.INK, va="center")
        for txt, (_, x) in zip((volt, pw, who), COLS[1:4]):
            ax.text(x, y, txt, color=S.INK if txt != "any" else S.INK3, va="center")
        if i < n - 1:
            ax.plot([0.135, 0.785], [i + 0.9, i + 0.9], color=S.GRID, lw=0.6)
    for a, b, lab in SERIES:
        y0, y1 = a + 0.1, b + 0.7
        x = 0.815
        ax.plot([x, x], [y0, y1], color=S.NEW, lw=1.6, solid_capstyle="butt")
        ax.text(x + 0.012, (y0 + y1) / 2, lab, va="center", color=S.INK2 if a == b else S.INK,
                fontweight="normal" if a == b else "bold")
    ax.text(0, n + 0.15, "Low voltage (up to 1 kV) is split by contracted power; above 1 kV, by voltage alone. "
            "Source: CNMC Circular 3/2020, art. 6.", color=S.INK3, fontsize=6.5, va="top")
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "tariff_voltages.pdf")
    fig.savefig(FIG / "tariff_voltages.png", dpi=180)


if __name__ == "__main__":
    main()
