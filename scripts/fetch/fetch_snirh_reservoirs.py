#!/usr/bin/env python3
"""Portuguese hydro reservoirs from SNIRH: volume, level and daily flows.

    .venv/bin/python scripts/fetch/fetch_snirh_reservoirs.py              # fetch missing + parse
    .venv/bin/python scripts/fetch/fetch_snirh_reservoirs.py --force      # re-fetch every station
    .venv/bin/python scripts/fetch/fetch_snirh_reservoirs.py --parse-only # rebuild parquet from raw

Writes data/snirh/snirh_reservoir_series.parquet (long: one row per station,
timestamp and parameter) and keeps each station's raw CSV under data/snirh/raw/.

ACCESS -- RUNS ONLY FROM ONE ADDRESS

SNIRH (snirh.apambiente.pt, APA's water-resources information system) refuses
every request from outside Portugal: APA's security officer says it runs on
1990s technology that cannot be patched. On 2026-09-30 APA whitelisted
194.95.236.6, the IPv4 exit of LMU's eduVPN (DFN), knowing it is shared
(`notes/email-apa-reservoir-data.md`). So:

  - connect LMU eduVPN first; the script checks the exit address and refuses
    to send anything to SNIRH from any other one;
  - it sends one request per station, sequentially, DELAY seconds apart;
  - never route around the block from elsewhere (a Portuguese VPN): it is a
    security control APA has explained.

This is the one fetcher in the repo that cannot run from an arbitrary network.
Keep data/snirh/raw/ -- it is the only copy that does not need the whitelist.

WHAT IT FETCHES

For each station below, from 2018-01-01 to today, the SNIRH "dados de base"
CSV export (`paraCSV/dados_csv.php`) of eight parameters. Each station is a
reservoir gauge marked "(R.E.)"; the flows are the dam's own, so turbined flow
is the plant's generation water and inflow is the water arriving from upstream.

    volume_dam3            Volume armazenado (convencional)     weekly, dam3 = 1e3 m3
    volume_month_end_dam3  Volume armazenado mensal (final do mes)
    level_m                Cota da albufeira                    hourly in some years
    inflow_m3s             Caudal afluente medio diario         daily
    turbined_m3s           Caudal turbinado medio diario        daily
    pumped_m3s             Caudal bombeado medio diario         daily, pumped plants
    spilled_m3s            Caudal descarregado medio diario     daily
    outflow_m3s            Caudal efluente medio diario         daily

A parameter a station does not record comes back as an empty column; an empty
cell is missing, not zero. Columns are mapped by their header text, and an
unknown header is an error, so a renamed parameter fails loudly.

TIME

Timestamps are Lisbon local time (WET/WEST), one hour behind Madrid. The spring
day skips 01:00 and the autumn repeated hour appears ONCE (checked on Alto
Lindoso, 2018). `time_utc` assigns that hour to its first (summer-time) pass,
which is a guess the file does not settle. Daily values are stamped 00:00 of
their day; the weekly volume is stamped 23:00, mostly on Mondays or Fridays.

SUSPECT VALUES -- FLAGGED, NOT CHANGED

`suspect` marks two faults found on the first fetch (2026-09-30), both in the
source (the raw CSVs carry them):

  1. PUMPED FLOW IN THE WRONG UNITS. At Alto Rabagao, Venda Nova, Torrao and
     Aguieira, pumped flow reads 43,000-63,000 on 2023-04-01..08-01 and in
     January 2026, while every other flow at those stations reads 0 on the same
     days. That looks like l/s, or another series, filed as m3/s. Every flow of
     a station-day with pumped flow above PUMP_MAX is flagged.
  2. ONE-DAY INFLOW SPIKES, e.g. ~2,340 m3/s at Baixo Sabor, Feiticeiro and Foz
     Tua on 2025-10-03 between days of 5-70. Reservoir inflow looks derived from
     the water balance, so one bad volume reading makes a spike. Flagged when
     inflow exceeds SPIKE_MIN and SPIKE_RATIO times the median of the three days
     either side, and outflow that day is below SPIKE_PASS of it. Real floods
     ramp over days (the Douro in December 2019 and February 2026 grows station
     by station downstream), and one that rises in a day passes through a
     run-of-river dam (Belver, 2019-12-20: outflow = inflow, Fratel upstream
     high too). A storm a storage reservoir absorbs in one day would still be
     flagged; `suspect` means "check", not "wrong".

The weekly volume closes the water balance well only at large single
reservoirs (weekly correlation 0.8-0.9 at Alto Lindoso, Paradela, Pracana).
At run-of-river dams the weekly change is small against the volume's own
rounding, and pumped-storage pairs move water between two gauges.

STATIONS

Resolved 2026-09-30 from SNIRH's station search ("ALBUFEIRA", hydrometric
network): EDP's and Movhera's cascades mapped in `build_storage_hours.py`, plus
Iberdrola's Tamega scheme, which that map does not cover. `24M/08A` "Alqueva
jusante" is taken to be Pedrogao, the re-regulating dam below Alqueva; no
station carries Pedrogao's own name.
"""
from __future__ import annotations

