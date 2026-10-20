#!/usr/bin/env python3
"""Which legs of a firm's schedule move on its customers' holidays (PDBF).

    .venv/bin/python scripts/analysis/holiday_schedule_legs.py

Step 2 of the regional-holiday design explains its failed first stage with this
(`notes/rq-regional-holidays.md`, step 2). Each of the five firms' PDBF schedule per day,
split by leg: retail purchases, generation sales, pumping and other purchases, each in the
auction and in bilateral contracts (role code 4); MW = signed MWh / 24 (+ sold, - bought).
Each leg's change against the step-1 reference days (`build_holiday_exposure.add_deltas`)
is regressed on the firm's daily holiday dose (`holiday_dose.parquet`, daily mean), with
date and firm x year effects, errors clustered by date. Weekdays only.

Writes outputs/tables/holiday_schedule_legs.csv (leg, b, se): MW per MW of dose.
"""

import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parent.parent.parent
for s in ("lib", "analysis", "build"):
    sys.path.insert(0, str(ROOT / "scripts" / s))
from unit_ownership import majority_group, spells
from build_holiday_exposure import add_deltas
from midday_hydro_iv import cluster_meat
from step_estimator import wdemean
FIRMS = ["ENDESA", "IBERDROLA", "NATURGY", "EDP", "REPSOL"]
reg = pd.read_parquet(ROOT / "data/omie/registry/unit_registry.parquet", columns=["unit", "role"]).set_index("unit").role
sp = spells()
parts = []
for f in sorted((ROOT / "data/omie/pdbf/parquet").glob("pdbf_*.parquet")):
    p = pd.read_parquet(f, columns=["date", "unit", "schedule_mw", "resolution_min", "role_code"])
    p["date"] = pd.to_datetime(p.date)
    p["mwh"] = p.schedule_mw * p.resolution_min / 60
    p["bil"] = p.role_code == "4"
    parts.append(p.groupby(["unit", "date", "bil"], as_index=False).mwh.sum())
u = pd.concat(parts, ignore_index=True)
u["group"] = majority_group(u, sp, exposed=True)
u = u[u.group.isin(FIRMS)]
role = u.unit.map(reg)
u["leg"] = np.select([role.eq("purchase_retail"), role.isin(["pumping"]), u.mwh > 0], ["retail", "pumping", "gen"], "other_buy")
u["leg"] = u.leg + np.where(u.bil, "_bilateral", "_auction")
d = u.groupby(["group", "date", "leg"]).mwh.sum().unstack(fill_value=0.0) / 24
d["net_auction"] = d.filter(like="_auction").sum(axis=1)
d = d.reset_index()
dose = pd.read_parquet(ROOT / "outputs/tables/holiday_dose.parquet").groupby(["group", "date"]).dose_mw.mean().rename("dose").reset_index()
dose["date"] = dose.date.astype("datetime64[ns]")
rows = []
legs = [c for c in d.columns if c not in ("group", "date")]
for leg in legs:
    x = d[["group", "date", leg]].rename(columns={leg: "retail_mw"})
    x = add_deltas(x)
    x = x.merge(dose, on=["group", "date"], how="left").fillna({"dose": 0.0})
    x = x[x.delta_mw.notna() & (x.date.dt.dayofweek < 5)]
    codes = [pd.factorize(x.date)[0], pd.factorize(x.group + x.date.dt.strftime("%Y"))[0]]
    M = wdemean(x[["delta_mw", "dose"]].to_numpy(float), codes, np.ones(len(x)))
    b = (M[:, 1] @ M[:, 0]) / (M[:, 1] @ M[:, 1])
    se = np.sqrt(cluster_meat(M[:, [1]], M[:, 0] - b * M[:, 1], x.date.to_numpy())[0, 0]) / (M[:, 1] @ M[:, 1])
    rows.append((leg, b, se))
pd.DataFrame(rows, columns=["leg", "b", "se"]).to_csv(ROOT / "outputs/tables/holiday_schedule_legs.csv", index=False)
print("MW change in each leg per MW of holiday dose (sign: + = more sold / less bought), date and firm-year effects, date clusters")
for leg, b, se in rows:
    print(f"  {leg:22s} {b:+.3f} ({se:.3f})")
