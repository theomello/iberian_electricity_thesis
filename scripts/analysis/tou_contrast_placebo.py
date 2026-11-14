"""Contrast placebo (docs/specs/2026-11-12-area-weather-design.md, last section): weekday peak minus off-peak, six non-overlapping windows.

Reads the cached cross-fitted errors (no refit). Writes outputs/tables/tou_contrast_placebo.csv and prints C1-C3.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_area_panel as AP  # noqa: E402
import tou_area_panel_pc as P  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402

AREAS = P.AREAS
x = AP.load_frame()
x = x[(x.date >= P.START) & (x.date <= P.POST1)].copy()
cs, ptc = P.spain_counts(), P.pt_counts()
covid = x.date.between(*EV.COVID)
pre = (x.date >= P.START) & (x.date <= "2020-12-31") & ~covid
w = {a: float(x.loc[pre, "date"].map(cs[a]).mean()) for a in AREAS}
w["PT"] = float(x.loc[pre, "date"].map(ptc).mean())
real_mask = pre | ((x.date >= P.POST0) & (x.date <= P.POST1))
pmask = (x.date >= P.START) & (x.date <= "2019-12-31")
starts = [P.START + pd.Timedelta(days=106 * k) for k in range(6)]
rows = []
for src in ("area_panel_pcw_errors", "area_panel_pc_errors"):
    c = pd.read_parquet(P.CACHE / f"{src}.parquet")
    errs = {tuple(k.split("|", 1)): c[k] for k in c.columns}

    def cf(n):
        a, b = errs[(n, "(2018,)")], errs[(n, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], b[x.date.reindex(b.index).dt.year == 2019]])
    ea = {a: errs[(f"{a}_p48", "()")] for a in AREAS}
    eac = {a: cf(f"{a}_p48") for a in AREAS}
    for lab, ctl, ctlcf in (("M", errs[("PTU", "()")], cf("PTU")), ("F", errs[("PTREN", "()")], cf("PTREN"))):
        r = AP.did_types(AP.long_stack(x, ea, ctl, AREAS, w, real_mask), P.POST0, P.POST1, True)
        rows.append(dict(src=src, version=lab, window="real", start=str(P.POST0.date()), contrast=100 * (r["wd_peak"][0] - r["wd_off"][0])))
        Sc = AP.long_stack(x, eac, ctlcf, AREAS, w, pmask)
        for s0 in starts:
            r = AP.did_types(Sc, s0, s0 + pd.Timedelta(days=105), True)
            rows.append(dict(src=src, version=lab, window="placebo", start=str(s0.date()), contrast=100 * (r["wd_peak"][0] - r["wd_off"][0])))
R = pd.DataFrame(rows)
R.round(3).to_csv(T.OUT / "tou_contrast_placebo.csv", index=False)
print(R.round(2).to_string(index=False))
for src, g in R.groupby("src"):
    res = {}
    for v, h in g.groupby("version"):
        real = h[h.window == "real"].contrast.iloc[0]
        pl = h[h.window == "placebo"].contrast
        rms = float(np.sqrt((pl ** 2).mean()))
        c1 = bool(real < 0 and abs(real) > pl.abs().max())
        c2 = bool(abs(real) >= 2 * rms)
        res[v] = (c1, c2)
        print(f"{src} {v}: real {real:.2f}, max |placebo| {pl.abs().max():.2f}, rms {rms:.2f}; C1 {c1}, C2 {c2}")
    print(f"{src} C3 (both controls pass C1 and C2):", all(a and b for a, b in res.values()))
