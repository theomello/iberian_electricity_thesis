"""R2 of docs/specs/2026-11-12-demand-redesign-options.md: synthetic control on the day-level night-minus-midday log gap. Real break NOT computed.

Per series and local day: gap = mean ln load over 00-07h minus mean ln load over 11-14h (local clock of each series' country). Treated: ESIOS 352.
Donors: E0 (1201), E1-E6 (1202-1207), 351, 353, Portugal total (REN, Lisbon clock), France (RTE eco2mix, Paris clock). Per placebo break b (the 26 of Step 2):
non-negative weights on dow-demeaned gaps fitted on 2021-09-01 -> 2023-01-31 EXCLUDING [b-35, b+21] and the real event's neighbourhood
[2022-06-08, 2022-07-06]; effect = coefficient on post in a regression of (352 gap - weighted donors) on post + weekday over [b-28, b+14).
Baseline: 352 gap minus Portugal's gap, same regression. MDE = 2.8 x sd. Data root: env VRE_DATA_ROOT.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = Path(os.environ.get("VRE_DATA_ROOT", ROOT))
OUT = ROOT / "outputs" / "tables"
NIGHT, MID = range(0, 7), range(11, 14)
EXCL = set(os.environ.get("R2_EXCLUDE", "").split(",")) - {""}  # donors left out (E0 contains the treated customers)
TAG = os.environ.get("R2_TAG", "")


def esios(i):
    d = pd.read_parquet(DATA / f"data/esios/esios_{i}.parquet")
    return d[d.geo_name == "Península"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value.resample("1h").mean()


def gap(s, tz):
    d = pd.DataFrame({"v": np.log(s.where(s > 0))}).dropna()
    loc = d.index.tz_convert(tz)
    d["date"], d["h"] = pd.to_datetime(loc.date), loc.hour
    d = d.drop_duplicates(["date", "h"])
    n = d[d.h.isin(NIGHT)].groupby("date").v.agg(["mean", "size"])
    m = d[d.h.isin(MID)].groupby("date").v.agg(["mean", "size"])
    ok = (n["size"] == len(NIGHT)) & (m["size"] == len(MID))
    return (n["mean"] - m["mean"])[ok]


def main():
    pt = pd.read_parquet(DATA / "data/ren/ren_production_15min.parquet")
    pt = pt[pt.series == "Consumption"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value_mw.resample("1h").mean()
    fr = pd.read_parquet(DATA / "data/rte/eco2mix_national.parquet").drop_duplicates("utc").set_index("utc").consommation
    G = {"352": gap(esios(352), "Europe/Madrid"), "351": gap(esios(351), "Europe/Madrid"), "353": gap(esios(353), "Europe/Madrid"),
         "E0": gap(esios(1201), "Europe/Madrid"), "PT": gap(pt, "Europe/Lisbon"), "FR": gap(fr, "Europe/Paris")}
    for i in range(1202, 1208):
        G[f"E{i - 1201}"] = gap(esios(i), "Europe/Madrid")
    G = pd.DataFrame(G).dropna()
    G = G[(G.index >= "2021-09-01") & (G.index <= "2023-02-15")]
    G["dow"] = G.index.dayofweek
    donors = [c for c in G.columns if c not in ("352", "dow") and c not in EXCL]
    breaks = [pd.Timestamp(f"{y}-{m:02d}-{d:02d}") for y in (2021, 2022, 2023) for m in range(1, 13) for d in (1, 15)]
    breaks = [b for b in breaks if (pd.Timestamp("2021-10-01") <= b <= pd.Timestamp("2022-04-15")) or (pd.Timestamp("2022-08-01") <= b <= pd.Timestamp("2023-01-15"))]
    rows, W = [], []
    for b in breaks:
        w = G[(G.index >= b - pd.Timedelta(days=28)) & (G.index < b + pd.Timedelta(days=14))]
        if len(w) < 38:
            continue
        ex = ((G.index >= b - pd.Timedelta(days=35)) & (G.index < b + pd.Timedelta(days=21))) | ((G.index >= "2022-06-08") & (G.index < "2022-07-06"))
        tr = G[~ex]
        dm = tr.groupby("dow")[["352"] + donors].transform(lambda v: v - v.mean())
        wt, _ = nnls(dm[donors].to_numpy(), dm["352"].to_numpy())
        W.append(dict(zip(donors, wt)))

        def eff(y):
            post = (w.index >= b).astype(float)
            X = np.column_stack([np.ones(len(w)), post, pd.get_dummies(w.dow.astype(str), drop_first=True, dtype=float).to_numpy()])
            return np.linalg.lstsq(X, y, rcond=None)[0][1]
        res = {"break": b, "synth": eff((w["352"] - w[donors].to_numpy() @ wt).to_numpy()), "pt_only": eff((w["352"] - w["PT"]).to_numpy()),
               "n_train": len(tr), "train_R2": 1 - ((dm["352"] - dm[donors].to_numpy() @ wt) ** 2).sum() / (dm["352"] ** 2).sum()}
        rows.append(res)
    r = pd.DataFrame(rows)
    r.to_csv(OUT / f"gascap_demand_r2{TAG}_placebo.csv", index=False)
    o = pd.DataFrame({"variant": ["synth", "pt_only"], "n": len(r), "sd": [r.synth.std(), r.pt_only.std()]})
    o["mde"] = 2.8 * o.sd
    o["P1_mde<=1.45%"], o["P2_mde<=14.5%"], o["stop_sd>=3%"] = o.mde <= 0.0145, o.mde <= 0.145, o.sd >= 0.03
    o.to_csv(OUT / f"gascap_demand_r2{TAG}.csv", index=False)
    print(o.round(4).to_string(index=False)); print("train R2 mean", r.train_R2.mean().round(3)); print(pd.DataFrame(W).mean().round(3).to_dict())


if __name__ == "__main__":
    main()
