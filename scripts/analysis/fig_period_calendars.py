"""Figure: the tariff period calendars before and after the 1 June 2021 reform, working days, peninsula.

Each panel is a month x hour grid coloured by the tariff period that applies (darkest = most expensive). Rows are the
tariff families: 2.0 (households, up to 15 kW: old 2.0A single period -> 2.0TD three periods), 3.0 (above 15 kW,
below 1 kV: old 3.0A three periods by winter/summer clock time -> 3.0TD six periods) and 6.x (1 kV and above: old
6.1A-6.4 six periods by day type -> 6.1TD-6.4TD six periods; 3.0TD and 6.xTD share one calendar after the reform).
Period rules: tou_tariff_schedule (Orden ITC/2794/2007 annex II; Circular 3/2020 art. 7) and tou_cross_tariff (2.0TD).
June is split because the old six-period calendar changes day type on 16 June. Each row is a representative working
day in that month of 2021 (the 15th, or the next working day; 8 and 23 June). On weekends and national holidays the
new calendars are flat at the cheapest period (P6; P3 for 2.0TD), as was the old six-period calendar; old 3.0A did
not distinguish weekends. Writes paper/figures/period_calendars.pdf (and a .png preview).
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig_style as S  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
FIG = ROOT / "paper" / "figures"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun 1–15", "Jun 16–30", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def rep_days(hol):
    out = []
    for lab in MONTHS:
        if lab.startswith("Jun"):
            d = pd.Timestamp("2021-06-08") if "1–15" in lab else pd.Timestamp("2021-06-23")
        else:
            d = pd.Timestamp(f"2021-{MONTHS.index(lab) + 1 - (MONTHS.index(lab) > 5):02d}-15")
        while d.dayofweek >= 5 or d in hol:
            d += pd.Timedelta(days=1)
        out.append(d)
    return out


def p20_new(h):
    return 3 if h < 8 else (1 if (10 <= h < 14 or 18 <= h < 22) else 2)


def grids():
    hol = TS.holidays()
    days = rep_days(hol)
    g = {k: np.zeros((len(days), 24), int) for k in ("2.0 old", "2.0 new", "3.0 old", "3.0 new", "6 old", "6 new")}
    for i, d in enumerate(days):
        dt = TS.old_day_type(d, d in hol)
        for h in range(24):
            g["2.0 old"][i, h] = 0                              # single period
            g["2.0 new"][i, h] = p20_new(h)
            g["3.0 old"][i, h] = TS.old_period_3(d, h)
            g["3.0 new"][i, h] = g["6 new"][i, h] = TS.new_period_6(d, h, d in hol)
            g["6 old"][i, h] = TS.old_period_6(dt, h)
    return g


def colour_index(grid, n):
    """Map periods to the ramp: 0 = flat, 3-period tariffs use dark/mid/light of the 6-step ramp."""
    if n == 1:
        return np.zeros_like(grid)
    if n == 3:
        return np.vectorize({1: 1, 2: 3, 3: 6}.get)(grid)
    return grid


def main():
    S.apply()
    g = grids()
    cmap = ListedColormap([S.FLAT] + S.RAMP6)
    rows = [("2.0", r"2.0A $\rightarrow$ 2.0TD", "up to 15 kW (mostly households)", 1, 3),
            ("3.0", r"3.0A $\rightarrow$ 3.0TD", "above 15 kW, below 1 kV (small business)", 3, 6),
            ("6", r"6.1A–6.4 $\rightarrow$ 6.1TD–6.4TD", "1 kV and above (industry)", 6, 6)]
    headers = []
    fig, axes = plt.subplots(3, 2, figsize=(6.3, 7.4), sharex=True, gridspec_kw={"hspace": 0.42, "wspace": 0.06})
    for i, (key, code, desc, n_old, n_new) in enumerate(rows):
        for j, (when, n) in enumerate((("old", n_old), ("new", n_new))):
            ax = axes[i, j]
            ci = colour_index(g[f"{key} {when}"], n)
            ax.imshow(ci, cmap=cmap, vmin=-0.5, vmax=6.5, aspect="auto", interpolation="nearest",
                      extent=(0, 24, len(MONTHS), 0))
            # thin surface-coloured gaps between month rows
            for y in range(1, len(MONTHS)):
                ax.axhline(y, color="white", lw=0.8)
            # period numbers once per run of equal cells in a row (only where the run is wide enough)
            per = g[f"{key} {when}"]
            for r in range(per.shape[0]):
                h0 = 0
                for h in range(1, 25):
                    if h == 24 or per[r, h] != per[r, h0]:
                        if h - h0 >= 3 and per[r, h0] > 0:
                            c = ci[r, h0]
                            ax.text((h0 + h) / 2, r + 0.5, f"P{per[r, h0]}", ha="center", va="center", fontsize=5.2,
                                    color="white" if c <= 3 else S.INK)
                        h0 = h
            ax.set_xticks(range(0, 25, 6))
            ax.set_xticklabels(["0", "6", "12", "18", "24"])
            ax.set_yticks(np.arange(len(MONTHS)) + 0.5)
            ax.set_yticklabels(MONTHS if j == 0 else [], fontsize=6.5)
            ax.tick_params(axis="y", length=0)
            for s in ax.spines.values():
                s.set_visible(False)
            if i == 0:
                ax.text(0.5, 1.22, "Before (to 31 May 2021)" if j == 0 else "After (from 1 June 2021)",
                        transform=ax.transAxes, ha="center", va="bottom", fontsize=9.5, fontweight="bold",
                        color=S.INK)
            if j == 0:
                t = ax.text(0, 1.03, code, transform=ax.transAxes, fontweight="bold", color=S.INK, va="bottom")
                headers.append((ax, t, desc))
    fig.text(0.5, 0.055, "Hour of the day, working day", ha="center", color=S.INK2)
    # legend: a grey swatch for "single period" and the six-step ramp from most expensive to cheapest
    lg = fig.add_axes((0.1, 0.012, 0.8, 0.022))
    lg.set_xlim(0, 12)
    lg.set_ylim(0, 1)
    lg.axis("off")
    lg.add_patch(plt.Rectangle((0.6, 0), 0.6, 1, color=S.FLAT))
    lg.text(1.3, 0.5, "single period", va="center", color=S.INK, fontsize=7)
    for k, c in enumerate(S.RAMP6):
        lg.add_patch(plt.Rectangle((6.4 + k * 0.6, 0), 0.6, 1, color=c, ec="white", lw=0.6))
    lg.text(6.3, 0.5, "most expensive", ha="right", va="center", color=S.INK, fontsize=7)
    lg.text(10.1, 0.5, "cheapest", ha="left", va="center", color=S.INK, fontsize=7)
    fig.text(0.5, -0.008, "Shade ranks periods within each tariff; labels give the period. Weekends and holidays: cheapest period all day.",
             ha="center", color=S.INK3, fontsize=6.5)
    # description after each bold tariff code, placed from the code's measured width
    fig.canvas.draw()
    for ax, t, desc in headers:
        bb = t.get_window_extent().transformed(ax.transAxes.inverted())
        ax.text(bb.x1 + 0.03, 1.03, desc, transform=ax.transAxes, color=S.INK2, va="bottom")
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "period_calendars.pdf")
    fig.savefig(FIG / "period_calendars.png", dpi=170)


if __name__ == "__main__":
    main()
