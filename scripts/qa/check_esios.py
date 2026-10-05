#!/usr/bin/env python3
"""ESIOS: REE's day-ahead forecasts and installed capacity -- the fetcher and the data.

    .venv/bin/python scripts/qa/check_esios.py

Checks `fetch/fetch_esios_spain.py`:
  - indicator ids resolve by exact catalogue name, and a renamed id fails loudly
    (541/542 are rolling forecasts and must not slip in);
  - a payload parses to UTC timestamps, and an empty one to an empty frame;
  - a cached chunk is not requested again once complete, a chunk still growing
    is, and a refused request raises rather than leaving a hole; monthly
    aggregates are cached apart from native values;
  - forecasts (--forecasts): every day from 2019-01-01 present with 23/24/25
    hours, and each tracks REE's realised 5-minute series;
  - capacity (--capacity): every month from 2015-01 present, the technologies
    except pure pumped storage sum to the total, and realised output never exceeds
    capacity (nuclear, which runs flat out, reaches it).
Exits non-zero on any failure.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "fetch"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from fetch_esios_spain import (  # noqa: E402
    CAPACITY, CAPACITY_OUT, CAPACITY_START, FORECAST_START, FORECASTS, NON_PENINSULAR, OUT, chunk_is_final,
    fetch_indicator, month_chunks, parse_payload, resolve_ids, search_catalogue, year_chunks,
)
from omie_common import day_span_utc  # noqa: E402

REALTIME = ROOT / "data/ree/ree_realtime_5min.parquet"
# realtime column each forecast is compared with; minimum hourly correlation
REALISED = {1775: ("demand", 0.95), 1777: ("wind", 0.90), 1779: ("solar_pv", 0.90)}
# before REE's realtime contract change on 2025-12-12, which altered the actuals
COMPARE_END = "2025-12-11"
# capacity indicator -> realtime output column, for the output <= capacity test
CAPACITY_OUTPUT = {1477: "nuclear", 1485: "wind", 1486: "solar_pv", 1483: "combined_cycle"}
TECHNOLOGIES = range(1475, 1492)
TOTAL = 10300
PUMPED = 1476


def payload(ind_id: int, days: list[date]) -> dict:
    """An ESIOS-shaped payload with hourly values over whole local days (CET)."""
    vals = []
    for d in days:
        for h in range(24):
            utc = pd.Timestamp(d) + pd.Timedelta(hours=h - 1)
            vals.append({"value": float(h), "datetime": f"{d}T{h:02d}:00:00.000+01:00",
                         "datetime_utc": f"{utc:%Y-%m-%dT%H:%M:%S}Z", "geo_id": 8741,
                         "geo_name": "Península"})
    return {"indicator": {"id": ind_id, "name": FORECASTS.get(ind_id, "x"), "values": vals}}


def monthly(ind_id: int, months: list[str], geos=(4, 5)) -> dict:
    """A monthly-aggregated payload: one value per month and region, stamped on the 1st."""
    vals = [{"value": 100.0, "datetime": f"{m[:4]}-{m[4:]}-01T00:00:00.000+01:00",
             "datetime_utc": f"{pd.Timestamp(m[:4] + '-' + m[4:] + '-01') - pd.Timedelta(hours=1):%Y-%m-%dT%H:%M:%S}Z",
             "geo_id": g, "geo_name": str(g)} for m in months for g in geos]
    return {"indicator": {"id": ind_id, "name": "x", "values": vals}}


class FakeSession:
    """Serves `body` for every request and counts the requests made."""

    def __init__(self, body: dict, status: int = 200):
        self.body, self.status, self.calls, self.params = body, status, 0, []

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        self.params.append(params)
        body, status = self.body, self.status

        class R:
            status_code = status
            text = json.dumps(body)[:200]

            def json(self):
                return body
        return R()


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    # --- the fetcher, without the network -----------------------------------
    cat = pd.DataFrame({"id": [541, 1775, 1777, 1779],
                        "name": ["Previsión de la producción eólica peninsular", *FORECASTS.values()],
                        "description": [None, "D+1", None, "D+1"]})
    check(resolve_ids(cat, FORECASTS) == [1775, 1777, 1779], "forecast ids resolve to 1775/1777/1779")
    renamed = cat.assign(name=cat.name.where(cat.id != 1777, "Previsión de la producción eólica peninsular"))
    try:
        resolve_ids(renamed, FORECASTS)
        check(False, "an id whose catalogue name changed raises")
    except ValueError:
        check(True, "an id whose catalogue name changed raises")
    check(list(search_catalogue(cat, "previsi").id) == [541, 1775, 1777, 1779],
          "search runs over empty descriptions")

    p = parse_payload(payload(1777, [date(2024, 1, 15)]))
    check(len(p) == 24 and p.utc_timestamp.iloc[0] == pd.Timestamp("2024-01-14 23:00", tz="UTC"),
          "payload parses: 24 rows, local midnight CET -> 23:00 UTC the day before")
    check(set(p.indicator_id) == {1777} and p.indicator_name.iloc[0] == FORECASTS[1777],
          "payload parses: indicator id and name carried")
    e = parse_payload({"indicator": {"id": 1777, "name": "x", "values": []}})
    check(e.empty and "utc_timestamp" in e.columns, "an empty payload parses to an empty frame")

    check(month_chunks(date(2019, 1, 15), date(2019, 2, 3))
          == [("201901", date(2019, 1, 1), date(2019, 1, 31)), ("201902", date(2019, 2, 1), date(2019, 2, 28))],
          "month chunks are whole calendar months")
    check(year_chunks(date(2015, 3, 1), date(2016, 5, 1))
          == [("2015", date(2015, 1, 1), date(2015, 12, 31)), ("2016", date(2016, 1, 1), date(2016, 12, 31))],
          "year chunks are whole calendar years, also the current one")

    jan = [date(2019, 1, d) for d in range(1, 32)]
    end_jan = date(2019, 1, 31)
    check(chunk_is_final(payload(1777, jan), end_jan, date(2019, 2, 2)),
          "a month covering its last day is final")
    check(not chunk_is_final(payload(1777, jan[:10]), end_jan, date(2019, 1, 10)),
          "a month fetched mid-month is not final")
    check(chunk_is_final(payload(1777, jan[:10]), end_jan, date(2020, 1, 1)),
          "a short month fetched long after it closed is final")
    months24 = [f"2024{m:02d}" for m in range(1, 13)]
    check(chunk_is_final(monthly(1485, months24), date(2024, 12, 31), date(2025, 1, 5), trunc="month"),
          "a monthly year reaching December is final")
    check(not chunk_is_final(monthly(1485, months24[:10]), date(2024, 12, 31), date(2024, 10, 2), trunc="month"),
          "a monthly year that stops in October is not final")

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp)
        jan_chunk = month_chunks(date(2019, 1, 1), date(2019, 1, 1))
        s = FakeSession(payload(1777, jan))
        d1 = fetch_indicator(s, 1777, jan_chunk, 8741, raw_dir=raw, today=date(2019, 2, 2))
        d2 = fetch_indicator(s, 1777, jan_chunk, 8741, raw_dir=raw, today=date(2019, 2, 3))
        check(s.calls == 1 and len(d1) == len(d2) == 31 * 24,
              "a complete cached month is not requested again")
        g = FakeSession(payload(1777, jan[:10]))
        fetch_indicator(g, 1777, jan_chunk, 8741, raw_dir=raw / "g", today=date(2019, 1, 10))
        fetch_indicator(g, 1777, jan_chunk, 8741, raw_dir=raw / "g", today=date(2019, 1, 11))
        check(g.calls == 2, "a month still growing is requested again")
        fetch_indicator(g, 1777, jan_chunk, 8741, raw_dir=raw / "g", today=date(2019, 1, 11))
        check(g.calls == 2, "but not twice on the same day")
        try:
            fetch_indicator(FakeSession({}, status=403), 1777, month_chunks(date(2019, 2, 1), date(2019, 2, 1)),
                            8741, raw_dir=raw, today=date(2019, 3, 2))
            check(False, "a refused request raises")
        except RuntimeError:
            check(True, "a refused request raises")
        check(not (raw / "1777" / "201902.json").exists(), "a refused request caches nothing")

        m = FakeSession(monthly(1485, months24))
        c = fetch_indicator(m, 1485, year_chunks(date(2024, 1, 1), date(2024, 1, 1)), None,
                            trunc="month", raw_dir=raw, today=date(2025, 1, 5))
        check((raw / "1485" / "month" / "2024.json").exists() and not (raw / "1485" / "2024.json").exists(),
              "monthly aggregates are cached apart from native values")
        check(m.params[0].get("time_trunc") == "month" and "geo_ids[]" not in m.params[0],
              "a monthly request asks for time_trunc=month and no region filter")
        check(len(c) == 24 and c.groupby("geo_id").size().eq(12).all(),
              "regions are kept apart, not dropped as duplicates")

        z = FakeSession(payload(1159, jan))
        zd = fetch_indicator(z, 1159, jan_chunk, None, raw_dir=raw, today=date(2019, 2, 2), gz=True)
        zd2 = fetch_indicator(z, 1159, jan_chunk, None, raw_dir=raw, today=date(2019, 2, 3), gz=True)
        check((raw / "1159" / "201901.json.gz").exists() and not (raw / "1159" / "201901.json").exists()
              and z.calls == 1 and len(zd) == len(zd2) == 31 * 24,
              "a gzipped cache is written, read back, and not requested again")

    # --- the forecasts --------------------------------------------------------
    rt = None
    if REALTIME.exists():
        rt = pd.read_parquet(REALTIME, columns=["utc_timestamp", "demand", "wind", "solar_pv",
                                                "nuclear", "combined_cycle"])
    rt_h = None
    if rt is not None:
        rt_h = rt[rt.utc_timestamp < pd.Timestamp(COMPARE_END, tz="UTC") + pd.Timedelta(days=1)]
        rt_h = rt_h.groupby(rt_h.utc_timestamp.dt.floor("h")).mean()  # MW averaged over the hour = MWh
    for ind_id, name in FORECASTS.items():
        path = OUT / f"esios_{ind_id}.parquet"
        if not path.exists():
            check(False, f"{path.relative_to(ROOT)} missing -- run fetch_esios_spain.py --forecasts")
            continue
        d = pd.read_parquet(path)
        print(f"[{ind_id}] {name}: {len(d):,} rows, {d.utc_timestamp.min()} -> {d.utc_timestamp.max()}")
        check(not d.utc_timestamp.duplicated().any(), f"{ind_id}: no duplicate hour")
        local = d.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.date
        last = local.max() - timedelta(days=1)  # the frontier day may be partial
        days = pd.date_range(FORECAST_START, last).date
        n = local.value_counts()
        missing = [x for x in days if x not in n.index]
        check(not missing, f"{ind_id}: every day {FORECAST_START} -> {last} present "
                           f"(missing {len(missing)}: {missing[:5]})")
        want = {x: int((day_span_utc(x)[1] - day_span_utc(x)[0]).total_seconds() // 3600) for x in days}
        bad = [x for x in days if x in n.index and n[x] != want[x]]
        check(not bad, f"{ind_id}: hours per day match the local day, 23/24/25 "
                       f"(wrong on {len(bad)}: {[(x, n[x], want[x]) for x in bad[:3]]})")
        check(bool((d.value >= 0).all()), f"{ind_id}: no negative forecast")
        if rt_h is not None:
            col, min_r = REALISED[ind_id]
            j = d.set_index("utc_timestamp").value.to_frame("f").join(rt_h[col].rename("r"), how="inner").dropna()
            r = float(np.corrcoef(j.f, j.r)[0, 1])
            ratio = float(j.f.mean() / j.r.mean())
            print(f"      vs realised {col}: {len(j):,} hours, corr {r:.3f}, mean forecast / realised {ratio:.3f}")
            check(r >= min_r, f"{ind_id}: hourly correlation with realised {col} >= {min_r}")
            check(0.8 <= ratio <= 1.2, f"{ind_id}: mean forecast within 20% of realised {col}")

    # --- installed capacity ---------------------------------------------------
    if not CAPACITY_OUT.exists():
        check(False, f"{CAPACITY_OUT.relative_to(ROOT)} missing -- run fetch_esios_spain.py --capacity")
    else:
        k = pd.read_parquet(CAPACITY_OUT)
        k["month"] = k.datetime.str[:7]
        print(f"[capacity] {len(k):,} rows, {k.indicator_id.nunique()} indicators, "
              f"{k.month.min()} -> {k.month.max()}, {k.geo_id.nunique()} regions")
        check(set(k.indicator_id) == set(CAPACITY), "every capacity indicator present")
        check(not k.duplicated(["indicator_id", "month", "geo_id"]).any(), "no duplicate (indicator, month, region)")
        want_m = pd.period_range(f"{CAPACITY_START:%Y-%m}", k.month.max(), freq="M").astype(str)
        have = set(k.loc[k.indicator_id == TOTAL, "month"])
        miss = [x for x in want_m if x not in have]
        check(not miss, f"total capacity every month {CAPACITY_START:%Y-%m} -> {k.month.max()} (missing {miss[:5]})")
        nat = k.groupby(["indicator_id", "month"]).value.sum().unstack(0)
        # REE counts pure pumped storage (1476) as storage: it is in neither the
        # hydro figure (1475) nor the total. Adding it overstates the total by 3,331 MW.
        techs = nat[[c for c in TECHNOLOGIES if c in nat.columns and c != PUMPED]].sum(axis=1)
        gap = (techs / nat[TOTAL] - 1).abs()
        print(f"      technologies except pumped storage / total: max gap {gap.max():.5f}; total "
              f"{nat[TOTAL].iloc[0]:,.0f} MW ({nat.index[0]}) -> {nat[TOTAL].iloc[-1]:,.0f} MW ({nat.index[-1]}); "
              f"pumped storage {nat[PUMPED].iloc[-1]:,.0f} MW outside it")
        check(gap.max() <= 0.001, "the technologies except pumped storage sum to the total every month")
        if rt is not None:
            pen = k[~k.geo_id.isin(NON_PENINSULAR)].groupby(["indicator_id", "month"]).value.sum()
            out = rt.assign(month=rt.utc_timestamp.dt.tz_convert("Europe/Madrid").dt.strftime("%Y-%m"))
            out = out.groupby(out.utc_timestamp.dt.floor("h")).agg(
                month=("month", "first"), **{c: (c, "mean") for c in CAPACITY_OUTPUT.values()})
            for ind_id, col in CAPACITY_OUTPUT.items():
                peak = out.groupby("month")[col].max()
                cf = (peak / pen.xs(ind_id)).dropna()
                cf = cf[cf.index >= "2018-01"]
                yearly = cf.groupby(cf.index.str[:4]).max().round(3).to_dict()
                print(f"      {col}: highest hourly output / peninsular capacity, by year {yearly}")
                check(cf.max() <= 1.02, f"{ind_id} {col}: output never exceeds capacity")
            nuc = (out.groupby("month").nuclear.max() / pen.xs(1477)).dropna()
            nuc = nuc[nuc.index >= "2018-01"]
            check(nuc.quantile(0.9) >= 0.9, "nuclear reaches its capacity (90th pct month >= 0.9)")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
