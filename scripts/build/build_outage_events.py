#!/usr/bin/env python3
"""Large unplanned outages of every dispatchable plant, and what each costs its owners.

    .venv/bin/python scripts/build/build_outage_events.py
    .venv/bin/python scripts/build/build_outage_events.py --verify

Design: docs/specs/2026-10-19-outage-events-design.md. The reactor instrument
(build_reactor_outages.py) is clean but has 49 unplanned spells; OMIE's `indisp`
register holds far more faults on gas, coal, steam and hydro plant. Reactors stay
out here: they are built by their own script.

DECLARATIONS. Each `indisp` declaration's last revision, linked to its OMIE unit
through REE's physical-unit register (ESIOS archive 81: `uf` -> `up`, a 2026-08-12
snapshot), lost MW = the group's max power minus the declared available. `indisp`
times are Madrid local; `declared` is when the declaration was made, so start minus
declared is its lead time.

CLASS, from the reason text (first match in this order wins):
    fault        breakdowns: trips, faults, leaks, ruptures, unplanned work
    coldstart    cold-start lead time: the plant is off, a consequence, not a shock
    operational  "indisponibilidad operacional": no cause given, possibly chosen
    water        reservoir levels, flow requirements: the hydro unit's own cost
    planned      programmed stops, maintenance, inspections, revisions
    unclassified the rest, kept out
The reactor classifier defaults unknown text to "unplanned", which would let every
one of these in; here the default is out.

EVENTS. Kept: lost >= MIN_MW, lasting >= MIN_H hours; faults only when declared less
than LEAD_H hours before they start (`fault`), planned stops at any lead (`planned`).
Fault hours a planned declaration of the same group also covers go to `planned`.
Groups are summed to their OMIE unit hour by hour; consecutive hours form a spell.

DOSE. A fault binds only where it cuts into what the unit would have produced:
    bind = max(0, lost - (cap - expected)),  at most expected
with cap the month's `cab` max power and expected the unit's PDBF schedule (all
role codes) in the same UTC hour of day over the 7 days before the spell. A unit
expected at 0 loses nothing. A pumping unit's expected is what it would have bought:
its fault RAISES its owner's net position, a generating unit's fault lowers it
(`dn_mw`). Owners and shares by date (lib/unit_ownership.py). The dose counts only the
first MAX_DAYS of a spell: the week before says nothing about what a unit would have
run months later, and a fault lasting a year (Castelnou from May 2019, Castejón 2 from
May 2022) is a state, not a shock.

OUTPUTS (outputs/tables/, gitignored except the spell table):
  outage_event_hours.parquet  up, kind, cls, utc, spell, lost_mw, cap_mw, exp_mw, bind_mw
  outage_event_dose.parquet   firm, utc, cls, kind, dose_mw (>= 0), dn_mw (signed effect on n)
  outage_event_spells.csv     spell, up, kind, cls, start, end, hours, peak_lost_mw,
                              exp_mean_mw, bind_gwh, ran_before, lead_h, reason, firm
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from omie_common import day_periods_utc  # noqa: E402
from unit_ownership import attach_owners, spells  # noqa: E402
from build_reactor_outages import norm  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT_HOURS = TABLES / "outage_event_hours.parquet"
OUT_DOSE = TABLES / "outage_event_dose.parquet"
OUT_SPELLS = TABLES / "outage_event_spells.csv"
MIN_MW = 100.0       # lost MW per declaration
MIN_H = 6.0          # hours per declaration
LEAD_H = 24.0        # a fault declared this close to its start, or after it
BASE_DAYS = 7        # days before a spell that set its expected output
MAX_DAYS = 14        # days of a spell its dose counts

# REE technology (archive 81) -> kind. Nuclear is built by build_reactor_outages.py.
KIND = {
    "Ciclo combinado": "gas",
    "Hulla antracita": "coal", "Hulla sub-bituminosa": "coal",
    "Vapor": "steam", "Turbina vapor - Fuel gas": "steam", "Fuel": "steam",
    "Derivados del petróleo o carbón": "steam",
    "Embalse": "hydro", "Fluyente": "hydro", "Hidráulica - No UGH": "hydro",
    "Turbinación bombeo": "pumped_gen",
    "Consumo bombeo": "pumping",
}
CLASSES = [
    ("fault", r"DISPAR|AVER|FALLO|FUGA|ROTURA|INCIDEN|DEFECTO|ANOMAL|REPARACI|VIBRACI|PROBLEMA|FISURA|"
              r"NO PROGRAMAD|CORRECTIV"),
    ("coldstart", r"ARRANQUE|FRIO"),
    ("operational", r"INDISPONIBILIDAD OPERACIONAL"),
    ("water", r"COTA|EMBALSE|DEPOSITO|CAUDAL|SALTO|JUNTA|CHD|CONFEDERACI|ALBUFEIRA|DESEMBALSE|HIDRAUL|"
              r"SEQUIA|NIVEL"),
    ("planned", r"PROGRAMAD|MANTENIMIENTO|MAINTENANCE|INSPECCI|REVISI|ANUAL|PREVIST"),
]


def classify(reason: str) -> str:
    r = norm(reason)
    for cls, pat in CLASSES:
        if re.search(pat, r):
            return cls
    return "unclassified"


def to_utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).dt.tz_localize("Europe/Madrid", ambiguous=True,
                                            nonexistent="shift_forward").dt.tz_convert("UTC")


def declarations() -> pd.DataFrame:
    """One row per outage_id (last revision) of a dispatchable group, with class, kind,
    UTC span, lead time and lost MW."""
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(DATA / "omie/indisp/parquet/indisp_*.parquet")))])
    d["unit"] = d.unit.astype(str)
    d = d.sort_values("snapshot").drop_duplicates("outage_id", keep="last")
    uf = pd.read_parquet(DATA / "esios/esios_physical_units.parquet", columns=["uf", "up", "tech", "max_power_mw"])
    d = d.merge(uf, left_on="unit", right_on="uf", how="inner")
    # One kind per OMIE unit: a combined cycle registers its steam turbine as a `Vapor`
    # group (12 units: Castellón, Escombreras 6, Puentes 5, ...), which is still gas.
    uk = uf.assign(kind=uf.tech.map(KIND)).dropna(subset=["kind"])
    up_kind = uk.groupby("up").kind.agg(lambda s: "gas" if "gas" in set(s) else s.mode().iloc[0])
    d["kind"] = d.up.map(up_kind)
    d = d[d.kind.notna()].copy()
    d["lost"] = (d.max_power_mw - d.available_mw).clip(lower=0)
    d["cls_reason"] = d.reason.astype(str).map(classify)
    for c in ("start", "end", "declared"):
        d[c] = to_utc(d[c])
    d["hours"] = (d.end - d.start).dt.total_seconds() / 3600
    d["lead_h"] = (d.start - d.declared).dt.total_seconds() / 3600
    big = (d.lost >= MIN_MW) & (d.hours >= MIN_H)
    d["cls"] = np.where(big & (d.cls_reason == "fault") & (d.lead_h < LEAD_H), "fault",
                        np.where(big & (d.cls_reason == "planned"), "planned", None))
    return d[["outage_id", "uf", "up", "tech", "kind", "start", "end", "hours", "lead_h", "lost",
              "reason", "cls_reason", "cls"]]


def expand(d: pd.DataFrame) -> pd.DataFrame:
    """uf, up, kind, cls, utc, lost: every UTC hour a kept declaration overlaps; the
    largest loss per group-hour and class; fault hours under a planned stop go to planned."""
    k = d[d.cls.notna()].reset_index(drop=True)
    h0 = k.start.dt.floor("h")
    n = ((k.end - h0).dt.total_seconds() / 3600).apply(np.ceil).astype(int).clip(lower=1)
    rows = k.loc[k.index.repeat(n), ["uf", "up", "kind", "cls", "lost", "reason", "lead_h"]].reset_index(drop=True)
    base = h0.dt.tz_convert(None).to_numpy().astype("datetime64[ns]").repeat(n.to_numpy())
    steps = np.concatenate([np.arange(m) for m in n]).astype("timedelta64[h]").astype("timedelta64[ns]")
    rows["utc"] = pd.DatetimeIndex(base + steps).tz_localize("UTC")
    rows = rows.sort_values("lost", ascending=False).drop_duplicates(["uf", "cls", "utc"])
    plan = rows.loc[rows.cls == "planned", ["uf", "utc"]].assign(under_plan=True)
    rows = rows.merge(plan, on=["uf", "utc"], how="left")
    rows = rows[~((rows.cls == "fault") & rows.under_plan.fillna(False).astype(bool))]
    return rows.drop(columns=["under_plan"])


def capacity(units: list[str]) -> pd.DataFrame:
    """up, month, side, cap_mw: the month's median `cab` max power, by side."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/cab/parquet/cab_*.parquet"))):
        frames.append(pq.read_table(f, columns=["date", "unit", "side", "max_power_mw"],
                                    filters=[("unit", "in", units)]).to_pandas())
    c = pd.concat(frames)
    c["month"] = pd.to_datetime(c.date).dt.to_period("M")
    c = c[c.max_power_mw > 0]
    return (c.groupby(["unit", "month", "side"], as_index=False).max_power_mw.median()
             .rename(columns={"unit": "up", "max_power_mw": "cap_mw"}))


