#!/usr/bin/env python3
"""Two checks on leg B in levels: what makes β negative, and why storage takes the wrong sign.

    .venv/bin/python scripts/analysis/leg_b_levels.py --atcost         # the results checked here
    .venv/bin/python scripts/build/build_catchment_rain.py             # rain per plant catchment
    .venv/bin/python scripts/analysis/leg_b_water_checks.py [--hydro] [--thermal] [--storage]

`notes/rq-leg-b-levels.md` §5–§6.

1. THE NEGATIVE β (hydro, then thermal). With the at-cost instrument β is −0.22 across
days within a month, and the negative part comes from net sellers' steps. The candidate:
on wet or windy days a firm sells more zero-priced energy (run-of-river, wind), so its
net position n and X are high, and on the same days its water is worth less than λ*,
so its steps sit below λ*. Then e = λ − λ* falls as X rises and β is biased down. The
at-cost curve keeps that zero-priced volume, so Zb carries it too. If so, controlling for
it moves β up toward zero. Two controls, both known when offers close:
  V0     the firm's own sell offers at or below €1 in the hour, GW, less its storage and
         pumped hydro offered there (that part is a water-value choice, not weather):
         nuclear, wind, solar, run-of-river, cogeneration. From `own_` and `hydro_` caches.
  rain   rain over the catchments of the unit's own plants in the 90 (30) days to D−2,
         z-scored against 1991–2020 for the calendar month (`hydro_rain_catchment_first_stage
         .plant_z`), capacity-weighted over the unit's linked plants; and H90, the same
         over the firm's whole hydro fleet weighted by GW × ownership share (six firms).
The same V0 and H90 controls on the thermal step estimator (at-cost, unit × month).

2. THE STORAGE SIGN (the paper's method, §4). λ̂ on the forward and the fill anomaly gives
+0.9 €/MWh per 10 points of fill, where a water value should fall with storage. The fill
series are incomplete: MITECO is the whole demarcation (irrigation and supply dams with the
firm's), SNIRH only EDP's and Movhera's reservoirs, and 14 of the 28 units have no
storage series. Classical error in fill only shrinks the coefficient toward zero; it
cannot flip the sign, but error correlated with the water value can. Checks:
  - coverage by unit and source;
  - the fit by source (own reservoirs, SNIRH, against basin, MITECO) and with year effects;
  - rain instead of fill: complete for every unit, and not chosen by the firm;
  - fill instrumented by rain (90 and 365 days);
  - by year: λ̂ less its forward term, the fill anomaly, and when in the day storage sets
    the price (the forward is a baseload price);
  - the same on every day, not only price-setting hours: log(ocf / λ*30s), the offer at the
    expected running share (`water_value_forward_check.py`), within unit × calendar month.

Writes outputs/tables/leg_b_water_checks.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import hydro_rain_catchment_first_stage as hc  # noqa: E402
import leg_b_levels as lb  # noqa: E402
import step_estimator as st  # noqa: E402
import step_estimator_hydro as sh  # noqa: E402
from iv_two_endog import sw_f, tsls_k  # noqa: E402
from midday_hydro_iv import cluster_meat  # noqa: E402
from water_value_forward_check import offered  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
CACHE = ROOT / "outputs/cache/step"
OUT = TABLES / "leg_b_water_checks.csv"
ZERO = 1.0                                  # €/MWh: "zero-priced" offers
SIX = ["EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "MOVHERA"]


# ---------------------------------------------------------------- controls

def zero_volume() -> pd.DataFrame:
    """hid, group, V0 (GW): the group's own sell offers at ≤ ZERO, less its storage and pumped
    hydro offered there; V0_hy, that hydro part."""
    parts = []
    for f in sorted(CACHE.glob("own_2*.parquet")):
        ym = f.stem.split("_")[1]
        o = pd.read_parquet(f)
        v = o[o.price <= ZERO].groupby(["hid", "group"]).v_sell.sum().rename("v0_all")
        h = pd.read_parquet(CACHE / f"hydro_{ym}.parquet", columns=["hid", "group", "price", "mw", "withdrawn"])
        hy = h[~h.withdrawn & (h.price <= ZERO)].groupby(["hid", "group"]).mw.sum().rename("v0_hy")
        parts.append(pd.concat([v, hy], axis=1).fillna(0.0).reset_index())
    z = pd.concat(parts, ignore_index=True)
    z["V0"] = (z.v0_all - z.v0_hy).clip(lower=0) / 1000
    z["V0_hy"] = z.v0_hy / 1000
    return z[["hid", "group", "V0", "V0_hy"]]


def unit_rain(ks=(90, 30, 365)) -> pd.DataFrame:
    """unit, date, rain{k}: capacity-weighted catchment-rain z of the unit's linked plants,
    rain through D−2 (the z of D−1, which sums the k days before D−1)."""
    links = pd.read_parquet(DATA / "omie/registry/hydro_plant_units.parquet",
                            columns=["plant_id", "unit", "start", "end", "jrc_mw"])
    out = None
    for k in ks:
        z = hc.plant_z(k).rename_axis(index="date", columns="plant_id").stack().rename("z").reset_index()
        m = z.merge(links, on="plant_id")
        m = m[(m.date >= m.start) & (m.date < m.end)]
        m["wz"] = m.jrc_mw * m.z
        g = m.groupby(["unit", "date"])
        r = (g.wz.sum() / g.jrc_mw.sum()).rename(f"rain{k}").reset_index()
        r["date"] = r.date + pd.Timedelta(days=1)          # z of D−1 used for delivery day D
        out = r if out is None else out.merge(r, on=["unit", "date"], how="outer")
    return out


def firm_rain() -> pd.DataFrame:
    """group, date, H90: the firm's GW × share-weighted catchment-rain z (the first-stage
    index), taken on the Monday of the delivery day's week."""
    z = hc.plant_z(90)
    mondays = pd.DatetimeIndex(z.index[z.index.weekday == 0])
    h = hc.firm_index(z, hc.weights(mondays)).rename(columns={"firm": "group", "week": "monday", "H": "H90"})
    return h


