#!/usr/bin/env python3
"""The day-ahead − intraday price premium against the five firms' combined position.

    .venv/bin/python scripts/analysis/firm_x.py              # input: each firm's exposed n
    .venv/bin/python scripts/build/build_reactor_outages.py  # input: outage doses
    .venv/bin/python scripts/analysis/da_id_premium.py

Framework spec §9.5, "the buyers' test" (Ito & Reguant 2016). A firm that is a net
seller in the day-ahead auction gains from a high day-ahead price: it holds back
there and sells the rest in the first intraday auction, where the price is lower. A
net buyer gains from a low day-ahead price: it buys less there and the rest later.
With limited arbitrage, the premium p_DA − p_ID should rise with the strategic firms'
combined net position N and be negative when they are net buyers.

    premium_t = p_DA − p_ID1 (Spanish zone, €/MWh)
    N_t       = sum of the five firms' exposed day-ahead net positions (firm_x.py,
                `net_mw`: cleared sell − cleared buy, regulated pass-through suppliers
                excluded; ownership by date and share), GW

ID1 is the first intraday auction after the day-ahead: MIBEL's session 1 (about 17:00
on D-1) until 2024-06-13, the European IDA1 (15:00 on D-1) from 2024-06-14. Sample
2019-01-01 (REE's D-1 forecasts start) → 2025-03-18 (intraday prices quarter-hourly
from the 19th); 2018 is shown without forecast controls.

CONTROLS. The premium also moves with what nobody knew at noon on D-1: realised minus
D-1 forecast wind (ESIOS 1159 by province, summed, against 1777; hours with fewer than
30 provinces reporting dropped), solar (1161 against 1779; ESIOS omits zero rows, so
an hour without a PV report is zero, and its forecast averages 0.1 MWh), both
peninsular, and demand (REE realtime against 1775; the realtime series
includes the islands, about 6% of demand, a level the effects absorb). Effects: year-
month × hour. Week clusters.

A DESCRIPTION, NOT AN ESTIMATE. N is the firms' own day-ahead outcome, so it moves with
the day-ahead price that the premium contains. As a check, N is instrumented by the
reactors' planned outage dose (`reactor_outage_dose`, cls planned): refuelling is set
months ahead and every reactor belongs to the five, so a planned outage lowers N by
its lost output. It also tightens the market for everyone; read the check with that
in mind.

Writes outputs/tables/da_id_premium_results.csv, da_id_premium_bins.csv and
outputs/figures/da_id_premium.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from ivpee_tax_test import vcov  # noqa: E402
from outage_offer_test import demean  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
FIG = ROOT / "outputs/figures/da_id_premium.png"
START, FC_START, END = "2018-01-01", "2019-01-01", "2025-03-18"
MIN_PROVINCES = 30
ERAS = [("2019-01-01", "2021-06-30", "2019 – 2021 H1"), ("2021-07-01", "2023-12-31", "2021 H2 – 2023 (gas crisis)"),
        ("2024-01-01", END, "2024 – 2025 Q1")]


def hourly(df: pd.DataFrame, col: str = "value") -> pd.Series:
    return df.assign(utc=df.utc_timestamp.dt.floor("h")).groupby("utc")[col].mean()


def prices() -> pd.DataFrame:
    da = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet")
    da["date"] = pd.to_datetime(da.date)
    da = da[(da.date >= START) & (da.date <= END) & (da.resolution_min == 60)]
    ip = pd.read_parquet(DATA / "omie/intraday_prices/omie_intraday_prices.parquet")
    ip["date"] = pd.to_datetime(ip.date)
    ip = ip[(ip.session == 1) & (ip.date >= START) & (ip.date <= END)]
    if ip.duplicated(["date", "period"]).any():
        raise SystemExit("more than one session-1 price per period")
    d = da.merge(ip[["date", "period", "price_b", "price_a"]], on=["date", "period"], how="left")
    print(f"day-ahead hours {len(d):,}; with a session-1 price {d.price_b.notna().sum():,}")
    d = d.dropna(subset=["price_b"])
    d["premium"] = d.price_es - d.price_b
    d["premium_pt"] = d.price_pt - d.price_a
    d["utc"] = d.utc_timestamp.dt.floor("h")
    return d


def positions() -> pd.DataFrame:
    x = pd.read_parquet(TABLES / "firm_x.parquet", columns=["date", "period", "firm", "net_mw", "clean", "split",
                                                            "zero_price"])
    g = x.groupby(["date", "period"])
    n = g.net_mw.sum().div(1000).rename("N").to_frame()
    n["clean"] = g.clean.first()
    n["zero_price"] = g.zero_price.first()
    w = x.pivot_table(index=["date", "period"], columns="firm", values="net_mw").div(1000)
    w.columns = [f"n_{c.lower()}" for c in w.columns]
    return n.join(w).reset_index()


def surprises() -> pd.DataFrame:
    fc = {}
    for i, name in [(1777, "wind"), (1779, "solar"), (1775, "demand")]:
        f = pd.read_parquet(DATA / f"esios/esios_{i}.parquet", columns=["value", "utc_timestamp"])
        fc[name] = hourly(f)
    p = pd.read_parquet(DATA / "esios/esios_measured_generation_province.parquet",
                        columns=["indicator_id", "value", "utc_timestamp", "geo_id"])
    p["utc"] = p.utc_timestamp.dt.floor("h")
    real = {}
    q = p[p.indicator_id == 1159]
    n = q.groupby("utc").geo_id.nunique()
    real["wind"] = q.groupby("utc").value.sum()[n >= MIN_PROVINCES]
    # ESIOS omits zero rows: an hour without a PV report is zero output (night)
    q = p[p.indicator_id == 1161]
    idx = fc["solar"].index[fc["solar"].index <= q.utc.max()]
    real["solar"] = q.groupby("utc").value.sum().reindex(idx, fill_value=0.0)
    r = pd.read_parquet(DATA / "ree/ree_realtime_5min.parquet", columns=["utc_timestamp", "demand"])
    real["demand"] = hourly(r, "demand")
    out = pd.DataFrame({f"err_{k}": (real[k] - fc[k]) / 1000 for k in ("wind", "solar", "demand")})
    return out.rename_axis("utc").reset_index()


def planned_dose() -> pd.DataFrame:
    d = pd.read_parquet(TABLES / "reactor_outage_dose.parquet")
    d = d[d.cls == "planned"].groupby("utc").lost_mw.sum().div(1000).rename("dose_plan")
    return d.reset_index()


def build() -> pd.DataFrame:
    d = prices().merge(positions(), on=["date", "period"], how="left")
    d = d.merge(surprises(), on="utc", how="left").merge(planned_dose(), on="utc", how="left")
    d["dose_plan"] = d.dose_plan.fillna(0.0)
    loc = d.utc.dt.tz_convert("Europe/Madrid")
    d["hour"] = loc.dt.hour
    d["ym"] = loc.dt.strftime("%Y-%m")
    d["ymh"] = d.ym + "|" + d.hour.astype(str)
    d["week"] = loc.dt.strftime("%G-%V")
    return d


def ols_fe(d: pd.DataFrame, y: str, xs: list[str], fe: list[str], cl: str = "week"):
    codes = [pd.factorize(d[f])[0] for f in fe]
    M = demean(d[[y] + xs].to_numpy(float), codes) if fe else d[[y] + xs].to_numpy(float)
    if not fe:
        M = np.column_stack([M, np.ones(len(d))])
        xs = xs + ["const"]
    yt, Xt = M[:, 0], M[:, 1:]
    b = np.linalg.lstsq(Xt, yt, rcond=None)[0]
    e = yt - Xt @ b
    se = np.sqrt(np.diag(vcov(Xt, e, [d[cl].to_numpy()])))
    return dict(zip(xs, b)), dict(zip(xs, se)), yt, Xt


def iv_fe(d: pd.DataFrame, y: str, x: str, z: str, ctrl: list[str], fe: list[str], cl: str = "week"):
    codes = [pd.factorize(d[f])[0] for f in fe]
    M = demean(d[[y, x, z] + ctrl].to_numpy(float), codes)
    yt, xt, zt, C = M[:, 0], M[:, 1], M[:, 2], M[:, 3:]
    if C.shape[1]:
        Q, _ = np.linalg.qr(C)
        yt, xt, zt = (v - Q @ (Q.T @ v) for v in (yt, xt, zt))
    pi = (zt @ xt) / (zt @ zt)
    fs_se = np.sqrt(vcov(zt[:, None], xt - pi * zt, [d[cl].to_numpy()])[0, 0])
    b = (zt @ yt) / (zt @ xt)
    e = yt - b * xt
    se = np.sqrt(vcov((pi * zt)[:, None], e, [d[cl].to_numpy()])[0, 0])   # just identified: x-hat = pi z
    return b, se, pi, fs_se


def main() -> int:
    d = build()
    s = d[d.date >= FC_START].dropna(subset=["N", "err_wind", "err_solar", "err_demand"]).copy()
    print(f"sample {FC_START} → {END}: {len(s):,} hours ({len(d[d.date >= FC_START]) - len(s):,} dropped for a "
          f"missing position or surprise)")
    print(f"premium (€/MWh): mean {s.premium.mean():+.2f}, median {s.premium.median():+.2f}, sd {s.premium.std():.2f}")
    print(f"N (GW): mean {s.N.mean():+.2f}, share of hours with N < 0 {(s.N < 0).mean():.3f}")
    print("mean premium by sign of N: " + ", ".join(f"{k}: {v:+.2f} ({n:,} h)" for k, v, n in
          [("N < 0", s[s.N < 0].premium.mean(), (s.N < 0).sum()), ("N > 0", s[s.N > 0].premium.mean(), (s.N > 0).sum())]))

    rows = []
    errs = ["err_wind", "err_solar", "err_demand"]

    def add(label, sample, coef, se, extra=None):
        r = {"spec": label, "sample": sample, "n": coef.pop("_n", None)}
        for k in coef:
            r[f"b_{k}"], r[f"se_{k}"] = coef[k], se[k]
        r.update(extra or {})
        rows.append(r)

    print("\n== premium on N (€/MWh per GW)")
    for label, xs, fe in [("N only, hour effects", ["N"], ["hour"]),
                          ("N + surprises, hour effects", ["N"] + errs, ["hour"]),
                          ("N + surprises, year-month x hour effects (main)", ["N"] + errs, ["ymh"]),
                          ("N + surprises, main effects, clean periods", ["N"] + errs, ["ymh"])]:
            x = s[s.clean & ~s.zero_price] if "clean" in label else s
            b, se, _, _ = ols_fe(x, "premium", xs, fe)
            print(f"  {label}: N {b['N']:+.3f} ({se['N']:.3f}); " + ", ".join(
                f"{k[4:]} {b[k]:+.2f} ({se[k]:.2f})" for k in errs if k in b) + f"; {len(x):,} h")
            add(label, f"{FC_START} to {END}", dict(b, _n=len(x)), se)

    # the level: premium at N = 0 with hour effects only (intercept from demeaned-by-hour means)
    b, se, _, _ = ols_fe(s, "premium", ["N"] + errs, [])
    print(f"  no effects: premium at N = 0 and no surprise {b['const']:+.2f} ({se['const']:.2f}), "
          f"N {b['N']:+.3f} ({se['N']:.3f})")
    add("N + surprises, no effects (level)", f"{FC_START} to {END}", dict(b, _n=len(s)), se)

    print("\n== by era (main specification)")
    for a, z, name in ERAS:
        x = s[(s.date >= a) & (s.date <= z)]
        b, se, _, _ = ols_fe(x, "premium", ["N"] + errs, ["ymh"])
        print(f"  {name}: N {b['N']:+.3f} ({se['N']:.3f}); mean premium {x.premium.mean():+.2f}, "
              f"mean N {x.N.mean():+.2f}; {len(x):,} h")
        add(f"main, {name}", f"{a} to {z}", dict(b, _n=len(x)), se, {"mean_premium": x.premium.mean(), "mean_N": x.N.mean()})

    print("\n== by firm (each firm's n, the others' sum as a control; main effects)")
    firms = [c for c in s.columns if c.startswith("n_")]
    for f in firms:
        x = s.assign(others=s.N - s[f])
        b, se, _, _ = ols_fe(x, "premium", [f, "others"] + errs, ["ymh"])
        print(f"  {f[2:]}: {b[f]:+.3f} ({se[f]:.3f}); others {b['others']:+.3f} ({se['others']:.3f})")
        add(f"by firm: {f[2:]}", f"{FC_START} to {END}", dict(b, _n=len(s)), se)

    print("\n== check: N instrumented by the planned reactor outage dose (main effects, surprises controlled)")
    b, se, pi, fs_se = iv_fe(s, "premium", "N", "dose_plan", errs, ["ymh"])
    print(f"  first stage: N on planned dose {pi:+.3f} GW per GW ({fs_se:.3f}), F {(pi / fs_se) ** 2:.1f}; "
          f"premium on N {b:+.3f} ({se:.3f})")
    rows.append({"spec": "IV: N on planned reactor outage dose", "sample": f"{FC_START} to {END}", "n": len(s),
                 "b_N": b, "se_N": se, "first_stage": pi, "first_stage_se": fs_se, "F": (pi / fs_se) ** 2})

    out = TABLES / "da_id_premium_results.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"-> {out.relative_to(ROOT)}")
    bins(s, errs)
    early(d)
    return 0


def early(d: pd.DataFrame) -> None:
    x = d[d.date < FC_START].dropna(subset=["N"])
    b, se, _, _ = ols_fe(x, "premium", ["N"], ["ymh"])
    print(f"\n2018, no forecast controls: N {b['N']:+.3f} ({se['N']:.3f}); mean premium {x.premium.mean():+.2f}, "
          f"mean N {x.N.mean():+.2f}; {len(x):,} h")


def bins(s: pd.DataFrame, errs: list[str], k: int = 20) -> None:
    """Premium against N in 20 equal-count bins, both net of the surprises and the
    year-month × hour effects (Frisch–Waugh), the overall means added back."""
    codes = [pd.factorize(s.ymh)[0]]
    M = demean(s[["premium", "N"] + errs].to_numpy(float), codes)
    C = M[:, 2:]
    Q, _ = np.linalg.qr(C)
    yr = M[:, 0] - Q @ (Q.T @ M[:, 0]) + s.premium.mean()
    xr = M[:, 1] - Q @ (Q.T @ M[:, 1]) + s.N.mean()
    q = pd.qcut(xr, k, labels=False)
    b = pd.DataFrame({"N": xr, "premium": yr, "bin": q, "N_raw": s.N.to_numpy(), "premium_raw": s.premium.to_numpy()})
    g = b.groupby("bin").agg(N=("N", "mean"), premium=("premium", "mean"), N_raw=("N_raw", "mean"),
                             premium_raw=("premium_raw", "mean"), hours=("N", "size"))
    out = TABLES / "da_id_premium_bins.csv"
    g.to_csv(out)
    print(f"-> {out.relative_to(ROOT)}")
    print(g.round(2).to_string())

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].axhline(0, color="0.6", lw=0.8)
    ax[0].axvline(0, color="0.6", lw=0.8)
    ax[0].plot(g.N_raw, g.premium_raw, "o", color="0.6", ms=4, label="raw")
    ax[0].plot(g.N, g.premium, "o", color="C0", ms=5, label="net of surprises and year-month × hour")
    ax[0].set_xlabel("five firms' combined day-ahead net position N (GW)")
    ax[0].set_ylabel("day-ahead − first intraday price (€/MWh)")
    ax[0].legend(fontsize=8, frameon=False)
    ax[0].set_title("Premium against N, 20 bins, 2019 – 2025 Q1", fontsize=10)
    m = s.groupby(s.date.dt.to_period("M")).agg(premium=("premium", "mean"), N=("N", "mean"))
    t = m.index.to_timestamp()
    ax[1].plot(t, m.premium, color="C0", label="premium (€/MWh)")
    ax2 = ax[1].twinx()
    ax2.plot(t, m.N, color="C3", label="N (GW)")
    ax[1].axhline(0, color="0.6", lw=0.8)
    ax[1].set_ylabel("premium (€/MWh)", color="C0")
    ax2.set_ylabel("N (GW)", color="C3")
    ax[1].set_title("Monthly means", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG, dpi=150)
    print(f"-> {FIG.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
