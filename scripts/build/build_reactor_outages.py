#!/usr/bin/env python3
"""Reactor outages, hour by hour, by cause, and each owner's dose by share.

    .venv/bin/python scripts/build/build_reactor_outages.py
    .venv/bin/python scripts/build/build_reactor_outages.py --verify

Framework spec §9.3: an outage of a co-owned reactor moves each co-owner's net
position by its share of the lost output (Almaraz 1 down: Iberdrola 52.7%, Endesa
36.0%, Naturgy 11.3%), so the same shock reaches three firms in known proportions.
The instrument is only as good as the outage is unchosen, so every lost hour is
classified by the cause its owner declared.

LOST OUTPUT. The scheduled output of each of the seven reactors (Almaraz 1 and 2,
Asco 1 and 2, Cofrentes, Trillo, Vandellos II) is its PDBF schedule, all role codes
summed (auction and bilateral), averaged to the UTC hour. PDBF is fixed the day
before delivery, so an outage seen there was known when the day's offers were
made. Lost MW = the month's `cab` max power minus the schedule, counted when it
exceeds MIN_LOSS of capacity.

CAUSE. Each lost hour takes the reason of the OMIE `indisp` declaration covering it
(the one leaving the least available capacity when several do), read from its last
revision and classified by keyword (CAUSES, first match wins). A declaration explains
at most the capacity it declares unavailable (cap - available): a reactor that
declares a summer-long cooling limit to 960 MW and then runs at 400 MW at low prices
has 40 MW of weather and 560 MW undeclared in that hour. `indisp` times are
Madrid local. Ramp declarations ("rampa", "subida de carga") inherit the cause of
the outage they lead into or out of, within the same run of lost hours. A lost hour
no declaration covers is `undeclared`, or `undeclared_gap` on a day `indisp` holds
no snapshot for (43 of its 100 monthly zips are partial at source, CLAUDE.md).

    planned        refuelling, programmed maintenance, tests, end-of-cycle derates
    unplanned      trips, faults, leaks, unplanned maintenance, long stops
    weather        cooling limits from river temperature or flow, sea-storm fouling
    regulatory     waiting for authorisation, grid-caused
    economic       declared flexible operation, the 2020 lockdown derate
    undeclared     reductions nobody declared: since about 2023 mostly output cut
                   at low prices, a price response

OUTPUTS (outputs/tables/, gitignored except the spell table):
  reactor_outage_hours.parquet   unit, utc, cap_mw, sched_mw, lost_mw, and its two
                                 parts: lost_decl_mw (cause, cls, outage_id, reason,
                                 lead_h: hours from first sight to start) and
                                 lost_undecl_mw (undecl_cause)
  reactor_outage_dose.parquet    firm, utc, cls, lost_mw (x the firm's share that day)
  reactor_outage_spells.csv      runs of >= 50% lost: unit, start, end, hours, cls,
                                 cause, lost_gwh, lead_h, reason
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_common import day_periods_utc  # noqa: E402
from unit_ownership import attach_owners, spells  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT_HOURS = TABLES / "reactor_outage_hours.parquet"
OUT_DOSE = TABLES / "reactor_outage_dose.parquet"
OUT_SPELLS = TABLES / "reactor_outage_spells.csv"
REACTORS = ["ALZ1", "ALZ2", "ASC1", "ASC2", "COF1", "TRL1", "VAN2"]
MIN_LOSS = 0.03      # share of capacity below which a shortfall is noise
DOWN = 0.50          # share of capacity lost that makes an hour part of an outage spell

# (cause, class, regex on the normalised reason); first match wins. Order matters:
# "previo a recarga" is a derate before refuelling, not the refuelling itself.
CAUSES = [
    ("flexible", "economic", r"FLEXIB|FUNCIONAMIENTO A 630"),
    ("coastdown", "planned", r"ALARGAMIENTO|FIN DE CICLO|COAST ?DOWN|AGOTAMIENTO|FFWTR|CERCANIA PARADA RECARGA"),
    ("refuelling_extension", "unplanned", r"(PROLONGACI|AMPLIACI).*RECARGA|RECARGA.*AMPLIACI"),
    ("refuelling", "planned", r"RECARGA|ARRANQUE Y PRUEBAS INICIALES DEL CICLO"),
    ("weather", "weather", r"AMBIENTAL|TEMPORAL|TEMPERATURA.*R.O|DELTA T DEL R|CAUDAL REFRIGERACI|"
                           r"BAJO CAUDAL AGUA DE REFRIGERACI|CONDICIONES DE REFRIGERACI"),
    ("regulatory", "regulatory", r"ESPERA DE AUTORIZACI|BAJA TENSI|400 ?KV|ESPECIFICACIONES TECNICAS"),
    ("ramp", "ramp", r"RAMPA|SUBIDA DE CARGA|SUBIDA CARGA|ESTABILIZACI|RETRASO|ACOPLAMIENTO\.?$|"
                     r"BAJADA DE CARGA PARA PARADA|BAJADA PARA RECARGA|BAJADA DE CARGA\.?$"),
    ("planned_work", "planned", r"PRUEBA|BARRAS DE CONTROL|SCRAM|FLUX|MANTENIMIENTO PREVENTIVO|"
                                r"PLAN DE MANTENIMIENTO|PROGRAMADA PARA|ACTIVIDADES PROGRAMADAS|"
                                r"BAJADA DE CARGA PARA|ACTIVIDADES DE MANTENIMIENTO|TRABAJOS|"
                                r"COMIENZO MANTENIMIENTO|VARIACION EN PRODUCCION"),
    ("long_stop", "unplanned", r"LARGA DURACI"),
    ("fault", "unplanned", r"DISPAR|AVER|FALLO|FUGA|NO PROGRAMAD|PROBLEMA|ANOMAL|REPARACI|INOPERAB|"
                           r"VIBRACI|DEFECTO|DETECTOR|QUIMIC|VACIO|SENAL|OSCILAC|SUMIDERO|POZO SECO|"
                           r"INTERVENCI|DESACOPLAMIENTO|FISURA|REFRIGERACI|PARADA DE LA CENTRAL|AJUSTE|"
                           r"COMPROBACIONES|INSTRUMENTACION"),
]


def norm(s: str) -> str:
    """Upper case, accents and the source's mojibake stripped, whitespace collapsed."""
    s = str(s)
    for bad, good in (("Ã³", "o"), ("Ã©", "e"), ("Ã¡", "a"), ("Ã\xad", "i"), ("Ãº", "u"), ("Ã±", "n")):
        s = s.replace(bad, good)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.upper().replace("?", "").replace("¿", "")).strip()


