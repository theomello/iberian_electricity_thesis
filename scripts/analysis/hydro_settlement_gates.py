"""Precision and power gates for settling the hydro conduct cells (no estimation).

Pre-registration: docs/specs/2026-11-19-hydro-conduct-settlement-design.md (gates G1, G3).
Reads only stored outputs: outputs/tables/price_taking_simulation_hydro_corrected.csv
(actual offers = seed 0, simulated price-takers = seeds 1-10, control `level`).

G1  Pooled hydro, unit x month: can the equivalence rule of rq-price-taking-simulation.md §7
    (accept price-taking when AR_hi - min(seeds) < delta = 0.1) accept, with probability >= 0.80,
    if firms ARE price-takers (actual centred on the seeds' mean)?  Scenarios: current data,
    more seeds, data extended to 2026-05, a perfect bias correction.
G3  Hydro 2024 - 2025-09: can new data (2025-10 -> 2026-05) decide the borderline cell under the
    reading rule (differs when the AR set misses the seeds' band), with power >= 0.80 against the
    cell's own point estimate?

Approximations, stated: AR set = b +/- 1.96 se (F 79-530, near-symmetric sets); se and the
seeds' spread scale with 1/sqrt(months); new months carry the same information per month as old.
WRITES outputs/tables/hydro_settlement_gates.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "outputs/tables/price_taking_simulation_hydro_corrected.csv"
OUT = ROOT / "outputs/tables/hydro_settlement_gates.csv"
DELTA, Z, POWER_BAR, NSIM = 0.1, 1.96, 0.80, 200_000
rng = np.random.default_rng(20261119)


def cell(sample: str) -> tuple[float, float, float, float]:
    d = pd.read_csv(SRC)
    d = d[(d.control == "level") & (d["sample"] == sample)]
    act = d[d.seed == 0].iloc[0]
    seeds = d[d.seed > 0].b_iv.to_numpy()
    return act.b_iv, act.se_iv, seeds.mean(), seeds.std(ddof=1)


def g1(rows: list) -> None:
    b0, se0, m, sd = cell("unit × month | Zb | sel: level")
    scen = [("current data, 10 seeds", 1.0, 10, False),
            ("20 seeds", 1.0, 20, False), ("50 seeds", 1.0, 50, False),
            ("to 2026-05 (89 months), 10 seeds", 89 / 81, 10, False),
            ("to 2026-05, 15-min months counted 4x (113), 10 seeds", 113 / 81, 10, False),
            ("current data, perfect correction (band = seeds' mean)", 1.0, 10, True)]
    for name, k, s, perfect in scen:
        se, sds = se0 / np.sqrt(k), sd / np.sqrt(k)
        b = rng.normal(m, se, NSIM)                       # firms are price-takers
        nmin = m if perfect else rng.normal(m, sds, (NSIM, s)).min(axis=1)
        power = np.mean(b + Z * se - nmin < DELTA)
        rows.append(dict(gate="G1", scenario=name, se=se, seeds=s, power=power,
                         passes=power >= POWER_BAR))
    # data multiple needed for power 0.80 with 10 seeds
    for k in np.arange(1, 15.01, 0.1):
        se, sds = se0 / np.sqrt(k), sd / np.sqrt(k)
        b = rng.normal(m, se, 50_000)
        nmin = rng.normal(m, sds, (50_000, 10)).min(axis=1)
        if np.mean(b + Z * se - nmin < DELTA) >= POWER_BAR:
            break
    rows.append(dict(gate="G1", scenario=f"data multiple needed for 0.80: {k:.1f}x",
                     se=se0 / np.sqrt(k), seeds=10, power=POWER_BAR, passes=np.nan))
    # current observed reading (for the record; the rule was fixed 2026-10-08)
    d = pd.read_csv(SRC)
    smin = d[(d.control == "level") & (d["sample"] == "unit × month | Zb | sel: level")
             & (d.seed > 0)].b_iv.min()
    rows.append(dict(gate="G1", scenario="observed: AR_hi - min(seeds), already read 2026-10-28",
                     se=se0, seeds=10, power=np.nan, passes=np.nan, value=b0 + Z * se0 - smin))


def g3(rows: list) -> None:
    b0, se0, m, sd = cell("unit × month | Zb | 2024 – 2025-09 | sel: level")
    old, new = 21, 8
    for alt_name, beta in [("alt = point estimate", b0), ("alt = 2019-21H1 size 0.25", 0.25),
                           ("null = price-takers", m)]:
        # fresh data only: an 8-month cell 2025-10 -> 2026-05
        se_n, sd_n = se0 * np.sqrt(old / new), sd * np.sqrt(old / new)
        b = rng.normal(beta, se_n, NSIM)
        smax = rng.normal(m, sd_n, (NSIM, 10)).max(axis=1)
        p_fresh = np.mean(b - Z * se_n > smax)
        # extended cell 2024-01 -> 2026-05, conditional on the 21 months already read
        k = (old + new) / old
        se_c, sd_c = se0 / np.sqrt(k), sd / np.sqrt(k)
        bc = (old * b0 + new * b) / (old + new)
        smax_c = rng.normal(m, sd_c, (NSIM, 10)).max(axis=1)
        p_ext = np.mean(bc - Z * se_c > smax_c)
        rows.append(dict(gate="G3", scenario=f"fresh 8 months | {alt_name}", se=se_n, seeds=10,
                         power=p_fresh, passes=(p_fresh >= POWER_BAR) if "alt = point" in alt_name else np.nan))
        rows.append(dict(gate="G3", scenario=f"extended 29 months (reuses read data) | {alt_name}",
                         se=se_c, seeds=10, power=p_ext, passes=np.nan))


def main() -> None:
    rows: list = []
    g1(rows)
    g3(rows)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    with pd.option_context("display.width", 200, "display.max_colwidth", 80):
        print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
