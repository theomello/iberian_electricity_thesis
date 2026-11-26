"""docs/specs/2026-11-26-offset-stability-design.md: is tariff 6.4's placebo offset stable in 2021? Spring-window check.

Cached errors only. Spring window of year Y: 107 days starting 112 days before the aligned summer window start.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_drift_location as DL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
K = "6.4"


def main():
    x = S6.build()
    clean = S6.gates(x)
    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S6.YEARS) & ~covid
    spring = {}
    for y in S6.SUMMERS + [2021]:
        a = (S6.R0 if y == 2021 else S6.aligned(y)[0]) - pd.Timedelta(days=112)
        spring[y] = (a, a + pd.Timedelta(days=S6.LEN))
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)) | set(pd.date_range(*spring[2021])))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
    tab = RP.tables(dates, RP.power_table(), "full", wp=wp)
    dpk = np.nan_to_num(CT.series_dose(K, tab, ebar).reindex(idx).to_numpy())
    errs = S6.errors(x, clean)

    def run(windows):
        res = {}
        for y in S6.SUMMERS + [2021]:
            a, b = windows[y]
            w = ((x.date >= a) & (x.date <= b)).to_numpy()
            key, mask = ("()", pre | pd.Series(w, index=x.index)) if y == 2021 else (f"({y},)", pre)
            res[y] = DL.eta_variant(x, errs, key, {K: np.where(w, dpk, 0.0)}, mask, [K], (a, b), "baseline")[0]
        return res

    summer = run({y: ((S6.R0, S6.R1) if y == 2021 else S6.aligned(y)) for y in S6.SUMMERS + [2021]})
    pl = np.array([summer[y] for y in S6.SUMMERS])
    ok = abs(summer[2021] + 0.33676) < 0.0015 and abs(pl.mean() - 0.32562) < 0.0015 and abs(pl.std(ddof=1) - 0.083) < 0.0015
    print(f"R0 summer 6.4: eta {summer[2021]:+.5f} mean {pl.mean():+.5f} sd {pl.std(ddof=1):.5f} -> {'pass' if ok else 'FAIL'}", flush=True)
    if not ok:
        sys.exit("R0 failed")
    sp = run(spring)
    ps = np.array([sp[y] for y in S6.SUMMERS])
    m, sd = ps.mean(), ps.std(ddof=1)
    t = (sp[2021] - m) / (sd * np.sqrt(1 + 1 / 6))
    print("spring windows: " + " ".join(f"{y}:{sp[y]:+.3f}" for y in S6.SUMMERS + [2021]))
    print(f"spring placebo mean {m:+.4f} sd {sd:.4f}; 2021 spring {sp[2021]:+.4f}; t {t:+.2f}; summer offset {pl.mean():+.4f}")
    print("RULES")
    print(f"O1 |t| {abs(t):.2f} <= 2.57: {bool(abs(t) <= 2.57)}")
    print(f"O2 spring mean {m:+.3f} >= +0.16 and positive: {bool(m >= 0.16)}")
    pd.DataFrame([dict(year=y, spring=sp[y], summer=summer[y], spring_start=spring[y][0].date(), spring_end=spring[y][1].date()) for y in S6.SUMMERS + [2021]]
                 ).to_csv(OUT / "tou_offset_stability.csv", index=False)


if __name__ == "__main__":
    main()
