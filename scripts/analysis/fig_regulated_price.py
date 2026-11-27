"""Figure: the regulated energy price (access tolls + charges, EUR/MWh) by hour of a working day, before and after
the 1 June 2021 reform, for each access tariff, in July and in August.

Old regime: access-toll energy terms of Orden IET/107/2014 and IET/2444/2014 (periods of Orden ITC/2794/2007);
new regime: tolls of the CNMC resolution of 18 March 2021 (Circular 3/2020 periods) + charges of Orden TED/371/2021,
in force 1 June to 15 September 2021, before the charge cut of RDL 17/2021 (outputs/tables/tou_tariff_prices_2021.csv).
Both come from the same tables the estimates use: tou_tariff_schedule (3.0, 6.1-6.4) and tou_cross_tariff (2.0).
The wholesale energy price is not included. Example days: Wednesday 14 July and Wednesday 11 August 2021.
Writes paper/figures/regulated_price_by_hour.pdf (and a .png preview).
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
FIG = ROOT / "paper" / "figures"
DAYS = {"July": pd.Timestamp("2021-07-14"), "August": pd.Timestamp("2021-08-11")}
TARIFFS = [("2.0", "2.0TD: up to 15 kW (mostly households)"), ("3.0", "3.0TD: above 15 kW, below 1 kV (small business)"),
           ("6.1", "6.1TD: 1–30 kV"), ("6.2", "6.2TD: 30–72.5 kV"),
           ("6.3", "6.3TD: 72.5–145 kV"), ("6.4", "6.4TD: 145 kV and above")]
import fig_style as S  # noqa: E402


def step(ax, y, **kw):
    """Hourly step line over 0-24 h."""
    ax.step(np.arange(25), np.append(y, y[-1]), where="post", **kw)


def main():
    tabs = CT.old_new_tables(list(DAYS.values()))
    S.apply()
    fig, axes = plt.subplots(len(TARIFFS), 2, figsize=(6.3, 7.6), sharex=True, sharey="row",
                             gridspec_kw={"hspace": 0.62, "wspace": 0.16})
    for i, (tar, title) in enumerate(TARIFFS):
        for j, (month, day) in enumerate(DAYS.items()):
            ax = axes[i, j]
            t = tabs[tar].loc[day].sort_index()
            old, new = t.old_price.to_numpy(), t.new_price.to_numpy()
            x = np.arange(25)
            ax.fill_between(x, np.append(old, old[-1]), np.append(new, new[-1]), step="post", color=S.NEW_FILL,
                            lw=0, alpha=0.75)
            step(ax, old, color=S.OLD, lw=1.4, ls=(0, (2.5, 1.5)), label="Before reform (to 31 May 2021)")
            step(ax, new, color=S.NEW, lw=1.8, label="After reform (from 1 June 2021)")
            ax.set_ylim(0, None)
            ax.set_xlim(0, 24)
            ax.set_xticks(range(0, 25, 6))
            ax.set_xticks(range(25), minor=True)
            ax.set_xticklabels(["0", "6", "12", "18", "24"])
            S.clean_axes(ax)
            if i == 0:
                ax.text(0.5, 1.45, f"{month}, working day", transform=ax.transAxes, ha="center", va="bottom", color=S.INK,
                        fontsize=9.5, fontweight="bold")
            if j == 0:
                code, desc = title.split(": ", 1)
                ax.text(0, 1.10, code, transform=ax.transAxes, color=S.INK, fontweight="bold", ha="left", va="bottom")
                ax.text(0.20, 1.10, desc, transform=ax.transAxes, color=S.INK2, ha="left", va="bottom")
    fig.supylabel("Tolls + charges (€/MWh)", color=S.INK2, fontsize=8, x=0.035)
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0), labelcolor=S.INK,
               handlelength=2.6, columnspacing=2.5)
    fig.text(0.5, 0.045, "Hour of the day (Wednesday 14 July and 11 August 2021)", ha="center",
             color=S.INK2)
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "regulated_price_by_hour.pdf")
    fig.savefig(FIG / "regulated_price_by_hour.png", dpi=170)
    # numbers behind the figure, for the text
    for tar, _ in TARIFFS:
        for month, day in DAYS.items():
            t = tabs[tar].loc[day]
            ev, ni = t.loc[19:20], t.loc[0:6]
            print(f"{tar:>4} {month:<7} evening/night ratio old {ev.old_price.mean() / ni.old_price.mean():5.1f}  "
                  f"new {ev.new_price.mean() / ni.new_price.mean():5.1f}")


if __name__ == "__main__":
    main()
