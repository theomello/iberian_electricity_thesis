#!/usr/bin/env python3
"""REE's day-ahead forecasts from ESIOS: the fetcher, coverage, and fit to outcomes.

    .venv/bin/python scripts/qa/check_esios_forecasts.py

Checks `fetch/fetch_esios_spain.py --forecasts`:
  - the forecast ids resolve to the D+1 series by exact catalogue name, and a
    renamed id fails loudly (541/542 are rolling forecasts and must not slip in);
  - a payload parses to UTC timestamps, and an empty one to an empty frame;
  - a cached month is not requested again once it is complete, a month still
    growing is, and a refused request raises rather than leaving a hole;
  - every day from 2019-01-01 is present with 23/24/25 hours as the local day has;
  - each forecast tracks REE's realised 5-minute series (correlation and scale).
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
    FORECAST_START, FORECASTS, OUT, fetch_indicator, month_is_final, parse_payload,
    resolve_forecast_ids, search_catalogue,
)
from omie_common import day_span_utc  # noqa: E402

REALTIME = ROOT / "data/ree/ree_realtime_5min.parquet"
# realtime column each forecast is compared with; minimum hourly correlation
REALISED = {1775: ("demand", 0.95), 1777: ("wind", 0.90), 1779: ("solar_pv", 0.90)}
# before REE's realtime contract change on 2025-12-12, which altered the actuals
COMPARE_END = "2025-12-11"


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


class FakeSession:
    """Serves `body` for every request and counts the requests made."""

    def __init__(self, body: dict, status: int = 200):
        self.body, self.status, self.calls = body, status, 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
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

    cat = pd.DataFrame({"id": [541, 1775, 1777, 1779],
                        "name": ["Previsión de la producción eólica peninsular", *FORECASTS.values()],
                        "description": [None, "D+1", None, "D+1"]})
    check(resolve_forecast_ids(cat) == [1775, 1777, 1779], "forecast ids resolve to 1775/1777/1779")
    renamed = cat.assign(name=cat.name.where(cat.id != 1777, "Previsión de la producción eólica peninsular"))
    try:
        resolve_forecast_ids(renamed)
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

    jan = [date(2019, 1, d) for d in range(1, 32)]
    check(month_is_final(payload(1777, jan), "201901", date(2019, 2, 2)),
          "a month covering its last day is final")
    check(not month_is_final(payload(1777, jan[:10]), "201901", date(2019, 1, 10)),
          "a month fetched mid-month is not final")
    check(month_is_final(payload(1777, jan[:10]), "201901", date(2020, 1, 1)),
          "a short month fetched long after it closed is final")

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp)
        s = FakeSession(payload(1777, jan))
        d1 = fetch_indicator(s, 1777, ["201901"], 8741, raw_dir=raw, today=date(2019, 2, 2))
        d2 = fetch_indicator(s, 1777, ["201901"], 8741, raw_dir=raw, today=date(2019, 2, 3))
        check(s.calls == 1 and len(d1) == len(d2) == 31 * 24,
              "a complete cached month is not requested again")
        g = FakeSession(payload(1777, jan[:10]))
        fetch_indicator(g, 1777, ["201901"], 8741, raw_dir=raw / "g", today=date(2019, 1, 10))
        fetch_indicator(g, 1777, ["201901"], 8741, raw_dir=raw / "g", today=date(2019, 1, 11))
        check(g.calls == 2, "a month still growing is requested again")
        try:
            fetch_indicator(FakeSession({}, status=403), 1777, ["201902"], 8741, raw_dir=raw,
                            today=date(2019, 3, 2))
            check(False, "a refused request raises")
        except RuntimeError:
            check(True, "a refused request raises")
        check(not (raw / "1777" / "201902.json").exists(), "a refused request caches nothing")

    rt = None
    if REALTIME.exists():
        rt = pd.read_parquet(REALTIME, columns=["utc_timestamp", *[c for c, _ in REALISED.values()]])
        rt = rt[rt.utc_timestamp < pd.Timestamp(COMPARE_END, tz="UTC") + pd.Timedelta(days=1)]
        rt = rt.groupby(rt.utc_timestamp.dt.floor("h")).mean()  # MW averaged over the hour = MWh
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
        if rt is not None:
            col, min_r = REALISED[ind_id]
            j = d.set_index("utc_timestamp").value.to_frame("f").join(rt[col].rename("r"), how="inner").dropna()
            r = float(np.corrcoef(j.f, j.r)[0, 1])
            ratio = float(j.f.mean() / j.r.mean())
            print(f"      vs realised {col}: {len(j):,} hours, corr {r:.3f}, mean forecast / realised {ratio:.3f}")
            check(r >= min_r, f"{ind_id}: hourly correlation with realised {col} >= {min_r}")
            check(0.8 <= ratio <= 1.2, f"{ind_id}: mean forecast within 20% of realised {col}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
