#!/usr/bin/env python3
"""Ownership by date and by share: the module, and its wiring into firm_x.

    .venv/bin/python scripts/qa/check_unit_ownership.py

Checks `lib/unit_ownership.py` on the registry itself:
  - renamed entities roll up to one group (Total -> TotalEnergies, Clidom ->
    Holaluz, both BP entities, both PH Energia entities, Aldro -> Eni Plenitude);
  - co-owned reactors split by the listing's shares (Almaraz 1, Trillo,
    Vandellos II, Asco 2), shares summing to 1;
  - dated sales: EDP Comercializadora is EDP's until 2020-11-30 and
    TotalEnergies' from 2020-12-01; Viesgo is Repsol's from 2018-11-02;
  - a unit no listing names keeps the inference chain's owner, share 1;
  - attach_owners splits a row across owners and preserves its total;
and the wiring: `firm_x.month` for January 2024 must differ from the stored
`firm_x.parquet` (built on the static owner) by exactly the share changes
times each unit's signed cleared volume. Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from omie_owner import owner_group  # noqa: E402
from unit_ownership import attach_owners, owners_on, spells  # noqa: E402

FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    check(owner_group("TOTAL GAS & POWER LIMITED") == "TOTALENERGIES", "Total Gas & Power -> TOTALENERGIES")
    check(owner_group("CLIDOM ENERGY SL") == owner_group("HOLALUZ-CLIDOM SA") == "HOLALUZ", "Clidom -> HOLALUZ")
    check(owner_group("BP GAS EUROPE, S.A.U.") == owner_group("BP GAS AND POWER IBERIA, S.A.U.") == "BP",
          "both BP entities -> BP")
    check(owner_group("PH ENERGIA, LDA") == owner_group("PH ENERGIA UNIPESSOAL LDA") == "PH ENERGIA",
          "both PH Energia entities -> PH ENERGIA")
    check(owner_group("ALDRO ENERGIA Y SOLUCIONES S.L") == owner_group("ENI PLENITUDE IBERIA, S.L.U.")
          == "ENI PLENITUDE", "Aldro -> ENI PLENITUDE")

    sp = spells()
    day = pd.Timestamp("2024-01-15")
    expect = {
        "ALZ1": {"IBERDROLA": 0.52687, "ENDESA": 0.36021, "NATURGY": 0.11292},
        "TRL1": {"IBERDROLA": 0.49, "NATURGY": 0.345, "IBERENERGIA": 0.155, "ENDESA": 0.01},
        "VAN2": {"ENDESA": 0.72, "IBERDROLA": 0.28},
        "ASC2": {"ENDESA": 0.85, "IBERDROLA": 0.15},
    }
    for u, want in expect.items():
        got = owners_on(u, day, sp).groupby("group").share.sum().round(5).to_dict()
        check(got == {k: round(v, 5) for k, v in want.items()}, f"{u} on {day.date()} splits {want} (got {got})")
    s = sp.groupby(["unit", "start"]).share.sum()
    check(bool(np.allclose(s, 1.0)), f"shares sum to 1 in every spell (worst {s.sub(1).abs().max():.2e})")

    lst = pd.read_parquet(ROOT / "data/omie/registry/omie_unit_lists.parquet", columns=["snapshot", "unit", "agent_owner"])
    edpc = lst[(lst.agent_owner == "EDP COMERCIALIZADORA") & (lst.snapshot.astype(str) == "2020-03-09")].unit.iloc[0]
    g0 = owners_on(edpc, pd.Timestamp("2020-11-30"), sp).group.tolist()
    g1 = owners_on(edpc, pd.Timestamp("2020-12-01"), sp).group.tolist()
    check(g0 == ["EDP"] and g1 == ["TOTALENERGIES"], f"{edpc} (EDP Comercializadora): EDP on 2020-11-30, "
          f"TotalEnergies on 2020-12-01 (got {g0} / {g1})")
    v0 = owners_on("VIES", pd.Timestamp("2018-11-01"), sp).group.tolist()
    v1 = owners_on("VIES", pd.Timestamp("2018-11-02"), sp).group.tolist()
    check(v0 == ["VIESGO"] and v1 == ["REPSOL"], f"VIES (Viesgo hydro): VIESGO on 2018-11-01, REPSOL on 2018-11-02 "
          f"(got {v0} / {v1})")

    ua = pd.read_parquet(ROOT / "data/omie/registry/unit_agents.parquet", columns=["unit", "agent_owner"]).dropna()
    unlisted = ua[~ua.unit.isin(set(lst.unit))]
    if len(unlisted):
        u0 = unlisted.iloc[0]
        o = owners_on(u0.unit, day, sp)
        check(len(o) == 1 and o.share.iloc[0] == 1.0 and o.group.iloc[0] == owner_group(u0.agent_owner),
              f"unlisted unit {u0.unit} keeps the inference chain's owner, share 1")

    df = pd.DataFrame({"unit": ["ALZ1", "ASC1"], "date": [day, day], "power_mw": [1000.0, 500.0]})
    a = attach_owners(df, sp)
    check(len(a) == 4 and abs(a.power_mw.sum() - 1500.0) < 1e-9,
          f"attach_owners: ALZ1 -> 3 rows, ASC1 -> 1, total preserved (rows {len(a)}, total {a.power_mw.sum():.3f})")

    # Wiring: January 2024 through firm_x.month, against the stored static-owner panel.
    import firm_x
    old = pd.read_parquet(ROOT / "outputs/tables/firm_x.parquet")
    old = old[old.date.dt.strftime("%Y%m") == "202401"]
    new = firm_x.month("202401", firm_x.unit_map(), firm_x.prices())
    j = new.merge(old, on=["date", "period", "firm"], suffixes=("", "_old"))
    b = pd.read_parquet(ROOT / "data/omie/bids/parquet/bids_202401.parquet",
                        columns=["date", "period", "unit", "side", "status", "power_mw"])
    b = b[b.status.astype(str) == "C"].copy()
    b["date"] = pd.to_datetime(b.date)
    b["unit"] = b.unit.astype(str)
    b["signed"] = b.power_mw * b.side.astype(str).map({"V": 1.0, "C": -1.0})
    ua["static"] = ua.agent_owner.map(owner_group)
    st = b.merge(ua[["unit", "static"]], on="unit")
    st = st[st.static.isin(FIRMS)].groupby(["date", "period", "static"]).signed.sum().rename("s_old")
    dn = attach_owners(b, sp, value_cols=("signed",))
    dn = dn[dn.group.isin(FIRMS)].groupby(["date", "period", "group"]).signed.sum().rename("s_new")
    e = pd.concat([st.rename_axis(["date", "period", "firm"]), dn.rename_axis(["date", "period", "firm"])], axis=1).fillna(0)
    e["delta"] = e.s_new - e.s_old
    j = j.merge(e.delta.reset_index(), on=["date", "period", "firm"], how="left").fillna({"delta": 0.0})
    gap = (j.net_built_mw - j.net_built_mw_old - j.delta).abs().max()
    check(len(j) == len(old) and gap < 1e-3,
          f"firm_x.month(202401) = stored panel + share changes x signed cleared volume (max gap {gap:.2e} MW)")
    mean_change = (j.net_built_mw - j.net_built_mw_old).groupby(j.firm).mean().round(1).to_dict()
    print(f"      mean change in n (as built), January 2024, MW: {mean_change}")

    # The all-firm chain, same month, same test, on the five firms (whose group names
    # the 2026-10-02 merges left alone): firm_incentive_rebuild's net position, and
    # residual_demand_firm's own cleared sell volume (supply units only).
    import firm_incentive_rebuild as fir
    import residual_demand_firm as rdf
    inc = pd.read_parquet(ROOT / "outputs/tables/firm_incentive_net.parquet", columns=["date", "period", "firm", "net_mw"])
    inc = inc[(inc.date.dt.strftime("%Y%m") == "202401") & inc.firm.isin(FIRMS)]
    px = inc.drop_duplicates(["date", "period"])[["date", "period"]].merge(
        old.drop_duplicates(["date", "period"])[["date", "period", "p_star"]], on=["date", "period"])
    ex = fir.month_extras("202401", fir.unit_firm(), px)
    ex = ex[ex.firm.isin(FIRMS)].merge(inc, on=["date", "period", "firm"], suffixes=("", "_old"))
    ex = ex.merge(e.delta.reset_index(), on=["date", "period", "firm"], how="left").fillna({"delta": 0.0})
    gap2 = (ex.net_mw - ex.net_mw_old - ex.delta).abs().max()
    check(len(ex) > 0 and gap2 < 1e-3, f"firm_incentive_rebuild.month_extras(202401) = stored + share changes "
          f"(max gap {gap2:.2e} MW, {len(ex):,} firm-periods)")

    rdf.TIER = "owner"
    lo, hi = rdf.month_bounds("202401")
    bids = rdf.load_bids_month("202401", lo, hi)
    pxa = rdf.load_prices()
    pxm = pxa[(pxa.date >= lo) & (pxa.date <= hi)]
    th = rdf.load_theta()
    # Both versions built here, not read from the stored panel, whose vintage may
    # predate later registry changes: the old static attribution (each supply unit
    # whole to its latest owner's group) against the spells.
    thm = th[(th.date >= lo) & (th.date <= hi)]
    sup = set(pd.read_parquet(ROOT / "data/omie/registry/unit_agents.parquet", columns=["unit", "role"])
              .query("role in @rdf.SUPPLY_ROLES").unit)
    static_agents = ua[ua.unit.isin(sup)].rename(columns={"static": "firm"})[["unit", "firm"]]
    _, firm = rdf.compute_month(bids, pxm, rdf.load_agents(), thm)
    _, rd = rdf.compute_month(bids, pxm, static_agents, thm)
    firm["date"], rd["date"] = pd.to_datetime(firm.date), pd.to_datetime(rd.date)
    rd = rd[rd.firm.isin(FIRMS)][["date", "period", "firm", "q_firm_mw"]]
    sv = b[(b.side.astype(str) == "V") & b.unit.isin(sup)]
    so = sv.merge(ua[["unit", "static"]], on="unit")
    so = so[so.static.isin(FIRMS)].groupby(["date", "period", "static"]).power_mw.sum().rename("q_old")
    sn = attach_owners(sv, sp)
    sn = sn[sn.group.isin(FIRMS)].groupby(["date", "period", "group"]).power_mw.sum().rename("q_new")
    qd = pd.concat([so.rename_axis(["date", "period", "firm"]), sn.rename_axis(["date", "period", "firm"])], axis=1).fillna(0)
    qd["dq"] = qd.q_new - qd.q_old
    r = firm[firm.firm.isin(FIRMS)].merge(rd, on=["date", "period", "firm"], suffixes=("", "_old"))
    r = r.merge(qd.dq.reset_index(), on=["date", "period", "firm"], how="left").fillna({"dq": 0.0})
    gap3 = (r.q_firm_mw - r.q_firm_mw_old - r.dq).abs().max()
    check(len(r) > 0 and gap3 < 1e-3, f"residual_demand_firm.compute_month(202401) q_firm = static build + share changes "
          f"(max gap {gap3:.2e} MW, {len(r):,} firm-periods)")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
