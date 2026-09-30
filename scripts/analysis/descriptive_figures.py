#!/usr/bin/env python3
"""The six figures for the price-formation chapter.

    .venv/bin/python scripts/analysis/descriptive_figures.py

Every number is read from the panels in outputs/tables/ (or the raw fetched
data in data/) at run time. Nothing is transcribed -- see fig_divergence in
slides_figures.py for why that matters: it hardcoded a Lerner array that is
exactly the defect this script exists to avoid. These are paper figures, not
slides: no chart titles, the dataviz reference palette, 200 dpi.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

mpl.use("Agg")

ROOT = Path(__file__).resolve().parent.parent.parent
FIGS = ROOT / "outputs" / "figures"

ETA_PANEL = ROOT / "outputs" / "tables" / "residual_demand_slope_full.parquet"
# The firm indices as rebuilt on 2026-09-29 (firm_incentive_rebuild.py): owner
# tier, own demand removed from the slope, incentive on the net auction position.
# The raw firm panel's incentive_h* subtracts contracts twice and is not plotted.
FIRM_PANEL = ROOT / "outputs" / "tables" / "firm_incentive_net.parquet"
CONC_PANEL = ROOT / "outputs" / "tables" / "concentration_panel.parquet"
ANAT_PANEL = ROOT / "outputs" / "tables" / "supply_anatomy_panel.parquet"
REQUIRED = [ETA_PANEL, FIRM_PANEL, CONC_PANEL, ANAT_PANEL]

CNMC_PANEL = ROOT / "data" / "cnmc" / "cnmc_generation_shares.parquet"
PRICES_PANEL = ROOT / "data" / "omie" / "prices" / "omie_day_ahead_prices.parquet"
DEMAND_FORECAST = ROOT / "data" / "ree" / "ree_demand_forecast_5min.parquet"
DEMAND_REALTIME = ROOT / "data" / "ree" / "ree_realtime_5min.parquet"

# dataviz reference palette, light mode -- matches scripts/analysis/slides_figures.py
BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8983"
GRID, SURFACE = "#e6e5e1", "#ffffff"

THIN_NOTE = "Coverage thins in later years -- see Figure 1 for retained-period shares."

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


def check_inputs() -> int:
    missing = [p for p in REQUIRED if not p.exists()]
    for p in missing:
        print(f"  MISSING {p.relative_to(ROOT)}", file=sys.stderr)
    if missing:
        print("Run Tasks 2-6 first.", file=sys.stderr)
    return 1 if missing else 0


def _retained_share(eta: pd.DataFrame) -> pd.Series:
    """Periods retained in the eta panel vs. every day-ahead period published.

    The eta panel drops zero-price and other excluded periods (see
    residual_demand_slope.py); the day-ahead price panel is complete. Capping
    the price panel at the eta panel's own max date matters for 2026, whose
    bids stop at the ~3-month publication frontier while prices run further.
    """
    prices = pd.read_parquet(PRICES_PANEL, columns=["date"])
    prices["date"] = pd.to_datetime(prices["date"])
    prices = prices[prices["date"] <= eta["date"].max()]
    total = prices.groupby(prices["date"].dt.year).size()
    retained = eta.groupby(eta["date"].dt.year).size()
    return (retained / total).dropna()


def fig_divergence(eta: pd.DataFrame, conc: pd.DataFrame, cnmc: pd.DataFrame) -> None:
    """eta, HHI_total and HHI_margin on a common 2018 = 100 base.

    Single axis, by the no-dual-axis rule: quantities of different units go on
    a common base rather than on two scales. A companion strip below shows the
    retained share of periods by year, so the late years are not read as
    equally sampled as the early ones.
    """
    e = eta.groupby(eta.date.dt.year).eta_h5.median()
    c = conc.groupby(conc.date.dt.year).agg(
        tot=("hhi_total", "median"), mar=("hhi_margin_h5", "median"))
    base = lambda s: s / s.loc[2018] * 100
    retained = _retained_share(eta)

    fig = plt.figure(figsize=(12.4, 5.4))
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.10)
    ax = fig.add_subplot(gs[0])
    axr = fig.add_subplot(gs[1], sharex=ax)

    _frame(ax)
    ax.axhline(100, color=GRID, lw=1.2, zorder=1)
    for s, colour, label in ((base(e), BLUE, "Residual demand elasticity"),
                             (base(c.mar), RED, "Concentration at the margin"),
                             (base(c.tot), ORANGE, "Concentration, all volume")):
        ax.plot(s.index, s.values, color=colour, lw=3, marker="o", ms=7, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(label, xy=(s.index[-1], s.iloc[-1]), xytext=(12, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=14)
    cn = base(cnmc.set_index("year").HHI.loc[2018:2023])
    ax.plot(cn.index, cn.values, color=MUTED, lw=2, ls=(0, (4, 3)), zorder=2)
    # The dashed line runs visually coincident with "Concentration, all volume"
    # (orange) for most of its span, so a same-color leader line anchored to
    # its own endpoint -- not just nearby text -- is what makes the label
    # unambiguous rather than reading as attached to whichever line is closest.
    ax.annotate("CNMC, published", xy=(2023, cn.loc[2023]), xytext=(34, -34),
                textcoords="offset points", color=MUTED, fontsize=12,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=1.3,
                                 shrinkA=2, shrinkB=4))
    for a, b in ((2021.71, 2023.99), (2022.46, 2023.99)):
        ax.axvspan(a, b, color=GRID, alpha=0.45, zorder=0)
    ax.set_ylabel("Index, 2018 = 100")
    ax.set_xlim(2017.9, 2027.4)
    ax.tick_params(labelbottom=False)

    axr.bar(retained.index, retained.values * 100, width=0.6, color=MUTED, zorder=3)
    axr.set_ylim(0, 100)
    axr.set_yticks([0, 50, 100])
    axr.set_ylabel("Retained\nshare, %", fontsize=11, color=INK2)
    axr.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    axr.set_axisbelow(True)
    axr.tick_params(length=0, labelsize=12)
    for side in ("top", "right", "left"):
        axr.spines[side].set_visible(False)
    axr.set_xlim(2017.9, 2027.4)

    fig.savefig(FIGS / "divergence.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_band_density(anat: pd.DataFrame) -> None:
    """Median offer density within +-5 EUR/MWh of the clearing price, by year."""
    g = anat.groupby(anat.date.dt.year).band_density_h5.median()

    fig, ax = plt.subplots(figsize=(11.5, 4.4))
    _frame(ax)
    ax.plot(g.index, g.values, color=BLUE, lw=3, marker="o", ms=7, zorder=3,
            markeredgecolor=SURFACE, markeredgewidth=2, solid_capstyle="round")
    ax.set_ylabel("MW offered within ±5 €/MWh of the clearing price")
    ax.set_ylim(0, g.values.max() * 1.12)
    ax.set_xlim(g.index.min() - 0.4, g.index.max() + 0.4)
    ax.text(0.0, -0.24, THIN_NOTE, transform=ax.transAxes, fontsize=10.5, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIGS / "band_density.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_stack_shape(anat: pd.DataFrame) -> None:
    """Two components of the offered supply curve's shape, both trending up."""
    g = anat.groupby(anat.date.dt.year)[["share_at_zero", "share_below_p"]].median()

    fig, ax = plt.subplots(figsize=(11.5, 4.4))
    _frame(ax)
    for col, colour, label in (("share_at_zero", BLUE, "Offered at zero"),
                               ("share_below_p", ORANGE, "Offered below clearing price")):
        ax.plot(g.index, g[col], color=colour, lw=3, marker="o", ms=7, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=2, solid_capstyle="round",
                label=label)
    ax.legend(loc="upper left", frameon=False, fontsize=12.5)
    ax.set_ylabel("Share of offered sell volume")
    ax.set_ylim(0, 1)
    ax.set_xlim(g.index.min() - 0.4, g.index.max() + 0.4)
    ax.text(0.0, -0.24, THIN_NOTE, transform=ax.transAxes, fontsize=10.5, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIGS / "stack_shape.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_eta_hour_year(eta: pd.DataFrame) -> None:
    """The Jha & Leslie test: does the elasticity collapse concentrate in the
    evening ramp, where thermal plants that shut at midday do not restart?

    Madrid local time, not UTC -- the duck curve is a solar phenomenon and
    must be read on the clock the sun keeps.
    """
    d = eta.copy()
    d["hour"] = pd.to_datetime(d.utc_timestamp, utc=True).dt.tz_convert(
        "Europe/Madrid").dt.hour
    g = d.pivot_table(index="hour", columns=d.date.dt.year,
                      values="eta_h5", aggfunc="median")
    fig, ax = plt.subplots(figsize=(10.5, 6.4))
    im = ax.imshow(g.values, aspect="auto", origin="lower", cmap="magma",
                   extent=[g.columns.min() - 0.5, g.columns.max() + 0.5, -0.5, 23.5])
    ax.set_ylabel("Hour, Madrid local time")
    ax.set_yticks([0, 6, 12, 18, 23])
    fig.colorbar(im, ax=ax, label="Residual demand elasticity (median)")
    ax.text(0.0, -0.14, THIN_NOTE, transform=ax.transAxes, fontsize=10.5, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIGS / "eta_hour_year.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_firm_ability(firm: pd.DataFrame) -> None:
    """ability_exp_h5 and incentive_exp_h5 by year for the six largest firms.

    ability (BLUE) is the firm's price impact: EUR/MWh per 1% of its output
    withheld, with the firm's own offers -- sell AND buy -- taken out of the
    slope. incentive (ORANGE) scales it by the firm's exposure to the auction
    price, its EXPOSED net auction position (cleared sales minus purchases,
    regulated pass-through suppliers excluded), so it turns
    negative for a net buyer, who gains when the price falls. Both from
    firm_incentive_rebuild.py; see notes/rq-descriptive-price-formation.md §4.5.
    """
    d = firm.copy()
    d["mwh"] = d.q_exp_mw * d.resolution_min / 60
    top6 = d.groupby("firm").mwh.sum().sort_values(ascending=False).head(6).index.tolist()

    d["year"] = d.date.dt.year
    cols = ["ability_exp_h5", "incentive_exp_h5"]
    g = d[d.firm.isin(top6)].groupby(["firm", "year"])[cols].median().reset_index()
    buyer = (d[d.firm.isin(top6)].assign(b=lambda x: x.net_exp_mw < 0)
             .groupby("firm").b.mean())

    lo, hi = g[cols].min().min(), g[cols].max().max()
    pad = (hi - lo) * 0.10
    ylim = (lo - pad, hi + pad)

    fig = plt.figure(figsize=(13.6, 7.2))
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.14)
    axes = []
    for i, f in enumerate(top6):
        r, c = divmod(i, 3)
        ax = fig.add_subplot(gs[r, c], sharey=axes[0] if axes else None)
        _frame(ax)
        dd = g[g.firm == f].sort_values("year")
        ax.axhline(0, color=GRID, lw=1.0, zorder=1)
        # incentive drawn wider and underneath, so where the two coincide (a
        # firm that never buys) the orange series stays visible at the edges.
        ax.plot(dd.year, dd.incentive_exp_h5, color=ORANGE, lw=4.6, marker="o", ms=9,
                zorder=2, markeredgecolor=SURFACE, markeredgewidth=1.4,
                label="Incentive (exposed net auction position)")
        ax.plot(dd.year, dd.ability_exp_h5, color=BLUE, lw=2.2, marker="o", ms=6,
                zorder=3, markeredgecolor=SURFACE, markeredgewidth=1.4,
                label="Ability (own offers removed)")
        ax.set_ylim(*ylim)
        ax.text(0.05, 0.92, f, transform=ax.transAxes, fontsize=13.5,
                fontweight="bold", color=INK, va="top")
        # Read off the data, not a firm name: the note appears wherever the
        # firm's incentive is negative on average.
        if dd.incentive_exp_h5.mean() < 0:
            ax.text(0.05, 0.78, f"net buyer in {buyer[f]:.0%} of periods",
                    transform=ax.transAxes, ha="left", va="top", fontsize=10.5,
                    color=MUTED, style="italic")
        if c != 0:
            ax.tick_params(labelleft=False)
        else:
            ax.set_ylabel("€/MWh per 1% withheld", fontsize=12)
        ax.tick_params(labelsize=11)
        axes.append(ax)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=13)
    fig.text(0.125, 0.0, THIN_NOTE, fontsize=10.5, color=MUTED)
    fig.savefig(FIGS / "firm_ability.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_predictability() -> None:
    """Hourly forecast-error dispersion by year: did both series degrade together?

    Excludes the three unusable periods documented in CLAUDE.md: the REE
    realtime contract change (2025-12-12 onward), the 2025Q2 blackout
    quarter, and the unexplained 2023Q1 mean-error episode.
    """
    fc = pd.read_parquet(DEMAND_FORECAST)
    rt = pd.read_parquet(DEMAND_REALTIME, columns=["utc_timestamp", "demand"])
    d = fc.merge(rt, on="utc_timestamp", how="inner")

    local = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
    quarter = local.dt.year.astype(str) + "Q" + local.dt.quarter.astype(str)
    BAD_FROM = pd.Timestamp("2025-12-12", tz="UTC")
    BAD_QUARTERS = ("2025Q2", "2023Q1")
    d = d[(d.utc_timestamp < BAD_FROM) & (~quarter.isin(BAD_QUARTERS))].copy()
    d["err_forecast"] = d.demand - d.demand_forecast_mw
    d["err_scheduled"] = d.demand - d.demand_scheduled_mw

    hourly = (d.groupby(d.utc_timestamp.dt.floor("h"))
                .agg(err_forecast=("err_forecast", "mean"),
                     err_scheduled=("err_scheduled", "mean")))
    hourly["year"] = hourly.index.tz_convert("Europe/Madrid").year
    counts = hourly.groupby("year").size()
    years = counts[counts >= 1000].index  # drop the sub-day boundary sliver
    g = (hourly[hourly.year.isin(years)]
         .groupby("year").agg(sd_forecast=("err_forecast", "std"),
                              sd_scheduled=("err_scheduled", "std")))

    fig, ax = plt.subplots(figsize=(11.5, 4.7))
    _frame(ax)
    for col, colour, label in (("sd_forecast", BLUE, "vs. forecast (prevista)"),
                               ("sd_scheduled", ORANGE, "vs. scheduled (programada)")):
        ax.plot(g.index, g[col], color=colour, lw=3, marker="o", ms=7, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=2, solid_capstyle="round",
                label=label)

    y2022 = g.loc[2022, "sd_forecast"]
    ax.annotate(f"{y2022:.0f} MW", xy=(2022, y2022), xytext=(0, 14),
                textcoords="offset points", ha="center", color=INK, fontsize=13,
                fontweight="bold")

    ax.legend(loc="upper left", frameon=False, fontsize=12.5)
    ax.set_ylabel("SD of hourly-mean forecast error, MW")
    ax.set_ylim(0, g.to_numpy().max() * 1.18)
    ax.set_xlim(years.min() - 0.4, years.max() + 0.4)
    ax.text(0.0, -0.24,
            "Excludes 2025-12-12 onward (realtime contract change), 2025Q2 (blackout), "
            "2023Q1 (unexplained).",
            transform=ax.transAxes, fontsize=10, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIGS / "predictability.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    if check_inputs():
        return 1
    FIGS.mkdir(parents=True, exist_ok=True)

    eta = pd.read_parquet(ETA_PANEL)
    firm = pd.read_parquet(FIRM_PANEL)
    conc = pd.read_parquet(CONC_PANEL)
    anat = pd.read_parquet(ANAT_PANEL)
    cnmc = pd.read_parquet(CNMC_PANEL)
    for df in (eta, firm, conc, anat):
        df["date"] = pd.to_datetime(df["date"])

    fig_divergence(eta, conc, cnmc)
    fig_band_density(anat)
    fig_stack_shape(anat)
    fig_eta_hour_year(eta)
    fig_firm_ability(firm)
    fig_predictability()

    print(f"wrote 6 figures to {FIGS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