def classify(reason: str) -> tuple[str, str]:
    r = norm(reason)
    for cause, cls, pat in CAUSES:
        if re.search(pat, r):
            return cause, cls
    return "other", "unplanned"


def schedule() -> pd.DataFrame:
    """unit, utc (hour), sched_mw: PDBF summed over role codes, mean MW over the UTC hour."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/pdbf/parquet/pdbf_*.parquet"))):
        p = pq.read_table(f, columns=["date", "period", "unit", "schedule_mw"],
                          filters=[("unit", "in", REACTORS)]).to_pandas()
        if p.empty:
            continue
        p = p.groupby(["date", "unit", "period"], as_index=False).schedule_mw.sum()
        # Each day's periods carry their own UTC start; the step follows from their count.
        utc = []
        for d, g in p.groupby("date"):
            n = int(g.period.max())
            ts = day_periods_utc(pd.Timestamp(d).date(), n)
            utc.append(pd.DataFrame({"date": d, "period": range(1, n + 1), "utc": ts}))
        u = pd.concat(utc)
        u["utc"] = pd.to_datetime(u.utc, utc=True)
        p = p.merge(u, on=["date", "period"])
        p["utc"] = p.utc.dt.floor("h")
        frames.append(p.groupby(["unit", "utc"], as_index=False).schedule_mw.mean())
    s = pd.concat(frames).rename(columns={"schedule_mw": "sched_mw"})
    # Every hour of the window, so an hour with no schedule row (a reactor off) counts.
    hours = pd.date_range(s.utc.min(), s.utc.max(), freq="h", tz="UTC")
    full = pd.MultiIndex.from_product([REACTORS, hours], names=["unit", "utc"])
    return s.set_index(["unit", "utc"]).reindex(full, fill_value=0.0).reset_index()


def capacity() -> pd.DataFrame:
    """unit, month, cap_mw: the month's median `cab` max power."""
    frames = []
    for f in sorted(glob.glob(str(DATA / "omie/cab/parquet/cab_*.parquet"))):
        c = pq.read_table(f, columns=["date", "unit", "max_power_mw"], filters=[("unit", "in", REACTORS)]).to_pandas()
        frames.append(c)
    c = pd.concat(frames)
    c["month"] = pd.to_datetime(c.date).dt.to_period("M")
    return c[c.max_power_mw > 0].groupby(["unit", "month"], as_index=False).max_power_mw.median().rename(
        columns={"max_power_mw": "cap_mw"})


