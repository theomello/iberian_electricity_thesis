"""Shared look for the thesis figures (paper/figures/): colours, fonts, axis styling.

Colours follow the default validated palette of the dataviz guide: series blue for the post-reform regime, a neutral
grey for the old regime, and a single-hue blue ramp (dark = expensive) for tariff periods.
"""
import matplotlib.pyplot as plt

INK, INK2, INK3 = "#0b0b0b", "#52514e", "#8a8984"
GRID = "#e4e3df"
NEW, OLD = "#2a78d6", "#8a8984"
NEW_FILL = "#cde2fb"
# blue ramp, darkest first: P1 (most expensive) ... P6 (cheapest)
RAMP6 = ["#0d366b", "#1c5cab", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"]
RAMP3 = [RAMP6[0], RAMP6[2], RAMP6[5]]
FLAT = "#b9b8b2"   # a single-period tariff: no time differentiation


def apply():
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
        "axes.edgecolor": INK3, "axes.linewidth": 0.6, "axes.labelcolor": INK2,
        "xtick.color": INK2, "ytick.color": INK2, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 0, "xtick.minor.size": 1.2, "xtick.minor.width": 0.4,
        "legend.frameon": False, "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    })


def clean_axes(ax, grid=True):
    ax.spines[["top", "right", "left"]].set_visible(False)
    if grid:
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
