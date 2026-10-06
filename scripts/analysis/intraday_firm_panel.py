#!/usr/bin/env python3
"""Each group's intraday position and slope, and its dispatchable units' intraday offers.

    .venv/bin/python scripts/analysis/intraday_firm_panel.py [--months 202301 ...]

Framework spec §9.5 and §9.7 step 5: the intraday counterpart of `firm_x.py` (X) and
`outage_offer_panel.py` (offer levels), on OMIE's intraday auctions (`curva_pibc_uof`).
MIBEL's six sessions, 2019-01-01 (REE's D-1 forecasts start) → 2024-06-13 (the
European IDA auctions replaced them on the 14th); hourly throughout. Sessions 1–3
cover the whole day, 4 from hour 5, 5 from hour 8, 6 from hour 13.

PER SESSION s, DELIVERY DATE AND PERIOD, for each group (as in firm_x.py):
  n_mw        exposed net cleared position in that session: sell − buy over the
              group's units, regulated pass-through suppliers excluded, ownership by
              date and share (lib/unit_ownership)
  n_built_mw  the same with pass-through suppliers in
  slope       (all offered MW within ±H of the session's Spanish price, both sides,
              − the group's own exposed offered MW in that band) / 2H
  X           n_mw / slope, NaN below MIN_SLOPE
  p_s, split  the published session price (`marginalpibc`, Spain) and whether
              Portugal's differs; identity_gap as in firm_x
Groups: every group that owns a leg-D unit on some date (`leg_d_units`); the offer
regression needs no others.

UNIT OFFERS (leg D's units: storage hydro, pumped-storage turbines, combined cycle,
coal), sell offers in each session: o25, o50 (offer price at 25% and 50% of the unit's
offered volume, as in outage_offer_panel.py) and off_mw; the unit's largest owner that
day (`group`, `firm5`).

Writes outputs/tables/intraday_firm_panel.parquet and intraday_offer_panel.parquet.
"""
from __future__ import annotations

import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from leg_d_panel import FIRMS, leg_d_units  # noqa: E402
from unit_ownership import attach_owners, majority_group, spells  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
BIDS = DATA / "omie/intraday/parquet"
OUT_FIRM = TABLES / "intraday_firm_panel.parquet"
OUT_OFFERS = TABLES / "intraday_offer_panel.parquet"
START, END = "2019-01-01", "2024-06-13"
SKEY = ["session", "date", "period"]
H = 5.0
MIN_SLOPE = 5.0
PRICE_CAP = 1000.0


def session_prices() -> pd.DataFrame:
    p = pd.read_parquet(DATA / "omie/intraday_prices/omie_intraday_prices.parquet")
    p["date"] = pd.to_datetime(p.date)
    p = p[(p.date >= START) & (p.date <= END)]
    if p.duplicated(SKEY).any():
        raise SystemExit("more than one published price per session, date and period")
    p["split"] = p.price_a != p.price_b
    return p.rename(columns={"price_b": "p_s"})[SKEY + ["p_s", "split"]]


def unit_offers(b: pd.DataFrame) -> pd.DataFrame:
    """unit, session, date, period: off_mw, o25, o50 from the sell offers (steps sorted
    by price, prices capped at PRICE_CAP)."""
    b = b[(b.power_mw > 0)].sort_values(["unit"] + SKEY + ["price_eur_mwh"], kind="stable", ignore_index=True)
    codes, keys = pd.factorize(pd.MultiIndex.from_frame(b[["unit"] + SKEY]), sort=False)
    size = np.bincount(codes)
    start = np.concatenate([[0], np.cumsum(size)[:-1]])
    cum = b.groupby(codes, sort=False).power_mw.cumsum().to_numpy()
    price = np.minimum(b.price_eur_mwh.to_numpy(), PRICE_CAP)
    out = pd.DataFrame({c: keys.get_level_values(i) for i, c in enumerate(["unit"] + SKEY)})
    out["off_mw"] = cum[start + size - 1]

    def at(target: np.ndarray) -> np.ndarray:
        below = np.bincount(codes, weights=(cum < target[codes]).astype(float), minlength=len(size)).astype(np.int64)
        return price[start + np.minimum(below, size - 1)]

    out["o25"] = at(0.25 * out.off_mw.to_numpy())
    out["o50"] = at(0.50 * out.off_mw.to_numpy())
    return out


