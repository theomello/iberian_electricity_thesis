#!/usr/bin/env python3
"""Was the hydro capacity the firms did not offer out of service, or offered intraday?

    .venv/bin/python scripts/analysis/hydro_unoffered_capacity.py

`rq-water-value-forward.md` §5.5 found that Endesa and Naturgy offer only part of their
hydro capacity in the day-ahead auction, and sell part of the rest bilaterally. This asks
whether what is left was declared unavailable (§5.6), whether it was offered in the
intraday auction sessions instead (§5.7), whether reserves could hold it (§5.8), and,
on a sample of days, how much REE's per-unit files show held as reserve or used later
(§5.9).

THE TEST, WITH AN EXAMPLE. Endesa's Ebro unit declares 1,899 MW (`cab` max power). In an
hour it offers 150 MW in the auction and delivers 400 MW under bilateral contracts, so
1,349 MW is neither offered nor contracted: the unoffered capacity G. If its generator
groups have declared 900 MW out of service in that hour, 900 MW of G is explained and
449 MW is not.

DATA, per Spanish hydro unit of the six large groups and hour (step caches, 2019-01 →
2025-09):
  C   `cab` max power that day
  O   MW offered in the auction (status O, not withdrawn by a minimum income condition)
  B   MW delivered under bilateral contracts (PDBF role 4)
  U   MW its generator groups declared unavailable: OMIE `indisp`, each declaration's last
      revision, group capacity minus the available MW it declares; the largest loss when
      several cover the same group and hour; summed over groups, at most C. Groups link
      to units through REE's register of physical units (ESIOS archive 81, `up`; a
      2026-08-12 snapshot), whose codes are the ones `indisp` uses.
  G   C − O − B, at least 0
Explained share = Σ min(U, G) / Σ G.

INTRADAY. What is neither declared out nor explained, R = G − min(U, G), against the
unit's sell offers in the intraday auction sessions (`curva_pibc_uof`, status O, side V;
quarter-hours averaged to the hour):
  I   MW offered to sell in the hour, the largest over the sessions (each session re-offers
      the same capacity, so they are not added)
  S   MW sold net over the sessions (cleared sell less cleared buy)
  A   MW cleared in the day-ahead auction (step caches)
A unit can offer intraday what it offered day-ahead and did not sell (O − A) as well as G,
so the share of R offered intraday is bounded:
  upper   Σ min(I, R) / Σ R
  lower   Σ min(max(I − (O − A), 0), R) / Σ R   (intraday offers first re-offer O − A)
and the share of R sold intraday is at most Σ min(max(S, 0), R) / Σ R. The continuous
intraday market (trades between sessions) is not in these files.

RESERVES (§5.8). No per-unit reserve data is on disk, so a bound: what is left after the
intraday upper bound, R − min(I, R), summed over a group's units each hour, against the
upward secondary regulation band REE allocated to the whole peninsula that hour (ESIOS
632, every technology and firm; 15-minute values averaged to the hour). If the whole
system's band is smaller, reserves cannot explain the rest even if every MW of it came
from this group's hydro. The additional upward reserve (ESIOS 627) was allocated in 602
hours, all in 2019, and is left out.

BY UNIT, ON A SAMPLE OF DAYS (§5.9). REE's I90DIA workbooks for the 15th of each month
(`fetch/fetch_esios_i90.py --parse`): per unit and hour, the upward secondary band
allocated (I90DIA05), and the energy scheduled after the day-ahead market, P48 − PDBF
(I90DIA02, I90DIA26): intraday auctions and continuous trading (PHFC − PDBF, I90DIA36) and
REE's balancing and real-time processes (P48 − PHFC). Against R, the unoffered capacity
outages do not explain, the shares Σ min(x, R) / Σ R for x = the band, the energy added
later, and both. Upper bounds: energy added later may also come from capacity offered
day-ahead that did not sell.

CAUSE, by keyword in the declaration's reason (first match wins):
  water     water or authority: reservoir level, minimum reserve, water quality, anoxia,
            flow, drought, concessions, and orders of the basin authority or the
            Directorate-General for Sustainability
  technical everything else: maintenance, revisions, rehabilitation, repairs, repowering

LIMITS. `indisp` is partial at source in 43 monthly zips, mostly from 2023 (CLAUDE.md):
planned outages are still seen, short-notice ones on missing days are not, so the explained
share is also given on days `indisp` holds a snapshot for. Groups never named in `indisp`
count as available. Times are Madrid local, read on the cache's hour index (an hour off on
the 23- and 25-hour days).

WRITES outputs/tables/hydro_unoffered_capacity.csv (by group and year; by unit; by hour of
day) and hydro_unavailable_daily.parquet (unit, date, mean U, gitignored).
Runs in about a minute.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from counterfactual_hydro import EPOCH, FIRST, LAST, bilateral  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
CACHE = ROOT / "outputs/cache/step"
OUT = TABLES / "hydro_unoffered_capacity.csv"
OUT_D = TABLES / "hydro_unavailable_daily.parquet"
SIX = ["EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "MOVHERA"]
WATER = ("NIVEL", "EMBALSE", "RESERVA MINIMA", "RESERVA MÍNIMA", "CALIDAD", "ANOXIA", "CAUDAL", "SEQUIA",
         "SEQUÍA", "COTA", "CONFEDERACI", "SOSTENIBILIDAD", "RESOLUCION", "RESOLUCIÓN", "DIRECCION GENERAL",
         "DIRECCIÓN GENERAL", "CONCESI")


def groups() -> pd.DataFrame:
    """uf, unit, group_mw: REE generator groups of the six groups' Spanish hydro units."""
    w = pd.read_parquet(TABLES / "hydro_cost_daily.parquet", columns=["unit", "group", "cls", "zone"])
    units = w[(w.cls == "hydro") & w.group.isin(SIX)].drop_duplicates("unit")
    uf = pd.read_parquet(DATA / "esios/esios_physical_units.parquet", columns=["uf", "up", "max_power_mw"])
    g = uf[uf.up.isin(units.unit)].rename(columns={"up": "unit", "max_power_mw": "group_mw"})
    return g.merge(units[["unit", "group"]], on="unit")


