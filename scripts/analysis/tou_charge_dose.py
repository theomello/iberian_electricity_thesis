"""Pre-registered charge-cut dose-response (docs/specs/2026-11-11-tou-hardening-design.md, "Pre-registration: the charge-cut dose-response").

E0 against Portugal and France, evening peak 18-21h against night, working days against weekends and holidays, V2 pre-window (2018-01-01 -> 2020-12-31
without March-June 2020). Post windows A = 2021-06-01 -> 2021-09-15 (system charges high) and B = 2021-09-16 -> 2021-12-31 (charges cut), each estimated with
the other removed. Change in ln relative price by window from ESIOS 1001 and 1876 (evening vs night, working days); elasticity = DDD / change. Monthly path.
LASSO errors (Portugal) for both windows. Writes outputs/tables/tou_charge_dose_{main,path}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ddd as D  # noqa: E402
import tou_ddd_robust as R  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as E  # noqa: E402

PRE_END = pd.Timestamp("2020-12-31")
WINDOWS = {"A high charge 2021-06-01 -> 2021-09-15": (pd.Timestamp("2021-06-01"), pd.Timestamp("2021-09-15")),
           "B low charge 2021-09-16 -> 2021-12-31": (pd.Timestamp("2021-09-16"), pd.Timestamp("2021-12-31"))}
HOURS = [18, 19, 20, 21]


def price_change(start, end):
    def hourly(i):
        d = pd.read_parquet(T.ROOT / f"data/esios/esios_{i}.parquet")
        d = d[d.geo_name.isin(["Península", "España"])].drop_duplicates("utc_timestamp")
        loc = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
        return pd.DataFrame({"date": loc.dt.tz_localize(None).dt.normalize().to_numpy(), "hour": loc.dt.hour.to_numpy(), f"v{i}": d.value.to_numpy()})
    p = hourly(1001).merge(hourly(1876), on=["date", "hour"])
    p = p[(p.date >= start) & (p.date <= end) & (p.date.dt.dayofweek < 5)].copy()
    p["E"] = p.v1001 - p.v1876
    p["blk"] = np.where(p.hour.isin(HOURS), "b", np.where(p.hour < 8, "n", "x"))
    day = p[p.blk != "x"].groupby(["date", "blk"])[["E", "v1876"]].mean().unstack()
    new = np.log((day[("E", "b")] + day[("v1876", "b")]) / (day[("E", "n")] + day[("v1876", "n")]))
    old = np.log((day[("E", "b")] + E.OLD) / (day[("E", "n")] + E.OLD))
    return float((new - old).mean())


def estimate(x, start, end):
    """DDD for the evening peak: pre-window (up to PRE_END, no COVID) plus days start..end; break = start."""
    keep = (x.date <= PRE_END) | ((x.date >= start) & (x.date <= end))
    keep &= ~x.date.between(*E.COVID)
    y = E.classed(x[keep], HOURS)
    (b, se), (bw, _), (bk, _) = E.contrasts_of(y, start, end)
    return b, se, bw, bk, y


def main():
    x0 = D.prep(T.build("e0", end="2021-12-31"))
    xf = R.with_france(x0)
    rows, path = [], []
    for ctrl, col in (("Portugal", "d_pt"), ("France", "d_fr")):
        x = xf.assign(d=xf[col])
        for wname, (s, e) in WINDOWS.items():
            b, se, bw, bk, y = estimate(x, s, e)
            dln = price_change(s, e)
            row = dict(control=ctrl, window=wname, ddd_pct=100 * b, se_pct=100 * se, t=b / se, work_pct=100 * bw, weekend_pct=100 * bk, d_ln_relative_price=dln, elasticity=b / dln)
            if ctrl == "Portugal":
                z = E.classed(x[((x.date <= PRE_END) | ((x.date >= s) & (x.date <= e))) & ~x.date.between(*E.COVID)], HOURS)
                lb, lse = E.lasso_cells(z, s, e)
                row.update(lasso_ddd_pct=100 * lb, lasso_se_pct=100 * lse)
            rows.append(row)
            print(row, flush=True)
    main_t = pd.DataFrame(rows)
    main_t.round(4).to_csv(T.OUT / "tou_charge_dose_main.csv", index=False)
    # monthly path, Portugal
    x = xf.assign(d=xf.d_pt)
    for lab, s, e in (("Jun", "2021-06-01", "2021-06-30"), ("Jul", "2021-07-01", "2021-07-31"), ("Aug", "2021-08-01", "2021-08-31"), ("Sep 1-15", "2021-09-01", "2021-09-15"),
                      ("Sep 16-30", "2021-09-16", "2021-09-30"), ("Oct", "2021-10-01", "2021-10-31"), ("Nov", "2021-11-01", "2021-11-30"), ("Dec", "2021-12-01", "2021-12-31")):
        b, se, bw, bk, _ = estimate(x, pd.Timestamp(s), pd.Timestamp(e))
        path.append(dict(month=lab, ddd_pct=100 * b, se_pct=100 * se, work_pct=100 * bw, weekend_pct=100 * bk))
        print(path[-1], flush=True)
    pd.DataFrame(path).round(3).to_csv(T.OUT / "tou_charge_dose_path.csv", index=False)
    pd.set_option("display.width", 220)
    print(main_t.round(3).to_string(index=False))
    print(pd.DataFrame(path).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