def schedule(units: list[str]) -> pd.DataFrame:
    """up, utc (hour), sched_mw: PDBF summed over role codes, mean MW over the UTC hour.
    Absent rows are 0 (PDBF lists only scheduled units)."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/pdbf/parquet/pdbf_*.parquet"))):
        p = pq.read_table(f, columns=["date", "period", "unit", "schedule_mw"],
                          filters=[("unit", "in", units)]).to_pandas()
        if p.empty:
            continue
        p = p.groupby(["date", "unit", "period"], as_index=False).schedule_mw.sum()
        # periods per day from the whole file: PDBF went quarter-hourly on 2025-03-19
        nper = pq.read_table(f, columns=["date", "period"]).to_pandas().groupby("date").period.max()
        utc = []
        for d, n in nper.items():
            utc.append(pd.DataFrame({"date": d, "period": range(1, int(n) + 1),
                                     "utc": day_periods_utc(pd.Timestamp(d).date(), int(n))}))
        u = pd.concat(utc)
        u["utc"] = pd.to_datetime(u.utc, utc=True)
        p = p.merge(u, on=["date", "period"])
        p["utc"] = p.utc.dt.floor("h")
        # mean over the hour's periods, counting periods the unit has no row for as 0
        per_h = u.assign(utc=u.utc.dt.floor("h")).groupby("utc").size().rename("np")
        s = p.groupby(["unit", "utc"]).schedule_mw.sum().reset_index().merge(per_h, on="utc")
        s["sched_mw"] = s.schedule_mw / s.np
        frames.append(s[["unit", "utc", "sched_mw"]])
    return pd.concat(frames).rename(columns={"unit": "up"})


def spells_up(rows: pd.DataFrame, cap: pd.DataFrame) -> pd.DataFrame:
    """Unit-hours by class: groups summed (at most the unit's capacity), spells numbered."""
    h = rows.groupby(["up", "kind", "cls", "utc"], as_index=False).agg(
        lost_mw=("lost", "sum"), reason=("reason", "first"), lead_h=("lead_h", "min"))
    h["month"] = h.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.to_period("M")
    h["side"] = np.where(h.kind == "pumping", "C", "V")
    h = h.merge(cap, on=["up", "month", "side"], how="left")
    h["cap_mw"] = h.groupby("up").cap_mw.transform(lambda x: x.ffill().bfill())
    h["lost_mw"] = np.minimum(h.lost_mw, h.cap_mw.fillna(h.lost_mw))
    h = h.sort_values(["up", "cls", "utc"]).reset_index(drop=True)
    new = ((h.utc.diff() != pd.Timedelta(hours=1)) | (h.up != h.up.shift()) | (h.cls != h.cls.shift()))
    h["spell"] = new.cumsum()
    return h.drop(columns=["month", "side"])


def expected(h: pd.DataFrame, sched: pd.DataFrame) -> pd.DataFrame:
    """Each spell's expected output by UTC hour of day: the unit's mean schedule in that
    hour over the BASE_DAYS before the spell (consumption, as a positive number, for a
    pumping unit). Adds exp_mw, bind_mw and ran_before."""
    st = h.groupby("spell").agg(up=("up", "first"), kind=("kind", "first"), start=("utc", "min")).reset_index()
    s = sched.set_index(["up", "utc"]).sched_mw.sort_index()
    out = []
    for r in st.itertuples(index=False):
        hrs = pd.date_range(r.start - pd.Timedelta(days=BASE_DAYS), r.start - pd.Timedelta(hours=1), freq="h")
        try:
            v = s.loc[r.up].reindex(hrs, fill_value=0.0)
        except KeyError:
            v = pd.Series(0.0, index=hrs)
        v = (-v).clip(lower=0) if r.kind == "pumping" else v.clip(lower=0)
        prof = v.groupby(v.index.hour).mean().reindex(range(24), fill_value=0.0)
        out.append(pd.DataFrame({"spell": r.spell, "hod": range(24), "exp_mw": prof.to_numpy(),
                                 "ran_before": v.mean() > 0}))
    e = pd.concat(out)
    h = h.assign(hod=h.utc.dt.hour).merge(e, on=["spell", "hod"], how="left").drop(columns=["hod"])
    cap = h.cap_mw.fillna(h.exp_mw)
    h["bind_mw"] = np.clip(h.exp_mw - (cap - h.lost_mw), 0, None)
    h["bind_mw"] = np.minimum(h.bind_mw, h.exp_mw)
    start = h.groupby("spell").utc.transform("min")
    h.loc[h.utc >= start + pd.Timedelta(days=MAX_DAYS), "bind_mw"] = 0.0
    return h


def dose(h: pd.DataFrame) -> pd.DataFrame:
    x = h[h.bind_mw > 0][["up", "utc", "cls", "kind", "bind_mw"]].copy()
    x["date"] = x.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    a = attach_owners(x, spells(), unit_col="up", value_cols=("bind_mw",))
    a = a.rename(columns={"group": "firm", "bind_mw": "dose_mw"})
    a["firm"] = a.firm.fillna("UNOWNED")
    a["dn_mw"] = np.where(a.kind == "pumping", 1.0, -1.0) * a.dose_mw
    return a.groupby(["firm", "utc", "cls", "kind"], as_index=False)[["dose_mw", "dn_mw"]].sum()


def spell_table(h: pd.DataFrame) -> pd.DataFrame:
    g = h.groupby("spell")
    s = g.agg(up=("up", "first"), kind=("kind", "first"), cls=("cls", "first"), start=("utc", "min"),
              end=("utc", "max"), hours=("utc", "size"), peak_lost_mw=("lost_mw", "max"),
              exp_mean_mw=("exp_mw", "mean"), bind_gwh=("bind_mw", lambda x: x.sum() / 1000),
              ran_before=("ran_before", "first"), lead_h=("lead_h", "min"), reason=("reason", "first"))
    s["end"] = s.end + pd.Timedelta(hours=1)
    first = h.sort_values("utc").drop_duplicates("spell")[["spell", "up", "utc"]].copy()
    first["date"] = first.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    a = attach_owners(first, spells(), unit_col="up", value_cols=())
    a = a.sort_values("share", ascending=False).drop_duplicates("spell")
    s = s.join(a.set_index("spell").group.rename("firm"))
    return s.reset_index()


def report(d: pd.DataFrame, h: pd.DataFrame, s: pd.DataFrame, dz: pd.DataFrame) -> None:
    print("DECLARATIONS of dispatchable groups by reason class (all sizes and leads):")
    print(d.cls_reason.value_counts().to_string())
    print(f"\nkept: {d.cls.notna().sum():,} declarations "
          f"({(d.cls == 'fault').sum():,} fault, {(d.cls == 'planned').sum():,} planned)")
    print("\nSPELLS by class and kind: count, median hours, share that bind, GWh bound")
    t = s.groupby(["cls", "kind"]).agg(spells=("spell", "size"), median_h=("hours", "median"),
                                        ran_before=("ran_before", "mean"),
                                        binds=("bind_gwh", lambda x: (x > 0).mean()),
                                        gwh=("bind_gwh", "sum"))
    print(t.round(2).to_string())
    print("\nfault spells that bind, by year and firm:")
    f = s[(s.cls == "fault") & (s.bind_gwh > 0)]
    print(pd.crosstab(f.firm.fillna("?"), f.start.dt.year).loc[lambda x: x.sum(axis=1) >= 10].to_string())
    print("\nfault dose, mean MW by firm and kind (all hours of the window):")
    nh = (h.utc.max() - h.utc.min()).total_seconds() / 3600 + 1
    m = dz[dz.cls == "fault"].groupby(["firm", "kind"]).dose_mw.sum().unstack().fillna(0) / nh
    print(m.loc[m.sum(axis=1).sort_values(ascending=False).index[:10]].round(1).to_string())
    print("\nunits under `Vapor` and `steam`:", sorted(h[h.kind == "steam"].up.unique()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="re-check the stored outputs")
    args = ap.parse_args()
    if args.verify:
        h, dz = pd.read_parquet(OUT_HOURS), pd.read_parquet(OUT_DOSE)
        assert (h.bind_mw >= -1e-9).all() and (h.bind_mw <= h.lost_mw + 1e-6).all(), "bind outside [0, lost]"
        assert (h.bind_mw <= h.exp_mw + 1e-6).all(), "bind above expected output"
        assert not h.duplicated(["up", "cls", "utc"]).any(), "a unit-hour twice in one class"
        tot_h, tot_d = h.bind_mw.sum(), dz.dose_mw.sum()
        assert abs(tot_h - tot_d) / tot_h < 1e-6, f"dose does not add up to the bound output ({tot_d} vs {tot_h})"
        sign = np.where(dz.kind == "pumping", 1.0, -1.0)
        assert ((np.sign(dz.dn_mw) == sign) | (dz.dose_mw == 0)).all(), "dn_mw has the wrong sign"
        print("--verify passed")
        return 0
    d = declarations()
    rows = expand(d)
    units = sorted(rows.up.unique())
    print(f"{len(d):,} declarations of dispatchable groups; {len(units)} OMIE units with a kept one")
    h = spells_up(rows, capacity(units))
    h = expected(h, schedule(units))
    s = spell_table(h)
    dz = dose(h)
    TABLES.mkdir(parents=True, exist_ok=True)
    h.drop(columns=["reason", "lead_h"]).to_parquet(OUT_HOURS, index=False)
    dz.to_parquet(OUT_DOSE, index=False)
    s.to_csv(OUT_SPELLS, index=False)
    report(d, h, s, dz)
    print(f"\nwrote {OUT_HOURS.relative_to(ROOT)}, {OUT_DOSE.relative_to(ROOT)}, {OUT_SPELLS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
