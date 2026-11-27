"""Interruptibility service and the industry shape drift (docs/specs/2026-11-27-interruptibility-drift-design.md).

    .venv/bin/python scripts/analysis/interruptibility_drift.py

Descriptive only. P = participants' metered load (ESIOS 836-842, 844-846; 10-minute MW averaged to the hour), T = E3..E6
(1204-1207, absent E5 hours = 0; fallback E1..E6), R = T - P. Window 1 June - 15 September, working days (Mon-Fri, not a
national holiday), summers 2015-2019 (2021 for the comparison). Shape = ln(mean load 18-21h / mean load 0-7h).
Writes outputs/tables/interruptibility_drift.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
P_IDS = [836, 837, 838, 839, 840, 841, 842, 844, 845, 846]
YEARS = [2015, 2016, 2017, 2018, 2019]
EV, NI = range(18, 22), range(0, 8)


def participants():
    s = None
    for i in P_IDS:
        d = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")[["utc_timestamp", "value"]].drop_duplicates("utc_timestamp")
        h = d.set_index("utc_timestamp").value.resample("h").mean()
        s = h if s is None else s.add(h, fill_value=0.0)
    loc = s.index.tz_convert("Europe/Madrid")
    return pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "P": s.to_numpy()}).drop_duplicates(["date", "hour"])


def voltage_sum(ids):
    rest = [i for i in ids if i != 1206]
    v = CT.esios_load(rest).merge(CT.esios_load([1206]).rename(columns={"v": "e5"}), on=["date", "hour"], how="left")
    v["T"] = v.v + v.e5.fillna(0.0)
    return v[["date", "hour", "T"]]


def window(df, hol):
    d = df.date
    keep = (d.dt.month.between(6, 9)) & ~((d.dt.month == 9) & (d.dt.day > 15)) & (d.dt.dayofweek < 5) & ~d.isin(hol)
    return df[keep].assign(year=d.dt.year)


def prof(g, col):
    return dict(mean=g[col].mean(), ev=g.loc[g.hour.isin(EV), col].mean(), ni=g.loc[g.hour.isin(NI), col].mean())


shape = lambda p: float(np.log(p["ev"] / p["ni"]))


def slope(y):
    x = np.array(YEARS, float)
    X = np.column_stack([np.ones_like(x), x - x.mean()])
    b, res, *_ = np.linalg.lstsq(X, np.array(y), rcond=None)
    e = np.array(y) - X @ b
    se = float(np.sqrt(e @ e / (len(x) - 2) / ((x - x.mean()) ** 2).sum()))
    return float(b[1]), se


def main():
    hol = TS.holidays()
    P = participants()
    rows = []
    chosen = None
    for name, ids in (("E3-E6", [1204, 1205, 1206, 1207]), ("E1-E6", [1202, 1203, 1204, 1205, 1206, 1207])):
        df = window(voltage_sum(ids).merge(P, on=["date", "hour"], how="inner"), hol)
        df = df[df.year.isin(YEARS)].dropna(subset=["T", "P"])
        frac = float((df.P <= df["T"]).mean())
        corr = float(np.corrcoef(df.P, df["T"])[0, 1])
        ok = frac >= 0.995 and corr > 0.5
        print(f"S1 nesting in {name}: P <= T in {frac:.4f} of {len(df)} hours, corr {corr:.3f} -> {'pass' if ok else 'FAIL'}")
        rows.append(dict(step="S1", set=name, share_hours_nested=frac, corr=corr, passed=ok))
        if ok:
            chosen = (name, ids)
            break
    if chosen is None:
        pd.DataFrame(rows).to_csv(OUT / "interruptibility_drift.csv", index=False)
        sys.exit("S1 failed for both sets: stop (only the bound from the scheme's published size remains)")

    name, ids = chosen
    allT = window(voltage_sum(ids).merge(P, on=["date", "hour"], how="left"), hol)
    allT["P"] = allT.P.fillna(0.0)
    allT["R"] = allT["T"] - allT.P
    stats = {}
    for y in YEARS + [2021]:
        g = allT[allT.year == y].dropna(subset=["T"])
        stats[y] = {c: prof(g, c) for c in ("T", "R", "P")}
        st = stats[y]
        s = st["P"]["mean"] / st["T"]["mean"]
        rows.append(dict(step="summer", set=name, year=y, mean_T=st["T"]["mean"], mean_P=st["P"]["mean"], share_P=s,
                         shape_T=shape(st["T"]), shape_R=shape(st["R"]), shape_P=shape(st["P"]) if st["P"]["ni"] > 0 else np.nan))
        print(f"{y}: T {st['T']['mean']:.0f} MW, P {st['P']['mean']:.0f} (s {s:.3f}); shape T {shape(st['T']):+.4f} "
              f"R {shape(st['R']):+.4f} P {rows[-1]['shape_P']:+.4f}")

    # S2 slopes and shift-share 2015 -> 2019
    sl = {k: slope([r[k] for r in rows if r.get("step") == "summer" and r["year"] in YEARS]) for k in ("shape_T", "shape_R", "shape_P", "share_P")}
    for k, (b, se) in sl.items():
        print(f"slope {k}: {b:+.4f} per year (se {se:.4f})")
    a, b = stats[2015], stats[2019]

    def combine(src_prof, src_mean):
        """Aggregate shape from per-group normalised profiles (src_prof) and group means (src_mean)."""
        ev = sum(src_mean[g]["mean"] * src_prof[g]["ev"] / src_prof[g]["mean"] for g in ("R", "P"))
        ni = sum(src_mean[g]["mean"] * src_prof[g]["ni"] / src_prof[g]["mean"] for g in ("R", "P"))
        return float(np.log(ev / ni))

    s15, s19 = combine(a, a), combine(b, b)
    comp = combine(a, b) - s15      # 2015 profiles, 2019 sizes
    within = combine(b, a) - s15    # 2019 profiles, 2015 sizes
    total = s19 - s15
    inter = total - comp - within
    print(f"S2 shift-share 2015->2019: total {total:+.4f} = composition {comp:+.4f} + within {within:+.4f} + interaction {inter:+.4f}")
    bT, seT = sl["shape_T"]
    bR, _ = sl["shape_R"]
    if bT <= 0 or bT < seT:
        verdict = "D2: no upward slope in shape(T) over 2015-2019; S2 uninformative"
    else:
        d1 = comp >= 0.5 * total and bR < 0.5 * bT
        verdict = f"D1: participants explain the drift -> {'YES' if d1 else 'NO'} (composition share {comp / total:.2f}, slope R/T {bR / bT:.2f})"
    print(verdict)

    # S3 bound at the 2019 share
    st = stats[2019]
    evp = st["R"]["ev"] + st["P"]["mean"] * st["R"]["ev"] / st["R"]["mean"]
    nip = st["R"]["ni"] + st["P"]["mean"] * st["R"]["ni"] / st["R"]["mean"]
    B = float(np.log(evp / nip)) - shape(st["T"])
    shift21 = shape(stats[2021]["T"]) - np.mean([shape(stats[y]["T"]) for y in YEARS])
    v1 = abs(B) < 0.25 * abs(shift21)
    print(f"S3 bound B {B:+.4f}; raw 2021 shift of shape(T) against 2015-2019 mean {shift21:+.4f}; |B|/|shift| {abs(B) / abs(shift21):.2f} "
          f"-> V1 {'minor threat' if v1 else 'MAJOR threat'}")
    rows.append(dict(step="S2", set=name, total=total, composition=comp, within=within, interaction=inter,
                     slope_T=bT, slope_T_se=seT, slope_R=bR, slope_R_se=sl["shape_R"][1], slope_P=sl["shape_P"][0],
                     slope_share=sl["share_P"][0], verdict=verdict))
    rows.append(dict(step="S3", set=name, bound_B=B, shift_2021=shift21, ratio=abs(B) / abs(shift21), minor=v1))
    pd.DataFrame(rows).to_csv(OUT / "interruptibility_drift.csv", index=False)


if __name__ == "__main__":
    main()