import io
import sys
import time
from argparse import ArgumentParser
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "data" / "snirh"
RAW = OUT_DIR / "raw"
OUT = OUT_DIR / "snirh_reservoir_series.parquet"

WHITELISTED_IP = "194.95.236.6"
IP_CHECK = "https://api.ipify.org"
URL = "https://snirh.apambiente.pt/snirh/_dadosbase/site/paraCSV/dados_csv.php"
START = "01/01/2018"
DELAY = 5.0   # seconds between requests to SNIRH
PUMP_MAX = 1000.0                 # m3/s; no Portuguese pump comes close
SPIKE_MIN, SPIKE_RATIO, SPIKE_PASS = 500.0, 10.0, 0.5
FLOWS = ["inflow_m3s", "turbined_m3s", "pumped_m3s", "spilled_m3s", "outflow_m3s"]

# SNIRH parameter id -> (short name, header text in the CSV export)
PARAMS = {
    1866: ("volume_dam3", "Volume armazenado (convencional) (dam3)"),
    304545050: ("volume_month_end_dam3", "Volume armazenado mensal (final do mês) (dam3)"),
    1629599726: ("level_m", "Cota da albufeira (m)"),
    2279: ("inflow_m3s", "Caudal afluente médio diário (m3/s)"),
    2282: ("turbined_m3s", "Caudal turbinado médio diário (m3/s)"),
    827282598: ("pumped_m3s", "Caudal bombeado médio diário (m3/s)"),
    2284: ("spilled_m3s", "Caudal descarregado médio diário (m3/s)"),
    212296818: ("outflow_m3s", "Caudal efluente médio diário (m3/s)"),
}
HEADER_TO_PARAM = {h: p for p, h in PARAMS.values()}

# (code, SNIRH site id, name, basin)
STATIONS = [
    ("02H/01A", 1627743428, "Alto Lindoso", "Lima"),
    ("03G/01A", 1627759476, "Touvedo", "Lima"),
    ("03J/03A", 1627743430, "Alto Rabagão", "Cávado"),
    ("03J/01A", 1627758928, "Paradela", "Cávado"),
    ("03J/04A", 1627759522, "Venda Nova", "Cávado"),
    ("03J/05A", 1627759524, "Venda Nova Frades", "Cávado"),
    ("03I/04A", 12303382358, "Venda Nova Frades II", "Cávado"),
    ("03H/01A", 1627759560, "Vilarinho das Furnas", "Cávado"),
    ("03I/01A", 1627759378, "Salamonde", "Cávado"),
    ("04H/01A", 1627743674, "Caniçada", "Cávado"),
    ("05T/01A", 1627758786, "Miranda", "Douro"),
    ("05S/01A", 1627758968, "Picote", "Douro"),
    ("06S/01A", 1627743548, "Bemposta", "Douro"),
    ("06O/09A", 7554777518, "Baixo Sabor", "Douro"),
    ("06O/10A", 7554829602, "Feiticeiro", "Douro"),
    ("06M/06A", 9321904688, "Foz Tua", "Douro"),
    ("07O/02A", 1627758976, "Pocinho", "Douro"),
    ("07M/02A", 1627759510, "Valeira", "Douro"),
    ("07K/01A", 1627759340, "Régua", "Douro"),
    ("07I/01A", 1627743682, "Carrapatelo", "Douro"),
    ("07G/01A", 1627751912, "Crestuma-Lever", "Douro"),
    ("08L/01A", 1627759554, "Vilar-Tabuaço", "Douro"),
    ("07K/02A", 1627759512, "Varosa", "Douro"),
    ("07H/01A", 1627759468, "Torrão", "Douro"),
    ("04K/04A", 11508860178, "Alto Tâmega", "Douro"),
    ("04J/08A", 9978398426, "Daivões", "Douro"),
    ("05K/02A", 10908513554, "Gouvães", "Douro"),
    ("14I/01A", 1627743586, "Cabril", "Tejo"),
    ("14H/01A", 1627743562, "Bouçã", "Tejo"),
    ("16H/01A", 1627743896, "Castelo do Bode", "Tejo"),
    ("13J/01A", 1627759390, "Santa Luzia", "Tejo"),
    ("16K/01A", 1627759292, "Pracana", "Tejo"),
    ("16K/02A", 1627758658, "Fratel", "Tejo"),
    ("17J/01A", 1627743544, "Belver", "Tejo"),
    ("11H/01A", 1627743384, "Aguieira", "Mondego"),
    ("12H/01A", 1627759328, "Raiva", "Mondego"),
    ("10M/01A", 1627743662, "Caldeirão", "Mondego"),
    ("24M/07A", 1627743416, "Alqueva", "Guadiana"),
    ("24M/08A", 7554862818, "Alqueva jusante (Pedrógão)", "Guadiana"),
]


