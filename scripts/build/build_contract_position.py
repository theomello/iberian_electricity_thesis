#!/usr/bin/env python3
"""Firm-level bilateral contract position (theta) from PDBF role 4.

    .venv/bin/python scripts/build/build_contract_position.py --verify
    .venv/bin/python scripts/build/build_contract_position.py --save

WHY THIS EXISTS

Volume already sold forward at a fixed price earns nothing extra when the
day-ahead price rises, so a heavily contracted firm has a weaker incentive to
withhold whatever its share -- the theta term in Wolak (2000) and Hortacsu &
Puller (2008). PDBF publishes the physical contract position directly.

READ ROLE 4; DO NOT COMPUTE PDBF MINUS PDBC. Role 4's sell and buy legs sum to
exactly zero within a period, which is the identity a bilateral contract must
satisfy and the subtraction cannot check.

STILL A PROXY. This captures *physical* bilateral contracts only and misses
financial hedges entirely -- an OMIP future or a financially settled PPA fixes
revenue while the energy still clears in the auction. Since what matters is
whether revenue is fixed rather than whether electrons flow bilaterally, that
omission is the more serious one. Bound theta; do not claim to measure it.

TRAP: PDBF has several rows per unit-period, one per role code, so
(date, period, unit) is NOT a key. Filtering to role 4 first is what makes the
grouping safe.

WHAT --verify ASSERTS, AND WHAT IT ONLY REPORTS

Hard failure: the role-4 netting identity. Sell and buy legs must sum to zero
within a period, and a non-zero sum can only mean a parse or filter error --
that is a check on this script, so it fails the build.

Warning only: firm-mapping coverage of contracted sell MW. It is a *finding*,
not a fault. Coverage is 71.5% in 2018-01, 95.7% in 2024-01 and 76.9% in
2026-05, and that drift is documented and carried through the analysis as
`theta_coverage` (see notes/rq-descriptive-price-formation.md, sections 3.2
and 4.5, where the 2018 figure is a reported result). A hard gate here would
assert as a build failure the very thing the note establishes, leaving a
permanently red --verify in a repo whose whole test discipline is these flags.
The check therefore prints the coverage prominently so a *change* is still
visible; it does not fail.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PDBF = ROOT / "data" / "omie" / "pdbf" / "parquet"
AGENTS = ROOT / "data" / "omie" / "registry" / "unit_agents.parquet"
UNIT_LISTS = ROOT / "data" / "omie" / "registry" / "omie_unit_lists.parquet"
OUT = ROOT / "outputs" / "tables" / "contract_position_panel.parquet"
OUT_OWNER = ROOT / "outputs" / "tables" / "contract_position_panel_owner.parquet"

sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from unit_ownership import attach_owners, spells  # noqa: E402

COLS = ["date", "period", "resolution_min", "unit", "schedule_mw", "role_code"]

# Below this, --verify prints the coverage loudly but still exits 0.
COVERAGE_FLOOR = 0.90


def unit_firm_map(tier: str) -> pd.DataFrame:
    """unit -> firm. Static for `firm`; dated snapshots for `owner`.

    `owner` reads `omie_unit_lists.parquet` **directly** rather than
    `unit_agents.agent_owner`. That matters: `unit_agents` is restricted to the
    5,137 codes in `unit_registry.parquet`, and PDBF role 4 contains contract
    registrations the listings cover but the registry does not. Going through
    `unit_agents` left January 2018 at 71.5% -- identical to the inference chain,
    i.e. no gain at all -- while the listings give 100%.

    Since 2026-10-02 `owner` returns the ownership spells of lib/unit_ownership.py,
    which read the listings the same way: the owners in force on each delivery
    date (the preceding listing naming the unit; the first listing also covers
    the time before it), each with its share, and the dated sales. Until then
    this took the NEAREST snapshot in either direction and one owner per unit,
    so a co-owned contract unit went whole to an arbitrary co-owner.
    548 units change owner across the snapshots.

    `owner` names a different entity from `firm` (the commercialising one); the
    roll-up to groups is lib/omie_owner.owner_group.
    """
    if tier == "owner":
        return spells()
    return pd.read_parquet(AGENTS, columns=["unit", "firm"])


def attach_firm(sell: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    """Join the firm label: statically for `firm`, by date and share for `owner`
    (one row per owner in force, schedule_mw times its share)."""
    if "start" not in agents.columns:
        return sell.merge(agents, on="unit", how="left")
    s = sell.copy()
    s["unit"] = s.unit.astype(str)
    a = attach_owners(s, agents, value_cols=("schedule_mw",))
    return a.drop(columns=["pt", "share"]).rename(columns={"group": "firm"})


def load_month(path: Path) -> pd.DataFrame:
    d = pd.read_parquet(path, columns=COLS)
    return d[d.role_code == "4"].copy()


def verify(path: Path, tier: str = "firm") -> int:
    """Re-derive the two facts this build depends on, from the file itself.

    Returns 1 only on the netting identity -- see the module docstring on why
    coverage warns instead.
    """
    r4 = load_month(path)
    net = r4.groupby(["date", "period"])["schedule_mw"].sum().abs().max()
    agents = unit_firm_map(tier)
    sell = attach_firm(r4[r4.schedule_mw > 0], agents)
    mapped_mw = sell.loc[sell.firm.notna(), "schedule_mw"].sum() / sell.schedule_mw.sum()

    print(f"  {path.name}  (tier={tier})")
    print(f"    role-4 net per period, max |sum| : {net:.6f}   (must be ~0)")
    print(f"    sell rows firm-mapped            : {sell.firm.notna().mean():.1%}")
    print(f"    sell MW   firm-mapped            : {mapped_mw:.1%}")
    bad = 0
    if net > 0.01:
        print("    FAIL: role-4 legs do not net to zero -- parse or filter error")
        bad = 1
    if mapped_mw < COVERAGE_FLOOR:
        print(f"    NOTE: firm mapping covers {mapped_mw:.1%} of contracted sell MW"
              f" (< {COVERAGE_FLOOR:.0%}) -- a measured finding, not a failure;"
              " carried through as theta_coverage")
    return bad


def build_month(path: Path, agents: pd.DataFrame) -> pd.DataFrame:
    r4 = load_month(path)
    sell = attach_firm(r4[r4.schedule_mw > 0], agents)
    sell["firm"] = sell.firm.fillna("UNMAPPED")
    g = (sell.groupby(["date", "period", "resolution_min", "firm"])
             .agg(theta_mw=("schedule_mw", "sum"), n_units=("unit", "nunique"))
             .reset_index())
    g["theta_mwh"] = g.theta_mw * g.resolution_min / 60
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--tier", choices=["firm", "owner"], default="firm",
                    help="firm: the inference chain. owner: OMIE's published "
                         "agent_owner, which removes the theta_coverage drift.")
    args = ap.parse_args()

    months = sorted(PDBF.glob("pdbf_*.parquet"))
    if not months:
        print(f"no PDBF archive at {PDBF}", file=sys.stderr)
        return 1

    if args.verify:
        checks = [m for m in months if m.stem in
                  ("pdbf_201801", "pdbf_202401", "pdbf_202605")]
        return max(verify(m, args.tier) for m in checks)

    if args.save:
        agents = unit_firm_map(args.tier)
        out_path = OUT_OWNER if args.tier == "owner" else OUT
        frames = []
        for i, m in enumerate(months, 1):
            frames.append(build_month(m, agents))
            print(f"  [{i:3d}/{len(months)}] {m.stem}", end="\r", flush=True)
        d = pd.concat(frames, ignore_index=True)
        d["date"] = pd.to_datetime(d["date"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        d.to_parquet(out_path, index=False)
        print(" " * 40, end="\r")
        print(f"wrote {len(d):,} rows -> {out_path.relative_to(ROOT)}")
        share = d.groupby(d.date.dt.year).apply(
            lambda g: g.loc[g.firm == "UNMAPPED", "theta_mwh"].sum()
                      / g.theta_mwh.sum(), include_groups=False)
        print("  UNMAPPED share of contracted volume, by year:")
        print("   " + "  ".join(f"{y}:{v:5.1%}" for y, v in share.items()))
        return 0

    print("nothing to do; pass --verify or --save")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
