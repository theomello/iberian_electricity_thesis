#!/usr/bin/env python3
"""The IVPEE's full 7% steps: its return on 2019-04-01, and the two suspensions.

    .venv/bin/python scripts/analysis/ivpee_2019_test.py

Follows `ivpee_tax_test.py` (the 2024 steps, too small to see: 1.8–3.6% against a
month-start noise of 3.5–5.5%). Here the Spanish tax on generation revenue moves by
the full 7% in one day, so a Spanish unit's declared variable cost should move by
log(1/0.93) = 7.3% relative to a Portuguese unit's:

  2019-04-01  back to 7% after the 2018 Q4 – 2019 Q1 suspension (RDL 15/2018).
              MAIN: nothing else changed that day. Portugal's clawback is set per
              year, and its 2019 value only on 2019-09-26 (Despacho 8521/2019).
  2018-10-07  suspended. RDL 15/2018 was approved on Friday 5 October, after that
              day's offers had closed, and also removed the hydrocarbon tax on fuel
              for power plants from the 7th; the predicted drop is 7.3% plus that.
  2021-07-01  suspended (RDL 12/2021). Portugal's clawback was suspended for the
              same months, so the gap moves less if Portuguese units priced that in.

Same outcome and model as the 2024 test: log of the minimum-income variable term
(`cab`), each unit's own slope on its log implied cost, unit effects, and here date ×
fuel effects, since combined cycles (gas) and coal plants (Portugal's Sines and Pego
until 2021) are both used and a common date effect cannot absorb two fuel prices.
Terms of 999 ("never") and outside 0.5–3 times the implied cost are dropped.

The step-day jump: the Spanish − Portuguese gap in the 7 or 14 days after against the
days before. Benchmark: the same jump on every first of the month from 2018-02 to
2021-06 without a tax change (39 dates), which also gives the p-values of the
pass-through θ = jump / 7.3%, for April 2019 alone and the three events stacked. Also day by day (±14) and pooled over 2018-01-04 →
2021-06 (τ = 7%, 0 in the suspension), with a wild cluster bootstrap by unit.

Which side moved: the regression identifies only the gap, so each country's change
in declared term and cost is printed beside it (`by_side`).

Writes outputs/tables/ivpee_2019_test.csv, ivpee_2019_daily.csv,
ivpee_2019_by_side.csv and outputs/figures/ivpee_2019_event_study.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from ivpee_tax_test import NEVER, RATIO, COST, declared, fit, units, vcov, wild_p  # noqa: E402

TABLES = ROOT / "outputs/tables"
FIG = ROOT / "outputs/figures/ivpee_2019_event_study.png"
START, END = "2018-01-04", "2021-12-31"   # the cost at bidding uses prices from D-2 or earlier
POOLED_END = "2021-06-30"
STEP = np.log(1 / 0.93)
EVENTS = [("2019-04-01", +STEP, "return to 7% (main)"),
          ("2018-10-07", -STEP, "suspension; hydrocarbon tax removed the same day"),
          ("2021-07-01", -STEP, "suspension; Portugal's clawback suspended too")]
SUSPENDED = [("2018-10-01", "2019-03-31"), ("2021-07-01", "2100-01-01")]
WIDTHS = (7, 14)
SEED = 20261006


def sample() -> pd.DataFrame:
    u = units(("combined_cycle", "thermal"))
    d = declared(u, START, END)
    v = d.min_income_var_eur_mwh
    r = v / d[COST]
    drop = {"no term (0)": v <= 0, "999": v >= NEVER, f"ratio to cost outside {RATIO}":
            (v > 0) & (v < NEVER) & ~r.between(*RATIO)}
    keep = ~np.logical_or.reduce(list(drop.values()))
    print(f"{len(d):,} unit-days; dropped: " + ", ".join(f"{k} {int(m.sum()):,}" for k, m in drop.items())
          + f"; kept {int(keep.sum()):,}")
    d = d[keep].copy()
    d["fuel"] = np.where(d.cab_tech == "combined_cycle", "gas", "coal")
    d["es"] = (d.country == "ES").astype(float)
    d["lv"] = np.log(d.min_income_var_eur_mwh)
    d["lc"] = np.log(d[COST])
    d["dfuel"] = d.date.dt.strftime("%Y-%m-%d") + "|" + d.fuel
    tau = np.full(len(d), 0.07)
    for a, b in SUSPENDED:
        tau[((d.date >= a) & (d.date <= b)).to_numpy()] = 0.0
    d["T"] = d.es * np.log(1 / (1 - tau))
    n = d.groupby(["fuel", "country"]).unit.nunique().unstack()
    print("units by fuel and country:\n" + n.to_string())
    return d


def jump(d: pd.DataFrame, D: pd.Timestamp, w: int, fuel: str | None = None):
    x = d[(d.date >= D - pd.Timedelta(days=w)) & (d.date < D + pd.Timedelta(days=w))]
    if fuel:
        x = x[x.fuel == fuel]
    x = x.copy()
    x["post"] = x.es * (x.date >= D)
    _, Xt, b, e = fit(x, "lv", ["post"], True, time="dfuel")
    return b[0], np.sqrt(vcov(Xt, e, [x.unit.to_numpy()])[0, 0]), len(x), int((x.groupby("unit").es.first() == 0).sum())


def main() -> int:
    d = sample()
    rows = []
    events = {pd.Timestamp(e) for e, _, _ in EVENTS}
    placebo_days = [D for D in pd.date_range("2018-02-01", "2021-06-01", freq="MS")
                    if not any(abs((D - E).days) <= 14 for E in events)]
    print(f"\n== step-day jumps, against {len(placebo_days)} first-of-month dates without a tax change")
    for w in WIDTHS:
        p = np.array([jump(d, D, w)[0] for D in placebo_days])
        rows += [{"model": "placebo month start", "date": D.date(), "days": w, "b": b, "predicted": 0.0}
                 for D, b in zip(placebo_days, p)]
        print(f"±{w} days: ordinary month starts sd {p.std(ddof=1):.4f}, 5–95% "
              f"[{np.quantile(p, .05):+.4f}, {np.quantile(p, .95):+.4f}]")
        signed = []
        for day, pred, what in EVENTS:
            D = pd.Timestamp(day)
            b, se, n, npt = jump(d, D, w)
            signed.append(np.sign(pred) * b)
            share = (np.sign(pred) * p >= np.sign(pred) * b).mean()
            rows.append({"model": "step day", "date": D.date(), "days": w, "b": b, "se": se, "predicted": pred,
                         "share_placebo_as_far": share, "n": n, "units_pt": npt, "event": what})
            print(f"  {day} {what}: {b:+.4f} ({se:.4f}), predicted {pred:+.4f}; "
                  f"month starts as far in that direction: {share:.3f}; {npt} Portuguese units")
            for fuel in ("gas", "coal"):
                bf, sef, nf, nptf = jump(d, D, w, fuel)
                rows.append({"model": f"step day, {fuel} only", "date": D.date(), "days": w, "b": bf, "se": sef,
                             "predicted": pred, "n": nf, "units_pt": nptf, "event": what})
                print(f"      {fuel} only: {bf:+.4f} ({sef:.4f}), {nptf} Portuguese units")
        rows += pass_through(p, signed, w)

    print(f"\n== pooled, {START} → {POOLED_END}: τ = 7%, 0 from 2018-10-01 to 2019-03-31")
    pdat = d[d.date <= POOLED_END]
    yt, Xt, b, e = fit(pdat, "lv", ["T"], True, time="dfuel")
    se = np.sqrt(vcov(Xt, e, [pdat.unit.to_numpy()])[0, 0])
    rng = np.random.default_rng(SEED)
    p0 = wild_p(yt, Xt[:, 0], pdat.unit.to_numpy(), 0.0, rng)
    p1 = wild_p(yt, Xt[:, 0], pdat.unit.to_numpy(), 1.0, rng)
    print(f"θ = {b[0]:.3f} ({se:.3f}); wild bootstrap p(θ=0) {p0:.3f}, p(θ=1) {p1:.3f}; predicted 1")
    rows.append({"model": "pooled 2018-01 to 2021-06", "b": b[0], "se": se, "predicted": 1.0,
                 "wild_p_theta0": p0, "wild_p_theta1": p1, "n": len(pdat),
                 "units_pt": int((pdat.groupby("unit").es.first() == 0).sum())})

    out = TABLES / "ivpee_2019_test.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"-> {out.relative_to(ROOT)}")
    by_side(d)
    daily(d)
    return 0


def by_side(d: pd.DataFrame, w: int = 14) -> None:
    """Which side moved: the change in each country's declared term and implied cost,
    on the day (median of day 0 against day −1) and over ±w days (unit means, units
    present on both sides). Descriptive: the regression identifies only the gap."""
    rows = []
    for day, pred, what in EVENTS:
        D = pd.Timestamp(day)
        x = d[(d.date >= D - pd.Timedelta(days=w)) & (d.date < D + pd.Timedelta(days=w))]
        for (fuel, ctry), g in x.groupby(["fuel", "country"]):
            m = g.groupby([g.unit, g.date >= D])[["lv", "lc"]].mean().unstack().dropna()
            a = g[g.date == D - pd.Timedelta(days=1)]
            b = g[g.date == D]
            rows.append({"event": day, "fuel": fuel, "country": ctry, "units": len(m),
                         "declared_day_before": a.min_income_var_eur_mwh.median(),
                         "declared_day": b.min_income_var_eur_mwh.median(),
                         "cost_day_before": a[COST].median(), "cost_day": b[COST].median(),
                         f"dlog_declared_{w}d": (m[("lv", True)] - m[("lv", False)]).mean(),
                         f"dlog_cost_{w}d": (m[("lc", True)] - m[("lc", False)]).mean()})
    r = pd.DataFrame(rows)
    r["dlog_declared_day"] = np.log(r.declared_day / r.declared_day_before)
    r["dlog_cost_day"] = np.log(r.cost_day / r.cost_day_before)
    out = TABLES / "ivpee_2019_by_side.csv"
    r.to_csv(out, index=False)
    print("\n== which side moved (medians on the day; unit means over ±14 days)")
    print(r[["event", "fuel", "country", "units", "declared_day_before", "declared_day", "dlog_declared_day",
             "dlog_cost_day", f"dlog_declared_{w}d", f"dlog_cost_{w}d"]].round(3).to_string(index=False))
    print(f"-> {out.relative_to(ROOT)}")


def pass_through(p: np.ndarray, signed: list[float], w: int) -> list[dict]:
    """θ = jump / 7.3%, for April 2019 alone and for the three events stacked (mean
    of the signed jumps). Inference from the ordinary month starts: under θ = θ0
    the jump is θ0 × 7.3% plus a month-start jump (for the stack, the mean of as many
    distinct month starts as events)."""
    from itertools import combinations
    out = []
    for label, idx in [("2019-04-01 alone", [0]), ("three events stacked", [0, 1, 2])]:
        obs = np.mean([signed[i] for i in idx])
        null = np.array([np.mean(c) for c in combinations(p, len(idx))])
        theta = obs / STEP
        p0 = (null >= obs).mean()
        p1 = (np.abs(null) >= abs(obs - STEP)).mean()
        print(f"  pass-through, {label}, ±{w} days: θ {theta:.2f} (month-start sd {null.std(ddof=1) / STEP:.2f}); "
              f"p(θ=0) {p0:.3f}, p(θ=1) {p1:.3f}")
        out.append({"model": f"pass-through, {label}", "days": w, "b": theta, "se": null.std(ddof=1) / STEP,
                    "predicted": 1.0, "p_theta0_placebo": p0, "p_theta1_placebo": p1})
    return out


def daily(d: pd.DataFrame, w: int = 14) -> None:
    """Spain × day relative to each event, day −1 the reference."""
    res = []
    for day, pred, what in EVENTS:
        D = pd.Timestamp(day)
        x = d[(d.date >= D - pd.Timedelta(days=w)) & (d.date < D + pd.Timedelta(days=w))].copy()
        rel = (x.date - D).dt.days
        cols = []
        for k in range(-w, w):
            if k != -1:
                x[f"k{k}"] = x.es * (rel == k)
                cols.append(f"k{k}")
        _, Xt, b, e = fit(x, "lv", cols, True, time="dfuel")
        se = np.sqrt(np.diag(vcov(Xt, e, [x.unit.to_numpy()])))
        r = pd.DataFrame({"event": day, "day": [int(c[1:]) for c in cols], "b": b, "se": se})
        res.append(pd.concat([r, pd.DataFrame({"event": [day], "day": [-1], "b": [0.0], "se": [0.0]})]))
    r = pd.concat(res).sort_values(["event", "day"])
    out = TABLES / "ivpee_2019_daily.csv"
    r.to_csv(out, index=False)
    print(f"-> {out.relative_to(ROOT)}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    for ax, (day, pred, what) in zip(axes, EVENTS):
        s = r[r.event == day]
        ax.axhline(0, color="0.6", lw=0.8)
        ax.axvline(-0.5, color="0.6", lw=0.8, ls=":")
        ax.plot([-w, -0.5, -0.5, w - 1], [0, 0, pred, pred], color="C3", lw=1.5, label="full pass-through")
        ax.errorbar(s.day, s.b, yerr=1.96 * s.se, fmt="o", ms=3, color="C0", capsize=0, lw=0.8,
                    label="Spain − Portugal (95%)")
        ax.set_title(f"{day}: {what}", fontsize=9)
        ax.set_xlabel("days from the change")
    axes[0].set_ylabel("log declared variable cost,\nrelative to the day before")
    axes[0].legend(fontsize=8, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIG, dpi=150)
    print(f"-> {FIG.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
