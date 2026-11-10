#!/usr/bin/env python3
"""Registry of cogeneration offer units: thermal plants in the special regime, with fuel and entry into the gas cap.

    .venv/bin/python scripts/build/build_cogeneration_units.py

Design: docs/specs/2026-11-10-cogeneration-design.md (step 0). Universe: every unit OMIE's *Listado de Unidades*
labels "RE Mercado Térmica no renovable" (`nonren`) or "RE Mercado Térmica Renovable" (`renew`) in any snapshot
(the label exists from 2022-02-08). Writes data/omie/registry/cogeneration_units.parquet, one row per unit:

- descr, agent_owner, label: from the latest listing giving the unit one of the two labels.
- max_power_mw: the median day's `cab` maximum power on the sell side, 2019-2023; cap_max_mw the largest;
  mw_202201 January 2022's (null without an offer header that month).
- first_day, last_day: first and last day with a positive PDBF schedule, 2018-2023; active_202201.
- new_after_cap: first_day on or after 2022-06-01. The gas-cap decree (RDL 10/2022, art. 4) requires a separate
  offer unit for a subsidised plant, so a new unit after the cap marks a plant entering the mechanism.
  entry_day, mechanism_source ("new_unit").
- fuel, ree_plants, ree_mw, match_how: REE's physical units (ESIOS archive 81, a 2026-08-12 snapshot) matched to the
  unit. Four rules, each needing positive evidence:
    code            the OMIE code is the plant's programming unit (`up`) or physical unit (`uf`)
    up_in_descr     OMIE's description names the programming unit ("UOF PARA UP TTECQU")
    name_capacity   names agree (similarity >= 0.8) and capacity within 15%, mutually the best candidate
    agent_capacity  the representative is the plant's REE agent and capacity agrees within 2%, with no other
                    unit or plant of that agent within 5% (the weakest rule; kept apart in `match_how`)
  Units from before and after the cap are matched separately, so a plant that changed code matches both.
- portfolio: several plants matched, or above 60 MW with under 60% of the capacity matched.
- linked_from: for a new unit, the earlier unit its plant left (shared REE plant, or same owner and name).
- sector, region: keyword rule on the name; region from MITECO's producer register by exact name.

Every accepted name_capacity and agent_capacity pair, and every rejected ambiguous one, is printed. Read them.
"""
from __future__ import annotations

import glob
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from build_direct_consumers import sector  # noqa: E402

LISTS = ROOT / "data" / "omie" / "registry" / "omie_unit_lists.parquet"
PHYS = ROOT / "data" / "esios" / "esios_physical_units.parquet"
ELECTRA = ROOT / "data" / "miteco" / "electra" / "raw" / "ElectraExp.csv"
OUT = ROOT / "data" / "omie" / "registry" / "cogeneration_units.parquet"
CAP_DAY = pd.Timestamp("2022-06-01").date()

FUEL = {"Gas natural cogeneración": "gas",
        "Derivados del petróleo o carbón": "other_fossil", "Fuel": "other_fossil",
        "Turbina vapor - Fuel gas": "other_fossil", "Energía residual": "other_fossil",
        "Biomasa": "biomass_waste", "Biogás": "biomass_waste", "Residuos varios": "biomass_waste",
        "Residuos domésticos y similares": "biomass_waste"}

# OMIE's representative (as the listing names the owner) -> REE's agent code. Read off the two registers' own
# names; each is the same company.
REP_AGENT = {"AXPO IBERIA": "EGLE", "CEPSA GAS Y ELECTRICIDAD": "DETIC", "NEXUS ENERG": "NEXU",
             "ENERGYA VM": "CEG", "FACTOR ENERGIA": "AME", "GNERA ENERGIA": "GNRA", "WIND TO MARKET": "WMARK",
             "LONJAS TECNOLOG": "LMER", "GESTION DE ENERG": "GEMSL", "IGNIS ENERGIA": "IGNIS",
             "ENERGY BY COGEN": "COGEN"}

CODE_LIKE = re.compile(r"^[A-Z0-9]{2,8}( ?\d+)?$")
MANUAL: dict[str, list[str]] = {}  # unit -> REE uf codes; each entry needs a comment with names and capacities

WORDS = re.compile(r"\b(UOF|UF|UP|PARA|COGENERACION|COGEN|PLANTA|CENTRAL|VENTA|TARIFA|TERMICA|EXCED|AUTOPROD|"
                   r"UNIDAD|FISICA|RE|REG|ESP|ESPECIAL|S A|S L|SA|SL)\b")


def norm(s: str | None) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", WORDS.sub(" ", s)).strip()


