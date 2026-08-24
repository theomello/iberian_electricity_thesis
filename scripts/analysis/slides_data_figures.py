#!/usr/bin/env python3
"""Figures for the data-and-designs supervisor deck.

    .venv/bin/python scripts/analysis/slides_data_figures.py

Companion to slides_figures.py, which builds the hydro-design deck. Same house
style, imported rather than restated. Every number here is re-derived from the
files in data/ and outputs/tables/ -- parquet row counts come from file
metadata, not from the stale outputs/tables/dataset_inventory.csv -- so a figure
cannot drift away from what is actually on disk.

Writes PNG at 200 dpi into slides/figures/.
"""
from __future__ import annotations

import glob
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

mpl.use("Agg")

from slides_figures import (  # noqa: E402  -- sets rcParams on import
    BLUE, ORANGE, RED, INK, INK2, MUTED, GRID, SURFACE, _frame,
)

ROOT = Path(__file__).resolve().parent.parent.parent
FIGS = ROOT / "slides" / "figures"
TABLES = ROOT / "outputs" / "tables"

GREEN, PURPLE = "#3f9e6b", "#8a6bbf"


def _span(path: Path, col: str) -> tuple[pd.Timestamp, pd.Timestamp, int]:
    """Min/max of a date column plus row count, reading only that column."""
    t = pq.read_table(path, columns=[col])
    s = pd.to_datetime(pd.Series(t.column(col).to_pandas()))
    return s.min(), s.max(), t.num_rows


def _monthly_span(pattern: str) -> tuple[pd.Timestamp, pd.Timestamp, int]:
    """Span of a month-partitioned dataset, from filenames and file metadata."""
    fs = sorted(glob.glob(str(ROOT / pattern)))
    rows = sum(pq.ParquetFile(f).metadata.num_rows for f in fs)
    stems = [Path(f).stem.split("_")[-1] for f in fs]
    lo = pd.Timestamp(f"{stems[0][:4]}-{stems[0][4:]}-01")
    hi = pd.Timestamp(f"{stems[-1][:4]}-{stems[-1][4:]}-01") + pd.offsets.MonthEnd(0)
    return lo, hi, rows


def inventory() -> pd.DataFrame:
    """Re-derive the data inventory: coverage span and size, per source."""
    rows = []

    def add(label, group, lo, hi, n, unit="rows"):
        rows.append(dict(label=label, group=group, lo=lo, hi=hi, n=n, unit=unit))

    # OMIE, month-partitioned
    for label, pat in [
        ("Day-ahead bids and offers, per plant", "data/omie/bids/parquet/*.parquet"),
        ("Intraday bids and offers, per plant", "data/omie/intraday/parquet/*.parquet"),
        ("Plant capacity and declared cost floor", "data/omie/cab/parquet/*.parquet"),
        ("Operating schedule and forward contracts", "data/omie/pdbf/parquet/*.parquet"),
    ]:
        lo, hi, n = _monthly_span(pat)
        add(label, "Market", lo, hi, n)

    # Single-file sources
    singles = [
        ("Day-ahead clearing price", "Market", "data/omie/prices/omie_day_ahead_prices.parquet", "date"),
        ("Spanish demand and generation, every 5 minutes", "System", "data/ree/ree_realtime_5min.parquet", "utc_timestamp"),
        ("Spanish generation by technology, daily", "System", "data/ree/ree_generation_daily.parquet", "local_date"),
        ("Portuguese generation, every 15 minutes", "System", "data/ren/ren_production_15min.parquet", "utc_timestamp"),
        ("Reservoir water storage, weekly", "Water and fuel", "data/miteco/embalses_historico.parquet", "date"),
        ("Natural gas price, daily", "Water and fuel", "data/mibgas/mibgas_price_index_daily.parquet", "date"),
        ("Carbon permit price, daily", "Water and fuel", "data/investing/eua_carbon_price_daily.parquet", "date"),
        ("Implied marginal cost per plant, daily", "Water and fuel", "data/jrc_ppdb/implied_marginal_cost_daily.parquet", "date"),
    ]
    for label, group, rel, col in singles:
        p = ROOT / rel
        if not p.exists():
            print(f"  skip (absent): {rel}")
            continue
        lo, hi, n = _span(p, col)
        add(label, group, pd.Timestamp(lo).tz_localize(None), pd.Timestamp(hi).tz_localize(None), n)

    return pd.DataFrame(rows)


