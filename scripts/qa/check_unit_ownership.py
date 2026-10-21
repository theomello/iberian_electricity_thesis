#!/usr/bin/env python3
"""Ownership by date and by share: the module, and its wiring into firm_x.

    .venv/bin/python scripts/qa/check_unit_ownership.py

Checks `lib/unit_ownership.py` on the registry itself:
  - renamed entities roll up to one group (Total -> TotalEnergies, Clidom ->
    Holaluz, both BP entities, both PH Energia entities, Aldro -> Eni Plenitude);
  - co-owned reactors split by the listing's shares (Almaraz 1, Trillo,
    Vandellos II, Asco 2), shares summing to 1;
  - dated sales: EDP Comercializadora is EDP's until 2020-11-30 and
    TotalEnergies' from 2020-12-01; EDP Energia (HCENE01) TotalEnergies' from
    2021-01-01; Viesgo is Repsol's from 2018-11-02;
  - a share over a window: ADOURO is 60% Movhera's from 2020-12-17 to 2021-09-08;
  - a unit no listing names keeps the inference chain's owner, share 1;
  - attach_owners splits a row across owners and preserves its total;
and the wiring: `firm_x.month` and `firm_incentive_rebuild.month_extras` for
January 2024 must equal the stored panels (rebuilt on the spells on 2026-10-03),
and `residual_demand_firm` must differ from a static build made here by exactly
the share changes times each unit's cleared volume. Exits non-zero on any failure.

Since 2026-10-05 the same for the panels migrated then: `own_demand_in_band`'s
January 2024 band volumes against the static attribution (and the stored panel
against them), and `edp_hydro_panel`'s groups and X (leg A).
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
from unit_ownership import attach_owners, majority_group, owners_on, spells  # noqa: E402

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
    check(owner_group("IBERENERGIA,S.A.") == "EDP", "Iberenergia (Trillo's 15.5%) -> EDP")

    sp = spells()
    day = pd.Timestamp("2024-01-15")
    expect = {
        "ALZ1": {"IBERDROLA": 0.52687, "ENDESA": 0.36021, "NATURGY": 0.11292},
        "TRL1": {"IBERDROLA": 0.49, "NATURGY": 0.345, "EDP": 0.155, "ENDESA": 0.01},   # Iberenergia is EDP's
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

    for u in ("CTJON1", "CTJON3"):
        c0 = owners_on(u, pd.Timestamp("2020-11-30"), sp).group.tolist()
        c1 = owners_on(u, pd.Timestamp("2020-12-01"), sp).group.tolist()
        check(c0 == ["EDP"] and c1 == ["TOTALENERGIES"], f"{u} (Castejon, sold with EDP's retail): EDP on "
              f"2020-11-30, TotalEnergies on 2020-12-01 (got {c0} / {c1})")
    h0 = owners_on("HCENE01", pd.Timestamp("2020-12-31"), sp).group.tolist()
    h1 = owners_on("HCENE01", pd.Timestamp("2021-01-01"), sp).group.tolist()
    check(h0 == ["EDP"] and h1 == ["TOTALENERGIES"], f"HCENE01 (EDP Energia, the residential book): EDP on "
          f"2020-12-31, TotalEnergies on 2021-01-01 (got {h0} / {h1})")
    dou = [owners_on("ADOURO", pd.Timestamp(d), sp).groupby("group").share.sum().round(5).to_dict()
           for d in ("2020-12-16", "2020-12-17", "2021-09-08", "2021-09-09")]
    check(dou[0] == dou[3] == {"EDP": 1.0} and dou[1] == dou[2] == {"EDP": 0.4, "MOVHERA": 0.6},
          f"ADOURO: EDP's to 2020-12-16 and from 2021-09-09, 60% Movhera's in between (got {dou})")
    nat = [owners_on(f"NATVD1{i}", pd.Timestamp("2019-06-01"), sp).group.tolist() for i in range(1, 6)]
    check(all(g == ["EDP"] for g in nat), f"NATVD11-15 (EDP's parks via EDP Comercializadora) are EDP's in 2019 "
          f"(got {nat}); this retired build_rival_solar.OWNER_FIX")
    mj = majority_group(pd.DataFrame({"unit": ["ALZ1", "TRL1", "VAN2", "ASC1"], "date": [day] * 4}), sp)
    check(mj.tolist() == ["IBERDROLA", "IBERDROLA", "ENDESA", "ENDESA"],
          f"majority_group: ALZ1, TRL1 -> Iberdrola; VAN2, ASC1 -> Endesa (got {mj.tolist()})")

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
    # The stored panel was rebuilt on the spells on 2026-10-03, so it must equal a
    # fresh build; the static attribution survives only as `st`, built here.
    # (Until 2026-10-05 this compared against a stored STATIC panel and failed by
    # construction once the panel was rebuilt.)
    gap = (j.net_built_mw - j.net_built_mw_old).abs().max()
    check(len(j) == len(old) and gap < 1e-3,
          f"firm_x.month(202401) = stored firm_x.parquet, both on the spells (max gap {gap:.2e} MW)")
    mean_change = e.delta.groupby(level=2).mean().reindex(list(FIRMS)).round(1).to_dict()
    print(f"      spells minus static attribution, signed cleared volume, January 2024 mean, MW: {mean_change}")

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
    gap2 = (ex.net_mw - ex.net_mw_old).abs().max()
    check(len(ex) > 0 and gap2 < 1e-3, f"firm_incentive_rebuild.month_extras(202401) = stored firm_incentive_net, "
          f"both on the spells (max gap {gap2:.2e} MW, {len(ex):,} firm-periods)")

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

    # Leg A and the descriptive panels (migrated 2026-10-05). own_demand_in_band:
    # January 2024 through month_band against the static attribution, built the same
    # way, differs by exactly the share changes times each unit's in-band volume; and
    # the stored panel carries month_band's numbers.
    import own_demand_in_band as odb
    usp = odb.unit_map()
    pxo = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet",
                          columns=["date", "period", "price_es"]).rename(columns={"price_es": "p_star"})
    pxo["date"] = pd.to_datetime(pxo.date)
    band = odb.month_band("202401", usp, pxo).set_index(["date", "period", "firm"])
    ob = pd.read_parquet(ROOT / "data/omie/bids/parquet/bids_202401.parquet",
                         columns=["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"])
    ob = ob[ob.status.astype(str) == "O"].copy()
    ob["date"], ob["unit"], ob["side"] = pd.to_datetime(ob.date), ob.unit.astype(str), ob.side.astype(str)
    ob = ob.merge(pxo, on=["date", "period"])
    ob = ob[(ob.price_eur_mwh - ob.p_star).abs() <= odb.H]
    bo = ob.merge(ua[["unit", "static"]], on="unit")
    bo = bo[bo.static.isin(FIRMS)].groupby(["date", "period", "static", "side"]).power_mw.sum().unstack("side")
    bn = attach_owners(ob[ob.unit.isin(set(usp.unit))], usp)
    bn = bn[bn.group.isin(FIRMS)].groupby(["date", "period", "group", "side"]).power_mw.sum().unstack("side")
    dv = bn.rename_axis(["date", "period", "firm"]).sub(bo.rename_axis(["date", "period", "firm"]), fill_value=0)
    st_band = bo.rename_axis(["date", "period", "firm"]).reindex(band.index).fillna(0)
    gap4 = max(float((band.own_sell_band - st_band.get("V", 0) - dv.V.reindex(band.index).fillna(0)).abs().max()),
               float((band.own_buy_band - st_band.get("C", 0) - dv.C.reindex(band.index).fillna(0)).abs().max()))
    check(gap4 < 1e-3, f"own_demand_in_band.month_band(202401) = static build + share changes (max gap {gap4:.2e} MW)")
    sto = pd.read_parquet(ROOT / "outputs/tables/own_demand_in_band.parquet",
                          columns=["date", "period", "firm", "own_sell_band", "own_buy_band"])
    sto = sto[sto.date.dt.strftime("%Y%m") == "202401"].set_index(["date", "period", "firm"])
    cmp_ = sto.join(band, rsuffix="_new", how="inner")
    gap5 = float((cmp_.own_buy_band - cmp_.own_buy_band_new).abs().max()) if len(cmp_) else np.inf
    check(len(cmp_) > 0 and gap5 < 1e-3, f"stored own_demand_in_band.parquet carries month_band's January 2024 "
          f"(max gap {gap5:.2e} MW, {len(cmp_):,} firm-periods)")

    # edp_hydro_panel: every row's group is the one in force on its date, the only
    # rows off the latest-owner group are VIES before Repsol's purchase, and X is
    # firm_x's X for that group on every firm-panel period.
    import hydro_within_day_probe as hwd
    hp = pd.read_parquet(ROOT / "outputs/tables/edp_hydro_panel.parquet",
                         columns=["date", "period", "unit", "group", "X"])
    latest = hp.unit.map(hwd.storage_hydro().set_index("unit").group)
    off = hp[hp.group.ne(latest)]
    vies, dou = off[off.unit == "VIES"], off[off.unit == "ADOURO"]
    check(set(off.unit) <= {"VIES", "ADOURO"} and vies.date.max() < pd.Timestamp("2018-11-02")
          and (vies.group == "VIESGO").all() and (dou.group == "MOVHERA").all()
          and (dou.empty or (dou.date.min() >= pd.Timestamp("2020-12-17") and dou.date.max() < pd.Timestamp("2021-09-09"))),
          f"edp_hydro_panel: groups off the latest owner are VIES -> VIESGO before 2018-11-02 and ADOURO -> "
          f"MOVHERA from 2020-12-17 to 2021-09-08 only ({len(vies):,} + {len(dou):,} rows, units {sorted(set(off.unit))})")
    m1 = hp[hp.date.dt.strftime("%Y%m") == "202401"]
    check(bool((m1.group.to_numpy() == hwd.dated_group(m1).to_numpy()).all()),
          "edp_hydro_panel January 2024: group = dated_group on every row")
    fx = pd.read_parquet(ROOT / "outputs/tables/firm_x.parquet", columns=["date", "period", "firm", "X", "clean", "zero_price"])
    fx = fx[fx.clean & ~fx.zero_price].rename(columns={"firm": "group"})
    jx = hp.dropna(subset=["X"]).merge(fx[["date", "period", "group", "X"]], on=["date", "period", "group"],
                                       how="left", suffixes=("", "_fx"))
    gap6 = float((jx.X - jx.X_fx).abs().max())
    check(jx.X_fx.notna().all() and gap6 < 1e-9,
          f"edp_hydro_panel X = firm_x X for the row's dated group (max gap {gap6:.1e}, {len(jx):,} rows)")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
