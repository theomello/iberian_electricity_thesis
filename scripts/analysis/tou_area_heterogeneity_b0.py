"""Step zero (B0, B4) of Part B of docs/specs/2026-11-17-dose-and-area-design.md. No real-window area effect is computed or printed.

    .venv/bin/python scripts/analysis/tou_area_heterogeneity_b0.py

Per Spanish regulated area: mean regulated supply points over the pre-window and the standard deviation of its weekday-peak effect (area vs the Portuguese regulated unit per consumer, cross-fitted errors) in the 18
placebo windows of the area panel; the cross-area variance of the five effects in each placebo window. Writes outputs/tables/tou_area_heterogeneity_b0*.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_area_panel as AP  # noqa: E402
import tou_area_panel_pc as PC  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402

AREAS = AP.AREAS


def main():
    x = AP.load_frame()
    x = x[(x.date >= PC.START) & (x.date <= PC.POST1)].copy()
    cs, ptc = PC.spain_counts(), PC.pt_counts()
    PC.add_pc(x, cs, "", "p48", ptc)
    PC.add_pc(x, cs, "", "pdbf")
    PC.add_pc(x, PC.spain_counts(+0.005), "_up", "p48")
    PC.add_pc(x, PC.spain_counts(-0.005), "_dn", "p48")
    PC.add_pc(x, PC.spain_counts(drop_q3_2019=True), "_nq3", "p48")
    errs = PC.get_errors(x)
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= PC.START) & (x.date <= "2020-12-31") & ~covid
    w = {a: float(x.loc[pre, "date"].map(cs[a]).mean()) for a in AREAS}
    w["PT"] = float(x.loc[pre, "date"].map(ptc).mean())

    def cf(name):
        a, b = errs[(name, "(2018,)")], errs[(name, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], b[x.date.reindex(b.index).dt.year == 2019]])
    ctl = cf("PTU")
    pmask = (x.date >= PC.START) & (x.date <= "2019-12-31")
    rows = []
    stacks = {a: AP.long_stack(x, {a: cf(f"{a}_p48")}, ctl, [a], {a: w[a], "PT": w["PT"]}, pmask) for a in AREAS}
    for s0 in pd.date_range("2018-04-01", "2019-09-01", freq="MS"):
        e0 = s0 + pd.Timedelta(days=105)
        if e0 > pd.Timestamp("2019-12-31"):
            continue
        for a in AREAS:
            b, se = AP.did_types(stacks[a], s0, e0, True)["wd_peak"]
            rows.append(dict(start=s0.date(), area=a, wd_peak=b, se=se))
    P = pd.DataFrame(rows)
    sd = P.groupby("area").wd_peak.agg(["mean", "std"]).rename(columns={"std": "placebo_sd"})
    sd["mean_regulated_points"] = pd.Series({a: w[a] for a in AREAS})
    sd["drop_if_sd_above_0.03"] = sd.placebo_sd > 0.03
    var = P.groupby("start").wd_peak.var(ddof=1).rename("cross_area_var")
    print((100 * sd[["mean", "placebo_sd"]]).round(2).join(sd[["mean_regulated_points", "drop_if_sd_above_0.03"]]).round(0).to_string(), flush=True)
    print(f"placebo cross-area variance of peak effects (windows {len(var)}): median {np.median(var):.2e}, 95th percentile {np.quantile(var, 0.95):.2e}, max {var.max():.2e}", flush=True)
    q = pd.read_csv(T.OUT / "cnmc_regulated_points_quarterly.csv")
    print("B4 tariff-mix fields in the CNMC counts:", [c for c in q.columns if "tarif" in c.lower() or "2.0" in c or "3.0" in c], "| regulated share varies by area:", q.groupby("area").regulated_share_domestic.mean().round(2).to_dict(), flush=True)
    sd.round(5).to_csv(T.OUT / "tou_area_heterogeneity_b0.csv")
    P.round(5).to_csv(T.OUT / "tou_area_heterogeneity_b0_placebo.csv", index=False)
    var.round(8).to_csv(T.OUT / "tou_area_heterogeneity_b0_variance.csv")


if __name__ == "__main__":
    main()
