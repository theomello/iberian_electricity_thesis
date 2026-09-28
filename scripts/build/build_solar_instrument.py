#!/usr/bin/env python3
"""Solar instruments for the midday-hydro design, one row per day-ahead period.

    .venv/bin/python scripts/build/build_solar_instrument.py

Writes `outputs/tables/solar_instrument.parquet`. Step 5 of
`notes/rq-midday-hydro.md`: the design instruments the firm's markup term
X = net / |RD'| with something that moves where residual demand meets the rival
stack but not the firm's own water value.

THREE CANDIDATES, BECAUSE THE FIXED EFFECTS DECIDE WHICH ONE IDENTIFIES

The design has unit-day (or day) and hour-by-month fixed effects. A
deterministic solar profile is almost entirely absorbed by those; what survives
of it is the profile times capacity GROWTH across years -- a slow trend, shared
with everything else that trends. Day-to-day solar weather survives them, and is
what should identify. So all three are built and the first stage decides:

* `z_clear`   -- clear-sky irradiance (Haurwitz model, own solar geometry) x
                 installed solar capacity. Astronomy and capacity only.
* `z_weather` -- ERA5 surface irradiance at the four `solar` sites of
                 `fetch_weather.py` x installed capacity. Realised weather.
* `z_offered` -- solar volume OFFERED in the day-ahead auction by solar-labelled
                 units, EDP's own excluded. Solar offers at ~0 EUR/MWh, so the
                 offered volume is the D-1 forecast as bid. Offered, not
                 cleared, because clearing depends on the price.

Also carried: `kt`, the clearness index (ERA5 / clear-sky, sun above
50 W/m^2), which is pure weather; and `solar_realised_mw` (REE Spain + REN
Portugal) as a check.

CAPACITY

No token-free source publishes Spain's installed solar (CLAUDE.md). The proxy is
the running maximum of REE's monthly peak 5-minute solar output, plus Portugal's
published installed solar (REN). A plain monthly maximum would carry the month's
weather into a capacity series; the running maximum only rises.

TIMING

OMIE's `utc_timestamp` is the START of a period. Open-Meteo's
`shortwave_radiation` is the mean over the PRECEDING hour. Each period is matched
to the ERA5 hour that contains it, and the alignment is tested against the
clear-sky model rather than assumed: the script checks that the "preceding
hour" reading fits the model better than the alternatives, and stops if not.

EXCLUSION, STATED NOT SOLVED

Sunny days are hotter, and heat raises cooling demand, which moves prices through
a channel other than solar output (`fetch_weather.py` says the same). Any use of
these instruments needs a demand control; the first stage uses REE's day-ahead
demand forecast.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_owner import owner_group  # noqa: E402

DATA = ROOT / "data"
OUT = ROOT / "outputs/tables/solar_instrument.parquet"
BIDS = DATA / "omie/bids/parquet"
SUN_UP = 50.0   # W/m^2 of clear-sky irradiance below which kt is undefined
EXCLUDE_OWNERS = {"EDP", "EDP COMERCIAL"}


def clear_sky_ghi(ts_utc: pd.DatetimeIndex, lat: float, lon: float) -> np.ndarray:
    """Haurwitz clear-sky GHI (W/m^2) from Spencer's declination and equation of time."""
    doy = ts_utc.dayofyear.to_numpy()
    hr = (ts_utc.hour + ts_utc.minute / 60 + ts_utc.second / 3600).to_numpy()
    g = 2 * np.pi / 365 * (doy - 1 + (hr - 12) / 24)
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g)
            - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g)
            - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    eot = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                    - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    tst = hr * 60 + eot + 4 * lon                       # true solar time, minutes
    omega = np.radians(tst / 4 - 180)
    phi = np.radians(lat)
    cosz = np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(omega)
    cosz = np.clip(cosz, 0, None)
    with np.errstate(divide="ignore", over="ignore"):
        ghi = np.where(cosz > 0.01, 1098 * cosz * np.exp(-0.057 / np.maximum(cosz, 0.01)), 0.0)
    return ghi


def hour_mean_clear_sky(hour_end: pd.DatetimeIndex, lat: float, lon: float,
                        offset_h: float = 0.0) -> np.ndarray:
    """Clear-sky mean over [end - 1h, end) shifted by offset_h, sampled every 5 minutes."""
    acc = np.zeros(len(hour_end))
    for k in range(12):
        t = hour_end - pd.Timedelta(minutes=57.5 - 5 * k) + pd.Timedelta(hours=offset_h)
        acc += clear_sky_ghi(t, lat, lon)
    return acc / 12


def weather_panel() -> pd.DataFrame:
    """Hourly ERA5 and clear-sky irradiance, mean over the solar sites, keyed on hour END."""
    w = pd.read_parquet(DATA / "weather/weather_spain_hourly.parquet")
    w = w[w.role == "solar"]
    w["ts"] = pd.to_datetime(w.utc_timestamp, utc=True)
    parts, fit = [], []
    for (pt, lat, lon), g in w.groupby(["point", "lat", "lon"]):
        idx = pd.DatetimeIndex(g.ts)
        cs = hour_mean_clear_sky(idx, lat, lon)
        parts.append(pd.DataFrame({"ts": idx, "point": pt, "ghi": g.shortwave_radiation.to_numpy(),
                                   "cs": cs}))
        # Timing test: which reading of the ERA5 stamp fits the clear-sky shape best?
        for off in (-1.0, -0.5, 0.0, 0.5, 1.0):
            c = hour_mean_clear_sky(idx, lat, lon, off)
            m = (c > SUN_UP) | (g.shortwave_radiation.to_numpy() > SUN_UP)
            fit.append((pt, off, np.corrcoef(c[m], g.shortwave_radiation.to_numpy()[m])[0, 1]))
    fit = pd.DataFrame(fit, columns=["point", "offset_h", "corr"])
    best = fit.groupby("offset_h")["corr"].mean()
    print("ERA5 timing test -- mean correlation with clear-sky, by shift of the model (hours):")
    print(best.round(4).to_string())
    if best.idxmax() != 0.0:
        raise SystemExit(f"ERA5 fits the clear-sky model best at an offset of {best.idxmax()} h, "
                         "not as a preceding-hour mean -- fix the timing before using this.")
    p = pd.concat(parts)
    return p.groupby("ts")[["ghi", "cs"]].mean()


