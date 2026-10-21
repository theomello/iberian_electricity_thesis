#!/usr/bin/env python3
"""The panel and step 1a of the self-supply cost design.

    .venv/bin/python scripts/qa/check_self_supply_cost.py

Design `docs/specs/2026-10-21-self-supply-cost-design.md`; script
`analysis/self_supply_cost.py`. Checks:
  - `margin_rows` on hand-computed unit-hours: a Spanish reactor (q 100, p 60, c 25: m 3,500),
    a Portuguese reservoir priced at the Portuguese price below its water value (m −750, all of
    it above cost), an uncosted combined cycle (counted in MWh, not in the margin);
  - `unit_classes` precedence: a cost source beats the technology label;
  - if the panel exists: on weekdays, its generation summed over classes equals the holiday
    quantity panel's `gen_auction` and `gen_bilateral` in every (group, date, hour), within 0.01 MW.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for s in ("lib", "analysis"):
    sys.path.insert(0, str(ROOT / "scripts" / s))
from self_supply_cost import PANEL, margin_rows, unit_classes  # noqa: E402

QPANEL = ROOT / "outputs/tables/holiday_quantity_panel.parquet"


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    # margin_rows on three hand unit-hours
    u = pd.DataFrame({"unit": ["N1", "H1", "G1"], "group": ["A", "B", "A"], "date": pd.Timestamp("2024-01-15"),
                      "hour": [12, 12, 12], "leg": ["bilateral", "auction", "auction"],
                      "cls": ["nuclear", "hydro_storage", "thermal_nocost"],
                      "q": [100.0, 50.0, 80.0], "p": [60.0, 40.0, 60.0], "pbar": [50.0, 40.0, 50.0],
                      "c": [25.0, 55.0, np.nan], "c_nuc_lo": [20.0, 55.0, np.nan],
                      "c_nuc_hi": [80.0, 55.0, np.nan], "c_hyd90": [25.0, 65.0, np.nan]})
    r = margin_rows(u).set_index("unit")
    check(np.isclose(r.at["N1", "m"], 3500) and r.at["N1", "above_mwh"] == 0 and r.at["N1", "costed_mwh"] == 100,
          f"reactor: m {r.at['N1', 'm']:.0f} (3,500), above {r.at['N1', 'above_mwh']:.0f} (0)")
    check(np.isclose(r.at["N1", "m_nuc_lo"], 4000) and np.isclose(r.at["N1", "m_nuc_hi"], -2000),
          f"reactor variants: lo {r.at['N1', 'm_nuc_lo']:.0f} (4,000), hi {r.at['N1', 'm_nuc_hi']:.0f} (−2,000)")
    check(np.isclose(r.at["H1", "m"], -750) and r.at["H1", "above_mwh"] == 50 and np.isclose(r.at["H1", "above_eur"], 750)
          and np.isclose(r.at["H1", "m_hyd90"], -1250),
          f"reservoir below its water value: m {r.at['H1', 'm']:.0f} (−750), above {r.at['H1', 'above_mwh']:.0f} MWh "
          f"€{r.at['H1', 'above_eur']:.0f} (50, 750), m_hyd90 {r.at['H1', 'm_hyd90']:.0f} (−1,250)")
    check(r.at["G1", "mwh"] == 80 and r.at["G1", "costed_mwh"] == 0 and r.at["G1", "m"] == 0 and r.at["G1", "above_mwh"] == 0
          and np.isclose(r.at["G1", "pq"], 4800) and np.isclose(r.at["G1", "pbarq"], 4000),
          "uncosted unit: in mwh and pq, not in costed_mwh, m or above")

    # class precedence: a cost source beats the label
    labels = pd.DataFrame({"unit": ["N1", "H1", "P1", "G1", "G2", "W1", "S1", "R1", "X1", "PS", "GX"],
                           "tech": ["cogeneration", "hydro", "hydro", "gas CCGT", "gas CCGT", "wind", "solar",
                                    "hydro", "cogeneration", "pumped storage", None]})
    c = unit_classes(nuclear={"N1"}, hydro=pd.DataFrame({"unit": ["H1", "P1"], "pumped": [False, True]}),
                     thermal=pd.DataFrame({"unit": ["G1"], "fuel": ["gas"]}), labels=labels,
                     generic={"GX", "N1", "GY"}).set_index("unit").cls
    want = {"N1": "nuclear", "H1": "hydro_storage", "P1": "pumped", "G1": "gas", "G2": "thermal_nocost",
            "W1": "wind", "S1": "solar", "R1": "hydro_other", "X1": "nocost", "PS": "pumped", "GX": "generic",
            "GY": "generic"}
    bad = {k: c.get(k) for k, v in want.items() if c.get(k) != v}
    check(not bad, f"class precedence, generic units below the cost sources ({'all twelve right' if not bad else bad})")

    # step 1a's tools: capture ratio, the daily fit, se under the null
    try:
        from self_supply_cost import capture, fit_daily, se_null
    except ImportError as e:
        check(False, f"step 1a tools missing ({e})")
    else:
        prices = np.array([10.0, 50.0])
        top = capture(prices * [0.0, 100.0], prices.mean() * np.array([0.0, 100.0]))
        flat = capture(prices * [50.0, 50.0], prices.mean() * np.array([50.0, 50.0]))
        check(top > 1 and np.isclose(top, 5000 / 3000) and np.isclose(flat, 1.0),
              f"capture: all output in the dear hour {top:.3f} (1.667), flat {flat:.3f} (1.000)")
        rng = np.random.default_rng(7)
        g = pd.MultiIndex.from_product([list("ABCDE"), pd.bdate_range("2020-01-01", periods=600)], names=["group", "date"])
        syn = pd.DataFrame(index=g).reset_index()
        n = len(syn)
        syn["Z"] = np.where(rng.uniform(size=n) < 0.15, rng.uniform(500, 8000, n), 0.0)
        day = pd.Series(rng.normal(0, 4e5, syn.date.nunique()), index=syn.date.unique())
        gm = rng.normal(0, 2e5, 5 * 30)
        e = rng.normal(0, 1e5, n) + syn.date.map(day).to_numpy() + gm[pd.factorize(syn.group + syn.date.dt.strftime("%Y%m"))[0] % 150]
        syn["y_b"] = -20.0 * syn.Z + e
        syn["y_0"] = e
        b, se = fit_daily(syn, "y_b", "Z")
        check(abs(b + 20) < 3 * se, f"fit_daily recovers a planted b of −20: {b:+.2f} ({se:.2f})")
        b0, se0 = fit_daily(syn, "y_0", "Z")
        sn = se_null(syn, "y_0", "Z")
        check(abs(sn / se0 - 1) < 0.10, f"se under the null {sn:.3f} against the fitted se {se0:.3f} at b = 0 (within 10%)")

    # the legs equal the holiday quantity panel's
    if PANEL.exists():
        p = pd.read_parquet(PANEL, columns=["group", "date", "hour", "leg", "mwh"])
        p = p[p.date.dt.dayofweek < 5]
        g = p.pivot_table(index=["group", "date", "hour"], columns="leg", values="mwh", aggfunc="sum", fill_value=0.0)
        q = pd.read_parquet(QPANEL, columns=["group", "date", "hour", "gen_auction", "gen_bilateral"])
        m = q.merge(g.reset_index(), on=["group", "date", "hour"], how="outer").fillna(0.0)
        d = max((m.gen_auction - m.auction).abs().max(), (m.gen_bilateral - m.bilateral).abs().max())
        check(d < 0.01, f"weekday legs equal the quantity panel's (max gap {d:.4f} MW, {len(m):,} group-hours)")
    else:
        print(f"  (panel {PANEL.relative_to(ROOT)} not built: leg check skipped)")

    print("FAIL: " + str(len(fails)) if fails else "all checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
