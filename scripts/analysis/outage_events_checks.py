#!/usr/bin/env python3
"""Outage events: the firm-level first stage and the two checks that faults are not chosen.

    .venv/bin/python scripts/analysis/outage_events_checks.py

Design: docs/specs/2026-10-19-outage-events-design.md §3, §4. Reads
build_outage_events.py's outputs. No offers, no β: this decides whether the faults
are worth using as an instrument at all.

FIRST STAGE. Each of the five firms' exposed net position n (`firm_x.parquet`, mean
over the UTC hour) on its fault dose by kind, its planned-stop dose, and its reactor
doses (unplanned, planned), with firm × month and hour effects (the hour effect absorbs
the price and every common shock), week clusters. Doses are MW of the firm's share of
output the outage removed (pumping: of purchases it removed). A dose that reaches n in
full reads −1 (generation) or +1 (pumping).
STOP RULE (fixed in the design): joint F of the fault doses below 20 -> stop.

TIMING 1. Price deviation from its month × hour mean, averaged over the 48–25 and the
24–1 hours before each binding fault spell starts. Chosen outages would follow prices.

TIMING 2. Do faults start more often when the owner has more at stake? Unit-days of
the units with a fault spell in the table, on days the unit was scheduled the day
before, whose largest owner is one of the five: 1 if a fault spell starts that day,
on the owner's X = n / |RD′| (and n) averaged over the previous day; unit × month and
date effects, week clusters. STOP RULE: a positive coefficient with p < 0.05 means the
faults follow the stake and are not used as an instrument.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from midday_hydro_iv import cluster_meat  # noqa: E402
from solar_first_stage import demean  # noqa: E402
from omie_common import day_periods_utc  # noqa: E402
from unit_ownership import majority_group, spells  # noqa: E402
from build_outage_events import schedule  # noqa: E402

TABLES = ROOT / "outputs/tables"
DATA = ROOT / "data"
FIRMS = ["ENDESA", "IBERDROLA", "NATURGY", "EDP", "REPSOL"]
GEN = ["gas", "coal", "steam", "hydro", "pumped_gen"]
OUT = TABLES / "outage_events_checks.csv"


def wald(y: np.ndarray, M: np.ndarray, cl: np.ndarray, idx: list[int]):
    inv = np.linalg.inv(M.T @ M)
    b = inv @ M.T @ y
    V = inv @ cluster_meat(M, y - M @ b, cl) @ inv
    se = np.sqrt(np.diag(V))
    r = b[idx]
    F = float(r @ np.linalg.solve(V[np.ix_(idx, idx)], r)) / len(idx)
    return b, se, F


def firm_hours() -> pd.DataFrame:
    x = pd.read_parquet(TABLES / "firm_x.parquet", columns=["date", "period", "firm", "net_mw", "X", "clean", "zero_price"])
    x["date"] = pd.to_datetime(x.date)
    n = x[["date", "period"]].drop_duplicates().groupby("date").period.max()
    utc = pd.concat([pd.DataFrame({"date": d, "period": range(1, k + 1), "utc": day_periods_utc(d.date(), int(k))})
                     for d, k in n.items()])
    utc["utc"] = pd.to_datetime(utc.utc, utc=True).dt.floor("h")
    x = x.merge(utc, on=["date", "period"])
    return x.groupby(["firm", "utc"], as_index=False).agg(n=("net_mw", "mean"), X=("X", "mean"),
                                                         clean=("clean", "min"), zp=("zero_price", "max"))


def first_stage(x: pd.DataFrame, rows: list) -> None:
    dz = pd.read_parquet(TABLES / "outage_event_dose.parquet")
    dz["col"] = np.where(dz.cls == "fault", "f_" + dz.kind,
                         np.where(dz.kind == "pumping", "p_pumping", "p_gen"))
    w = dz.pivot_table(index=["firm", "utc"], columns="col", values="dose_mw", aggfunc="sum").fillna(0).reset_index()
    rx = pd.read_parquet(TABLES / "reactor_outage_dose.parquet")
    rx = rx[rx.cls.isin(["unplanned", "planned"])].assign(col=lambda r: "rx_" + r.cls)
    rw = rx.pivot_table(index=["firm", "utc"], columns="col", values="lost_mw", aggfunc="sum").fillna(0).reset_index()
    d = x[x.firm.isin(FIRMS)].merge(w, on=["firm", "utc"], how="left").merge(rw, on=["firm", "utc"], how="left")
    fault = [c for c in [f"f_{k}" for k in GEN + ["pumping"]] if c in d.columns]
    others = [c for c in ["p_gen", "p_pumping", "rx_unplanned", "rx_planned"] if c in d.columns]
    cols = fault + others
    d[cols] = d[cols].fillna(0.0) / 1000.0                  # GW
    d["n"] = d.n / 1000.0                                    # GW
    d["fm"] = d.firm + "_" + d.utc.dt.strftime("%Y%m")
    d["t"] = d.utc.astype("int64")
    d["wk"] = d.utc.dt.strftime("%G%V")
    print("\nMEAN DOSE, MW, by firm (all hours):")
    print((d.groupby("firm")[cols].mean() * 1000).round(1).to_string())
    print("\nFIRST STAGE: n (GW) on doses (GW), firm x month + hour effects, week clusters")
    samples = (("all, 2018-2026", d), ("clean, priced", d[d.clean & ~d.zp]),
               ("2018-2022", d[d.utc.dt.year <= 2022]), ("2023-2026", d[d.utc.dt.year >= 2023]))
    for lab, g in samples:
        for y in ("n", "X"):
            g2 = g.dropna(subset=[y])
            use = [c for c in cols if g2[c].abs().sum() > 0]
            m = demean(g2, [y] + use, ["fm", "t"])
            idx = [i for i, c in enumerate(use) if c in fault]
            b, se, F = wald(m[y].to_numpy(), m[use].to_numpy(), g2.wk.to_numpy(), idx)
            print(f"  {lab:15s} {y}: joint F (fault doses) {F:6.1f}")
            print("     " + "  ".join(f"{c} {b[i]:+.3f} ({se[i]:.3f})" for i, c in enumerate(use)))
            for i, c in enumerate(use):
                rows.append(dict(check="first_stage", sample=lab, y=y, term=c, b=b[i], se=se[i],
                                 F_term=(b[i] / se[i]) ** 2, F_joint_fault=F))
    print("  (generation doses should read about -1 on n, pumping about +1; reactors read -0.86)")


def hourly_price() -> pd.Series:
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["utc_timestamp", "price_es"])
    px["utc"] = pd.to_datetime(px.utc_timestamp, utc=True).dt.floor("h")
    px = px.groupby("utc").price_es.mean().rename("p").reset_index()
    px["ym"] = px.utc.dt.strftime("%Y%m")
    px["hr"] = px.utc.dt.hour
    px["dev"] = px.p - px.groupby(["ym", "hr"]).p.transform("mean")
    return px.set_index("utc").dev


def timing_prices(s: pd.DataFrame, rows: list) -> None:
    dev = hourly_price()
    print("\nTIMING 1: price minus its month x hour mean before each spell starts, EUR/MWh (se)")
    print("  spells that bind and whose unit ran in the 7 days before")
    s = s[(s.bind_gwh > 0) & s.ran_before].copy()
    for lab, g in list(s.groupby(["cls", "kind"])) + [(("fault", "all"), s[s.cls == "fault"])]:
        out = []
        for a, z in ((48, 25), (24, 1)):
            v = []
            for t in g.start:
                w = dev.reindex(pd.date_range(t - pd.Timedelta(hours=a), t - pd.Timedelta(hours=z), freq="h"))
                if w.notna().any():
                    v.append(w.mean())
            v = np.array(v)
            out.append((v.mean(), v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan, len(v)))
        print(f"  {lab[0]:8s} {lab[1]:11s} n={out[0][2]:4d}  48-25h {out[0][0]:+6.2f} ({out[0][1]:.2f})"
              f"  24-1h {out[1][0]:+6.2f} ({out[1][1]:.2f})")
        rows.append(dict(check="timing_price", sample=f"{lab[0]}_{lab[1]}", term="48-25h", b=out[0][0], se=out[0][1], n=out[0][2]))
        rows.append(dict(check="timing_price", sample=f"{lab[0]}_{lab[1]}", term="24-1h", b=out[1][0], se=out[1][1], n=out[1][2]))


def timing_stake(s: pd.DataFrame, x: pd.DataFrame, rows: list) -> None:
    f = s[s.cls == "fault"].copy()
    f = f[f.kind.isin(GEN)]
    units = sorted(f.up.unique())
    sch = schedule(units)
    sch["date"] = sch.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    day = sch.groupby(["up", "date"]).sched_mw.mean()
    days = pd.date_range("2018-01-01", "2026-05-31", freq="D")
    full = pd.MultiIndex.from_product([units, days], names=["up", "date"])
    p = day.reindex(full, fill_value=0.0).rename("sched").reset_index()
    p["sched_prev"] = p.groupby("up").sched.shift(1)
    p = p[p.sched_prev > 0].copy()
    f["date"] = f.start.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    starts = f.groupby(["up", "date"]).size().rename("start_n").reset_index()
    p = p.merge(starts, on=["up", "date"], how="left")
    p["start"] = (p.start_n.fillna(0) > 0).astype(float)
    p["firm"] = majority_group(p, spells(), unit_col="up", date_col="date")
    p = p[p.firm.isin(FIRMS)].copy()
    x = x.copy()
    x["date"] = x.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    xd = x.groupby(["firm", "date"]).agg(X=("X", "mean"), n=("n", "mean")).reset_index()
    xd["date"] = xd.date + pd.Timedelta(days=1)            # the previous day's stake
    p = p.merge(xd.rename(columns={"X": "X_prev", "n": "n_prev"}), on=["firm", "date"], how="left")
    p["n_prev"] = p.n_prev / 1000.0
    p = p.dropna(subset=["X_prev", "n_prev"])
    p["um"] = p.up + "_" + p.date.dt.strftime("%Y%m")
    p["dt"] = p.date.dt.strftime("%Y%m%d")
    p["wk"] = p.date.dt.strftime("%G%V")
    rate = p.start.mean()
    print(f"\nTIMING 2: fault starts on the owner's stake the day before; {len(p):,} unit-days, "
          f"{int(p.start.sum())} starts, daily rate {rate:.4f}")
    for z in ("X_prev", "n_prev"):
        for lab, fes in (("unit x month + date", ["um", "dt"]), ("unit x month", ["um"])):
            m = demean(p, ["start", z], fes)
            M = m[[z]].to_numpy()
            inv = np.linalg.inv(M.T @ M)
            b = (inv @ M.T @ m.start.to_numpy())[0]
            V = inv @ cluster_meat(M, m.start.to_numpy() - M[:, 0] * b, p.wk.to_numpy()) @ inv
            se = float(np.sqrt(V[0, 0]))
            pv = 2 * (1 - stats.norm.cdf(abs(b / se)))
            sd = p[z].std()
            print(f"  {z:7s} {lab:20s} b {b:+.6f} ({se:.6f}) p {pv:.3f}; one sd ({sd:.2f}) moves the "
                  f"rate by {b * sd / rate:+.1%}")
            rows.append(dict(check="timing_stake", sample=lab, term=z, b=b, se=se, p=pv, n=len(p), rate=rate))
    print("  STOP RULE: a positive coefficient on X_prev with p < 0.05 (unit x month + date) ends the instrument")


def main() -> int:
    rows: list = []
    s = pd.read_csv(TABLES / "outage_event_spells.csv", parse_dates=["start", "end"])
    x = firm_hours()
    first_stage(x, rows)
    timing_prices(s, rows)
    timing_stake(s, x, rows)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