def declarations(g: pd.DataFrame) -> tuple[pd.DataFrame, set]:
    """One row per outage_id of these groups (last revision): uf, start, end (naive Madrid
    local), lost MW, cause; and the dates `indisp` holds a snapshot for."""
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(DATA / "omie/indisp/parquet/indisp_*.parquet")))])
    covered = set(pd.to_datetime(d.snapshot).dt.normalize())
    d["unit"] = d.unit.astype(str)
    d = d[d.unit.isin(g.uf)].sort_values("snapshot").drop_duplicates("outage_id", keep="last")
    d = d.merge(g[["uf", "group_mw"]], left_on="unit", right_on="uf")
    d["lost"] = (d.group_mw - d.available_mw).clip(lower=0)
    reason = d.reason.astype(str).str.upper()
    d["cause"] = np.where(reason.apply(lambda r: any(k in r for k in WATER)), "water", "technical")
    d["start"], d["end"] = pd.to_datetime(d.start), pd.to_datetime(d.end)
    return d[d.lost > 0][["uf", "start", "end", "lost", "cause", "reason"]], covered


def unavailable(dec: pd.DataFrame, g: pd.DataFrame, hids: np.ndarray) -> pd.DataFrame:
    """(hid, unit) -> U_technical, U_water: MW declared lost, the largest declaration per
    group and hour."""
    t0 = EPOCH + pd.to_timedelta(int(hids.min()), "h")
    t1 = EPOCH + pd.to_timedelta(int(hids.max()) + 1, "h")
    x = dec[(dec.start < t1) & (dec.end > t0)]
    rows = []
    for r in x.itertuples():
        a = max(int(np.ceil((r.start - EPOCH) / pd.Timedelta(hours=1))), int(hids.min()))
        b = min(int(np.ceil((r.end - EPOCH) / pd.Timedelta(hours=1))), int(hids.max()) + 1)
        if b > a:
            rows.append(pd.DataFrame({"hid": np.arange(a, b), "uf": r.uf, "lost": r.lost, "cause": r.cause}))
    if not rows:
        return pd.DataFrame(columns=["U_technical", "U_water"], dtype=float,
                            index=pd.MultiIndex.from_tuples([], names=["hid", "unit"]))
    h = pd.concat(rows).sort_values("lost", ascending=False).drop_duplicates(["uf", "hid"])
    h["unit"] = h.uf.map(g.set_index("uf").unit)
    return h.pivot_table(index=["hid", "unit"], columns="cause", values="lost", aggfunc="sum", fill_value=0.0) \
            .add_prefix("U_").reindex(columns=["U_technical", "U_water"], fill_value=0.0)


