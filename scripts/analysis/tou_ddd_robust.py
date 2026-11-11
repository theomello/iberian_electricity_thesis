"""Month-by-month path and France control for the time-of-use triple difference (docs/specs/2026-11-11-tou-hardening-design.md).

E0 (ESIOS 1201) against a control, DiD V1 triple difference of tou_ddd.py (working-day peak minus off, less the same clock hours on
weekends and holidays). Path: for each month 2019-01 -> 2021-09 (March-June 2020 out) the DDD with that month as the post window and
everything before it from 2018-01 (COVID months out) as the pre-window. France: RTE eco2mix consumption (hourly, French clock) in place
of Portugal's, and the mean of the two logs; real break 2021-06-01 -> 2021-09-30 and the 17 placebo breaks of tou_ddd.py.
Writes outputs/tables/tou_ddd_path.csv and tou_ddd_control.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402

COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2020-06-30"))


def with_france(x):
    f = pd.read_parquet(T.ROOT / "data/rte/eco2mix_national.parquet", columns=["utc", "consommation"]).drop_duplicates("utc").set_index("utc").consommation
    loc = f.index.tz_convert("Europe/Paris")
    fr = pd.DataFrame({"date": pd.to_datetime(loc.date), "hour": loc.hour, "load_fr": f.to_numpy()}).drop_duplicates(["date", "hour"])
    y = x.merge(fr, on=["date", "hour"], how="inner").dropna(subset=["load_fr"])
    y["d_pt"] = y.d
    y["d_fr"] = np.log(y.load_es) - np.log(y.load_fr)
    y["d_avg"] = np.log(y.load_es) - 0.5 * (np.log(y.load_pt) + np.log(y.load_fr))
    return y.reset_index(drop=True)


def main():
    x = D.prep(T.build("e0"))
    x = x[~x.date.between(*COVID)]  # COVID months out of every window (pre and post)
    rows = []
    for b in pd.date_range("2019-01-01", "2021-09-01", freq="MS"):
        end = b + pd.offsets.MonthEnd(0)
        if COVID[0] <= b <= COVID[1]:
            continue
        s = x[x.date <= end]
        # only the month in question counts as post: the earlier months are the pre-window
        r = D.did_ddd(s, b, end)
        rows.append(dict(month=b.strftime("%Y-%m"), ddd_peak=100 * r["DDD peak"][0], se=100 * r["DDD peak"][1], t=r["DDD peak"][0] / r["DDD peak"][1],
                         ddd_mid=100 * r["DDD mid"][0], peak_off_work=100 * r["peak-off work"][0], peak_off_wknd=100 * r["peak-off wknd"][0]))
        print(rows[-1], flush=True)
    path = pd.DataFrame(rows)
    path.round(3).to_csv(T.OUT / "tou_ddd_path.csv", index=False)
    # France control
    xf = with_france(D.prep(T.build("e0")))
    out = []
    for lab, col in (("Portugal", "d_pt"), ("France", "d_fr"), ("mean of Portugal and France", "d_avg")):
        y = xf.copy()
        y["d"] = y[col]
        r = D.did_ddd(y, T.BREAK, T.END)
        pl = []
        for b0 in pd.date_range("2019-01-01", "2020-12-01", freq="MS"):
            end = b0 + pd.DateOffset(months=4) - pd.Timedelta(days=1)
            if end >= COVID[0] and b0 <= COVID[1]:
                continue
            rr = D.did_ddd(y, b0, end)
            pl.append(rr["DDD peak"][0] * 100)
        pl = pd.Series(pl)
        real = r["DDD peak"][0] * 100
        out.append(dict(control=lab, n=len(y), ddd_peak=real, se=100 * r["DDD peak"][1], t=r["DDD peak"][0] / r["DDD peak"][1], ddd_mid=100 * r["DDD mid"][0],
                        peak_off_work=100 * r["peak-off work"][0], peak_off_wknd=100 * r["peak-off wknd"][0], placebo_sd=pl.std(), placebo_p05=pl.quantile(.05),
                        placebo_p95=pl.quantile(.95), rank=int((pl.abs() >= abs(real)).sum()) + 1, n_placebos=len(pl)))
        print(out[-1], flush=True)
    pd.DataFrame(out).round(3).to_csv(T.OUT / "tou_ddd_control.csv", index=False)
    pd.set_option("display.width", 220)
    print(path.round(2).to_string(index=False))
    print(pd.DataFrame(out).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