def raw_path(code: str) -> Path:
    return RAW / f"{code.replace('/', '_')}.csv"


def check_egress() -> None:
    """Refuse to contact SNIRH from anything but the whitelisted address."""
    try:
        ip = requests.get(IP_CHECK, timeout=15).text.strip()
    except requests.RequestException as e:
        raise SystemExit(f"could not determine the exit address ({e}); not contacting SNIRH")
    if ip != WHITELISTED_IP:
        raise SystemExit(f"exit address is {ip}, not {WHITELISTED_IP}: connect LMU eduVPN "
                         "first. APA whitelisted only that address; see the docstring.")
    print(f"exit address {ip} (whitelisted)")


def valid(text: str) -> bool:
    lines = [l for l in text.splitlines() if l.strip()]
    return (bool(lines) and lines[0].startswith("SNIRH") and any(l.startswith("DATA") for l in lines)
            and lines[-1].startswith("Dados obtidos"))


def fetch_station(site: int, tmax: str) -> str:
    params = {"sites": site, "pars": ",".join(str(p) for p in PARAMS),
              "tmin": START, "tmax": tmax, "formato": "csv"}
    r = requests.get(URL, params=params, timeout=300)
    r.raise_for_status()
    text = r.content.decode("latin-1")
    if not valid(text):
        raise RuntimeError(f"site {site}: response is not a SNIRH CSV export "
                           f"({len(text)} chars, starts {text[:80]!r})")
    return text


def fetch(force: bool) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    todo = [s for s in STATIONS if force or not raw_path(s[0]).exists()]
    print(f"{len(todo)} of {len(STATIONS)} stations to fetch")
    if not todo:
        return
    check_egress()
    tmax = date.today().strftime("%d/%m/%Y")
    for k, (code, site, name, _) in enumerate(todo):
        if k:
            time.sleep(DELAY)
        text = fetch_station(site, tmax)
        raw_path(code).write_text(text, encoding="utf-8")
        print(f"  {code} {name}: {len(text.splitlines()):,} lines", flush=True)


def parse_one(path: Path) -> pd.DataFrame:
    lines = path.read_text(encoding="utf-8").splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("DATA"))
    header = lines[i + 1].rstrip(",").split(",")
    body = [l for l in lines[i + 2:] if l[:2].isdigit()]
    d = pd.read_csv(io.StringIO("\n".join(body)), header=None, dtype=str)
    names = ["time_local"]
    for h in header[1:]:
        if h == "FLAG":
            names.append(f"{names[-1]}__flag")
        elif h in HEADER_TO_PARAM:
            names.append(HEADER_TO_PARAM[h])
        else:
            raise ValueError(f"{path.name}: unknown parameter header {h!r}")
    d = d.iloc[:, :len(names)]
    d.columns = names
    flags = [c for c in names if c.endswith("__flag")]
    if d[flags].notna().any().any():
        raise ValueError(f"{path.name}: FLAG columns carry values; decide how to read them first")
    long = d.drop(columns=flags).melt(id_vars="time_local", var_name="parameter").dropna(subset=["value"])
    long["value"] = long.value.astype(float)
    long["time_local"] = pd.to_datetime(long.time_local, format="%d/%m/%Y %H:%M")
    return long