def add_controls(d: pd.DataFrame, v0: pd.DataFrame, ur: pd.DataFrame | None, fr: pd.DataFrame) -> pd.DataFrame:
    d = d.merge(v0, on=["hid", "group"], how="left")
    d[["V0", "V0_hy"]] = d[["V0", "V0_hy"]].fillna(0.0)
    if ur is not None:
        d = d.merge(ur, on=["unit", "date"], how="left")
    d["monday"] = d.date - pd.to_timedelta(d.date.dt.weekday, unit="D")
    return d.merge(fr, on=["group", "monday"], how="left")


# ---------------------------------------------------------------- 1. the negative β

def fe_ols(s: pd.DataFrame, y: str, xs: list[str], fe, w: str = "m_n") -> tuple[np.ndarray, np.ndarray]:
    """Weighted least squares of y on xs with the fixed effects fe(s), week clusters."""
    s = s.dropna(subset=[y, *xs])
    wt = s[w].to_numpy(float)
    M = st.wdemean(s[[y, *xs]].to_numpy(float), fe(s), wt)
    r = np.sqrt(wt)
    Y, X = M[:, 0] * r, M[:, 1:] * r[:, None]
    inv = np.linalg.inv(X.T @ X)
    b = inv @ X.T @ Y
    V = inv @ cluster_meat(X, Y - X @ b, s.date.dt.strftime("%G%V").to_numpy()) @ inv
    return b, np.sqrt(np.diag(V))


