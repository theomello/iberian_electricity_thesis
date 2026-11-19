"""Part B of docs/specs/2026-11-17-industry-iv-day-level-and-metered-design.md (rules B1-B5): metered consumption of the interruptibility-service participants, 2019.

    .venv/bin/python scripts/analysis/industry_iv_metered.py --step 0     # power gate: planted effects only
    .venv/bin/python scripts/analysis/industry_iv_metered.py --step 1     # real outcome; refuses to run for a unit whose B1 failed in step 0

Outcome: hourly sum of ESIOS 836-846 (peninsular; 10-minute mean MW averaged to the hour) = metered load of the large consumers in the service, a contractual consumption floor applies (Orden IET/2013/2013).
Two units, each with its own gate: HOUR (week-on-week hourly, as industry_iv_wind_speed_estimation.py) and DAY (as industry_iv_day_level.py). Sample: non-holiday weekdays 2019-01-01 -> 2019-12-31 with
complete 24-hour days for DAY (the bid-curve common sample is not used: it leaves 142 complete days). Instrument C1 (d_pc, d_pc^2), double ML, 1,000 permutations, seed 20261117, elasticity = slope x
mean price of the sample. Step 0 plants -0.1 and -0.3 (the planted estimates contain the real component, as in the earlier planted tests). B4 translation uses the 2019 ratio of mean metered load to
mean E3-E6 load computed here (the two sets are not verified to be nested). Writes outputs/tables/industry_iv_metered_step0{,_checks}.csv and industry_iv_metered{,_checks}.csv.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_day_level as DL  # noqa: E402
import industry_iv_estimation as E  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402

IDS = (836, 837, 838, 839, 840, 841, 842, 844, 845, 846)
FIRST, LAST = "2019-01-01", "2019-12-31"
G1 = "G1 (all years, purchases): -0.033 [-0.116, +0.017]"


def interruptible_hourly():
    ser = []
    for i in IDS:
        f = DL.ROOT / f"data/esios/esios_{i}.parquet"
        if not f.exists():
            continue
        x = pd.read_parquet(f, columns=["utc_timestamp", "value", "geo_name"])
        x = x[x.geo_name == "Península"].drop_duplicates("utc_timestamp")
        if x.empty:
            continue
        s = pd.Series(x.value.to_numpy(), index=pd.to_datetime(x.utc_timestamp, utc=True)).sort_index()
        h = s.resample("h").mean()
        loc = h.index.tz_convert("Europe/Madrid")
        t = pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "v": h.to_numpy()}).drop_duplicates(["date", "hour"]).set_index(["date", "hour"]).v
        ser.append(t.rename(i))
    print("sectors used:", [s.name for s in ser], flush=True)
    return pd.concat(ser, axis=1).sum(axis=1, skipna=False)


def pipeline():
    load = interruptible_hourly()
    base = DL.hourly_base()
    e36 = base[(base.date >= FIRST) & (base.date <= LAST)].load.mean()
    df = DL.hourly_base(load=load)
    ratio = float(df[(df.date >= FIRST) & (df.date <= LAST)].load.mean() / e36)
    out = {}
    h = DL.hourly_frame(df, FIRST, LAST)
    d = DL.day_frame(df, FIRST, LAST)
    for unit, fr, X, lag in (("HOUR", h, DL.hour_X(h), 6), ("DAY", d, DL.day_X(d), 5)):
        R = DL.residualise(fr, X, own_lag_col=lag)
        pbar = float(fr.p.mean())
        srcs = E.perm_sources(fr, np.random.default_rng(N.SEED), E.NPERM)
        out[unit] = dict(d=fr, X=X, R=R, pbar=pbar, srcs=srcs)
        print(f"{unit}: {len(fr)} rows, {fr.date.nunique()} days, mean price {pbar:.2f}, mean metered load share of E3-E6 {ratio:.3f}", flush=True)
    return out, ratio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, choices=(0, 1), required=True)
    step = ap.parse_args().step
    f0 = T.OUT / "industry_iv_metered_step0_checks.csv"
    U, ratio = pipeline()
    pd.set_option("display.width", 250, "display.max_colwidth", 250)
    if step == 0:
        allP, ch = [], []
        for unit, u in U.items():
            plants = DL.plants_list(u["d"], betas=(-0.1, -0.3), halves=False)
            P = DL.run_plants(u["d"], u["X"], u["R"], u["srcs"], u["pbar"], plants)
            P.insert(0, "unit", unit)
            allP.append(P)
            ch += [(f"{unit} B1 power: planted -0.3 detected and recovered", *c[1:]) for c in DL.power_checks(P, -0.3, "B")[:1]]
            r1 = P[np.isclose(P.beta, -0.1)].iloc[0]
            ch.append((f"{unit} planted -0.1 (no pass/fail)", None, f"{'detected' if DL.detected(r1) else 'not detected'}: {r1.elasticity:.4f} [{r1.rand_lo:.4f},{r1.rand_hi:.4f}]"))
        pd.concat(allP).round(5).to_csv(T.OUT / "industry_iv_metered_step0.csv", index=False)
        C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
        C.to_csv(f0, index=False)
        print(C.to_string(index=False))
        return
    if not f0.exists():
        sys.exit("step 0 has not been run: no real-outcome result is produced")
    g = pd.read_csv(f0)
    rows, ch = [], []
    for unit, u in U.items():
        ok = bool(g[g.rule.str.startswith(f"{unit} B1")]["pass"].iloc[0])
        if not ok:
            ch.append((f"{unit} B1", False, "failed in step 0: uninformative, not run (spec rule B1)"))
            continue
        Rr = DL.real_run(u["d"], u["R"], u["srcs"], u["pbar"], with_regimes=False)
        Rr.insert(0, "unit", unit)
        rows.append(Rr)
        q = lambda v: Rr[(Rr.variant == v) & (Rr.block == "full")].iloc[0]
        m, pl = q("primary"), q("placebo")
        ch.append((f"{unit} B2 placebo", bool(pl.p_t_rank > 0.05), f"elasticity {pl.elasticity:.4f}, p_t {pl.p_t_rank:.3f}"))
        ch.append((f"{unit} B3 detection (negative, p<=0.05, interval excludes zero)", bool(m.elasticity < 0 and DL.detected(m)), f"{m.elasticity:.4f} [{m.rand_lo:.4f},{m.rand_hi:.4f}], p_t {m.p_t_rank:.3f}, F {m.F:.1f}"))
        ch.append((f"{unit} B4 translation (bound x ratio of means {ratio:.2f}, approximate)", None, f"lower bound {m.rand_lo:.4f} -> aggregate {m.rand_lo * ratio:.4f}; upper {m.rand_hi:.4f} -> {m.rand_hi * ratio:.4f}"))
        ch.append((f"{unit} B5 context (no pass/fail)", None, G1))
    if rows:
        pd.concat(rows).round(5).to_csv(T.OUT / "industry_iv_metered.csv", index=False)
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_metered_checks.csv", index=False)
    print(C.to_string(index=False))


if __name__ == "__main__":
    main()