def declarations() -> tuple[pd.DataFrame, set]:
    """One row per outage_id (its last revision) with cause, class, UTC span and first sight;
    and the set of local dates `indisp` holds a snapshot for."""
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(DATA / "omie/indisp/parquet/indisp_*.parquet")))])
    covered = set(pd.to_datetime(d.snapshot).dt.normalize())
    n = d[d.unit.isin(REACTORS)].sort_values("snapshot")
    first = n.groupby("outage_id").snapshot.min().rename("first_seen")
    last = n.drop_duplicates("outage_id", keep="last").set_index("outage_id").join(first).reset_index()
    last[["cause", "cls"]] = last.reason.map(classify).apply(pd.Series)
    for c in ("start", "end", "first_seen"):
        last[c] = (pd.to_datetime(last[c]).dt.tz_localize("Europe/Madrid", ambiguous=True,
                                                          nonexistent="shift_forward").dt.tz_convert("UTC"))
    last["lead_h"] = (last.start - last.first_seen).dt.total_seconds() / 3600
    return last[["outage_id", "unit", "start", "end", "available_mw", "reason", "cause", "cls", "lead_h"]], covered


def assign(h: pd.DataFrame, dec: pd.DataFrame, covered: set) -> pd.DataFrame:
    """Each lost hour's covering declaration (least available capacity), then ramps inherit."""
    h = h.copy()
    h[["outage_id", "cause", "cls", "reason"]] = None
    h["lead_h"] = np.nan
    h["avail"] = np.inf
    for u in REACTORS:
        iu = np.flatnonzero((h.unit == u).to_numpy() & (h.lost_mw > 0).to_numpy())
        t = h.utc.dt.tz_convert(None).to_numpy()[iu]          # naive UTC, datetime64
        for r in dec[dec.unit == u].itertuples():
            m = (t >= r.start.tz_convert(None).to_datetime64()) & (t < r.end.tz_convert(None).to_datetime64())
            if not m.any():
                continue
            rows = iu[m]
            better = h.avail.to_numpy()[rows] > r.available_mw
            rows = rows[better]
            h.loc[h.index[rows], ["outage_id", "cause", "cls", "reason", "lead_h", "avail"]] = (
                r.outage_id, r.cause, r.cls, r.reason, r.lead_h, r.available_mw)
    # A declaration explains at most the capacity it takes away; the rest is undeclared.
    room = (h.cap_mw - h.avail).clip(lower=0).where(np.isfinite(h.avail), 0.0)
    h["lost_decl_mw"] = np.minimum(h.lost_mw, room)
    excess = h.lost_mw - h.lost_decl_mw
    small = excess <= MIN_LOSS * h.cap_mw
    h.loc[small & (h.lost_decl_mw > 0), "lost_decl_mw"] = h.lost_mw     # rounding, not a second cause
    h["lost_undecl_mw"] = h.lost_mw - h.lost_decl_mw
    h.loc[h.lost_decl_mw <= 0, ["outage_id", "cause", "cls", "reason"]] = None
    gap = ~h.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize().isin(covered)
    h["undecl_cause"] = np.where(h.lost_undecl_mw > 0, np.where(gap, "undeclared_gap", "undeclared"), None)
    # Ramps take the cause of their run of lost hours (largest declared non-ramp class).
    h = h.sort_values(["unit", "utc"]).reset_index(drop=True)
    run = (h.lost_mw.gt(0) != h.groupby("unit").lost_mw.shift().gt(0)) | (h.unit != h.unit.shift())
    h["run"] = run.cumsum()
    dom = (h[h.cls.notna() & ~h.cls.eq("ramp")].groupby(["run", "cls", "cause"]).lost_decl_mw.sum()
             .reset_index().sort_values("lost_decl_mw", ascending=False).drop_duplicates("run"))
    ramp = h.cls.eq("ramp")
    m = h.loc[ramp, ["run"]].merge(dom[["run", "cls", "cause"]], on="run", how="left")
    h.loc[ramp, "cls"] = m.cls.fillna("unplanned").to_numpy()
    h.loc[ramp, "cause"] = ("ramp_" + m.cause.fillna("unknown")).to_numpy()
    return h.drop(columns=["avail"])


