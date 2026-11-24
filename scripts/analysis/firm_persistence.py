"""Estimation of the firm calendar persistence design (docs/specs/2026-11-23-firm-calendar-persistence-design.md).

    .venv/bin/python scripts/analysis/firm_persistence.py

Runs after step zero (4089e45): Part A (summers) for medium firms (E1+E2, S = 4) and large industry (6.2+6.3+6.4,
S = 6); Part B (calendar years, all months) for medium firms only (Z2). Post years 2022-2025 (K = 4). Statistic and
helpers from firm_persistence_step0 (same cells, d tables, fits). Rules R1-R9 as registered; verdict = highest-ranked
failing rule, order R1 > R5 > R4 > R3 > R6 > R2 > R7 > R8 > R9. R4 is read as in the medium-firm E7: it fails only if
the wrong-hours effect lies below the lower bound of its no-effect prediction interval, i.e. its pooled interval lies
wholly below zero. Price share for R5 from mf_period_calendar_estimate.price_share (REN ES, 2014-17 rebuilt).
Writes outputs/tables/firm_persistence{,_summary}.csv. Deterministic.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import firm_persistence_step0 as F  # noqa: E402
import mf_period_calendar_estimate as MFE  # noqa: E402
import tou_cross_tariff as CT  # noqa: E402
import tou_tariff_schedule as TS  # noqa: E402

OUT = F.OUT
POST = F.POST
K = len(POST)
ORDER = ["R1", "R5", "R4", "R3", "R6", "R2", "R7", "R8", "R9"]
DBAR = {"medium": 0.1049, "large": 0.0575}


def load_all(ids):
    return CT.esios_load(ids)


def cells_ps(f, dt, june_split, series, ps):
    f = f.assign(part=F.part_of(f.date, june_split)).merge(ps, on=["date", "hour"], how="left")
    c = f.groupby(["part", "hour"]).agg(s=("s", "mean"), ps=("ps", "mean")).reset_index()
    c["d"] = [dt.get((p, h), np.nan) for p, h in zip(c.part, c.hour)]
    assert c.d.notna().all() and c.ps.notna().all()
    c["series"] = series
    return c


def fit(c, form, extra=None):
    if form == "fe":
        key = c.series.astype(str) + "|" + c.hour.astype(str)
        cols = [(key == k).astype(float).to_numpy() for k in sorted(key.unique())]
    else:
        cols = [np.ones(len(c))]
    cols.append(c.d.to_numpy())
    if extra:
        cols.append(c[extra].to_numpy())
    coef = np.linalg.lstsq(np.column_stack(cols), c.s.to_numpy(), rcond=None)[0]
    return float(coef[-2] if extra else coef[-1])


def stats_of(post, pl, years):
    post, pl, years = np.asarray(post, float), np.asarray(pl, float), np.asarray(years, float)
    S, Kp = len(pl), len(post)
    m, s = pl.mean(), pl.std(ddof=1)
    eff = post.mean() - m
    se = s * np.sqrt(1 / Kp + 1 / S)
    se_c = s * np.sqrt(1 + 1 / S)
    q = stats.t.ppf(0.975, S - 1)
    slope, icpt = np.polyfit(years, pl, 1)
    s_e = np.sqrt(((pl - (icpt + slope * years)) ** 2).sum() / (S - 2))
    ypost = np.mean(POST[:Kp]) if Kp == K else None
    return dict(S=S, K=Kp, b_post=post.mean(), m=m, s=s, effect=eff, p=stats.t.cdf(eff / se, S - 1),
                p_upper=1 - stats.t.cdf(eff / se, S - 1), lo=eff - q * se, hi=eff + q * se,
                p_conservative=stats.t.cdf(eff / se_c, S - 1), icpt=icpt, slope=slope, s_e=s_e)


def trend(post, post_years, pl, years):
    post, pl, years = np.asarray(post, float), np.asarray(pl, float), np.asarray(years, float)
    S, Kp = len(pl), len(post)
    slope, icpt = np.polyfit(years, pl, 1)
    s_e = np.sqrt(((pl - (icpt + slope * years)) ** 2).sum() / (S - 2))
    yp = np.mean(post_years)
    se = s_e * np.sqrt(1 / Kp + 1 / S + (yp - years.mean()) ** 2 / ((years - years.mean()) ** 2).sum())
    eff = post.mean() - (icpt + slope * yp)
    return eff, stats.t.cdf(eff / se, S - 2)


def run(g, part, spec, loads, ps, hol, holy, drop):
    june_split = g == "medium"
    main_form = "fe" if spec["fe"] else "int"
    tar_of = (lambda n: spec["tariff"]) if spec["tariff"] else (lambda n: n)
    if part == "A":
        dts = pd.date_range("2021-06-01", "2021-09-30")
        months = [6, 7, 8, 9]
        win = lambda y: (pd.Timestamp(f"{y}-06-01"), pd.Timestamp(f"{y}-09-30"))
        extra_years = [2021]
    else:
        dts = pd.DatetimeIndex([d for d in pd.date_range("2022-01-01", "2022-12-31") if d not in holy and not (d.month == 1 and d.day == 1)])
        months = list(range(1, 13))
        win = lambda y: (pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31"))
        extra_years = []
    dt = {n: F.d_table(tar_of(n), dts, hol | holy, june_split) for n in loads}
    years = spec["years"]
    C = {}
    for y in years + POST + extra_years:
        d0, d1 = win(y)
        C[y] = pd.concat([cells_ps(F.frame(x, d0, d1, drop, months), dt[n], june_split, n, ps) for n, x in loads.items()], ignore_index=True)

    def bset(fun):
        return {y: fun(C[y]) for y in C}

    other = "int" if main_form == "fe" else "fe"

    def wrong(c):
        fake = c[c.hour.between(8, 23)].groupby(["series", "part"]).d.mean()
        w = c[c.hour.between(1, 4)].copy()
        w["d"] = [fake[(s_, p_)] for s_, p_ in zip(w.series, w.part)]
        return fit(w, "fe")

    B = {"main": bset(lambda c: fit(c, main_form)),
         "solar_robust": bset(lambda c: fit(c[~c.hour.isin(F.SOLAR)], main_form)),
         "no_august": bset(lambda c: fit(c[c.part != "08"], main_form)),
         "wrong_hours": bset(wrong),
         "price_control": bset(lambda c: fit(c, main_form, extra="ps")),
         f"other_form_{other}": bset(lambda c: fit(c, other))}
    if g == "large" and part == "A":
        for n in loads:
            B[f"series_{n}"] = bset(lambda c, n=n: fit(c[c.series == n], "int"))

    res = {}
    for name, b in B.items():
        r = stats_of([b[y] for y in POST], [b[y] for y in years], years)
        r["trend_effect"], r["p_trend"] = trend([b[y] for y in POST], POST, [b[y] for y in years], years)
        for y in POST + extra_years:
            r[f"eff_{y}"] = b[y] - r["m"]
        res[name] = r
    mn = res["main"]
    drops = {y: stats_of([B["main"][z] for z in POST if z != y], [B["main"][z] for z in years], years)["p"] for y in POST}
    rules = {
        "R1": mn["effect"] < 0 and mn["p"] <= 0.05,
        "R5": np.sign(res["price_control"]["effect"]) == np.sign(mn["effect"]) and mn["lo"] <= res["price_control"]["effect"] <= mn["hi"],
        "R4": not (res["wrong_hours"]["hi"] < 0),
        "R3": res["solar_robust"]["effect"] < 0 and res["solar_robust"]["p"] <= 0.10,
        "R6": res["no_august"]["effect"] < 0 and res["no_august"]["p"] <= 0.10 and res["no_august"]["trend_effect"] < 0,
        "R2": mn["effect"] < 0 and mn["p_conservative"] <= 0.10,
        "R7": all(p <= 0.10 for p in drops.values()),
        "R8": mn["trend_effect"] < 0 and mn["p_trend"] <= 0.10,
        "R9": all(mn[f"eff_{y}"] < 0 for y in POST),
    }
    wrong_sign = mn["effect"] > 0 and mn["p_upper"] <= 0.05
    failing = [r for r in ORDER if not rules[r]]
    verdict = "sign failure" if wrong_sign else (failing[0] + " fails" if failing else "all pass")
    # elasticity equivalent: s-bar over hours 8-23 in placebo years
    sbar = float(np.mean([C[y][C[y].hour >= 8].s.mean() for y in years]))
    return res, rules, drops, verdict, wrong_sign, sbar


def main():
    pd.set_option("display.width", 260)
    hol = TS.holidays()
    holy = F.holy_days(range(2014, 2027))
    drop = hol | holy | {pd.Timestamp(f"{y}-01-01") for y in range(2014, 2027)}
    ps = MFE.price_share()
    rows, summ = [], []
    for g, spec in F.GROUPS.items():
        loads = {n: load_all(ids) for n, ids in spec["series"].items()}
        for part in (["A", "B"] if g == "medium" else ["A"]):
            res, rules, drops, verdict, wsign, sbar = run(g, part, spec, loads, ps, hol, holy, drop)
            for name, r in res.items():
                rows.append(dict(group=g, part=part, statistic=name, **r))
            eff = res["main"]["effect"]
            summ.append(dict(group=g, part=part, verdict=verdict, wrong_sign=wsign, **{k: bool(v) for k, v in rules.items()},
                             drop_one_p=" ".join(f"{y}:{p:.3f}" for y, p in drops.items()), sbar=sbar,
                             elasticity_equivalent=(eff / sbar) / DBAR[g],
                             elasticity_lo=(res["main"]["lo"] / sbar) / DBAR[g], elasticity_hi=(res["main"]["hi"] / sbar) / DBAR[g]))
            print(f"\n=== {g} part {part}: verdict {verdict}")
            print(pd.DataFrame(res).T[["S", "K", "b_post", "m", "s", "effect", "p", "lo", "hi", "p_conservative", "trend_effect", "p_trend"]
                                      + [c for c in pd.DataFrame(res).T.columns if c.startswith("eff_")]].astype(float).round(4).to_string())
            print({k: ("PASS" if v else "FAIL") for k, v in rules.items()}, "| drop-one p:", {y: round(p, 3) for y, p in drops.items()},
                  "| wrong sign:", wsign)
            print(f"elasticity equivalent {(eff / sbar) / DBAR[g]:+.4f} [{(res['main']['lo'] / sbar) / DBAR[g]:+.4f}, {(res['main']['hi'] / sbar) / DBAR[g]:+.4f}] (s-bar {sbar:.1f}, d-bar {DBAR[g]})")
    pd.DataFrame(rows).to_csv(OUT / "firm_persistence.csv", index=False)
    pd.DataFrame(summ).to_csv(OUT / "firm_persistence_summary.csv", index=False)


if __name__ == "__main__":
    main()