def intraday(ym: str, units: list[str]) -> pd.DataFrame:
    """(hid, unit) -> I, S: the largest MW offered to sell in any intraday session, and the
    MW sold net over the sessions; quarter-hours averaged to the hour."""
    x = pd.read_parquet(DATA / f"omie/intraday/parquet/intraday_{ym}.parquet",
                        columns=["session", "date", "hour", "quarter", "unit", "side", "status", "power_mw"],
                        filters=[("unit", "in", units)])
    x = x.assign(unit=x.unit.astype(str), side=x.side.astype(str), status=x.status.astype(str))
    x["hid"] = (pd.to_datetime(x.date) - EPOCH).dt.days * 24 + x.hour - 1
    k = ["session", "hid", "unit", "quarter"]
    q = lambda m, v: x[m].groupby(k).power_mw.sum().rename(v)              # MW per session-quarter
    sell = q((x.side == "V") & (x.status == "O"), "I")
    net = q((x.side == "V") & (x.status == "C"), "s").sub(q((x.side == "C") & (x.status == "C"), "b"), fill_value=0)
    i = sell.groupby(["session", "hid", "unit"]).mean().groupby(["hid", "unit"]).max()
    s = net.rename("S").groupby(["session", "hid", "unit"]).mean().groupby(["hid", "unit"]).sum()
    return pd.concat([i, s], axis=1)