def load_listing_units() -> pd.DataFrame:
    u = pd.read_parquet(LISTS)
    t = u.technology.fillna("")
    u = u[t.str.startswith("RE Mercado Térmica no") | (t == "RE Mercado Térmica Renovable")].copy()
    u["label"] = u.technology.map(lambda x: "renew" if "Renovable" in x else "nonren")
    last = u.sort_values("snapshot").groupby("unit", as_index=False).last()
    return last[["unit", "descr", "agent_owner", "label"]]


def activity(units: set) -> pd.DataFrame:
    """First and last day with a positive PDBF schedule (all role codes summed), and activity in January 2022."""
    parts = []
    for f in sorted(glob.glob(str(ROOT / "data" / "omie" / "pdbf" / "parquet" / "pdbf_20*.parquet"))):
        if not "201801" <= Path(f).stem[-6:] <= "202312":
            continue
        d = pd.read_parquet(f, columns=["date", "unit", "schedule_mw", "resolution_min"])
        d = d[d.unit.isin(units)]
        e = (d.schedule_mw * d.resolution_min / 60).groupby([d.unit, d.date]).sum()
        parts.append(e[e > 0].reset_index(name="mwh"))
    a = pd.concat(parts)
    a["date"] = pd.to_datetime(a.date).dt.date
    g = a.groupby("unit").date.agg(first_day="min", last_day="max").reset_index()
    jan = set(a[(a.date >= pd.Timestamp("2022-01-01").date()) & (a.date <= pd.Timestamp("2022-01-31").date())].unit)
    g["active_202201"] = g.unit.isin(jan)
    return g


def capacity(units: set) -> pd.DataFrame:
    """Sell-side `cab` maximum power per unit, 2019-2023: the median day (max_power_mw), the largest (cap_max_mw),
    and January 2022 (mw_202201, null when the unit has no offer header that month)."""
    parts = []
    for f in sorted(glob.glob(str(ROOT / "data" / "omie" / "cab" / "parquet" / "cab_20*.parquet"))):
        if not "201901" <= Path(f).stem[-6:] <= "202312":
            continue
        d = pd.read_parquet(f, columns=["unit", "date", "side", "max_power_mw"])
        d = d[d.unit.isin(units) & (d.side == "V")]
        parts.append(d.groupby(["unit", "date"], as_index=False).max_power_mw.max())
    c = pd.concat(parts)
    c["date"] = c.date.astype(str)
    g = c.groupby("unit").max_power_mw.agg(max_power_mw="median", cap_max_mw="max").reset_index()
    jan = c[c.date.str.startswith("2022-01")].groupby("unit").max_power_mw.max().rename("mw_202201")
    return g.merge(jan, on="unit", how="left")


def regions() -> dict:
    e = pd.read_csv(ELECTRA, sep=";", encoding="latin-1", dtype=str)
    e["n"] = e.INSTALACION.map(norm)
    one = e.groupby("n").AUTONOMIA.nunique()
    e = e[e.n.isin(one[one == 1].index) & (e.n.str.len() >= 5)]
    return dict(zip(e.n, e.AUTONOMIA))


def load_plants() -> pd.DataFrame:
    p = pd.read_parquet(PHYS)
    p = p[p.tech.isin(FUEL)].copy()
    p["fuel"] = p.tech.map(FUEL)
    return p[["uf", "up", "descr_long", "descr_short", "agent", "max_power_mw", "fuel"]]


def _agent(owner: str | None) -> str | None:
    o = norm(owner)
    for k, v in REP_AGENT.items():
        if norm(k) in o:
            return v
    return None


