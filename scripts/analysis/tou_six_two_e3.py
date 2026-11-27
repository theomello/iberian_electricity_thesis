"""Tariff 6.2 on a constant population (docs/specs/2026-11-27-six-two-constant-population-design.md).

    .venv/bin/python scripts/analysis/tou_six_two_e3.py --m0    # machinery: source 1216 must reproduce the committed 6.2 baseline
    .venv/bin/python scripts/analysis/tou_six_two_e3.py         # E3: refit the 6.2 errors, then Step 3, joint regression, orthogonal score

Runs the registered estimators unchanged with one swap: the 6.2 outcome series is ESIOS 1204 (E3, 36-72.5 kV, one
population 2014-2026) instead of 1216 (which adds the 30-36 kV customers from October 2018). Only the 6.2 LASSO errors
are refitted; every other series' cached errors are reused. The merged cache and all outputs are written beside, not over,
the committed files: data/cache_tou/six_summer_errors_e3.parquet and outputs/tables/six_two_e3/.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_cross_tariff as CT  # noqa: E402
import tou_dml_pooled as DML  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402
import tou_joint_regression as JR  # noqa: E402
import tou_tariff_drift as TD  # noqa: E402

OUT = S6.OUT / "six_two_e3"
CACHE_E3 = S6.CACHE.with_name("six_summer_errors_e3.parquet")


def redirect(sub):
    out = OUT / sub
    out.mkdir(parents=True, exist_ok=True)
    TD.OUT = JR.OUT = DML.OUT = out
    return out


def build_e3_cache():
    """Refit the 6.2 leave-one-year-out errors on E3 and merge them into a copy of the committed cache."""
    old = pd.read_parquet(S6.CACHE)
    x = S6.build()
    clean = S6.gates(x)
    print("6.2 (E3) clean years:", sorted(clean["6.2"]), flush=True)
    xx = x.copy()
    xx.loc[~xx.date.dt.year.isin(clean["6.2"] | {2021}), "load_6.2"] = np.nan
    tasks = [("6.2", xx, "load_6.2", "temp_es", "hol_es", ex)
             for ex in [()] + [(y,) for y in S6.SUMMERS if y in clean["6.2"]]]
    print(f"fitting {len(tasks)} LASSO models for 6.2 on E3", flush=True)
    res = Parallel(n_jobs=min(4, os.cpu_count() or 1), verbose=5)(delayed(CT.one_task)(*t) for t in tasks)
    new = old.drop(columns=[c for c in old.columns if c.startswith("6.2|")])
    for n, ex, e in res:
        new[f"{n}|{ex}"] = e.reindex(new.index) if isinstance(e, pd.Series) else e
    new.to_parquet(CACHE_E3)
    print(f"wrote {CACHE_E3.name}: {sum(c.startswith('6.2|') for c in new.columns)} 6.2 columns", flush=True)


def main():
    if "--m0" in sys.argv:
        assert S6.IDS["6.2"] == [1216]
        redirect("m0_source_1216")
        sys.argv = [sys.argv[0]]
        TD.main()   # its T1 check stops the run if the committed 6.2 baseline is not reproduced
        print("M0 pass: source 1216 reproduces the committed 6.2 baseline")
        return

    S6.IDS["6.2"] = [1204]
    if not CACHE_E3.exists():
        build_e3_cache()
    S6.CACHE = CACHE_E3
    TD.COMMITTED = {k: v for k, v in TD.COMMITTED.items() if k != "6.2"}  # 6.2 is the series that changes

    redirect("step3")
    sys.argv = [sys.argv[0]]
    TD.main()

    redirect("joint")
    sys.argv = [sys.argv[0], "6.2"]
    JR.main()

    redirect("dml")
    sys.argv = [sys.argv[0], "--series", "6.2"]
    DML.main()


if __name__ == "__main__":
    main()