def parts(h: pd.DataFrame) -> pd.DataFrame:
    """Long form: one row per (unit, hour, part), the declared part with its class, the
    undeclared part as class `undeclared`."""
    d = h[h.lost_decl_mw > 0][["unit", "utc", "cls", "cause", "lost_decl_mw"]].rename(columns={"lost_decl_mw": "lost_mw"})
    u = h[h.lost_undecl_mw > 0][["unit", "utc", "undecl_cause", "lost_undecl_mw"]].rename(
        columns={"undecl_cause": "cause", "lost_undecl_mw": "lost_mw"}).assign(cls="undeclared")
    return pd.concat([d, u], ignore_index=True)


def spell_table(h: pd.DataFrame, pt: pd.DataFrame) -> pd.DataFrame:
    """Runs of hours with at least DOWN of capacity lost; class = the largest part."""
    d = h[h.lost_mw >= DOWN * h.cap_mw].copy()
    new = (d.utc.diff() != pd.Timedelta(hours=1)) | (d.unit != d.unit.shift())
    d["spell"] = new.cumsum()
    g = d.groupby("spell")
    out = g.agg(unit=("unit", "first"), start=("utc", "min"), end=("utc", "max"), hours=("utc", "size"),
                lost_gwh=("lost_mw", lambda x: x.sum() / 1000))
    p = pt.merge(d[["unit", "utc", "spell"]], on=["unit", "utc"])
    by = p.groupby(["spell", "cls", "cause"]).lost_mw.sum().reset_index().sort_values("lost_mw", ascending=False)
    top = by.drop_duplicates("spell").set_index("spell")[["cls", "cause"]]
    rs = d.dropna(subset=["reason"]).groupby("spell").agg(reason=("reason", "first"), lead_h=("lead_h", "first"))
    out = out.join(top).join(rs)
    out["end"] = out.end + pd.Timedelta(hours=1)
    return out.reset_index(drop=True)


def dose(pt: pd.DataFrame) -> pd.DataFrame:
    """firm, utc, cls, lost_mw: each owner's share of the lost output, owners in force that day."""
    x = pt[["unit", "utc", "cls", "lost_mw"]].copy()
    x["date"] = x.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    a = attach_owners(x, spells(), value_cols=("lost_mw",))
    return a.rename(columns={"group": "firm"}).groupby(["firm", "utc", "cls"], as_index=False).lost_mw.sum()


