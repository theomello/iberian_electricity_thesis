#!/usr/bin/env python3
"""Does start-up cost explain why the at-cost estimate of β changes sign with the fixed effects?

    .venv/bin/python scripts/analysis/step_engine.py --comp --months ...   # input (compcost)
    .venv/bin/python scripts/analysis/step_estimator.py                    # input (rows)
    .venv/bin/python scripts/analysis/step_startup_check.py

`rq-step-estimator.md` §7. With X̃ instrumented by its value on the at-cost curve, β is
−0.27 with unit × month and fuel × hour effects, −0.08 with unit × day effects and +0.10
with fuel × date and hour effects. The candidate explanation: a firm short of power on a
day starts more thermal plant, and a unit that must start up prices its steps to recover
the start-up cost. If so, the sign should stop moving on the steps that carry no
start-up cost.

TWO SPLITS, both known when offers close at noon on D-1:
  running   the unit was cleared in the day-ahead market in the last hour of D-1
            (published on D-2), so it can run on D without starting up; else "off"
  no MIC    the unit declares no minimum-income condition for D in `cab` (fixed and
            variable term both zero): it asks no start-up recovery in its offer; else "MIC"
The MIC split is the firm's own choice for the day, so it describes; the running split
is fixed before the offer. A unit that declares the condition recovers its start-up through
it and can offer its steps at cost; one that does not must put the start-up into its step
prices. So start-up cost should be absent from "running, MIC" and largest in "off, no MIC".

For each subsample, the at-cost instrument (Zb) under the three sets of fixed effects of
§7. Writes outputs/tables/step_startup_check.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import step_estimator as se  # noqa: E402

DATA = ROOT / "data"
OUT = ROOT / "outputs/tables/step_startup_check.csv"


def unit_days() -> pd.DataFrame:
    """unit, date, running (cleared in D-1's last hour), mic (declares a minimum-income condition on D)."""
    ms = se.months()
    prev = str(pd.Period(ms[0], "M") - 1).replace("-", "")
    cleared = []
    for ym in [prev, *ms]:
        f = se.CACHE / f"units_{ym}.parquet"
        if not f.exists():
            continue
        u = pd.read_parquet(f, columns=["hid", "unit", "cleared_mw"]).drop_duplicates(["hid", "unit"])
        h = pd.read_parquet(se.CACHE / f"hours_{ym}.parquet", columns=["hid", "date", "period"])
        u = u.merge(h, on="hid")
        last = u[u.period == u.groupby("date").period.transform("max")]
        cleared.append(last[["unit", "date", "cleared_mw"]])
    c = pd.concat(cleared, ignore_index=True)
    c["date"] = pd.to_datetime(c.date) + pd.Timedelta(days=1)       # D-1's last hour, seen from D
    c = c.groupby(["unit", "date"]).cleared_mw.sum().gt(0).rename("running").reset_index()
    cab = pd.concat([pd.read_parquet(DATA / f"omie/cab/parquet/cab_{ym}.parquet",
                                     columns=["date", "unit", "side", "min_income_fixed_eur",
                                              "min_income_var_eur_mwh"]) for ym in ms])
    cab = cab[cab.side == "V"]
    cab["mic"] = (cab.min_income_fixed_eur.fillna(0) > 0) | (cab.min_income_var_eur_mwh.fillna(0) > 0)
    cab["date"] = pd.to_datetime(cab.date)
    cab = cab.groupby(["unit", "date"]).mic.max().reset_index()
    return c.merge(cab, on=["unit", "date"], how="outer")


def main() -> int:
    d = se.at_cost(se.derive(se.instruments(pd.read_parquet(se.ROWS).drop(columns=se.INSTRUMENTS))))
    p = d[d.m_n > 0].merge(unit_days(), on=["unit", "date"], how="left")
    p["running"] = p.running.fillna(False).astype(bool)
    print(f"\nprice-setting steps {len(p):,}: running at the end of D-1 {p.running.mean():.3f}; "
          f"MIC declared {p.mic.mean():.3f} (unknown {p.mic.isna().mean():.3f})")
    print(pd.crosstab(p.running, p.mic.fillna("unknown"), values=p.m_n, aggfunc="sum", normalize=True)
          .round(3).to_string())
    print("\nmarkup b − c by group (weighted by marginal draws):")
    for k, g in p.groupby(["running", p.mic.fillna("unknown")]):
        print(f"  running {k[0]!s:5}  MIC {k[1]!s:7}  steps {len(g):>8,}  markup "
              f"{np.average(g.mk, weights=g.m_n):6.2f}  X̃ {np.average(g.Xt.fillna(0), weights=g.m_n):+6.2f}")
    subs = {"all": p, "running": p[p.running], "off": p[~p.running],
            "no MIC": p[p.mic == False], "MIC": p[p.mic == True],  # noqa: E712
            "running, MIC": p[p.running & (p.mic == True)],  # noqa: E712
            "off, no MIC": p[~p.running & (p.mic == False)]}  # noqa: E712
    res = []
    for name, s in subs.items():
        print(f"\n{name}:")
        for fe in ("main", "unitday", "date"):
            r = se.est(s, "mk", "Xt", "m_n", f"{name}, {fe}", zs=("Zb",), fe=fe)
            res.append(r | {"subsample": name})
    pd.DataFrame(res).to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
