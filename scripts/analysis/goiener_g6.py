"""G6 of docs/specs/2026-11-17-goiener-household-design.md: robustness of G2 across subsets, from the saved household errors (no new LASSO fit for households).

    .venv/bin/python scripts/analysis/goiener_g6.py

Inputs: data/goiener/daily/g2_household_window.parquet (window errors, peak and off-peak), g_placebo_errors.parquet (leave-year-out placebo errors, from goiener_save_errors.py), the Portuguese series through the same
pipeline (recomputed, cheap). Subsets of the 3,000-household 2.0TD sample: (a) all (reproduces G2), (b) declared self-consumption excluded (already true of the main sample: selection requires self_consumption_type
missing), (c) at least 24 pre-lockdown calendar months with data, (d) Gipuzkoa and Bizkaia only. Pooled response = mean household-day (peak - off) error - Portugal's; eta = response / 0.784; randomization against the
26 season-matched placebo windows (one-sided p = (1+#{placebo eta <= eta_real})/27, eta_RI = eta_real - mean placebo, interval eta_real - [q97.5, q2.5]). Rule G6: sign and G2 band hold: eta_RI in [-0.20, -0.03]
and p <= 0.05. Writes outputs/tables/goiener_g6.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goiener_household as GH  # noqa: E402
import goiener_noise as G  # noqa: E402
import tou_did as T  # noqa: E402
import tou_randomization_inference as RI  # noqa: E402

ROOT = T.ROOT
DOSE = 0.784


def main():
    meta = pd.read_parquet(ROOT / "data/goiener/daily/selected_metadata.parquet").set_index("user")
    daily = pd.read_parquet(ROOT / "data/goiener/daily/daily.parquet")
    daily["date"] = pd.to_datetime(daily.date)
    pre = daily[daily.date < "2020-03-01"]
    premonths = pre.assign(m=pre.date.dt.to_period("M")).groupby("user").m.nunique()
    E = pd.read_parquet(ROOT / "data/goiener/daily/g2_household_window.parquet")
    E["date"] = pd.to_datetime(E.date)
    P = pd.read_parquet(ROOT / "data/goiener/daily/g_placebo_errors_pre.parquet")
    P["date"] = pd.to_datetime(P.date)
    P["contrast"] = P.peak - P.off
    hol = pd.read_parquet(ROOT / "data/holidays/holidays_es_pt.parquet")
    hpt = set(pd.to_datetime(hol[hol.area == "PT"].date))
    temps = G.daily_temps()
    x = RI.D.prep(T.build("e0", end="2021-09-15"))
    d = x[~x.date.isin(hpt) & (x.date.dt.dayofweek < 5)].copy()
    d["per"] = np.where(d.hour.isin(GH.PEAK), "kwh_peak", np.where(d.hour < 8, "kwh_off", "kwh_mid"))
    d = d[(d.date < "2020-03-01") | ((d.date >= GH.W0) & (d.date <= GH.W1))]
    cnt = d.groupby("date").size()
    pv = d.pivot_table(index="date", columns="per", values="load_pt", aggfunc="sum")[["kwh_peak", "kwh_off"]]
    pv = pv[cnt.reindex(pv.index) == 24]
    pt_win = GH.series_window(pv, temps["pt"]).set_index("date").contrast
    pt_pl = G.one_household("PT", pv[pv.index < "2020-03-01"].reset_index(), temps["pt"]).set_index("date").contrast
    wins = [(k, a, b) for k, a, b in RI.windows() if a.year in (2018, 2019) and abs((a - pd.Timestamp(year=a.year, month=6, day=1)).days) <= 45]
    pt_real = float(pt_win.mean())
    pt_means = [float(pt_pl[(pt_pl.index >= a) & (pt_pl.index <= b)].mean()) for k, a, b in wins]
    users_all = set(E.user.unique())
    subsets = {
        "all (G2 sample)": users_all,
        "declared self-consumption excluded (true by construction)": users_all,
        ">= 24 pre-lockdown months": {u for u in users_all if premonths.get(u, 0) >= 24},
        "Gipuzkoa and Bizkaia only": {u for u in users_all if meta.loc[u, "province"] in ("Gipuzkoa", "Bizkaia")},
    }
    rows = []
    for name, us in subsets.items():
        e = E[E.user.isin(us)]
        real = float(e.contrast.mean()) - pt_real
        plc = []
        for (k, a, b), pm in zip(wins, pt_means):
            w = P[P.user.isin(us) & (P.date >= a) & (P.date <= b)]
            plc.append(float(w.contrast.mean()) - pm)
        plc = np.array(plc) / DOSE
        eta = real / DOSE
        p = (1 + np.sum(plc <= eta)) / (1 + len(plc))
        rows.append(dict(subset=name, households=len(us), window_household_days=len(e), eta_raw=eta, mean_placebo=float(plc.mean()), eta_RI=eta - float(plc.mean()), p_one_sided=p,
                         fisher_lo=eta - float(np.quantile(plc, 0.975)), fisher_hi=eta - float(np.quantile(plc, 0.025))))
        r = rows[-1]
        r["G6_pass"] = bool(-0.20 <= r["eta_RI"] <= -0.03 and p <= 0.05)
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "goiener_g6.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