def fig_coverage(inv: pd.DataFrame):
    """What we hold, and over what window -- one bar per source."""
    inv = inv.iloc[::-1].reset_index(drop=True)
    colours = {"Market": BLUE, "System": ORANGE, "Water and fuel": GREEN}

    fig, ax = plt.subplots(figsize=(14.6, 5.6))
    _frame(ax, axis="x")
    for i, r in inv.iterrows():
        ax.barh(i, (r.hi - r.lo).days, left=r.lo, height=0.62,
                color=colours[r.group], zorder=3)
        n = r.n
        txt = f"{n/1e6:.0f} M" if n >= 1e6 else f"{n/1e3:.0f} k" if n >= 1e4 else f"{n:,}"
        ax.annotate(txt, xy=(r.hi, i), xytext=(8, 0), textcoords="offset points",
                    va="center", color=INK2, fontsize=12)

    ax.set_yticks(range(len(inv)))
    ax.set_yticklabels(inv.label, fontsize=13)
    ax.set_xlim(pd.Timestamp("2016-10-01"), pd.Timestamp("2028-06-01"))
    ax.set_xticks([pd.Timestamp(f"{y}-01-01") for y in range(2017, 2027, 2)])
    ax.set_xticklabels([str(y) for y in range(2017, 2027, 2)])
    for x, lab, col in ((pd.Timestamp("2021-09-16"), "levy", RED),
                        (pd.Timestamp("2022-06-15"), "gas cap", RED)):
        ax.axvline(x, color=col, lw=1.6, ls=(0, (4, 3)), zorder=4)
    ax.annotate("levy →|← gas cap", xy=(pd.Timestamp("2022-02-01"), len(inv) - 0.2),
                ha="center", color=RED, fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / "data_coverage.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_price_vre():
    """The window the data covers: a price shock, and a doubling VRE share."""
    px = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "price_es"])
    px["date"] = pd.to_datetime(px["date"])
    m = px.groupby(px["date"].dt.to_period("M"))["price_es"].mean()
    vre = pd.read_csv(TABLES / "vre_share_by_year.csv")
    vre = vre[vre.zone == "Spain"]

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12.4, 5.4), sharex=False,
                                 gridspec_kw=dict(height_ratios=[1.35, 1]))
    _frame(a1)
    a1.fill_between(m.index.to_timestamp(), m.values, color=BLUE, alpha=0.18, zorder=2)
    a1.plot(m.index.to_timestamp(), m.values, color=BLUE, lw=2.4, zorder=3)
    for x, lab in ((pd.Timestamp("2021-09-16"), "levy"), (pd.Timestamp("2022-06-15"), "gas cap")):
        a1.axvline(x, color=RED, lw=1.6, ls=(0, (4, 3)), zorder=4)
        a1.annotate(lab, xy=(x, 215), xytext=(4, 0), textcoords="offset points",
                    color=RED, fontsize=13, fontweight="bold")
    a1.set_ylabel("Price, €/MWh")
    a1.set_ylim(0, 250)
    a1.set_xlim(pd.Timestamp("2018-01-01"), pd.Timestamp("2026-06-01"))

    _frame(a2)
    a2.bar(vre.year, vre.share, color=ORANGE, width=0.62, zorder=3)
    for _, r in vre.iterrows():
        a2.annotate(f"{r.share:.0f}", xy=(r.year, r.share), xytext=(0, 5),
                    textcoords="offset points", ha="center", color=INK2, fontsize=12)
    a2.set_ylabel("Wind + solar, %")
    a2.set_ylim(0, 52)
    a2.set_xticks(vre.year.astype(int))
    fig.tight_layout()
    fig.savefig(FIGS / "price_vre.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_concentration_markup():
    """The headline: markup ability doubled while concentration fell.

    Re-derived rather than transcribed -- eta from the residual-demand panel,
    shares and HHI from CNMC, combined by the same L = s / eta identity
    markup_from_shares.py uses.
    """
    d = pd.read_parquet(TABLES / "residual_demand_slope_full.parquet",
                        columns=["year", "eta_h5"])
    cnmc = pd.read_parquet(ROOT / "data/cnmc/cnmc_generation_shares.parquet").set_index("year")
    eta = d.groupby("year").eta_h5.median()
    yrs = sorted(set(eta.index) & set(cnmc.index))
    eta = eta.loc[yrs]
    lerner = (cnmc.loc[yrs, ["IBERDROLA", "ENDESA"]].mean(axis=1) / eta)
    hhi = cnmc.loc[yrs, "HHI"]

    li = (lerner / lerner.iloc[0] * 100).values
    hi = (hhi / hhi.iloc[0] * 100).values
    yr = np.array(yrs)

    fig, ax = plt.subplots(figsize=(12.4, 4.6))
    _frame(ax)
    ax.axhline(100, color=GRID, lw=1.2, zorder=1)
    for y, colour, label in ((li, BLUE, "Ability to mark up  (s / η)"),
                             (hi, ORANGE, "Measured concentration  (HHI)")):
        ax.plot(yr, y, color=colour, lw=3, marker="o", ms=8, zorder=3,
                solid_capstyle="round", markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(label, xy=(yr[-1], y[-1]), xytext=(12, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=14)
    ax.annotate(f"×{li[-1]/100:.1f} since 2018", xy=(yr[-2], li[-2]), xytext=(0, 20),
                textcoords="offset points", color=INK, fontsize=15,
                fontweight="bold", ha="center")
    ax.set_ylabel("Index, 2018 = 100")
    ax.set_xlim(2017.9, 2026.1)
    ax.set_ylim(55, 235)
    ax.set_xticks(yr)
    fig.tight_layout()
    fig.savefig(FIGS / "concentration_markup.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_eta_vre():
    """The mechanism: residual demand steepens where renewables are highest."""
    d = pd.read_parquet(TABLES / "residual_demand_slope_full.parquet",
                        columns=["year", "eta_h5", "vre_share"])
    d["tercile"] = d.groupby("year").vre_share.transform(
        lambda s: pd.qcut(s, 3, labels=["low", "mid", "high"], duplicates="drop"))
    g = d.groupby(["year", "tercile"], observed=True).eta_h5.median().unstack()

    fig, ax = plt.subplots(figsize=(12.4, 4.6))
    _frame(ax)
    for col, colour, label in (("low", MUTED, "Lowest third of hours by VRE"),
                               ("high", RED, "Highest third")):
        ax.plot(g.index, g[col], color=colour, lw=3, marker="o", ms=8, zorder=3,
                solid_capstyle="round", markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(label, xy=(g.index[-1], g[col].iloc[-1]), xytext=(12, 0),
                    textcoords="offset points", va="center", color=INK, fontsize=14)
    ax.fill_between(g.index, g["low"], g["high"], color=RED, alpha=0.09, zorder=2)
    ax.set_ylabel("Elasticity of residual demand, η")
    ax.set_xlim(2017.9, 2028.4)
    ax.set_ylim(0, None)
    ax.set_xticks(g.index)
    fig.tight_layout()
    fig.savefig(FIGS / "eta_vre.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_marginal_tech():
    """Who sets the price: hydro is the modal marginal technology throughout."""
    d = pd.read_csv(TABLES / "marginal_technology.csv").set_index("year")
    keep = ["hydro", "gas CCGT", "pumped storage", "wind", "solar", "coal"]
    other = d.drop(columns=keep).sum(axis=1)
    colours = [BLUE, ORANGE, PURPLE, GREEN, "#e8b13a", INK2]

    fig, ax = plt.subplots(figsize=(12.4, 4.6))
    _frame(ax)
    ax.stackplot(d.index, *[d[k] for k in keep], other.values,
                 colors=colours + [GRID], zorder=3)
    # Label each band at the year where that band is widest, so a technology
    # that is only ever marginal in one era (coal, CCGT) still gets a label.
    bands = [d[k] for k in keep] + [other.rename("other")]
    cum = np.cumsum(np.vstack([b.values for b in bands]), axis=0)
    for i, (b, c) in enumerate(zip(bands, colours + [MUTED])):
        j = int(np.argmax(b.values))
        if b.values[j] < 5:
            continue
        j = min(max(j, 1), len(d.index) - 2)  # keep the label off the plot edges
        y0 = cum[i - 1, j] if i else 0.0
        ax.annotate(b.name, xy=(d.index[j], (y0 + cum[i, j]) / 2),
                    color="white" if c != GRID else INK2,
                    fontsize=13, fontweight="bold", ha="center", va="center")
    ax.set_ylabel("Share of periods, %")
    ax.set_ylim(0, 100)
    ax.set_xlim(d.index.min(), d.index.max())
    ax.set_xticks(d.index)
    fig.tight_layout()
    fig.savefig(FIGS / "marginal_tech.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    inv = inventory()
    print(inv.to_string(index=False))
    fig_coverage(inv)
    fig_price_vre()
    fig_concentration_markup()
    fig_eta_vre()
    fig_marginal_tech()
    print(f"\nwrote 5 figures to {FIGS}")


if __name__ == "__main__":
    main()