def hydro_sign(d: pd.DataFrame) -> list[dict]:
    p = d[d.m_n > 0]
    um, ud = lb.UNIT_MONTH, lb.UNIT_DAY
    print("\nLINKS. Does water abundance move X and the gap? (unit × month, class × hour, class × position)")
    links = []
    for y, xs in [("Zb", ["V0"]), ("Xt", ["V0"]), ("Zb", ["rain90"]), ("Xt", ["rain90"]),
                  ("gap30", ["rain90"]), ("gap30", ["V0"]), ("V0", ["rain90"]), ("Zb", ["H90"])]:
        s = p[p.group.isin(SIX)] if "H90" in xs else p
        b, se = fe_ols(s.dropna(subset=[y, *xs, "Zb"]), y, xs, um)
        print(f"  {y:6s} on {xs[0]:7s}: {b[0]:+.3f} ({se[0]:.3f})")
        links.append({"part": "links", "sample": f"{y} on {xs[0]}", "b": b[0], "se": se[0]})

    print("\nTHE NEGATIVE β WITH CONTROLS (gap30 on X̃, at-cost instrument Zb)")
    res = []
    six = p[p.group.isin(SIX)]
    base = six.dropna(subset=["rain90", "H90"])
    for label, s, fe, y, ws in [
        ("unit × month | all | none", p, um, "gap30", ()),
        ("unit × month | all | V0", p, um, "gap30", ("V0",)),
        ("unit × month | six, rain linked | none", base, um, "gap30", ()),
        ("unit × month | six, rain linked | V0", base, um, "gap30", ("V0",)),
        ("unit × month | six, rain linked | unit rain 90, 30", base, um, "gap30", ("rain90", "rain30")),
        ("unit × month | six, rain linked | firm rain H90", base, um, "gap30", ("H90",)),
        ("unit × month | six, rain linked | V0 + rain + H90", base, um, "gap30", ("V0", "rain90", "rain30", "H90")),
        ("unit × day | all | none", p, ud, "price", ()),
        ("unit × day | all | V0", p, ud, "price", ("V0",)),
        ("unit | all | none", p, lb.UNIT, "gap30", ()),
        ("unit | all | V0", p, lb.UNIT, "gap30", ("V0",)),
        ("unit | six, rain linked | none", base, lb.UNIT, "gap30", ()),
        ("unit | six, rain linked | V0", base, lb.UNIT, "gap30", ("V0",)),
        ("unit | six, rain linked | unit rain 90, 30", base, lb.UNIT, "gap30", ("rain90", "rain30")),
        ("unit | six, rain linked | firm rain H90", base, lb.UNIT, "gap30", ("H90",)),
        ("unit | six, rain linked | V0 + rain + H90", base, lb.UNIT, "gap30", ("V0", "rain90", "rain30", "H90")),
        ("unit × month | 2021H2 – 2025-09 | none", p[p.date >= "2021-07-01"], um, "gap30", ()),
        ("unit × month | 2021H2 – 2025-09 | V0", p[p.date >= "2021-07-01"], um, "gap30", ("V0",)),
    ]:
        res.append(sh.est(s, label, ["Zb"], y=y, fe=fe, ws=ws) | {"part": "hydro"})
    for label, s, ws in [("two slopes | all | none", p, ()), ("two slopes | all | V0", p, ("V0",)),
                         ("two slopes | six, rain linked | V0 + rain + H90", base, ("V0", "rain90", "rain30", "H90"))]:
        res.append(sh.est(s, f"unit × month | {label}", ["Zbp", "Zbm"], xs2=("Xp", "Xm"), y="gap30", fe=um, ws=ws)
                   | {"part": "hydro"})
    return links + res