def flag_suspect(d: pd.DataFrame) -> pd.Series:
    """The two source faults in the docstring, as a boolean per row."""
    key = ["station_code", "date"]
    pump = d[(d.parameter == "pumped_m3s") & (d.value > PUMP_MAX)][key].drop_duplicates()
    bad_day = d[key].merge(pump.assign(b=True), on=key, how="left").b.fillna(False).to_numpy()
    s = bad_day & d.parameter.isin(FLOWS).to_numpy()

    inf = d[d.parameter == "inflow_m3s"].sort_values(key)
    out = d[d.parameter == "outflow_m3s"].set_index(key).value
    spike = pd.Series(False, index=inf.index)
    for code, g in inf.groupby("station_code"):
        v = g.set_index("date").value.asfreq("D")
        nb = pd.concat([v.shift(k) for k in (-3, -2, -1, 1, 2, 3)], axis=1).median(axis=1)
        o = out.xs(code, level="station_code").reindex(v.index) if code in out.index.get_level_values(0) \
            else pd.Series(float("nan"), index=v.index)
        # a real flood at a run-of-river dam passes through; a bad volume reading does not
        hit = (v > SPIKE_MIN) & (v > SPIKE_RATIO * nb) & ~(o >= SPIKE_PASS * v)
        spike.loc[g.index] = hit.reindex(g.date).to_numpy()
    s = s | d.index.isin(spike[spike].index)
    return pd.Series(s, index=d.index)


def parse() -> pd.DataFrame:
    meta = pd.DataFrame(STATIONS, columns=["station_code", "site_id", "station", "basin"])
    parts = []
    for code, *_ in STATIONS:
        p = raw_path(code)
        if not p.exists():
            print(f"  MISSING raw file for {code}")
            continue
        parts.append(parse_one(p).assign(station_code=code))
    d = pd.concat(parts, ignore_index=True).merge(meta, on="station_code", how="left")
    d["time_utc"] = (d.time_local.dt.tz_localize("Europe/Lisbon", ambiguous=True, nonexistent="NaT")
                     .dt.tz_convert("UTC"))
    d["date"] = d.time_local.dt.normalize()
    d = d.reset_index(drop=True)
    d["suspect"] = flag_suspect(d)
    d = d[["station_code", "site_id", "station", "basin", "parameter", "time_local", "time_utc",
           "date", "value", "suspect"]].sort_values(["station_code", "parameter", "time_local"])
    dup = d.duplicated(["station_code", "parameter", "time_local"]).sum()
    if dup:
        raise ValueError(f"{dup} duplicate (station, parameter, time) rows")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(d):,} rows, {d.station_code.nunique()} stations)")
    return d


def report(d: pd.DataFrame) -> None:
    g = d.groupby(["station", "parameter"]).time_local.agg(["count", "min", "max"])
    wide = g["count"].unstack().reindex(columns=[p for p, _ in PARAMS.values()])
    order = [s[2] for s in STATIONS if s[2] in wide.index]
    print("\nROWS PER STATION AND PARAMETER (blank = not recorded)")
    print(wide.reindex(order).fillna(0).astype(int).replace(0, "").to_string())
    last = d.groupby("parameter").time_local.max().dt.date
    print("\nLAST OBSERVATION by parameter:", last.to_dict())
    s = d[d.suspect]
    print(f"\nSUSPECT rows: {len(s):,}")
    print(s.groupby(["station", "parameter"]).size().unstack(fill_value=0).to_string())


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-fetch every station")
    ap.add_argument("--parse-only", action="store_true", help="rebuild the parquet from raw only")
    args = ap.parse_args()
    if not args.parse_only:
        fetch(args.force)
    report(parse())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
