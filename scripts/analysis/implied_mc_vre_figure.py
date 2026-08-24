#!/usr/bin/env python3
"""One figure: the market got thinner, and the markup firms take grew with it.

    .venv/bin/python scripts/analysis/implied_mc_vre_figure.py

Reads the panel written by `implied_mc_vre_iv.py --save`.

WHAT IT SHOWS, IN THREE PANELS ON A SHARED TIME AXIS

  1. renewables as a share of generation -- rises 22% to 38%, flattening after 2023;
  2. the slope of residual demand facing the six largest firms -- how much rival
     supply sits within +/-5 EUR/MWh of the clearing price. It COLLAPSES, 721 to
     ~230 MW per EUR/MWh. Fewer competitors near the margin is the mechanism;
  3. the markup those firms actually take, from the supply-function first-order
     condition with their OBSERVED forward positions, (q - theta)/|RD'|. It
     roughly triples, 2.4 to 6.5 EUR/MWh.

HONESTY ABOUT WHAT THIS IS

This is DESCRIPTIVE co-movement over nine years, not an identified effect, and
the 2021-22 energy crisis sits in the middle of it -- shaded, because the spike
to 11.8 EUR/MWh is a gas-price event, not a renewables event.

It also runs OPPOSITE to the identified within-year estimate. Instrumenting the
renewable share with weather, with year fixed effects, gives -1.25 EUR/MWh per
percentage point: within a year, a windy hour has a LOWER markup. Both can hold.
A windy hour is transitory and firms know it reverses; a decade of capacity
build is structural and changes who is left near the margin. The figure shows
the second; the regression identifies the first. Neither is the other's
robustness check.

Writes slides/figures/thinning_market.png.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

mpl.use("Agg")

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "outputs" / "tables" / "implied_mc_vre_panel.parquet"
FIGS = ROOT / "slides" / "figures"

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8983"
GRID, SURFACE, CRISIS = "#e6e5e1", "#ffffff", "#f2efe9"

mpl.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 13,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2,
    "xtick.labelsize": 13, "ytick.labelsize": 12,
    "axes.spines.top": False, "axes.spines.right": False,
    "grid.color": GRID, "grid.linewidth": 0.8,
})


def main() -> int:
    d = pd.read_parquet(PANEL)
    d = d[d.mc.between(d.mc.quantile(0.01), d.mc.quantile(0.99))].copy()
    d["markup"] = (d.q - d.theta) / d.slope
    d["year"] = pd.to_datetime(d.date).dt.year
    g = (d.groupby("year")
          .agg(vre=("vre_share", "mean"), slope=("slope", "median"),
               markup=("markup", "median"))
          .reset_index())

    fig, axes = plt.subplots(3, 1, figsize=(9.6, 8.4), sharex=True,
                             gridspec_kw={"hspace": 0.42})

    panels = [
        (axes[0], g.vre, BLUE, "Renewables", "% of generation",
         "{:.0f}%", (0, 48)),
        (axes[1], g.slope, AQUA, "Competitors near the margin",
         "MW per €/MWh", "{:.0f}", (0, 830)),
        (axes[2], g.markup, ORANGE, "Markup firms take",
         "€/MWh", "{:.1f}", (0, 13.6)),
    ]

    for ax, y, colour, title, unit, fmt, ylim in panels:
        ax.axvspan(2020.6, 2023.4, color=CRISIS, zorder=0)
        ax.grid(axis="y", zorder=1)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        ax.plot(g.year, y, color=colour, lw=3, marker="o", ms=8, zorder=4,
                markeredgecolor=SURFACE, markeredgewidth=2,
                solid_capstyle="round")
        ax.set_ylim(*ylim)
        ax.set_ylabel(unit, fontsize=12)
        ax.text(0, 1.13, title, transform=ax.transAxes, fontsize=15,
                fontweight="bold", color=INK, va="bottom")
        for xv, yv in ((g.year.iloc[0], y.iloc[0]), (g.year.iloc[-1], y.iloc[-1])):
            ax.annotate(fmt.format(yv), xy=(xv, yv), xytext=(0, 13),
                        textcoords="offset points", ha="center", color=INK,
                        fontsize=13, fontweight="bold")

    axes[0].text(2022.0, 43, "2021–22 energy crisis", ha="center",
                 color=INK2, fontsize=12.5)
    axes[2].set_xlabel("")
    axes[2].set_xticks(g.year)
    axes[2].set_xticklabels([str(y) if y % 2 == 0 else "" for y in g.year])
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    p = FIGS / "thinning_market.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {p}\n")
    print(g.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