def match_ree_plants(units: pd.DataFrame, plants: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Match offer units to REE plants. Returns (unit, uf, how) rows and the rejected ambiguous candidates."""
    rows, rejected = [], []
    used_u, used_p = set(), set()
    by_up = plants.groupby("up").uf.apply(list).to_dict()
    up_of_uf = dict(zip(plants.uf, plants.up))

    def take(unit, ufs, how):
        ufs = [x for x in ufs if x not in used_p]
        if not ufs:
            return
        for x in ufs:
            rows.append({"unit": unit, "uf": x, "how": how})
            used_p.add(x)
        used_u.add(unit)

    for r in units.itertuples():  # 1 code
        if r.unit in by_up:
            take(r.unit, by_up[r.unit], "code")
        elif r.unit in up_of_uf:
            take(r.unit, [r.unit], "code")
    codes = {c for c in list(by_up) + list(up_of_uf) if len(c) >= 5}
    for r in units.itertuples():  # 2 the description names the programming unit
        if r.unit in used_u:
            continue
        toks = set(re.sub(r"[^A-Z0-9]", " ", str(r.descr).upper()).split()) & codes
        if len(toks) == 1:
            c = toks.pop()
            take(r.unit, by_up.get(c, [c]), "up_in_descr")
        elif len(toks) > 1:
            rejected.append((r.unit, r.descr, sorted(toks), "several codes in the description"))

    P = plants[~plants.uf.isin(used_p)].copy()  # 3 name and capacity
    P["n1"], P["n2"] = P.descr_long.map(norm), P.descr_short.map(norm)
    cand = []
    for r in units.itertuples():
        if r.unit in used_u or not (r.max_power_mw and r.max_power_mw > 0):
            continue
        n = norm(r.descr)
        if len(n) < 4:
            continue
        near = P[(P.max_power_mw - r.max_power_mw).abs() <= 0.15 * r.max_power_mw]
        for q in near.itertuples():
            s = max(SequenceMatcher(None, n, q.n1).ratio(), SequenceMatcher(None, n, q.n2).ratio())
            if s >= 0.8:
                cand.append((r.unit, q.uf, s, r.descr, q.descr_long, r.max_power_mw, q.max_power_mw))
    c = pd.DataFrame(cand, columns=["unit", "uf", "s", "descr", "plant", "mw", "ree_mw"])
    if len(c):
        nu, npl = c.groupby("unit").uf.transform("nunique"), c.groupby("uf").unit.transform("nunique")
        for q in c[(nu == 1) & (npl == 1)].itertuples():
            print(f"  name_capacity  {q.unit:8s} {q.descr[:30]:30s} {q.mw:7.1f} | {q.uf:8s} {q.plant[:30]:30s} "
                  f"{q.ree_mw:7.1f}  s={q.s:.2f}")
            take(q.unit, [q.uf], "name_capacity")
        for q in c[(nu > 1) | (npl > 1)].itertuples():
            rejected.append((q.unit, q.descr, q.uf, "ambiguous name and capacity"))

    U = units[~units.unit.isin(used_u) & (units.max_power_mw >= 1)].copy()  # 4 agent and capacity
    U["agent"] = U.agent_owner.map(_agent)
    P = plants[~plants.uf.isin(used_p) & (plants.max_power_mw >= 1)]
    for ag, ug in U.dropna(subset=["agent"]).groupby("agent"):
        pg = P[P.agent == ag]
        for r in ug.itertuples():
            close = pg[(pg.max_power_mw - r.max_power_mw).abs() <= 0.02 * r.max_power_mw]
            wide_p = pg[(pg.max_power_mw - r.max_power_mw).abs() <= 0.05 * r.max_power_mw]
            if len(close) == 0:
                continue
            wide_u = ug[(ug.max_power_mw - close.max_power_mw.iloc[0]).abs() <= 0.05 * close.max_power_mw.iloc[0]]
            if len(close) == 1 and len(wide_p) == 1 and len(wide_u) == 1:
                q = close.iloc[0]
                print(f"  agent_capacity {r.unit:8s} {str(r.descr)[:30]:30s} {r.max_power_mw:7.1f} | {q.uf:8s} "
                      f"{str(q.descr_long)[:30]:30s} {q.max_power_mw:7.1f}  agent={ag}")
                take(r.unit, [q.uf], "agent_capacity")
            else:
                rejected.append((r.unit, r.descr, list(wide_p.uf), "agent and capacity not unique"))
    for unit, ufs in MANUAL.items():
        if unit in set(units.unit) and unit not in used_u:
            take(unit, ufs, "manual")
    return pd.DataFrame(rows, columns=["unit", "uf", "how"]), rejected


def attach_fuel(reg: pd.DataFrame, plants: pd.DataFrame) -> pd.DataFrame:
    parts, nrej = [], 0
    for era, g in reg.groupby(reg.new_after_cap):
        print(f"\nmatching {'new' if era else 'earlier'} units ({len(g)})")
        m, rej = match_ree_plants(g, plants)
        nrej += len(rej)
        for x in rej[:40]:
            print("  rejected", x)
        parts.append(m)
    m = pd.concat(parts).merge(plants[["uf", "max_power_mw", "fuel"]], on="uf")
    a = m.groupby("unit").agg(ree_plants=("uf", list), ree_mw=("max_power_mw", "sum"), match_how=("how", "first"),
                              fuel=("fuel", lambda s: s.iloc[0] if s.nunique() == 1 else "mixed")).reset_index()
    reg = reg.merge(a, on="unit", how="left")
    clash = (reg.label == "renew") & (reg.fuel == "gas")  # OMIE says renewable, REE says gas: trust neither
    if clash.any():
        print("\nlabel and fuel disagree, fuel set to 'conflict':")
        print(reg[clash][["unit", "descr", "agent_owner", "ree_plants"]].to_string())
        reg.loc[clash, "fuel"] = "conflict"
    n = reg.ree_plants.map(lambda x: len(x) if isinstance(x, list) else 0)
    reg["portfolio"] = (n > 1) | ((reg.max_power_mw > 60) & ~(reg.ree_mw >= 0.6 * reg.max_power_mw))
    print(f"\nmatched {reg.match_how.notna().sum()} of {len(reg)} units; {nrej} candidates rejected")
    print(reg.match_how.value_counts().to_string())
    return reg


def link_new_units(reg: pd.DataFrame) -> pd.DataFrame:
    """For each unit that starts after the cap, the earlier unit its plant left."""
    old = reg[~reg.new_after_cap & reg.first_day.notna()]
    plant_unit = {uf: r.unit for r in old.itertuples() if isinstance(r.ree_plants, (list, tuple)) or
                  hasattr(r.ree_plants, "__len__") and not isinstance(r.ree_plants, float) for uf in r.ree_plants}
    out = {}
    for r in reg[reg.new_after_cap].itertuples():
        ufs = [] if isinstance(r.ree_plants, float) or r.ree_plants is None else list(r.ree_plants)
        hit = {plant_unit[x] for x in ufs if x in plant_unit}
        if len(hit) == 1:
            out[r.unit] = hit.pop()
            print(f"  link (plant) {r.unit:8s} {str(r.descr)[:30]:30s} <- {out[r.unit]}")
            continue
        n = norm(r.descr)
        same = old[(old.agent_owner == r.agent_owner)]
        named = len(n) >= 6 and not CODE_LIKE.match(n) and n != r.unit  # a code or boilerplate is not a name
        c = [(SequenceMatcher(None, n, norm(d)).ratio(), u) for u, d in zip(same.unit, same.descr)] if named else []
        c = sorted([x for x in c if x[0] >= 0.8], reverse=True)
        if len(c) == 1 or (len(c) > 1 and c[0][0] - c[1][0] >= 0.1):
            out[r.unit] = c[0][1]
            print(f"  link (name)  {r.unit:8s} {str(r.descr)[:30]:30s} <- {c[0][1]}  s={c[0][0]:.2f}")
        elif c:
            print(f"  link rejected {r.unit} {r.descr}: {c[:4]}")
    reg["linked_from"] = reg.unit.map(out)
    return reg


def main() -> int:
    reg = load_listing_units()
    units = set(reg.unit)
    print(f"{len(reg)} units labelled thermal special regime ({(reg.label == 'nonren').sum()} non-renewable)")
    reg = reg.merge(capacity(units), on="unit", how="left").merge(activity(units), on="unit", how="left")
    reg["active_202201"] = reg.active_202201.fillna(False).astype(bool)
    reg["new_after_cap"] = reg.first_day.map(lambda d: isinstance(d, type(CAP_DAY)) and d >= CAP_DAY)
    reg = attach_fuel(reg, load_plants())
    reg = link_new_units(reg)
    reg["entry_day"] = reg.first_day.where(reg.new_after_cap)
    reg["mechanism_source"] = None
    reg.loc[reg.new_after_cap & (reg.label == "nonren"), "mechanism_source"] = "new_unit"
    reg["sector"] = [sector(d) or sector(o) for d, o in zip(reg.descr, reg.agent_owner)]
    rg = regions()
    reg["region"] = reg.descr.map(lambda d: rg.get(norm(d)))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    reg.to_parquet(OUT, index=False)

    a = reg[(reg.label == "nonren") & reg.mw_202201.notna()]
    print(f"\nnon-renewable, offering in January 2022: {len(a)} units, {a.mw_202201.sum():,.0f} MW")
    known = a[a.fuel.notna()].mw_202201.sum()
    print(f"gate G0: fuel known for {known / a.mw_202201.sum():.1%} of that capacity "
          f"(gas {a[a.fuel == 'gas'].mw_202201.sum():,.0f} MW)")
    print(f"  by rule (MW): {a.groupby('match_how').mw_202201.sum().round(0).to_dict()}")
    print(f"  portfolio units: {int(a.portfolio.sum())}, {a[a.portfolio].mw_202201.sum():,.0f} MW")
    new = reg[reg.new_after_cap & (reg.label == "nonren")]
    print(f"new non-renewable units from 2022-06: {len(new)}; linked to an earlier unit: {new.linked_from.notna().sum()}")
    print(f"sector known: {(reg.sector != '').mean():.0%}; region known: {reg.region.notna().mean():.0%}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
