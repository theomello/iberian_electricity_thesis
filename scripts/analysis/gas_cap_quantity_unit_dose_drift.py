import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, "/Users/theodor/projects/vre_spain_thesis/scripts/analysis")
import gas_cap_quantity_unit_dose as k
from gas_cap_quantity_b1 import panel, matrix, CAP0
from gas_cap_offer_panel import iberia_steps, italy_steps
h = panel(); W, _ = matrix(h, "run20"); W.index.name = "unit"
meta = h.drop_duplicates("unit").set_index("unit"); ib = meta.iberia.reindex(W.index)
h = h[h.unit.isin(W.index)]
si, ci = iberia_steps(); st, ct = italy_steps()
S = ci.groupby("date").subsidy.max()
src = {True: (si, ci), False: (st, ct)}
zone = h.groupby("unit").zone.first(); firm = meta.firm
cg = pd.concat([ci, ct]).groupby("unit").cost_gross.median()
stop = CAP0 - pd.Timedelta(days=1)
for P in k.PLACEBOS:
    Sp = pd.Series(S.reindex(pd.date_range(CAP0, CAP0 + (stop - P))).fillna(0).to_numpy(), index=pd.date_range(P, stop))
    print(f"\n===== placebo {P.date()} =====")
    for c in (True, False):
        G = k.dose(h[h.iberia == c], *src[c], P, Sp, stop).unstack()
        gi = G.mean(axis=1)
        Wc = W[ib == c]
        Wc = Wc.loc[:, Wc.columns < CAP0 - pd.Timedelta(days=6)]
        Y = Wc - Wc.mean(axis=0)            # week-demeaned within country
        t = pd.qcut(gi.reindex(Y.index), 3, labels=["low", "mid", "high"])
        win = pd.cut(pd.Series(Y.columns, index=Y.columns),
                     [pd.Timestamp("2000-01-01"), P - k.REF, P, CAP0], labels=["before ref", "ref", "after P"], right=False)
        tab = Y.T.groupby(win, observed=True).mean().T.groupby(t, observed=True).mean()
        tab["n"] = t.value_counts()
        tab["mean g"] = gi.groupby(t, observed=True).mean()
        print("Iberia" if c else "Italy", "| run20 minus week mean, by would-be-dose tercile:")
        print(tab.round(3).to_string())
        if not c:
            hi = t[t == "high"].index
            print("  high tercile by zone:", zone.reindex(hi).value_counts().to_dict())
            print("  high tercile by firm:", firm.reindex(hi).value_counts().head(6).to_dict())
            print("  corr(g, median gross cost):", round(gi.corr(cg.reindex(gi.index)), 2),
                  "| corr(g, ref-window run20):", round(gi.corr(Wc.loc[:, (Wc.columns >= P - k.REF) & (Wc.columns < P)].mean(axis=1)), 2))
    # monthly path of Italian high minus low
    G = k.dose(h[~h.iberia], *src[False], P, Sp, stop).unstack(); gi = G.mean(axis=1)
    Wc = W[~ib]; Y = Wc - Wc.mean(axis=0); t = pd.qcut(gi.reindex(Y.index), 3, labels=["low", "mid", "high"])
    m = Y.T.groupby(Y.columns.to_period("M")).mean().T.groupby(t, observed=True).mean()
    print("Italy high − low by month (whole window):")
    print((m.loc["high"] - m.loc["low"]).round(2).to_string())

# does Italy's high−low gap move with the gas price? (dose tercile from the real-cap curves, would-be S)
print("\n===== gap vs gas price, monthly =====")
psv = pd.read_parquet("/Users/theodor/projects/vre_spain_thesis/data/gme/gas/gme_mgp_gas_daily.parquet")
print(psv.columns.tolist()[:12])
