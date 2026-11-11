"""Pre-registered charge-change events against the seasonal baseline (docs/specs/2026-11-11-tou-hardening-design.md, "Pre-registration: charge-change events against the seasonal baseline").

Paper-style LASSO errors (tou_lasso_paper), E0 minus Portugal; DDD of the errors (evening 18-21h vs night, working vs weekend-holiday) in windows before and after three charge changes:
E1 2021-09-16 (cut), E2 2022-01-01 (rise), E3 2022-04-01 (partial cut, reported only). Placebo calendars 2018 and 2019 from errors cross-fitted by leaving each year out of the
training set (training years 2018-2020 without March-June 2020). Writes outputs/tables/tou_events.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_extended as X  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

TS = pd.Timestamp
EVENTS = {"E1 cut 2021-09-16": ((TS("2021-07-16"), TS("2021-09-15")), (TS("2021-09-16"), TS("2021-11-15"))),
          "E2 rise 2022-01-01": ((TS("2021-10-01"), TS("2021-12-31")), (TS("2022-01-01"), TS("2022-03-31"))),
          "E3 partial cut 2022-04-01": ((TS("2022-01-01"), TS("2022-03-31")), (TS("2022-04-01"), TS("2022-06-30")))}


def change(x, err, pre, post):
    b0, s0 = L.cell_ddd(x, err, *pre)
    b1, s1 = L.cell_ddd(x, err, *post)
    return b1 - b0, float(np.hypot(s0, s1)), b0, b1


def main():
    x = D.prep(T.build("e0", end="2022-06-30"))
    es, pt = L.errors(x)
    real = es - pt
    print("real-model errors done", flush=True)
    cf = pd.Series(np.nan, index=x.index)
    for yr in (2018, 2019, 2020):
        e1, e2 = L.errors(x, exclude_years=(yr,))
        m = x.date.dt.year == yr
        cf[m] = (e1 - e2)[m]
        print("cross-fit fold", yr, flush=True)
    dx = X.daily_regressors()
    rows = []
    for name, (pre, post) in EVENTS.items():
        d, se, b0, b1 = change(x, real, pre, post)
        dxc = dx.loc[post[0]:post[1], "x_charge"].mean() - dx.loc[pre[0]:pre[1], "x_charge"].mean()
        dxe = dx.loc[post[0]:post[1], "x_energy"].mean() - dx.loc[pre[0]:pre[1], "x_energy"].mean()
        rows.append(dict(event=name, kind="real", ddd_pre=100 * b0, ddd_post=100 * b1, change=100 * d, se=100 * se, t=d / se, d_x_charge=dxc, d_x_energy=dxe))
        print(rows[-1], flush=True)
    placebo = {"E1 cut 2021-09-16": [(TS(f"{y}-07-16"), TS(f"{y}-09-15"), TS(f"{y}-09-16"), TS(f"{y}-11-15")) for y in (2018, 2019)],
               "E2 rise 2022-01-01": [(TS(f"{y}-10-01"), TS(f"{y}-12-31"), TS(f"{y + 1}-01-01"), TS(f"{y + 1}-03-31")) for y in (2018, 2019)]}
    for name, wins in placebo.items():
        for a, b, c, d_ in wins:
            d, se, b0, b1 = change(x, cf, (a, b), (c, d_))
            rows.append(dict(event=name, kind=f"placebo {a.year}", ddd_pre=100 * b0, ddd_post=100 * b1, change=100 * d, se=100 * se, t=d / se))
            print(rows[-1], flush=True)
    r = pd.DataFrame(rows)
    r.round(4).to_csv(T.OUT / "tou_events.csv", index=False)
    pd.set_option("display.width", 220)
    print(r.round(3).to_string(index=False))
    g = lambda ev, kind: r[(r.event == ev) & (r.kind == kind)].iloc[0]
    e1, e2 = "E1 cut 2021-09-16", "E2 rise 2022-01-01"
    re1, re2 = g(e1, "real"), g(e2, "real")
    p1 = r[(r.event == e1) & r.kind.str.startswith("placebo")]
    p2 = r[(r.event == e2) & r.kind.str.startswith("placebo")]
    elig = {e: abs(g(e, "real").d_x_charge) >= 3 * abs(g(e, "real").d_x_energy) for e in (e1, e2)}
    print("RULE 1 eligibility:", elig, "-> E2 must pass:", elig[e2])
    print("RULE 2 E2 negative, t <= -2:", re2.change < 0 and re2.t <= -2, f"(change {re2.change:.2f}, t {re2.t:.2f})")
    print("RULE 3 E2 below both placebos:", bool((re2.change < p2.change).all()), p2.change.round(2).tolist())
    print("RULE 4 E1 positive, t >= 2, above both placebos:", re1.change > 0 and re1.t >= 2 and bool((re1.change > p1.change).all()), f"(change {re1.change:.2f}, t {re1.t:.2f})", p1.change.round(2).tolist())
    eps = {}
    for e, re, p in ((e1, re1, p1), (e2, re2, p2)):
        adj = (re.change - p.change.mean()) / 100.0
        se = np.sqrt(re.se ** 2 + (p.se ** 2).sum() / len(p) ** 2) / 100.0
        eps[e] = (adj / re.d_x_charge, se / abs(re.d_x_charge))
    print("implied elasticities (placebo-adjusted):", {k: (round(v[0], 3), round(v[1], 3)) for k, v in eps.items()})
    v = [eps[e1][0], eps[e2][0]]
    print("RULE 5 both negative, within factor two:", all(a < 0 for a in v) and 0.5 <= v[0] / v[1] <= 2)
    w = np.array([1 / eps[e][1] ** 2 for e in (e1, e2)])
    pooled = float((w * np.array(v)).sum() / w.sum())
    pse = float(1 / np.sqrt(w.sum()))
    print(f"RULE 6 pooled elasticity {pooled:.3f} (se {pse:.3f}, t {pooled / pse:.2f}):", pooled < 0 and pooled / pse <= -2)


if __name__ == "__main__":
    main()
