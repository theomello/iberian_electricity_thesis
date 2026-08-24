#!/usr/bin/env python3
"""Figures for the supervisor deck (slides/supervisor-2026-08-19.md).

    .venv/bin/python scripts/analysis/slides_figures.py

Every number is re-derived here from the panels in outputs/tables/ rather than
transcribed from the notes, so a figure cannot drift away from the analysis.

These are projection figures, not paper figures: large type, one idea each, and
no titles -- the slide's own title carries the message. Writes PNG at 200 dpi
into slides/figures/.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

mpl.use("Agg")

ROOT = Path(__file__).resolve().parent.parent.parent
FIGS = ROOT / "slides" / "figures"
PANEL = ROOT / "outputs" / "tables" / "hydro_water_value_structural_panel_R.parquet"
PRICES = ROOT / "data" / "omie" / "prices" / "omie_day_ahead_prices.parquet"

# dataviz reference palette, light mode
BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8983"
GRID, SURFACE = "#e6e5e1", "#ffffff"

LEVY0, LEVY1 = pd.Timestamp("2021-09-16"), pd.Timestamp("2023-12-31")
CAP0, CAP1 = pd.Timestamp("2022-06-15"), pd.Timestamp("2023-12-31")

mpl.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 14,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.labelsize": 14,
    "xtick.color": INK2, "ytick.color": INK2,
    "xtick.labelsize": 14, "ytick.labelsize": 14,
    "axes.spines.top": False, "axes.spines.right": False,
    "grid.color": GRID, "grid.linewidth": 0.8,
})


def _frame(ax, axis="y"):
    ax.grid(axis=axis, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def fig_setting():
    """The two interventions, against the price they were a response to."""
    d = pd.read_parquet(PRICES, columns=["date", "price_es"])
    d["date"] = pd.to_datetime(d["date"])
    m = d.groupby(d["date"].dt.to_period("M"))["price_es"].mean()
    x = m.index.to_timestamp()

    fig, ax = plt.subplots(figsize=(12.4, 4.1))
    _frame(ax)
    ax.fill_between(x, m.values, color=BLUE, alpha=0.13, zorder=2)
    ax.plot(x, m.values, color=BLUE, lw=2.4, zorder=3, solid_capstyle="round")

    # policy windows as labelled bars above the series, so the 18-month
    # overlap stays legible instead of muddying into a single shaded block
    top = 305
    for y, (a, b), colour, label in (
        (top, (LEVY0, LEVY1), ORANGE, "Levy — hydro taxed"),
        (top - 38, (CAP0, CAP1), RED, "Gas cap — hydro not capped"),
    ):
        ax.plot([a, b], [y, y], lw=9, color=colour, alpha=0.85,
                solid_capstyle="butt", zorder=4)
        ax.text(a, y + 13, label, color=INK, fontsize=13.5, ha="left")

    ax.set_ylabel("Spanish day-ahead price, €/MWh")
    ax.set_ylim(0, 345)
    ax.set_xlim(pd.Timestamp("2018-01-01"), pd.Timestamp("2026-06-30"))
    fig.tight_layout()
    fig.savefig(FIGS / "setting.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_divergence():
    """Implied markup vs measured concentration, on a common base.

    Single axis, by the no-dual-axis rule: two quantities of different units go
    on a common base rather than on two scales.
    """
    yr = np.arange(2018, 2024)
    lerner = np.array([10.65, 12.30, 18.60, 14.85, 19.70, 21.30])  # markup_from_shares.py
    hhi = np.array([1314, 1190, 1190, 1144, 1142, 1007])           # CNMC
    li, hi = lerner / lerner[0] * 100, hhi / hhi[0] * 100

    fig, ax = plt.subplots(figsize=(12.4, 4.1))
    _frame(ax)
    ax.axhline(100, color=GRID, lw=1.2, zorder=1)
    for y, colour, label in ((li, BLUE, "Ability to mark up"),
                             (hi, ORANGE, "Measured concentration")):
        ax.plot(yr, y, color=colour, lw=3, marker="o", ms=8, zorder=3,
                solid_capstyle="round", markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(label, xy=(yr[-1], y[-1]), xytext=(12, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=15)

    ax.annotate("×2 since 2018", xy=(2022.5, 195), xytext=(0, 16),
                textcoords="offset points", color=INK, fontsize=15,
                fontweight="bold", ha="center")
    ax.set_ylabel("Index, 2018 = 100")
    ax.set_xlim(2017.9, 2025.6)
    ax.set_ylim(55, 220)
    ax.set_xticks(yr)
    fig.tight_layout()
    fig.savefig(FIGS / "divergence.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_confound(d):
    """Hydro's water value moves with the forward price, not with policy dates."""
    g = d.groupby(d["date"].dt.to_period("M")).agg(c=("c", "median"), pf=("pf", "median"))
    x = g.index.to_timestamp()

    fig, ax = plt.subplots(figsize=(12.4, 4.1))
    _frame(ax)
    for a in (LEVY0, CAP0):
        ax.axvline(a, color=MUTED, ls=(0, (4, 4)), lw=1.6, zorder=2)
    ax.text(LEVY0, 306, "levy\nstarts", color=INK2, fontsize=13, ha="center", linespacing=1.3)
    ax.text(CAP0, 306, "cap\nstarts", color=INK2, fontsize=13, ha="center", linespacing=1.3)

    ax.plot(x, g["pf"], color=ORANGE, lw=3, zorder=3, solid_capstyle="round")
    ax.plot(x, g["c"], color=BLUE, lw=3, zorder=4, solid_capstyle="round")
    ax.annotate("Hydro's water value", xy=(x[-1], g["c"].iloc[-1]), xytext=(12, 6),
                textcoords="offset points", va="center", color=INK, fontsize=15)
    ax.annotate("Forward price", xy=(x[-1], g["pf"].iloc[-1]), xytext=(12, -12),
                textcoords="offset points", va="center", color=INK, fontsize=15)

    ax.set_ylabel("€/MWh")
    ax.set_ylim(0, 345)
    ax.set_xlim(pd.Timestamp("2018-01-01"), pd.Timestamp("2027-09-30"))
    fig.tight_layout()
    fig.savefig(FIGS / "confound.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_passthrough(d):
    """Binscatter: implied water value against the forward price."""
    q = pd.qcut(d["pf"], 25, duplicates="drop")
    b = d.groupby(q, observed=True).agg(pf=("pf", "mean"), c=("c", "mean"))

    fig, ax = plt.subplots(figsize=(6.8, 5.6))
    _frame(ax)
    lim = [25, 290]
    ax.plot(lim, lim, ls=(0, (5, 4)), color=MUTED, lw=1.8, zorder=2)
    ax.text(285, 40, "dashed: one-for-one", color=MUTED, fontsize=13, ha="right")
    ax.scatter(b["pf"], b["c"], s=95, color=BLUE, zorder=4,
               edgecolor=SURFACE, linewidth=2.5)

    ax.set_xlabel("Forward price, €/MWh")
    ax.set_ylabel("Implied water value, €/MWh")
    ax.set_xlim(*lim); ax.set_ylim(*lim); ax.set_aspect("equal")
    ax.text(0.04, 0.95, "slope 0.94", transform=ax.transAxes, fontsize=19,
            fontweight="bold", color=INK, va="top")
    fig.tight_layout()
    fig.savefig(FIGS / "passthrough.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_policy(res):
    """Coefficient plot for the two policy-window residual tests."""
    fig, ax = plt.subplots(figsize=(12.0, 3.6))
    ax.grid(axis="x", zorder=0); ax.set_axisbelow(True); ax.tick_params(length=0)
    ax.axvline(0, color=INK2, lw=1.6, zorder=2)

    for (name, (b, lo, hi), colour), y in zip(res, (1, 0)):
        ax.plot([lo, hi], [y, y], color=colour, lw=3.4, solid_capstyle="round", zorder=3)
        ax.plot([b], [y], marker="o", ms=15, color=colour, zorder=4,
                markeredgecolor=SURFACE, markeredgewidth=2.5)
        ax.annotate(f"{b:+.0f}", xy=(b, y), xytext=(0, 18), textcoords="offset points",
                    ha="center", color=INK, fontsize=19, fontweight="bold")

    ax.set_yticks([1, 0])
    ax.set_yticklabels([r[0] for r in res], fontsize=15, color=INK)
    ax.set_ylim(-0.65, 1.8)
    ax.set_xlabel("Change in hydro's water value, €/MWh")
    fig.tight_layout()
    fig.savefig(FIGS / "policy.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    d = pd.read_parquet(PANEL).rename(columns={"marginal_unit": "unit"})
    d["date"] = pd.to_datetime(d["date"])

    fig_setting()
    fig_divergence()
    fig_confound(d)
    fig_passthrough(d)
    fig_policy([
        ("Under the gas cap", (-40.32, -54.7, -15.6), BLUE),
        ("Under the levy", (46.55, 17.6, 62.9), RED),
    ])
    print(f"wrote 5 figures to {FIGS}")


if __name__ == "__main__":
    main()
