"""Price gate for the PVPC forward-price phase-in (docs/specs/2026-11-12-demand-redesign-options.md section 7). No demand series."""
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = Path(os.environ.get("VRE_DATA_ROOT", ROOT))
OUT = ROOT / "outputs" / "tables"


def main():
    p = pd.read_parquet(DATA / "data/esios/esios_1001.parquet")
    p = p[p.geo_name == "Península"].drop_duplicates("utc_timestamp").set_index("utc_timestamp").value
    o = pd.read_parquet(DATA / "data/omie/prices/omie_day_ahead_prices.parquet").drop_duplicates("utc_timestamp").set_index("utc_timestamp")
    x = pd.concat([p.rename("pv"), o.price_es.rename("om")], axis=1).dropna()
    x.index = x.index.tz_convert("Europe/Madrid")
    x["date"], x["h"] = pd.to_datetime(x.index.date), x.index.hour
    # 15-minute day-ahead prices from 2025-10: collapse to the hour first
    x = x.groupby(["date", "h"]).mean()
    ev, md = x.xs(19, level="h", drop_level=False), None
    def blk(v, hs):
        return x[x.index.get_level_values("h").isin(hs)][v].groupby(level="date").mean()
    g = pd.DataFrame({"pv": blk("pv", range(19, 23)) - blk("pv", range(11, 15)), "om": blk("om", range(19, 23)) - blk("om", range(11, 15))}).dropna()

    def slope(a, b):
        s = g[(g.index >= a) & (g.index < b)]
        return np.polyfit(s.om, s.pv, 1)[0] if len(s) >= 50 else np.nan

    def delta(brk):
        brk = pd.Timestamp(brk)
        d = pd.Timedelta(days=60)
        return slope(brk - d, brk), slope(brk, brk + d)

    f1 = slope("2023-11-01", "2024-01-01")
    steps = {"2024-01-01": -0.25, "2025-01-01": -0.15, "2026-01-01": -0.15}
    pb = [pd.Timestamp(f"{y}-{m:02d}-{d:02d}") for y in (2023, 2024, 2025) for m in range(3, 12) for d in (1, 15)]
    pl = pd.DataFrame([{"break": b, "b0": a, "b1": c, "delta": c - a} for b in pb for a, c in [delta(b)] if not np.isnan(a + c)])
    pl.to_csv(OUT / "pvpc_phasein_placebo.csv", index=False)
    p95 = pl.delta.abs().quantile(0.95)
    rows = []
    for s, e in steps.items():
        a, c = delta(s)
        rows.append({"step": s, "b0": a, "b1": c, "delta": c - a, "expected": e, "ratio": (c - a) / e, "F2": abs(c - a) >= 0.10 and abs(c - a) > p95, "F3": 0.5 <= (c - a) / e <= 1.5})
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "pvpc_phasein_gate.csv", index=False)
    print("F1 pre-slope Nov-Dec 2023:", round(f1, 3), "pass" if 0.85 <= f1 <= 1.15 else "FAIL")
    print("placebo |delta| p95:", round(p95, 3), "sd", round(pl.delta.std(), 3), "n", len(pl))
    print(r.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
