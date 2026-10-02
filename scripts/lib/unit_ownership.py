#!/usr/bin/env python3
"""Who owns a unit on a given date, and with what share.

The firm panels used to give each unit its latest listed owner for the whole
window (`unit_agents.agent_owner`). notes/report-ownership-mapping.md found what
that costs: co-owned reactors went whole to one co-owner, not always the largest
(Almaraz 1 and Trillo to Naturgy, Vandellos II to Iberdrola), and sold businesses
sat with their buyer for the whole window. This module replaces it.

SPELLS. OMIE's *Listado de Unidades* (12 snapshots, 2014-09-24 -> 2025-01-31, none
for 2021) lists each unit's owners with ownership percentages. A snapshot's owners
are in force from its date until the next snapshot that lists the unit; the first
listing also covers the time before it, the last the time after it. Shares are the
listed percentages normalised to sum to 1 within the snapshot.

DATED SALES. Between two snapshots a sale is invisible until the second one, so
the sales that matter are dated by hand in ENTITY_CHANGES: an owner entity belongs
to one group before the date and another from it. Spells are split there.

UNIT SALES. A unit sold between two listings is dated in UNIT_CHANGES: the change
the next listing shows takes effect on the sale date, not on the listing's date.

FALLBACK. A unit no listing names keeps the inference chain's owner
(`unit_agents.agent_owner`), share 1, for the whole window.

    sp = spells()                         # unit, start, end, owner, share, group, pt
    owners_on("ALZ1", pd.Timestamp("2024-01-15"), sp)
    attach_owners(bids, sp)               # one row per owner, power_mw x share
    majority_group(df, sp)                # the largest owner's exposed group per row

`group` is `omie_owner.owner_group` of the owner, or the dated group; `pt` flags a
regulated pass-through owner (`omie_owner.is_pass_through`), whose group the
callers keep but whose volume the exposed position leaves out.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omie_owner import _norm, is_pass_through, owner_group  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
REG = ROOT / "data" / "omie" / "registry"
LISTS = REG / "omie_unit_lists.parquet"
AGENTS = REG / "unit_agents.parquet"
EARLY, LATE = pd.Timestamp("1900-01-01"), pd.Timestamp("2100-01-01")

# (owner name, matched as a regex on the normalised name; date; group before; group from the date; source)
ENTITY_CHANGES = [
    (r"^EDP COMERCIALIZADORA$", "2020-12-01", "EDP", "TOTALENERGIES",
     "TotalEnergies bought EDP Comercializadora, EDP's Spanish retailer, effective 2020-12-01 "
     "(EDP market notification; CLAUDE.md, build_rival_solar.OWNER_FIX)"),
    (r"^VIESGO ", "2018-11-02", "VIESGO", "REPSOL",
     "Repsol completed its purchase of Viesgo's non-regulated generation and retail on "
     "2018-11-02 (notes/rq-leg-d-sign-of-n.md; before it Viesgo was not Repsol's)"),
]


# unit -> date: the change the next listing shows took effect on this date.
UNIT_CHANGES = {
    # Castejon 1 and 3, EDP's combined cycles, went to TotalEnergies with EDP's Spanish
    # retail on 2020-12-01 (leg_c_panel.CASTEJON_SALE). The listings show EDP Espana on
    # 2020-03-09 and EDP Comercializadora (TotalEnergies' from 2020-12-01) on 2022-02-08.
    "CTJON1": "2020-12-01",
    "CTJON3": "2020-12-01",
}


def _listed() -> pd.DataFrame:
    """unit, snapshot, owner, share (normalised within the unit-snapshot)."""
    l = pd.read_parquet(LISTS, columns=["snapshot", "unit", "agent_owner", "ownership_pct"])
    l = l.dropna(subset=["agent_owner"]).rename(columns={"agent_owner": "owner"})
    l["snapshot"] = pd.to_datetime(l.snapshot).astype("datetime64[ns]")
    l = l.groupby(["unit", "snapshot", "owner"], as_index=False).ownership_pct.sum(min_count=1)
    pct = l.ownership_pct.fillna(0.0).clip(lower=0.0)
    tot = pct.groupby([l.unit, l.snapshot]).transform("sum")
    n = l.groupby(["unit", "snapshot"]).owner.transform("size")
    l["share"] = np.where(tot > 0, pct / tot.where(tot > 0, 1.0), 1.0 / n)
    return l[["unit", "snapshot", "owner", "share"]]


def _group(owner: str, start: pd.Timestamp) -> str | None:
    n = _norm(owner)
    for pat, date, before, after, _ in ENTITY_CHANGES:
        if re.search(pat, n):
            return after if start >= pd.Timestamp(date) else before
    return owner_group(owner)


def spells() -> pd.DataFrame:
    """unit, start, end (exclusive), owner, share, group, pt: the owners in force."""
    l = _listed()
    snaps = l[["unit", "snapshot"]].drop_duplicates().sort_values(["unit", "snapshot"])
    snaps["end"] = snaps.groupby("unit").snapshot.shift(-1).fillna(LATE)
    first = snaps.groupby("unit").snapshot.transform("min")
    snaps["start"] = snaps.snapshot.where(snaps.snapshot != first, EARLY)
    # A dated unit sale: the first listing after the date takes effect on the date.
    for u, d in UNIT_CHANGES.items():
        d = pd.Timestamp(d)
        su = snaps[(snaps.unit == u) & (snaps.snapshot > d)]
        if su.empty:
            continue
        nxt = su.snapshot.min()
        snaps.loc[(snaps.unit == u) & (snaps.snapshot == nxt), "start"] = d
        snaps.loc[(snaps.unit == u) & (snaps.end == nxt), "end"] = d
    sp = l.merge(snaps, on=["unit", "snapshot"])
    # Split spells at the dated sales of an owner entity they contain.
    cuts = [pd.Timestamp(d) for pat, d, *_ in ENTITY_CHANGES]
    pats = [pat for pat, *_ in ENTITY_CHANGES]
    hit = sp.owner.map(lambda o: any(re.search(p, _norm(o)) for p in pats))
    units = set(sp.loc[hit, "unit"])
    parts = [sp[~sp.unit.isin(units)]]
    for _, s in sp[sp.unit.isin(units)].groupby(["unit", "snapshot"]):
        lo, hi = s.start.iloc[0], s.end.iloc[0]
        bounds = [lo] + sorted(c for c in cuts if lo < c < hi) + [hi]
        for a, b in zip(bounds[:-1], bounds[1:]):
            parts.append(s.assign(start=a, end=b))
    sp = pd.concat(parts, ignore_index=True)
    # Units no listing names: the inference chain's owner, for the whole window.
    ua = pd.read_parquet(AGENTS, columns=["unit", "agent_owner"]).dropna()
    rest = ua[~ua.unit.isin(set(l.unit))].rename(columns={"agent_owner": "owner"})
    rest = rest.assign(snapshot=pd.NaT, share=1.0, start=EARLY, end=LATE)
    sp = pd.concat([sp, rest], ignore_index=True)
    sp["group"] = [_group(o, s) for o, s in zip(sp.owner, sp.start)]
    sp["pt"] = sp.owner.map(is_pass_through).astype(bool)
    return sp[["unit", "start", "end", "owner", "share", "group", "pt"]].sort_values(["unit", "start"]).reset_index(drop=True)


def owners_on(unit: str, date: pd.Timestamp, sp: pd.DataFrame | None = None) -> pd.DataFrame:
    """The owners of one unit on one date, with shares."""
    sp = spells() if sp is None else sp
    s = sp[(sp.unit == unit) & (sp.start <= date) & (sp.end > date)]
    return s[["owner", "share", "group", "pt"]].reset_index(drop=True)


def attach_owners(df: pd.DataFrame, sp: pd.DataFrame | None = None, unit_col: str = "unit",
                  date_col: str = "date", value_cols: tuple = ("power_mw",)) -> pd.DataFrame:
    """One row per owner in force for each (unit, date) row of df, with value_cols
    multiplied by the owner's share; adds group, pt, share. A unit with no owner keeps
    one row with group NaN, pt False and share 1, so callers decide what to do with it."""
    sp = spells() if sp is None else sp
    keys = df[[unit_col, date_col]].drop_duplicates().copy()
    keys["_t"] = pd.to_datetime(keys[date_col]).astype("datetime64[ns]")
    keys["_u"] = keys[unit_col].astype(str)
    starts = sp[["unit", "start"]].drop_duplicates().rename(columns={"unit": "_u", "start": "_s"})
    starts["_s"] = starts._s.astype("datetime64[ns]")
    k = pd.merge_asof(keys.sort_values("_t"), starts.sort_values("_s"), left_on="_t", right_on="_s",
                      by="_u", direction="backward")
    own = sp.rename(columns={"unit": "_u", "start": "_s"}).astype({"_s": "datetime64[ns]"})
    k = k.merge(own[["_u", "_s", "end", "share", "group", "pt"]], on=["_u", "_s"], how="left")
    k = k[k.end.isna() | (k._t < k.end.astype("datetime64[ns]"))]
    k["share"] = k.share.fillna(1.0)
    k["pt"] = k.pt.fillna(False).astype(bool)
    out = df.merge(k[[unit_col, date_col, "group", "pt", "share"]], on=[unit_col, date_col], how="left")
    out["share"] = out.share.fillna(1.0)
    out["pt"] = out.pt.fillna(False).astype(bool)
    for c in value_cols:
        out[c] = out[c] * out.share
    return out


def majority_group(df: pd.DataFrame, sp: pd.DataFrame | None = None, unit_col: str = "unit",
                   date_col: str = "date", exposed: bool = True) -> pd.Series:
    """For each row of df, the group of the unit's largest owner in force that day
    (None for a pass-through owner when `exposed`, or for a unit with no owner).
    Aligned to df's index. Ties go to the owner listed first."""
    sp = spells() if sp is None else sp
    keys = df[[unit_col, date_col]].drop_duplicates()
    a = attach_owners(keys, sp, unit_col=unit_col, date_col=date_col, value_cols=())
    a = a.sort_values("share", ascending=False, kind="stable").drop_duplicates([unit_col, date_col])
    g = a.group.where(~a.pt) if exposed else a.group
    m = pd.Series(g.to_numpy(), index=pd.MultiIndex.from_frame(a[[unit_col, date_col]]))
    return pd.Series(m.reindex(pd.MultiIndex.from_frame(df[[unit_col, date_col]])).to_numpy(), index=df.index)
