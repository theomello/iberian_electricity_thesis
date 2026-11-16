"""Part A of docs/specs/2026-11-17-dose-and-area-design.md: estimate the dose parameters (energy price E, weight w of the 2.0 tariff) from the response shape, rules A0-A4.

    .venv/bin/python scripts/analysis/tou_dose_search.py

Household E0 against Portugal, Equation 4. For each grid point (E, w), the residual sum of squares of the stacked regression on the dose (eta free). Relative search gain G = RSS(paper convention E=100, w=0.69)/RSS_min - 1,
the same search repeated in each of the 109 placebo windows of tou_randomization_inference.py (the placebo dose laid on the placebo window, errors cross-fitted by year). Writes outputs/tables/tou_dose_search*.csv.
Deviation from the spec text: G is a relative gain (ratio of RSS) because the real stack (pre + window) and the placebo stack (pre only) differ in size.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402
import tou_evening_ddd as EV  # noqa: E402
import tou_randomization_inference as RI  # noqa: E402

TSP = pd.Timestamp
R0, R1 = CT.POST0, CT.POST1
EGRID = [40.0, 60.0, 80.0, 100.0, 120.0, 150.0, "H"]
WGRID = [0.5, 0.6, 0.69, 0.8, 0.9]
REF = (100.0, 0.69)


def rss_eta(fit, dpx):
    p = CT.EL.resid(fit.F, CT.dp_on(fit.s, dpx))
    b = float(p @ fit.y / (p @ p))
    r = fit.y - b * p
    return float(r @ r), b


def main():
    x = D.prep(T.build("e0", end="2021-09-15"))
    x = x.merge(CT.esios_load(CT.LOADS["E0"]).rename(columns={"v": "load_E0"}), on=["date", "hour"], how="left")
    errs = CT.get_errors(x)
    errs.update(RI.ri_errors(x))
    covid = x.date.between(*EV.COVID)
    pre = (x.date >= "2018-01-01") & (x.date <= "2020-12-31") & ~covid
    real_mask = (pre | ((x.date >= R0) & (x.date <= R1))) & ~covid
    year = x.date.dt.year

    def cf(n):
        parts = [errs[(n, f"({y},)")][year.reindex(errs[(n, f"({y},)")].index) == y] for y in (2018, 2019, 2020)]
        return pd.concat(parts)

    W = RI.windows()
    dates = sorted(set(pd.date_range(RI.SPAN0, RI.SPAN1)) | set(pd.date_range(R0, R1)))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ehx = eh.clip(lower=0)
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    to_x = lambda ser: np.nan_to_num(ser.reindex(idx).to_numpy())
    grid = [(e, w) for e in EGRID for w in WGRID]
    doses = {(e, w): to_x(CT.series_dose("E0", tabs, ehx if e == "H" else e, w1=w)) for e, w in grid}
    print(f"{len(grid)} grid points, {len(W)} placebo windows", flush=True)

    fr = CT.Fit(CT.make_stack(x, errs[("E0", "()")], errs[("PT", "()")], "PT", real_mask))
    fp = CT.Fit(CT.make_stack(x, cf("E0"), cf("PT"), "PT", pre))
    rw = ((x.date >= R0) & (x.date <= R1)).to_numpy()

    def search(fit, wmask):
        out = {g: rss_eta(fit, np.where(wmask, d_, 0.0)) for g, d_ in doses.items()}
        best = min(out, key=lambda g: out[g][0])
        G = out[REF][0] / out[best][0] - 1
        return out, best, G

    real, rbest, rG = search(fr, rw)
    grid_rows = [dict(E=g[0], w=g[1], rss=v[0], eta=v[1], rel_to_best=v[0] / real[rbest][0] - 1) for g, v in real.items()]
    print(f"real: best (E, w) {rbest}, eta {real[rbest][1]:+.3f}, G {rG:.3e}; reference eta {real[REF][1]:+.3f}", flush=True)
    pl = []
    for k, a, b in W:
        wm = ((x.date >= a) & (x.date <= b)).to_numpy()
        out, best, G = search(fp, wm)
        pl.append(dict(k=k, start=a.date(), best_E=best[0], best_w=best[1], G=G, eta_best=out[best][1], eta_ref=out[REF][1]))
        if len(pl) % 20 == 0:
            print(f"  placebo windows done: {len(pl)}", flush=True)
    PL = pd.DataFrame(pl)
    Gs = PL.G.to_numpy()
    q95 = float(np.quantile(Gs, 0.95))
    p_G = (1 + (Gs >= rG).sum()) / (1 + len(Gs))
    interior = bool(rbest[0] not in (40.0, 150.0))
    a1 = bool(interior and rG > q95)
    eta_sel = real[rbest][1]
    eta_s = PL.eta_best.to_numpy()
    p_eta = (1 + (eta_s <= eta_sel).sum()) / (1 + len(eta_s))
    a2 = bool(a1 and -0.15 <= eta_sel <= -0.05 and p_eta <= 0.05)
    cs = [g for g, v in real.items() if v[0] / real[rbest][0] - 1 <= q95]
    etas_cs = [real[g][1] for g in cs]
    width = (max(etas_cs) - min(etas_cs)) if etas_cs else np.nan
    a3 = bool(a1 and width < 0.033)
    GR = pd.DataFrame(grid_rows)
    GR.round(6).to_csv(T.OUT / "tou_dose_search_grid.csv", index=False)
    PL.round(6).to_csv(T.OUT / "tou_dose_search_placebo.csv", index=False)
    pd.set_option("display.width", 200)
    print(GR.pivot(index="E", columns="w", values="eta").round(3).to_string())
    print("\nplacebo best (E) counts:", PL.best_E.astype(str).value_counts().to_dict())
    print(f"\nA0 windows {len(W)} (as RI run)")
    print(f"A1 minimiser interior in E: {interior} (best E {rbest[0]}, w {rbest[1]}); real G {rG:.3e} vs placebo 95th pct {q95:.3e} (rank p {p_G:.3f}): {a1}")
    print(f"A2 eta at selected dose {eta_sel:+.3f}, one-sided randomization p {p_eta:.3f} (search repeated), in [-0.15, -0.05]: {a2}")
    print(f"A3 confidence set {len(cs)} of {len(grid)} points, eta range [{min(etas_cs):+.3f}, {max(etas_cs):+.3f}], width {width:.3f} < 0.033: {a3}")
    pd.DataFrame([dict(item="best E", value=str(rbest[0])), dict(item="best w", value=rbest[1]), dict(item="eta at best", value=eta_sel), dict(item="eta at reference", value=real[REF][1]),
                  dict(item="G real", value=rG), dict(item="G placebo q95", value=q95), dict(item="p G", value=p_G), dict(item="p eta", value=p_eta), dict(item="CS size", value=len(cs)),
                  dict(item="CS eta min", value=min(etas_cs)), dict(item="CS eta max", value=max(etas_cs))]).to_csv(T.OUT / "tou_dose_search_summary.csv", index=False)


if __name__ == "__main__":
    main()
