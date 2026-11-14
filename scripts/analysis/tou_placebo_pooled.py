"""Part A of docs/specs/2026-11-12-placebo-persistence-design.md: the cross-tariff doses laid on the 2018 and 2019 June-15 September windows, separately and pooled.

Same five series, errors, fixed effects and clustering as tou_cross_tariff.py (cross-fitted errors: each of 2018 and 2019 left out in turn, from the cached run). Sample 2018-01-01 -> 2019-12-31, the dose
(central weights, E = post-window 2021 mean OMIE price) laid on 2018-06-01 -> 2018-09-15, on 2019-06-01 -> 2019-09-15, and on both. Compared with the real eta of tou_cross_tariff_main.csv.
Writes outputs/tables/tou_placebo_pooled.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_ddd as D  # noqa: E402
import tou_did as T  # noqa: E402


def main():
    x = D.prep(T.build("e0", end="2021-09-15"))
    for name, ids in CT.LOADS.items():
        x = x.merge(CT.esios_load(ids).rename(columns={"v": f"load_{name}"}), on=["date", "hour"], how="left")
    x = x.merge(CT.france_load(), on=["date", "hour"], how="left")
    errs = CT.get_errors(x)
    W18, W19 = (pd.Timestamp("2018-06-01"), pd.Timestamp("2018-09-15")), (pd.Timestamp("2019-06-01"), pd.Timestamp("2019-09-15"))
    dates = list(pd.date_range(*W18)) + list(pd.date_range(*W19)) + list(pd.date_range(CT.POST0, CT.POST1))
    tabs = CT.old_new_tables(dates)
    eh = CT.omie_hourly()
    ebar = float(eh[(eh.index.get_level_values(0) >= CT.POST0) & (eh.index.get_level_values(0) <= CT.POST1)].mean())
    idx = pd.MultiIndex.from_arrays([x.date, x.hour])
    in18, in19 = x.date.between(*W18).to_numpy(), x.date.between(*W19).to_numpy()
    mask = (x.date >= "2018-01-01") & (x.date <= "2019-12-31")

    def cf(name):
        a, b = errs[(name, "(2018,)")], errs[(name, "(2019,)")]
        return pd.concat([a[x.date.reindex(a.index).dt.year == 2018], b[x.date.reindex(b.index).dt.year == 2019]])
    cf_pt = cf("PT")
    real = pd.read_csv(CT.OUT / "tou_cross_tariff_main.csv")
    real = real[(real.spec == "central") & (real.control == "Portugal")].set_index("series")
    dose = pd.read_csv(CT.OUT / "tou_cross_tariff_dose.csv").set_index("series")
    rows = []
    for n in CT.LOADS:
        dpx = np.nan_to_num(CT.series_dose(n, tabs, ebar).reindex(idx).to_numpy())
        f = CT.Fit(CT.make_stack(x, cf(n), cf_pt, "PT", mask))
        out = {}
        for lab, m in (("2018", in18), ("2019", in19), ("pooled", in18 | in19)):
            out[lab] = f.eta(np.where(m, dpx, 0.0))
            rows.append(dict(series=n, placebo=lab, eta=out[lab]["eta_am"], se=out[lab]["se_am"], t=out[lab]["t_am"], real_eta=real.loc[n, "eta_am"], real_se=real.loc[n, "se_am"],
                             readable=bool(dose.loc[n, "readable"])))
        print(n, {k: (round(v["eta_am"], 3), round(v["t_am"], 2)) for k, v in out.items()}, "real", round(real.loc[n, "eta_am"], 3), flush=True)
    R = pd.DataFrame(rows)
    R["floor_share"] = R.eta / R.real_eta
    R["separation_z"] = (R.real_eta - R.eta) / np.sqrt(R.real_se ** 2 + R.se ** 2)
    R.round(4).to_csv(CT.OUT / "tou_placebo_pooled.csv", index=False)
    pd.set_option("display.width", 200)
    print(R.round(3).to_string(index=False))
    for n in CT.LOADS:
        g = R[R.series == n].set_index("placebo")
        below = bool(g.loc["2018", "eta"] > g.loc["2018", "real_eta"] and g.loc["2019", "eta"] > g.loc["2019", "real_eta"])
        print(f"A2 {n}: real eta {g.loc['pooled', 'real_eta']:+.3f}; placebo 2018 {g.loc['2018', 'eta']:+.3f}, 2019 {g.loc['2019', 'eta']:+.3f}, pooled {g.loc['pooled', 'eta']:+.3f} (t {g.loc['pooled', 't']:.1f}); "
              f"real below both years: {below}; separation z {g.loc['pooled', 'separation_z']:.2f} (< -2 needed); floor share {g.loc['pooled', 'floor_share']:.2f}; readable {g.loc['pooled', 'readable']}")


if __name__ == "__main__":
    main()
