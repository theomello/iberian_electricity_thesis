"""Part 1 of docs/specs/2026-11-26-calendar-randomization-design.md: counterfactual calendars inside the same summer.

    tou_calendar_randomization.py 6.4        # one tariff per process; writes outputs/tables/tou_calendar_randomization_<tariff>.csv

For one tariff: the baseline estimate (tou_drift_location.eta_variant) for the real new calendar and for counterfactual calendars
whose new period of (date, hour) is the real new period of (date, (hour + k) mod 24), k in +-3..+-9, in 2021 and every placebo summer.
Cached errors only. The rules are evaluated in tou_calendar_randomization_rules.py.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_drift_location as DL  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_industry_regulated_price as RP  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
SHIFTS = [k for k in range(-9, 10) if abs(k) >= 3]


def main():
    tar = sys.argv[1]
    x = S6.build()
    clean = S6.gates(x)
    covid = x.date.between(*EV.COVID)
    pre = x.date.dt.year.isin(S6.YEARS) & ~covid
    dates = sorted(set(x.date[pre]) | set(pd.date_range(S6.R0, S6.R1)))
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= S6.R0) & (eh.index.get_level_values(0) <= S6.R1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    ren = pd.read_parquet(RP.T_ROOT / "data/ren/ren_market_prices.parquet")
    ren = ren[ren.series == "ES"]
    loc = ren.utc_timestamp.dt.tz_convert("Europe/Madrid")
    wp = ren.assign(date=pd.to_datetime(loc.dt.date.to_numpy()), hour=loc.dt.hour.to_numpy()).groupby(["date", "hour"]).value.mean()
    pt = RP.power_table()
    orig = RP.TS.new_period_6

    def dose(k):
        if k:
            RP.TS.new_period_6 = lambda d, h, hol: orig(d, (h + k) % 24, hol)
        try:
            tab = RP.tables(dates, pt, "full", wp=wp)
        finally:
            RP.TS.new_period_6 = orig
        return np.nan_to_num(CT.series_dose(tar, tab, ebar).reindex(idx).to_numpy())

    errs = S6.errors(x, clean)
    win21 = ((x.date >= S6.R0) & (x.date <= S6.R1)).to_numpy()
    work = (x.dow < 5).to_numpy() & (x.hol_es == 0).to_numpy()
    real = dose(0)
    rows = []
    for k in [0] + SHIFTS:
        dp = real if k == 0 else dose(k)
        corr = 1.0 if k == 0 else float(np.corrcoef(real[win21 & work], dp[win21 & work])[0, 1])
        for yr in [2021] + S6.SUMMERS:
            if yr == 2021:
                w, key, mask, rng = win21, "()", pre | pd.Series(win21, index=x.index), (S6.R0, S6.R1)
            else:
                a, b = S6.aligned(yr)
                w = ((x.date >= a) & (x.date <= b)).to_numpy()
                key, mask, rng = f"({yr},)", pre, (a, b)
            beta, se = DL.eta_variant(x, errs, key, {tar: np.where(w, dp, 0.0)}, mask, [tar], rng, "baseline")
            rows.append(dict(tariff=tar, shift=k, summer=yr, beta=beta, se=se, corr_with_real=corr))
        pd.DataFrame(rows).to_csv(OUT / f"tou_calendar_randomization_{tar}.csv", index=False)
        print(f"{tar} shift {k:+d} corr {corr:+.2f} done: 2021 {rows[-7]['beta']:+.3f}", flush=True)


if __name__ == "__main__":
    main()
