"""Render the data-coverage timeline: what is on disk and what is missing.

One row per dataset, time on the x-axis. Colour encodes *status* (have /
not yet published / no source) -- the reserved status palette, not a
categorical one. Status never carries meaning alone here: every bar is also
labelled and a legend is always present.

    .venv/bin/python scripts/plot_data_coverage.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Patch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omie_common import REPO  # noqa: E402

OUT = REPO / "outputs" / "figures" / "data_coverage.png"

# --- status palette + chrome ink -------------------------------------------
HAVE = "#0ca30c"      # good
LAG = "#fab219"       # warning
MISSING = "#d03b3b"   # critical
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8983"
SURFACE = "#fcfcfb"
GRID = "#e6e5e1"

WINDOW_START = date(2018, 1, 1)
WINDOW_END = date(2026, 5, 31)
BID_FRONTIER = date(2026, 5, 8)
TODAY = date(2026, 8, 7)
MTU_SWITCH = date(2025, 10, 1)
REE_MIGRATION = date(2025, 12, 12)
DROPOUTS = [date(2018, 6, 14), date(2022, 10, 12)]

GROUPS = [
    ("OMIE  ·  market", [
        ("Day-ahead prices   ES + PT", "hourly → 15-min", WINDOW_START, WINDOW_END,
         "have", "91,247"),
        ("Unit-level bid curves   ES + PT", "hourly → 15-min", WINDOW_START,
         BID_FRONTIER, "have", "354,247,072"),
    ]),
    ("REE  ·  Spain", [
        ("Generation, demand, flows", "5-minute", WINDOW_START, WINDOW_END,
         "have", "885,085"),
        ("Generation / demand / balance", "daily", WINDOW_START, WINDOW_END,
         "have", "122,334"),
        ("Installed capacity", "needs ESIOS token", WINDOW_START, WINDOW_END,
         "missing", ""),
    ]),
    ("REN  ·  Portugal", [
        ("Production breakdown", "15-minute", WINDOW_START, WINDOW_END,
         "have", "3,801,736"),
        ("Market prices   ES + PT", "hourly", WINDOW_START, WINDOW_END,
         "have", "147,502"),
        ("Consumption / supply balance", "daily", WINDOW_START, WINDOW_END,
         "have", "77,834"),
        ("Installed capacity", "monthly", WINDOW_START, WINDOW_END,
         "have", "887"),
    ]),
]


def rounded_bar(ax, x0, x1, y, h, color, hatch=None, ec="none", lw=0):
    p = FancyBboxPatch(
        (mdates.date2num(x0), y - h / 2),
        mdates.date2num(x1) - mdates.date2num(x0), h,
        boxstyle="round,pad=0,rounding_size=16",
        mutation_aspect=0.010,
        linewidth=lw, facecolor=color, edgecolor=ec, hatch=hatch, zorder=3,
    )
    ax.add_patch(p)


def main() -> int:
    fig, ax = plt.subplots(figsize=(15, 8.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    gt = ax.get_yaxis_transform()   # x in axes fraction, y in data units

    # ---- lay rows out top-down, with a gap between groups ----
    y = 0.0
    placed, headers = [], []
    for gname, rows in GROUPS:
        y -= 0.95
        headers.append((y, gname))
        for r in rows:
            y -= 0.92
            placed.append((y, r))
        y -= 0.45
    bottom = y

    bar_h = 0.50
    for yy, (label, res, s, e, status, rows) in placed:
        if status == "missing":
            rounded_bar(ax, s, e, yy, bar_h, SURFACE, hatch="////",
                        ec=MISSING, lw=1.3)
            ax.text(mdates.date2num(s) + 70, yy, "no token-free source",
                    va="center", ha="left", fontsize=9, color=MISSING,
                    fontweight="bold", zorder=6,
                    bbox=dict(boxstyle="round,pad=0.34", fc=SURFACE,
                              ec="none"))
        else:
            rounded_bar(ax, s, e, yy, bar_h, HAVE)
            ax.text(mdates.date2num(s) + 70, yy, f"{rows} rows", va="center",
                    ha="left", fontsize=8.9, color="#ffffff",
                    fontweight="bold", zorder=6)
        ax.text(-0.012, yy + 0.09, label, transform=gt, va="center", ha="right",
                fontsize=9.8, color=INK, zorder=5)
        ax.text(-0.012, yy - 0.20, res, transform=gt, va="center", ha="right",
                fontsize=7.9, color=MUTED, zorder=5)

    for yy, gname in headers:
        ax.text(-0.268, yy, gname, transform=gt, va="center", ha="left",
                fontsize=10.6, color=INK, fontweight="bold", zorder=5)

    # ---- callout 1: publication lag on the bid row ----
    bid_y = placed[1][0]
    rounded_bar(ax, BID_FRONTIER, TODAY, bid_y, bar_h, LAG)
    ax.text(mdates.date2num(TODAY) + 40, bid_y, "1", va="center", ha="left",
            fontsize=8.5, color="#ffffff", fontweight="bold", zorder=8,
            bbox=dict(boxstyle="circle,pad=0.30", fc=INK2, ec="none"))

    # ---- callout 2: whole-day dropouts, marked under the bid bar ----
    for d in DROPOUTS:
        ax.plot(mdates.date2num(d), bid_y - bar_h / 2 - 0.10, marker="^",
                markersize=6.5, color=MISSING, markeredgecolor=SURFACE,
                markeredgewidth=1.1, zorder=8, clip_on=False)
    ax.text(mdates.date2num(DROPOUTS[1]) + 90, bid_y - bar_h / 2 - 0.12, "2",
            va="center", ha="left", fontsize=8.5, color="#ffffff",
            fontweight="bold", zorder=8,
            bbox=dict(boxstyle="circle,pad=0.30", fc=INK2, ec="none"))

    # ---- callout 3: structural breaks ----
    for d in (MTU_SWITCH, REE_MIGRATION):
        ax.axvline(d, color=INK2, lw=1, ls=(0, (4, 3)), alpha=0.5, zorder=2)
    ax.text(mdates.date2num(MTU_SWITCH) - 40, -0.42, "3", va="center",
            ha="right", fontsize=8.5, color="#ffffff", fontweight="bold",
            zorder=8, bbox=dict(boxstyle="circle,pad=0.30", fc=INK2, ec="none"))

    # ---- notes block, in the clear space below the rows ----
    notes = [
        ("1", "Bids stop 2026-05-08 — OMIE publishes unit-level offers on a "
              "~3-month lag, so the newest ~3 months of every other series "
              "will never have matching bids."),
        ("2", "Whole-day unit dropouts in OMIE's own files (2018-06-14, "
              "2022-10-12): a block of units absent for all 24 hours. "
              "~0.1% of days; left unpatched."),
        ("3", "Structural breaks — 2025-10-01 OMIE 15-minute MTU switch; "
              "2025-12-12 REE endpoint contract change (3 fields swap)."),
    ]
    ny = bottom - 0.30
    for num, txt in notes:
        ax.text(-0.268, ny, num, transform=gt, va="center", ha="left",
                fontsize=7.6, color="#ffffff", fontweight="bold", zorder=8,
                bbox=dict(boxstyle="circle,pad=0.28", fc=INK2, ec="none"))
        ax.text(-0.248, ny, txt, transform=gt, va="center", ha="left",
                fontsize=8.4, color=INK2, zorder=6, wrap=False)
        ny -= 0.46

    # ---- axes ----
    ax.set_xlim(mdates.date2num(date(2017, 9, 1)), mdates.date2num(date(2026, 12, 1)))
    ax.set_ylim(ny - 0.35, 0.30)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", colors=INK2, labelsize=9, length=0, pad=6)
    ax.set_yticks([])
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    for sp in ax.spines.values():
        sp.set_visible(False)

    handles = [
        Patch(facecolor=HAVE, label="on disk, validated"),
        Patch(facecolor=LAG, label="not yet published at source"),
        Patch(facecolor=SURFACE, edgecolor=MISSING, hatch="////", linewidth=1.2,
              label="no token-free source"),
    ]
    ax.legend(handles=handles, loc="upper right", frameon=False, fontsize=9,
              ncol=3, bbox_to_anchor=(1.005, 1.075), labelcolor=INK2,
              handlelength=1.5, handleheight=1.0, columnspacing=1.6)

    fig.suptitle("Spain / MIBEL data inventory — coverage and gaps",
                 x=0.010, y=0.973, ha="left", fontsize=16, color=INK,
                 fontweight="bold")
    fig.text(0.010, 0.918,
             "Study window 2018-01-01 → 2026-05-31 (3,073 days).  359.4 M rows, "
             "3.8 GB, every source token-free.  Portugal is inside MIBEL — it "
             "clears jointly with Spain, so it is part of the unit of analysis, "
             "not a neighbour.",
             fontsize=9.6, color=INK2, ha="left")
    fig.text(0.010, 0.022,
             f"Fetched {TODAY:%Y-%m-%d}.  Cross-validated where an independent "
             "source exists: REN and OMIE prices agree to 100.0000% over 67,919 "
             "hourly instants, including 3,568 market-splitting hours.",
             fontsize=8.1, color=MUTED, ha="left")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(left=0.268, right=0.988, top=0.858, bottom=0.075)
    fig.savefig(OUT, facecolor=SURFACE)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