def month(ym: str, umap: pd.DataFrame, groups: list[str], dunits: pd.DataFrame, sp: pd.DataFrame,
          px: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    b = pq.read_table(BIDS / f"intraday_{ym}.parquet",
                      columns=["session", "date", "period", "resolution_min", "unit", "side", "status", "power_mw",
                               "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b[(b.date >= START) & (b.date <= END)]
    if (b.resolution_min != 60).any():
        raise SystemExit(f"{ym}: intraday rows not hourly")
    for c in ("unit", "side", "status"):
        b[c] = b[c].astype(str)
    b["sgn"] = b.side.map({"V": 1.0, "C": -1.0})

    c = b[b.status == "C"]
    sv = c.power_mw.where(c.side == "V", 0.0).groupby([c.session, c.date, c.period]).sum()
    bv = c.power_mw.where(c.side == "C", 0.0).groupby([c.session, c.date, c.period]).sum()
    idg = ((sv - bv).abs() / sv.where(sv > 0)).rename("identity_gap").reset_index()

    m = attach_owners(c[c.unit.isin(set(umap.unit))], umap)
    m = m[m.group.isin(groups)]
    gk = SKEY + ["group"]
    n_b = (m.power_mw * m.sgn).groupby([m[k] for k in gk]).sum().rename("n_built_mw")
    me = m[~m.pt]
    n_e = (me.power_mw * me.sgn).groupby([me[k] for k in gk]).sum().rename("n_mw")

    o = b[b.status == "O"].merge(px[SKEY + ["p_s"]], on=SKEY, how="inner")
    o = o[(o.price_eur_mwh - o.p_s).abs() <= H]
    band = o.groupby(SKEY).power_mw.sum().rename("band_mw")
    om = attach_owners(o[o.unit.isin(set(umap.unit))], umap)
    om = om[om.group.isin(groups) & ~om.pt]
    own = om.groupby([om[k] for k in gk]).power_mw.sum().rename("own_band_mw")

    per = px[px.date.dt.strftime("%Y%m") == ym]
    out = per.merge(pd.DataFrame({"group": groups}), how="cross")
    out = out.merge(idg, on=SKEY, how="left").merge(band.reset_index(), on=SKEY, how="left")
    out = out.merge(pd.concat([n_b, n_e, own], axis=1).reset_index(), on=gk, how="left")
    out[["n_built_mw", "n_mw", "own_band_mw", "band_mw"]] = out[["n_built_mw", "n_mw", "own_band_mw",
                                                                  "band_mw"]].fillna(0.0)
    out["slope"] = (out.band_mw - out.own_band_mw) / (2 * H)
    out["X"] = np.where(out.slope >= MIN_SLOPE, out.n_mw / out.slope, np.nan)

    s = b[(b.status == "O") & (b.side == "V") & b.unit.isin(set(dunits.unit))]
    u = unit_offers(s).merge(dunits, on="unit")
    ud = u[["unit", "date"]].drop_duplicates()
    ud["group"] = majority_group(ud, sp).to_numpy()
    u = u.merge(ud, on=["unit", "date"])
    u["firm5"] = np.where(u.group.isin(FIRMS), u.group, "FRINGE")
    f32 = ["n_built_mw", "n_mw", "own_band_mw", "band_mw", "slope", "X", "p_s", "identity_gap"]
    out[f32] = out[f32].astype("float32")
    u[["off_mw", "o25", "o50"]] = u[["off_mw", "o25", "o50"]].astype("float32")
    return out, u


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (a check; writes *_check.parquet)")
    args = ap.parse_args()
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("intraday_*.parquet"))
    months = [m for m in months if START[:7].replace("-", "") <= m <= END[:7].replace("-", "")]
    if args.months:
        months = [m for m in months if m in args.months]
    sp = spells()
    dunits = leg_d_units()[["unit", "cls"]]
    groups = sorted(sp.loc[sp.unit.isin(set(dunits.unit)) & ~sp.pt, "group"].dropna().unique())
    umap = sp[sp.unit.isin(set(sp.loc[sp.group.isin(groups), "unit"]))]
    px = session_prices()
    print(f"{len(groups)} groups own a leg-D unit on some date; {len(dunits)} leg-D units; {len(months)} months")
    fparts, uparts = [], []
    for ym in months:
        t = time.time()
        f, u = month(ym, umap, groups, dunits, sp, px)
        fparts.append(f)
        uparts.append(u)
        print(f"  {ym}: {len(f):,} group-session-periods, {len(u):,} unit offers ({time.time() - t:.0f} s)",
              file=sys.stderr, flush=True)
    f = pd.concat(fparts, ignore_index=True)
    u = pd.concat(uparts, ignore_index=True)
    sfx = "_check" if args.months else ""
    of, ou = (p.with_name(p.stem + sfx + ".parquet") for p in (OUT_FIRM, OUT_OFFERS))
    f.to_parquet(of, index=False)
    u.to_parquet(ou, index=False)
    print(f"wrote {of.relative_to(ROOT)} ({len(f):,} rows) and {ou.relative_to(ROOT)} ({len(u):,} rows)")
    five = f[f.group.isin(FIRMS)]
    print("\nfive firms, mean exposed intraday position (MW) by session:\n"
          + five.pivot_table(index="group", columns="session", values="n_mw", aggfunc="mean").round(0).to_string())
    print("\nslope (MW per EUR/MWh) by session, median over the five:\n"
          + five.groupby("session").slope.median().round(1).to_string())
    print(f"\nX defined on {five.X.notna().mean():.3f} of the five's rows; unit offers by class: "
          f"{u.groupby('cls').size().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