def capacity_proxy() -> pd.Series:
    """Monthly solar capacity proxy (MW): running max of REE's peak output + REN's PT installed."""
    r = pd.read_parquet(DATA / "ree/ree_realtime_5min.parquet", columns=["local_date", "solar_total"])
    r["m"] = pd.to_datetime(r.local_date).dt.to_period("M")
    es = r.groupby("m").solar_total.max().cummax()
    ip = pd.read_parquet(DATA / "ren/ren_installed_power_monthly.parquet")
    ip = ip[ip.type == "SOLAR"]
    pt = pd.Series(ip.value.to_numpy(), index=pd.PeriodIndex(
        [pd.Period(year=y, month=m, freq="M") for y, m in zip(ip.year, ip.month)]))
    pt = pt.reindex(es.index).ffill()
    return (es + pt.fillna(0.0)).rename("cap_mw")


def realised_solar(periods: pd.DataFrame) -> pd.Series:
    """REE Spain + REN Portugal solar, mean MW over each period."""
    r = pd.read_parquet(DATA / "ree/ree_realtime_5min.parquet", columns=["utc_timestamp", "solar_total"])
    r["ts"] = pd.to_datetime(r.utc_timestamp, utc=True)
    n = pd.read_parquet(DATA / "ren/ren_production_15min.parquet", columns=["utc_timestamp", "series", "value_mw"])
    n = n[n.series == "Solar"]
    n["ts"] = pd.to_datetime(n.utc_timestamp, utc=True)
    out = []
    for res, g in periods.groupby("resolution_min"):
        f = f"{res}min"
        es = r.set_index("ts").solar_total.resample(f).mean()
        pt = n.set_index("ts").value_mw.resample(f).mean()
        s = es.add(pt, fill_value=0.0)
        out.append(pd.Series(s.reindex(pd.DatetimeIndex(g.start)).to_numpy(), index=g.index))
    return pd.concat(out).rename("solar_realised_mw")


def offered_solar() -> pd.DataFrame:
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                        columns=["unit", "role", "tech", "tech_omie", "tech_omie_early", "agent_owner"])
    label = u.tech_omie.fillna(u.tech_omie_early).fillna(u.tech)
    own = u.agent_owner.map(owner_group)
    keep = (label == "solar") & ~u.role.str.startswith("purchase") & ~own.isin(EXCLUDE_OWNERS)
    units = sorted(u[keep].unit)
    print(f"z_offered: {len(units)} solar-labelled supply units, EDP-owned excluded")
    parts = []
    for f in sorted(BIDS.glob("bids_*.parquet")):
        b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw"],
                          filters=[("unit", "in", units), ("side", "==", "V"),
                                   ("status", "==", "O")]).to_pandas()
        parts.append(b.groupby(["date", "period"]).power_mw.sum().rename("z_offered").reset_index())
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    return d


def main() -> int:
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "utc_timestamp", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    px["start"] = pd.to_datetime(px.utc_timestamp, utc=True)
    px["end"] = px.start + pd.to_timedelta(px.resolution_min, unit="min")
    # The ERA5 hour containing the period: stamped at the first full hour >= end.
    px["era5_ts"] = px.end.dt.ceil("h")

    w = weather_panel()
    d = px.merge(w, left_on="era5_ts", right_index=True, how="left")
    d["kt"] = np.where(d.cs > SUN_UP, d.ghi / d.cs, np.nan)

    cap = capacity_proxy()
    d["cap_mw"] = d.date.dt.to_period("M").map(cap)
    d["z_clear"] = d.cs / 1000 * d.cap_mw
    d["z_weather"] = d.ghi / 1000 * d.cap_mw
    d["solar_realised_mw"] = realised_solar(d)
    d = d.merge(offered_solar(), on=["date", "period"], how="left")

    cols = ["date", "period", "resolution_min", "utc_timestamp", "cs", "ghi", "kt", "cap_mw",
            "z_clear", "z_weather", "z_offered", "solar_realised_mw"]
    d = d[cols]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)

    print("\nCHECKS")
    print(f"  periods: {len(d):,}; ghi defined {d.ghi.notna().mean():.3f}; "
          f"z_offered defined {d.z_offered.notna().mean():.3f}")
    day = d[d.cs > SUN_UP]
    print("  correlation with realised solar, sun-up periods:")
    for c in ("z_clear", "z_weather", "z_offered"):
        ok = day[[c, "solar_realised_mw"]].dropna()
        print(f"    {c:10s} {np.corrcoef(ok[c], ok.solar_realised_mw)[0, 1]:.3f}")
    print("  capacity proxy, MW, June of each year:",
          {p.year: int(v) for p, v in cap.items() if p.month == 6})
    print("  kt quantiles (sun up):", day.kt.quantile([.1, .5, .9]).round(2).to_dict())
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