def month(ym: str, g: pd.DataFrame, dec: pd.DataFrame) -> pd.DataFrame:
    units = g.unit.unique().tolist()
    h = pd.read_parquet(CACHE / f"hydro_{ym}.parquet", columns=["hid", "date", "unit", "mw", "cleared_mw", "withdrawn"])
    hids = np.arange(h.hid.min(), h.hid.max() + 1)
    h = h[h.unit.isin(units)]
    o = h[(~h.withdrawn) & (h.mw > 0)].groupby(["hid", "unit"]).mw.sum().rename("O")
    a = h.groupby(["hid", "unit"]).cleared_mw.first().rename("A")              # the hour's total, on every step
    c = pd.read_parquet(DATA / f"omie/cab/parquet/cab_{ym}.parquet", columns=["date", "unit", "max_power_mw"],
                        filters=[("unit", "in", units)])
    c = c.groupby(["unit", pd.to_datetime(c.date).rename("date")]).max_power_mw.max().rename("C").reset_index()
    grid = pd.MultiIndex.from_product([hids, units], names=["hid", "unit"]).to_frame(index=False)
    grid["date"] = EPOCH + pd.to_timedelta(grid.hid // 24, "D")
    d = grid.merge(c, on=["unit", "date"]).set_index(["hid", "unit"])
    d = d.join(o).join(a).join(bilateral(ym, units).rename("B")).join(unavailable(dec, g, hids))
    d = d.join(intraday(ym, units)).fillna(0.0)
    d = d[d.C > 0].reset_index()
    d["U"] = (d.U_technical + d.U_water).clip(upper=d.C)
    d["G"] = (d.C - d.O - d.B).clip(lower=0)
    d["E"] = np.minimum(d.U, d.G)
    d["E_water"] = np.minimum(d.U_water.clip(upper=d.C), d.G)              # water and authority first
    d["R"] = d.G - d.E
    d["I_up"] = np.minimum(d.I, d.R)
    d["I_lo"] = np.minimum((d.I - (d.O - d.A).clip(lower=0)).clip(lower=0), d.R)
    d["S_R"] = np.minimum(d.S.clip(lower=0), d.R)
    return d


def summary(d: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    s = d.groupby(by)[["C", "O", "A", "B", "G", "U", "E", "E_water", "E_cov", "G_cov", "R", "I", "S",
                       "I_up", "I_lo", "S_R"]].sum()
    hours = d.groupby(by).size()
    t = s[["C", "O", "B", "G", "U", "R", "I", "S"]].div(hours, axis=0)       # mean MW
    t["G_share_of_C"] = s.G / s.C
    t["explained"] = s.E / s.G
    t["explained_water"] = s.E_water / s.G
    t["explained_covered_days"] = s.E_cov / s.G_cov
    t["U_over_offered_or_contracted"] = (s.U - s.E) / s.U.where(s.U > 0)      # declared out yet offered/contracted
    t["R_intraday_upper"] = s.I_up / s.R
    t["R_intraday_lower"] = s.I_lo / s.R
    t["R_sold_intraday"] = s.S_R / s.R
    return t.join(hours.rename("hours"))


def reserves(d: pd.DataFrame) -> pd.DataFrame:
    """By year: the group's hourly unoffered capacity left after the intraday upper bound,
    against the whole peninsula's allocated upward secondary band (ESIOS 632)."""
    b = pd.read_parquet(DATA / "esios/esios_632.parquet", columns=["value", "datetime"])
    t = pd.to_datetime(b.datetime.str[:19])                                # Madrid local
    b["hid"] = (t.dt.normalize() - EPOCH).dt.days * 24 + t.dt.hour
    band = b.groupby("hid").value.mean().rename("band")
    d = d.assign(rest=d.R - d.I_up)
    rows = []
    for name, grp in [("ENDESA", ["ENDESA"]), ("NATURGY", ["NATURGY"]), ("ENDESA + NATURGY", ["ENDESA", "NATURGY"]),
                      ("ENDESA + NATURGY + EDP", ["ENDESA", "NATURGY", "EDP"])]:
        h = d[d.group.isin(grp)].groupby(["hid", "year"]).rest.sum().reset_index().merge(band, on="hid")
        for yr, x in [("all", h), *h.groupby("year")]:
            rows.append({"table": "reserves", "group": name, "year": yr, "hours": len(x), "rest": x.rest.mean(),
                         "band": x.band.mean(), "band_over_rest": x.band.sum() / x.rest.sum(),
                         "hours_band_covers_rest": (x.band >= x.rest).mean()})
    t = pd.DataFrame(rows)
    print("\nleft after outages and the intraday upper bound (mean MW, group total) against the whole "
          "peninsula's upward secondary band (ESIOS 632):")
    print(t.drop(columns="table").round(2).to_string(index=False))
    return t


def i90_sample(d: pd.DataFrame) -> pd.DataFrame:
    """By group, on the I90 sample days: R against the upward band held and the energy
    scheduled after the day-ahead market. The band is by unit to 2024-11-15; on the
    participant days after it, a firm's whole band (every technology) bounds its hydro's."""
    f = DATA / "esios/i90/i90_sample_hourly.parquet"
    if not f.exists():
        print("\nno I90 sample on disk (fetch/fetch_esios_i90.py --parse); §5.9 skipped")
        return pd.DataFrame()
    i = pd.read_parquet(f)
    unit_days = set(i[(i.sheet == "band") & (i.level == "unit")].date)
    s_ = i[(i.sheet != "band") & i.unit.isin(d.unit.unique())]
    w = s_.groupby(["date", "hour", "unit", "sheet"]).mw.sum().unstack("sheet").fillna(0.0).reset_index()
    band = (i[(i.sheet == "band") & (i.level == "unit") & (i.kind == "Subir")]
            .groupby(["date", "hour", "unit"]).mw.sum().rename("band").reset_index())
    x = d.assign(hour=d.hid % 24).merge(w, on=["date", "hour", "unit"]).merge(band, on=["date", "hour", "unit"], how="left")
    x["unit_day"] = x.date.isin(unit_days)
    x["band"] = x.band.fillna(0.0).where(x.unit_day)
    x["later"] = (x.p48 - x.pdbf).clip(lower=0)
    x["intraday"] = (x.phfc - x.pdbf).clip(lower=0)
    x["balancing"] = (x.p48 - x.phfc).clip(lower=0)
    for c in ("band", "later", "intraday", "balancing"):
        x[f"{c}_R"] = np.minimum(x[c], x.R)
    x["both_R"] = np.minimum(x.band + x.later, x.R)
    x["pdbf_gap"] = (x.pdbf - (x.A + x.B)).abs()
    rows = []
    for (grp, yr), z in [*(((k, "all"), v) for k, v in x.groupby("group")), *x.groupby(["group", "year"])]:
        u = z[z.unit_day]
        rows.append({"table": "i90 sample", "group": grp, "year": yr, "days": z.date.nunique(),
                     "band_days": u.date.nunique(), "R": z.R.mean(), "later": z.later.mean(),
                     "R_later": z.later_R.sum() / z.R.sum(), "R_intraday": z.intraday_R.sum() / z.R.sum(),
                     "R_balancing": z.balancing_R.sum() / z.R.sum(),
                     "band": u.band.mean(), "R_band": u.band_R.sum() / u.R.sum() if len(u) else np.nan,
                     "R_both": u.both_R.sum() / u.R.sum() if len(u) else np.nan,
                     "pdbf_check_mw": z.pdbf_gap.mean()})
    # participant days: the firm's whole band against its units' R, summed each hour
    firm = {"END": "ENDESA", "GN": "NATURGY", "HC": "EDP"}
    pb = (i[(i.sheet == "band") & (i.level == "participant") & (i.kind == "Subir") & i.unit.isin(firm)]
          .assign(group=lambda v: v.unit.map(firm)).groupby(["date", "hour", "group"]).mw.sum().rename("band_firm"))
    g = x[~x.unit_day].groupby(["date", "hour", "group"])[["R", "later"]].sum().join(pb, how="inner").reset_index()
    for grp, z in g.groupby("group"):
        rows.append({"table": "i90 sample, participant days", "group": grp, "year": "2024-12 to 2025-09",
                     "days": z.date.nunique(), "R": z.R.mean(), "band": z.band_firm.mean(),
                     "R_band": np.minimum(z.band_firm, z.R).sum() / z.R.sum(),
                     "R_both": np.minimum(z.band_firm + z.later, z.R).sum() / z.R.sum()})
    t = pd.DataFrame(rows)
    print("\nI90 sample (15th of each month): unoffered capacity outages do not explain (R, mean MW per unit-hour) "
          "against the upward band held (unit-level days) and the energy added after the day-ahead market; shares of R:")
    print(t[(t.table == "i90 sample") & (t.year == "all")].drop(columns=["table", "year"]).round(2).to_string(index=False))
    print(t[(t.table == "i90 sample") & t.group.isin(["ENDESA", "NATURGY"]) & (t.year != "all")]
          [["group", "year", "days", "R", "R_band", "R_later", "R_both"]].round(2).to_string(index=False))
    print("\nparticipant days: firm's whole upward band against its hydro units' R (group total, MW):")
    print(t[t.table != "i90 sample"][["group", "days", "R", "band", "R_band", "R_both"]].round(2).to_string(index=False))
    return t


def main() -> int:
    g = groups()
    dec, covered = declarations(g)
    print(f"{g.unit.nunique()} units, {len(g)} generator groups, {g.group_mw.sum():,.0f} MW; "
          f"{len(dec):,} declarations ({dec.cause.value_counts().to_dict()})")
    w = dec[dec.cause == "water"]
    print("water or authority, most frequent reasons:")
    print(w.reason.astype(str).str[:90].value_counts().head(12).to_string())
    months = [p.stem.split("_")[1] for p in sorted(CACHE.glob("hydro_2*.parquet"))]
    d = pd.concat([month(m, g, dec) for m in months if FIRST <= m <= LAST], ignore_index=True)
    d["group"] = d.unit.map(g.drop_duplicates("unit").set_index("unit").group)
    d["year"] = d.date.dt.year
    cov = d.date.isin(covered)
    d["E_cov"], d["G_cov"] = d.E.where(cov, 0.0), d.G.where(cov, 0.0)
    print(f"{len(d):,} unit-hours; days with an indisp snapshot: {cov.mean():.3f}")

    pd.set_option("display.width", 220)
    rows = []
    for name, by in [("group", ["group"]), ("group-year", ["group", "year"]), ("unit", ["group", "unit"])]:
        t = summary(d, by).reset_index()
        print(f"\nby {name} (mean MW; shares of unoffered capacity G):")
        print(t.round(2).to_string(index=False))
        rows.append(t.assign(table=name))
    rows.append(reserves(d))
    rows.append(i90_sample(d))
    d["hour"] = d.hid % 24
    t = (d[d.year >= 2023].groupby(["group", "hour"])[["G", "C", "E"]].sum()
         .assign(G_share_of_C=lambda x: x.G / x.C, unexplained_share_of_C=lambda x: (x.G - x.E) / x.C)
         [["G_share_of_C", "unexplained_share_of_C"]].reset_index())
    print("\nunoffered capacity over C by hour of day, 2023–2025:")
    print(t.pivot(index="hour", columns="group", values="unexplained_share_of_C").round(2).to_string())
    rows.append(t.assign(table="hour 2023-2025"))
    pd.concat(rows, ignore_index=True).to_csv(OUT, index=False)
    d.groupby(["unit", "date"], as_index=False)[["C", "U", "U_technical", "U_water"]].mean().to_parquet(OUT_D, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}, {OUT_D.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
