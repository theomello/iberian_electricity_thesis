"""Pre-registered evening-peak triple difference (docs/specs/2026-11-11-tou-hardening-design.md, "Pre-registration: the evening-peak design").

E0 (ESIOS 1201) against Portugal, France and their mean; break 2021-06-01, post window to 2021-09-30.
V1: DiD DDD on evening-peak (18-21h) and night (0-7h) hours, working days against weekends and holidays; pre-window all days since 2018-01-01
without March-June 2020. V2: V1 without January-May 2021. V3: LASSO prediction errors trained on 2018-01 -> 2020-12 without March-June 2020,
evaluated June-September 2021, DDD on the errors. Dose-response blocks (V2, Portugal), each against night with other blocks dropped, with the
change in ln relative price per block from ESIOS 1001, 1876 and the old flat 44. Placebo breaks (17) for V1 evening peak. Writes
outputs/tables/tou_evening_ddd_{main,blocks,placebo}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_ddd as D  # noqa: E402
import tou_ddd_robust as R  # noqa: E402
import tou_did as T  # noqa: E402

COVID = (pd.Timestamp("2020-03-01"), pd.Timestamp("2020-06-30"))
JAN_MAY = (pd.Timestamp("2021-01-01"), pd.Timestamp("2021-05-31"))
BLOCKS = {"evening peak 18-21h": [18, 19, 20, 21], "late mid-peak 22-23h": [22, 23], "afternoon mid-peak 14-17h": [14, 15, 16, 17],
          "morning mid-peak 8-9h": [8, 9], "morning peak 10-13h": [10, 11, 12, 13]}
NIGHT = list(range(0, 8))
OLD = 44.0


def classed(x, hours):
    y = x[x.hour.isin(hours + NIGHT)].copy()
    y["cls"] = np.where(y.hour < 8, "off", "peak")  # 'peak' = the block under test (tou_ddd contrasts key on it)
    y["cell"] = y.cls + "_" + y.kind
    return y


def contrasts_of(x, brk, end):
    r = D.did_ddd(x, brk, end)
    return r["DDD peak"], r["peak-off work"], r["peak-off wknd"]


def lasso_cells(x, brk, end):
    p = T.lasso_errors(x, brk, end)
    p["cell"] = x.loc[p.index, "cell"]
    Dm = pd.get_dummies(p.cell, dtype=float)
    Xv = Dm.to_numpy()
    b = np.linalg.pinv(Xv) @ p.err_d.to_numpy()
    e = p.err_d.to_numpy() - Xv @ b
    V = T.hac_cluster(Xv, e, p.date.dt.to_period("W").astype(str).factorize()[0])
    names = [f"post_{c}" for c in Dm.columns]
    return D.contrasts(b, V, names)["DDD peak"]


def block_price_change(hours):
    """Mean over working days June-September 2021 of ln relative price (block vs night): new regime minus old flat charge."""
    def hourly(i):
        d = pd.read_parquet(T.ROOT / f"data/esios/esios_{i}.parquet")
        d = d[d.geo_name.isin(["Península", "España"])].drop_duplicates("utc_timestamp")
        loc = d.utc_timestamp.dt.tz_convert("Europe/Madrid")
        return pd.DataFrame({"date": loc.dt.tz_localize(None).dt.normalize().to_numpy(), "hour": loc.dt.hour.to_numpy(), f"v{i}": d.value.to_numpy()})
    p = hourly(1001).merge(hourly(1876), on=["date", "hour"])
    p = p[(p.date >= "2021-06-01") & (p.date <= "2021-09-30") & (p.date.dt.dayofweek < 5)].copy()
    p["E"] = p.v1001 - p.v1876
    p["blk"] = np.where(p.hour.isin(hours), "b", np.where(p.hour < 8, "n", "x"))
    day = p[p.blk != "x"].groupby(["date", "blk"])[["E", "v1876"]].mean().unstack()
    new = np.log((day[("E", "b")] + day[("v1876", "b")]) / (day[("E", "n")] + day[("v1876", "n")]))
    old = np.log((day[("E", "b")] + OLD) / (day[("E", "n")] + OLD))
    return float((new - old).mean())


def main():
    base = D.prep(T.build("e0"))
    xf = R.with_france(base)
    drop_covid = lambda x: x[~x.date.between(*COVID)]
    rows = []
    for ctrl, col in (("Portugal", "d_pt"), ("France", "d_fr"), ("mean of Portugal and France", "d_avg")):
        y = xf.copy()
        y["d"] = y[col]
        y = drop_covid(y)
        for lab, data in (("V1", y), ("V2", y[~y.date.between(*JAN_MAY)])):
            (b, se), (bw, _), (bk, _) = contrasts_of(classed(data, BLOCKS["evening peak 18-21h"]), T.BREAK, T.END)
            rows.append(dict(control=ctrl, spec=lab, ddd_pct=100 * b, se_pct=100 * se, t=b / se, work_pct=100 * bw, weekend_pct=100 * bk))
        # V3: LASSO errors need temperature differences; available for Portugal only (France temperatures are not on disk)
        if ctrl == "Portugal":
            data = classed(y[~y.date.between(*JAN_MAY)], BLOCKS["evening peak 18-21h"])
            b, se = lasso_cells(data, T.BREAK, T.END)
            rows.append(dict(control=ctrl, spec="V3 LASSO errors", ddd_pct=100 * b, se_pct=100 * se, t=b / se))
        print(rows[-1], flush=True)
    main_t = pd.DataFrame(rows)
    main_t.round(3).to_csv(T.OUT / "tou_evening_ddd_main.csv", index=False)
    # placebo breaks, V1 evening peak, Portugal
    y = drop_covid(xf.assign(d=xf.d_pt))
    pl = []
    for b0 in pd.date_range("2019-01-01", "2020-12-01", freq="MS"):
        end = b0 + pd.DateOffset(months=4) - pd.Timedelta(days=1)
        if end >= COVID[0] and b0 <= COVID[1]:
            continue
        pl.append(100 * contrasts_of(classed(y, BLOCKS["evening peak 18-21h"]), b0, end)[0][0])
    pl = pd.Series(pl)
    real = main_t[(main_t.control == "Portugal") & (main_t.spec == "V1")].ddd_pct.iloc[0]
    pd.DataFrame({"placebo_ddd_pct": pl}).round(3).to_csv(T.OUT / "tou_evening_ddd_placebo.csv", index=False)
    print(f"placebo: real {real:+.2f}; {len(pl)} placebos sd {pl.std():.2f}, 5-95% [{pl.quantile(.05):+.2f}, {pl.quantile(.95):+.2f}], rank {int((pl.abs() >= abs(real)).sum()) + 1} of {len(pl) + 1}")
    # dose-response blocks, V2, Portugal
    y2 = drop_covid(xf.assign(d=xf.d_pt))
    y2 = y2[~y2.date.between(*JAN_MAY)]
    brows = []
    for name, hours in BLOCKS.items():
        (b, se), (bw, _), (bk, _) = contrasts_of(classed(y2, hours), T.BREAK, T.END)
        dln = block_price_change(hours)
        brows.append(dict(block=name, ddd_pct=100 * b, se_pct=100 * se, work_pct=100 * bw, weekend_pct=100 * bk, d_ln_relative_price=dln, elasticity=b / dln, se_elasticity=se / abs(dln)))
        print(brows[-1], flush=True)
    pd.DataFrame(brows).round(4).to_csv(T.OUT / "tou_evening_ddd_blocks.csv", index=False)
    pd.set_option("display.width", 220)
    print(main_t.round(2).to_string(index=False))
    print(pd.DataFrame(brows).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