def thermal_sign(v0: pd.DataFrame, fr: pd.DataFrame) -> list[dict]:
    d = st.derive(st.instruments(pd.read_parquet(st.ROWS).drop(columns=st.INSTRUMENTS)))
    d = st.at_cost(d)
    d = add_controls(d, v0, None, fr)
    p = d[d.m_n > 0]
    five = p[p.five]
    print("\nTHERMAL: markup on X̃, at-cost instrument Zb (unit × month, fuel × hour, fuel × position)")
    b, se = fe_ols(p.dropna(subset=["Zb"]), "Zb", ["V0"], lambda s: st.fe_codes(s, "main"))
    print(f"  link Zb on V0: {b[0]:+.3f} ({se[0]:.3f})")
    res = [{"part": "thermal links", "sample": "thermal Zb on V0", "b": b[0], "se": se[0]}]
    for label, s, fe, ws in [
        ("unit × month | all | none", p, "main", ()),
        ("unit × month | all | V0", p, "main", ("V0",)),
        ("unit × month | five | none", five, "main", ()),
        ("unit × month | five | V0", five, "main", ("V0",)),
        ("unit × month | five | firm rain H90", five, "main", ("H90",)),
        ("unit × month | five | V0 + H90", five, "main", ("V0", "H90")),
        ("unit × day | all | none", p, "unitday", ()),
        ("unit × day | all | V0", p, "unitday", ("V0",)),
        ("fuel × date | all | none", p, "date", ()),
        ("fuel × date | all | V0", p, "date", ("V0",)),
    ]:
        res.append(st.est(s, "mk", "Xt", "m_n", f"thermal {label}", zs=("Zb",), fe=fe, ws=ws) | {"part": "thermal"})
    return res


# ---------------------------------------------------------------- 2. the storage sign

def fit(s: pd.DataFrame, y: str, xs: list[str], fes: list[str]) -> tuple[np.ndarray, np.ndarray, int]:
    """OLS with the named effects (unit, year), week clusters."""
    s = s.dropna(subset=[y, *xs])
    codes = [pd.factorize(s.unit if f == "unit" else s.date.dt.year)[0] for f in fes]
    M = st.wdemean(s[[y, *xs]].to_numpy(float), codes, np.ones(len(s)))
    Y, X = M[:, 0], M[:, 1:]
    inv = np.linalg.inv(X.T @ X)
    b = inv @ X.T @ Y
    V = inv @ cluster_meat(X, Y - X @ b, s.date.dt.strftime("%G%V").to_numpy()) @ inv
    return b, np.sqrt(np.diag(V)), len(s)


def fit_iv(s: pd.DataFrame, y: str, x: str, zs: list[str], ws: list[str]) -> dict:
    """2SLS of y on x instrumented by zs, controls ws, unit effects, week clusters."""
    s = s.dropna(subset=[y, x, *zs, *ws])
    M = st.wdemean(s[[y, x, *zs, *ws]].to_numpy(float), [pd.factorize(s.unit)[0]], np.ones(len(s)))
    L = len(zs)
    Y, X, Z, W = M[:, 0], M[:, [1]], M[:, 2:2 + L], M[:, 2 + L:]
    cl = s.date.dt.strftime("%G%V").to_numpy()
    b, V = tsls_k(Y, X, Z, W, cl)
    return {"b": b[0], "se": float(np.sqrt(V[0, 0])), "F": sw_f(X, Z, W, cl, 0), "n": len(s)}