def report(h: pd.DataFrame, pt: pd.DataFrame, s: pd.DataFrame, dz: pd.DataFrame) -> None:
    yr = h.utc.dt.year
    lost = pt
    print("LOST OUTPUT by class and year, TWh")
    print((lost.groupby([lost.utc.dt.year, "cls"]).lost_mw.sum().unstack().fillna(0) / 1e6).round(2).to_string())
    print(f"\nlost share of capacity, all hours: {h.lost_mw.sum() / h.cap_mw.sum():.3f}  "
          f"(years: {', '.join(f'{y} {g.lost_mw.sum() / g.cap_mw.sum():.2f}' for y, g in h.groupby(yr))})")
    print("\nOUTAGE SPELLS (>= 50% lost) by class: count, median hours, median lead (h from first sight)")
    print(s.groupby("cls").agg(spells=("hours", "size"), median_hours=("hours", "median"),
                                gwh=("lost_gwh", "sum"), median_lead_h=("lead_h", "median")).round(1).to_string())
    print("\nspells by cause:")
    print(s.groupby(["cls", "cause"]).agg(spells=("hours", "size"), gwh=("lost_gwh", "sum")).round(0).to_string())
    print("\nunplanned and weather spells by year:")
    u = s[s.cls.isin(["unplanned", "weather"])]
    print(u.groupby([u.start.dt.year, "cls"]).size().unstack().fillna(0).astype(int).to_string())
    w = dz.pivot_table(index="utc", columns=["cls", "firm"], values="lost_mw", aggfunc="sum").fillna(0)
    for cls in ("unplanned", "planned"):
        if cls in w.columns.get_level_values(0):
            c = w[cls]
            c = c[[f for f in ("ENDESA", "IBERDROLA", "NATURGY", "EDP") if f in c.columns]]
            print(f"\n{cls} dose, MW: mean by firm {c.mean().round(1).to_dict()}; hourly correlation across firms:")
            print(c.corr().round(2).to_string())


def timing(s: pd.DataFrame) -> None:
    """Are unplanned outages timed on prices? Price on the start day against its month x hour mean."""
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["utc_timestamp", "price_es"])
    px["utc"] = pd.to_datetime(px.utc_timestamp, utc=True).dt.floor("h")
    px = px.groupby("utc").price_es.mean().rename("p").reset_index()
    px["ym"] = px.utc.dt.strftime("%Y%m")
    px["hr"] = px.utc.dt.hour
    px["dev"] = px.p - px.groupby(["ym", "hr"]).p.transform("mean")
    dev = px.set_index("utc").dev
    print("\nTIMING: price at the spell's start hour minus its month x hour mean, EUR/MWh")
    for cls, g in s.groupby("cls"):
        v = dev.reindex(g.start.dt.floor("h")).dropna()
        if len(v) >= 5:
            print(f"  {cls:12s} n={len(v):3d}  mean {v.mean():+6.2f}  se {v.std() / np.sqrt(len(v)):5.2f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="re-check the stored outputs")
    args = ap.parse_args()
    if args.verify:
        h, dz = pd.read_parquet(OUT_HOURS), pd.read_parquet(OUT_DOSE)
        tot_h = h.lost_mw.sum()
        tot_d = dz.lost_mw.sum()
        assert abs(tot_h - tot_d) / tot_h < 1e-6, f"dose does not add up to the lost output ({tot_d} vs {tot_h})"
        assert (h.lost_mw <= h.cap_mw + 1e-6).all() and (h.lost_mw >= 0).all(), "lost output outside [0, cap]"
        assert (abs(h.lost_decl_mw + h.lost_undecl_mw - h.lost_mw) < 1e-6).all(), "parts do not add up"
        assert h[h.lost_decl_mw > 0].cls.notna().all(), "a declared part without a class"
        print("--verify passed")
        return 0
    sched = schedule()
    sched["month"] = sched.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.to_period("M")
    h = sched.merge(capacity(), on=["unit", "month"], how="left")
    h["cap_mw"] = h.groupby("unit").cap_mw.transform(lambda x: x.ffill().bfill())
    short = (h.cap_mw - h.sched_mw).clip(lower=0)
    h["lost_mw"] = short.where(short > MIN_LOSS * h.cap_mw, 0.0)
    dec, covered = declarations()
    h = assign(h.drop(columns=["month"]), dec, covered)
    pt = parts(h)
    s = spell_table(h, pt)
    dz = dose(pt)
    TABLES.mkdir(parents=True, exist_ok=True)
    h.drop(columns=["run"]).to_parquet(OUT_HOURS, index=False)
    dz.to_parquet(OUT_DOSE, index=False)
    s.to_csv(OUT_SPELLS, index=False)
    print(f"{len(h):,} reactor-hours, {h.utc.min()} -> {h.utc.max()}; {len(dec)} declarations; "
          f"{len(s)} spells\n")
    report(h, pt, s, dz)
    timing(s)
    print(f"\nwrote {OUT_HOURS.relative_to(ROOT)}, {OUT_DOSE.relative_to(ROOT)}, {OUT_SPELLS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
