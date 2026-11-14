"""Exposed share of E0 and the evening-peak design on the regulated (PVPC) retailers' schedule, ESIOS 352, beside E0.

Share: monthly ratio of ESIOS 352 (scheduled demand of reference/regulated retailers) to E0 (ESIOS 1201, measured low-voltage demand), 2018-01 -> 2021-12 (also 351 and 353 over E0).
Design: as the charge-cut test (tou_charge_dose.py) with src="352": DDD of E0-style cells (evening 18-21h vs night, working days vs weekend-holiday), V2 pre-window, Portugal control, in windows
Jun-Sep 2021, A (to 09-15) and B (09-16 on), plus the paper-style LASSO errors (tou_lasso_paper) for the same windows. Elasticity = DDD / change in ln relative price (tou_charge_dose.price_change).
Writes outputs/tables/tou_pvpc_only_{share,main}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_charge_dose as C  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as E  # noqa: E402
import tou_lasso_paper as L  # noqa: E402

TS = pd.Timestamp
WINDOWS = {"Jun-Sep 2021": (TS("2021-06-01"), TS("2021-09-30")), "A 2021-06-01 -> 09-15": (TS("2021-06-01"), TS("2021-09-15")), "B 2021-09-16 -> 12-31": (TS("2021-09-16"), TS("2021-12-31"))}


def shares():
    def m(i):
        d = pd.read_parquet(T.ROOT / f"data/esios/esios_{i}.parquet")
        d = d[d.geo_name.isin(["Península", "España"])].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value
        return d.groupby(d.index.tz_convert("Europe/Madrid").tz_localize(None).to_period("M")).sum()
    s = pd.DataFrame({k: m(i) for k, i in (("e0", 1201), ("pvpc352", 352), ("free351", 351), ("direct353", 353))}).dropna()
    s = s[(s.index >= "2018-01") & (s.index <= "2021-12")]
    s["share352_of_e0"] = s.pvpc352 / s.e0
    s["share351_of_e0"] = s.free351 / s.e0
    return s


def main():
    sh = shares()
    sh.round(4).to_csv(T.OUT / "tou_pvpc_only_share.csv")
    print(sh[["share352_of_e0", "share351_of_e0"]].round(3).iloc[[0, 5, 11, 12, 17, 23, 24, 29, 35, 36, 41, 47]].to_string(), flush=True)
    rows = []
    for src in ("e0", "352"):
        x = D.prep(T.build(src, end="2021-12-31"))
        es, pt = L.errors(x)
        err = es - pt
        for wname, (s, e) in WINDOWS.items():
            keep = ((x.date <= C.PRE_END) | ((x.date >= s) & (x.date <= e))) & ~x.date.between(*E.COVID)
            y = E.classed(x[keep], C.HOURS)
            (b, se), (bw, _), (bk, _) = E.contrasts_of(y, s, e)
            lb, lse = L.cell_ddd(x, err, s, e)
            dln = C.price_change(s, e)
            rows.append(dict(series=src, window=wname, ddd_pct=100 * b, se_pct=100 * se, work_pct=100 * bw, weekend_pct=100 * bk, paper_lasso_pct=100 * lb, paper_lasso_se_pct=100 * lse,
                             d_ln_relative_price=dln, elasticity_ddd=b / dln, elasticity_paper_lasso=lb / dln))
            print(rows[-1], flush=True)
        b0, s0 = L.cell_ddd(x, err, TS("2018-01-01"), TS("2020-12-31"))
        print(src, "pre-period in-sample paper-LASSO DDD %.2f%% (se %.2f)" % (100 * b0, 100 * s0), flush=True)
    r = pd.DataFrame(rows)
    r.round(4).to_csv(T.OUT / "tou_pvpc_only_main.csv", index=False)
    pd.set_option("display.width", 220)
    print(r.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