def storage_sign(d: pd.DataFrame, ur: pd.DataFrame) -> list[dict]:
    r = d[(d.r_event == 1) & (d.cls == "hydro") & (d.r_s >= sh.FLOOR)].copy()
    r = r.drop_duplicates(["hid", "unit", "price"])
    r["lam1"] = r.r_p - r.r_n / r.r_s
    r = r.drop(columns=[c for c in r if c.startswith("rain")]).merge(ur, on=["unit", "date"], how="left")
    r["fill10"] = r.fill_anom * 10                            # per 10 points of fill
    print(f"\nTHE STORAGE SIGN: {len(r):,} price-setting storage hours, {r.unit.nunique()} units")
    cov = r.groupby(["group", "unit"]).agg(hours=("lam1", "size"), source=("storage", "first"),
                                           fill=("fill_anom", lambda x: x.notna().mean()),
                                           rain=("rain90", lambda x: x.notna().mean()))
    print("coverage (share of hours with a fill anomaly / with catchment rain):")
    print(cov.sort_values("hours", ascending=False).round(2).to_string())
    by_src = r.groupby(r.storage).lam1.size()
    print(f"hours by storage source: {by_src.to_dict()}")

    rows = []
    for g, x in [("all", r), *[(k, v) for k, v in r.groupby("group") if k in SIX]]:
        f = x.dropna(subset=["fwd", "fill10"])
        specs = [("fill, unit effects", f, ["fwd", "fill10"], ["unit"]),
                 ("fill, unit + year effects", f, ["fwd", "fill10"], ["unit", "year"]),
                 ("rain90, fill sample", f, ["fwd", "rain90"], ["unit"]),
                 ("rain90, every unit", x, ["fwd", "rain90"], ["unit"]),
                 ("rain365, every unit", x, ["fwd", "rain365"], ["unit"]),
                 ("rain90 + rain365, unit + year effects", x, ["fwd", "rain90", "rain365"], ["unit", "year"])]
        if g == "all":
            specs += [("fill, SNIRH units (own reservoirs)", f[f.storage == "snirh"], ["fwd", "fill10"], ["unit"]),
                      ("fill, MITECO units (basin)", f[f.storage == "miteco"], ["fwd", "fill10"], ["unit"])]
        for label, s, xs, fes in specs:
            s = s.dropna(subset=xs)
            if len(s) < 300:
                continue
            b, se, n = fit(s, "lam1", xs, fes)
            rows.append({"part": "storage", "group": g, "sample": label, "n": n, "units": s.unit.nunique(),
                         "b": b[1], "se": se[1], "b_fwd": b[0]} | ({"b2": b[2], "se2": se[2]} if len(b) > 2 else {}))
        if len(f.dropna(subset=["rain90", "rain365"])) >= 300:
            for zs in (["rain90"], ["rain90", "rain365"]):
                rows.append({"part": "storage", "group": g, "sample": f"fill instrumented by {' + '.join(zs)}"}
                            | fit_iv(f, "lam1", "fill10", zs, ["fwd"]))
        if len(f.dropna(subset=["rain90"])) >= 300:
            b, se, n = fit(f.dropna(subset=["rain90"]), "fill10", ["fwd", "rain90"], ["unit"])
            rows.append({"part": "storage", "group": g, "sample": "first stage: fill (10 pts) on rain90", "n": n,
                         "b": b[1], "se": se[1]})
    rows += by_year(r)
    t = pd.DataFrame([x for x in rows if x["part"] == "storage"])
    pd.set_option("display.width", 220)
    print("\nλ̂ (paper, β = 1) on the forward and water: coefficient on the water term (€/MWh per 10 points "
          "of fill, or per sd of rain)")
    print(t[["group", "sample", "n", "units", "b", "se", "F"] if "F" in t else ["group", "sample", "n", "b", "se"]]
          .round(2).to_string(index=False))
    return rows


