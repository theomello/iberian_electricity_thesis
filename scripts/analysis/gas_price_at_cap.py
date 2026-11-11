"""Did the Iberian gas price rise at the gas cap because of the cap, or with the European market?

On 15 June 2022 the Iberian cap began and the MIBGAS price rose (77 -> 113 EUR/MWh in the 14 days around it). Two
possible reasons: the cap raised Iberian gas burn and so the Iberian gas price; or the whole European gas market rose
that week (Russian flow cuts to Europe, mid-June 2022). Italy's PSV is the comparison: not coupled to Iberia, no cap.
Outcome: log MIBGAS minus log PSV (the Iberian spread) and each log price alone, as the change in the mean over the 14
days after 15 June against the 14 days before. Also Spanish minus Italian LNG send-out (GIE). Placebos: the same
28-day window on every Wednesday 2021-06-02 -> 2022-12-28 excluding windows touching the real break; the real change's
rank among them. Pass rule, set before the run: an Iberia-specific cap effect on the gas price needs the real spread
change outside the 5th-95th percentile of the placebos. Writes outputs/tables/gas_price_at_cap.csv.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
BREAK = pd.Timestamp("2022-06-15")
HALF = pd.Timedelta(days=14)


def prices() -> pd.DataFrame:
    m = pd.read_parquet(ROOT / "data/mibgas/mibgas_price_index_daily.parquet")
    m["d"] = pd.to_datetime(m.date)
    mib = m.set_index("d").mibgas_es_eur_mwh.rename("mibgas")
    g = pd.read_parquet(ROOT / "data/gme/gas/gme_mgp_gas_daily.parquet")
    g["gas_day"], g["session"] = pd.to_datetime(g.gas_day), pd.to_datetime(g.session)
    day_ahead = g[(g.gas_day - g.session).dt.days == 1].dropna(subset=["price_ref"])
    psv = day_ahead.groupby("gas_day").price_ref.last().rename("psv")
    d = pd.concat([mib, psv], axis=1).loc["2021-05-01":"2023-01-31"].dropna()
    d["ln_mibgas"], d["ln_psv"] = np.log(d.mibgas), np.log(d.psv)
    d["spread"] = d.ln_mibgas - d.ln_psv
    lng = []
    for c in ("ES", "IT"):
        x = pd.read_parquet(ROOT / "data/gie/gie_lng_daily.parquet")
        x = x[x.country == c]
        x["d"] = pd.to_datetime(x.gas_day)
        lng.append(x.set_index("d").sendOut.rename(f"lng_{c}"))
    d = d.join(pd.concat(lng, axis=1))
    d["ln_lng_es_minus_it"] = np.log(d.lng_ES.where(d.lng_ES > 0)) - np.log(d.lng_IT.where(d.lng_IT > 0))
    return d


def change(d, b, col):
    before = d.loc[b - HALF:b - pd.Timedelta(days=1), col].mean()
    after = d.loc[b:b + HALF - pd.Timedelta(days=1), col].mean()
    return after - before


def main():
    d = prices()
    print(f"{len(d)} days {d.index.min().date()} -> {d.index.max().date()}")
    cols = ["ln_mibgas", "ln_psv", "spread", "ln_lng_es_minus_it"]
    real = {c: change(d, BREAK, c) for c in cols}
    plac = {c: [] for c in cols}
    dates = []
    for pb in pd.date_range("2021-06-02", "2022-12-28", freq="7D"):
        if abs((pb - BREAK).days) < 28:
            continue
        if pb - HALF < d.index.min() or pb + HALF > d.index.max():
            continue
        for c in cols:
            plac[c].append(change(d, pb, c))
        dates.append(pb)
    rows = []
    for c in cols:
        p = np.array(plac[c])
        p = p[np.isfinite(p)]
        rows.append(dict(series=c, real_change=real[c], placebos=len(p), placebo_sd=p.std(), p05=np.percentile(p, 5),
                         p95=np.percentile(p, 95), rank_abs=int((np.abs(p) >= abs(real[c])).sum()) + 1))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "gas_price_at_cap.csv", index=False)
    pd.set_option("display.width", 200)
    print(out.round(3).to_string(index=False))
    b = d.loc[BREAK - HALF:BREAK - pd.Timedelta(days=1), ["mibgas", "psv", "lng_ES", "lng_IT"]].mean()
    a = d.loc[BREAK:BREAK + HALF - pd.Timedelta(days=1), ["mibgas", "psv", "lng_ES", "lng_IT"]].mean()
    print("\nlevels, mean of 14 days before -> after")
    print(pd.DataFrame({"before": b, "after": a, "change": a - b}).round(2).to_string())
    w = d.loc["2022-05-25":"2022-07-05", ["mibgas", "psv"]].round(1)
    print("\ndaily around the break\n", w.T.to_string())


if __name__ == "__main__":
    main()