def by_year(r: pd.DataFrame) -> list[dict]:
    """Year means, within unit, of λ̂ less its fitted forward term and of the fill anomaly;
    and when in the day storage hydro sets the price: the share of its hours at midday
    (10:00–16:59) and the price there over the day's mean (the forward is a baseload price)."""
    f = r.dropna(subset=["fwd", "fill10"]).copy()
    b_fwd = fit(f, "lam1", ["fwd", "fill10"], ["unit"])[0][0]
    f["res"] = f.lam1 - b_fwd * f.fwd
    for c in ("res", "fill10"):
        f[c] = f[c] - f.groupby("unit")[c].transform("mean")
    pr = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["date", "price_es"])
    pr["date"] = pd.to_datetime(pr.date)
    r = r.join(pr.groupby("date").price_es.mean().rename("day_mean"), on="date")
    hour = np.where(r.date >= "2025-10-01", (r.period - 1) // 4, r.period - 1)
    r = r.assign(year=r.date.dt.year, midday=(hour >= 10) & (hour <= 16),
                 rel=r.r_p / r.day_mean.where(r.day_mean > 5))
    a = f.assign(year=f.date.dt.year).groupby("year").agg(lam_less_fwd=("res", "mean"), fill10=("fill10", "mean"))
    b = r.groupby("year").agg(hours=("lam1", "size"), midday=("midday", "mean"), price_over_day_mean=("rel", "median"))
    t = b.join(a)
    print(f"\nby year (λ̂ less {b_fwd:.2f} × forward and fill, within unit; when storage hydro sets the price):")
    print(t.round(2).to_string())
    print(f"correlation of the year means of λ̂ less the forward term and fill: "
          f"{np.corrcoef(t.lam_less_fwd, t.fill10)[0, 1]:.2f}")
    return [{"part": "storage years", "group": "all", "sample": str(y)} | v for y, v in t.to_dict("index").items()]


def every_day(ur: pd.DataFrame) -> list[dict]:
    """log(ocf / λ*30s) on fill and on rain, every unit-day, within unit × calendar month."""
    w = pd.read_parquet(TABLES / "water_value_forward.parquet")
    w["date"] = pd.to_datetime(w.date)
    d = w[w.cls == "hydro"].merge(offered(w), on=["unit", "date"]).merge(ur, on=["unit", "date"], how="left")
    d = d[(d.ocf > 1) & (d.lam30s > 0)]
    d["gap"] = np.log(d.ocf / d.lam30s)
    d["fill10"] = d.fill_anom * 10
    rows = []
    print("\nEVERY DAY: log(ocf / λ*30s) within unit × calendar month (per 10 points of fill / per sd of rain)")
    for g, x in [("all", d), *[(k, v) for k, v in d.groupby("group") if k in SIX]]:
        for xv, smp, need in [("fill10", "fill", ["fill10"]), ("rain90", "rain90, fill sample", ["fill10", "rain90"]),
                              ("rain90", "rain90, every unit", ["rain90"]), ("rain365", "rain365, every unit", ["rain365"])]:
            s = x.dropna(subset=["gap", *need])
            if len(s) < 300:
                continue
            k = [s.unit, s.date.dt.month]
            a = s.gap - s.groupby(k).gap.transform("mean")
            f = s[xv] - s.groupby(k)[xv].transform("mean")
            b = float((a @ f) / (f @ f))
            u = a - b * f
            cl = s.date.dt.strftime("%G%V").to_numpy()
            meat = cluster_meat(f.to_numpy()[:, None], u.to_numpy(), cl)[0, 0]
            se = float(np.sqrt(meat) / (f @ f))
            rows.append({"part": "every day", "group": g, "sample": smp, "n": len(s), "units": s.unit.nunique(),
                         "b": b, "se": se})
            print(f"  {g:10s} {smp:22s} n={len(s):>6,} units {s.unit.nunique():>2}  {b:+.3f} ({se:.3f})")
    return rows


def main() -> int:
    args = set(sys.argv[1:]) or {"--hydro", "--thermal", "--storage"}
    v0 = zero_volume()
    fr = firm_rain()
    ur = unit_rain()
    print(f"V0: {len(v0):,} firm-hours, median {v0.V0.median():.2f} GW; unit rain: {ur.unit.nunique()} units; "
          f"firm rain: {fr.group.nunique()} firms")
    res = []
    if args & {"--hydro", "--storage"}:
        d = lb.at_cost(lb.load())
        d = add_controls(d, v0, ur, fr)
        if "--hydro" in args:
            res += hydro_sign(d)
        if "--storage" in args:
            res += storage_sign(d, ur) + every_day(ur)
    if "--thermal" in args:
        res += thermal_sign(v0, fr)
    new = pd.DataFrame(res)
    if OUT.exists():                        # a partial run replaces only its own parts
        old = pd.read_csv(OUT)
        new = pd.concat([old[~old.part.isin(new.part.unique())], new], ignore_index=True)
    new.to_csv(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
