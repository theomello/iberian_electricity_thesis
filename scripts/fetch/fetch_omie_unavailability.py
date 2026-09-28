#!/usr/bin/env python3
"""OMIE `indisp` / `indisppt` — declared unit unavailability, with its cause.

    .venv/bin/python scripts/fetch/fetch_omie_unavailability.py
    .venv/bin/python scripts/fetch/fetch_omie_unavailability.py --verify

Writes monthly zips to data/omie/indisp/zips/ and parsed tables to
data/omie/indisp/parquet/indisp_YYYYMM.parquet. Token-free. Resumable: months
already parsed are skipped.

WHY

Two designs in this repo need to know whether a unit was *able* to run, as
distinct from whether it *chose* to offer.

* The heat/demand conduct test. A heatwave is not a clean demand shifter,
  because heat also derates thermal plant and binds cooling-water limits —
  Ascó and Vandellós are river-cooled on the Ebro. Without an availability
  control, a heat coefficient blends "firms bid differently when demand is
  high" with "firms had less plant available". Those are opposite stories.
* Any withholding question at all. A unit absent from the bid file is either
  unavailable or withheld, and nothing in `curva_pbc_uof` distinguishes them.

FORMAT — semicolon-delimited, NOT fixed-width

Unlike `cab` and `pdbf`, this dataset is delimited, so none of this repo's
fixed-width parsers apply. Latin-1, dot decimal. Twenty-two fields:

    0      outage id            e.g. REPSB2023SB0794
    1-6    start   Y;M;D;h;m;period
    7-12   end     Y;M;D;h;m;period
    13     unit                 joins to unit_registry / unit_agents
    14     available_mw         MW still available during the outage
    15     reason               FREE TEXT, Spanish, inconsistently cased
    16     flag                 always 1 in the months checked
    17-21  declared Y;M;D;h;m   when the outage was declared

The first two lines are a header (`INDISP;`) and the snapshot timestamp.

THE DECLARATION TIMESTAMP IS THE POINT

Field 17-21 is when the outage was *declared*, not when it starts. That gives
`lead_days` — how far ahead the operator announced it — and that is the field
that separates a maintenance outage planned nine months out (the January 2024
file is full of `Parada programada` declared the previous September) from one
declared hours before delivery. Economic withholding, if it exists anywhere,
hides in the short-lead tail. No other OMIE dataset publishes this.

ONE SNAPSHOT PER DAY, NOT ALL OF THEM

OMIE republishes the whole forward register many times a day — 920 members in
the January 2024 zip, about thirty per day. Each is a complete snapshot of all
known outages, mostly for future dates, so parsing all of them multiplies the
same records thirtyfold. This keeps the **last snapshot of each day** and tags
it with its own timestamp. If a design ever needs the intraday revision path,
parse more; nothing here is lost that a re-run cannot recover.

TWO FINDINGS FROM THE FIRST RUN, BOTH WORTH KNOWING BEFORE USING THIS

**`indisppt` does not exist.** CLAUDE.md's file-catalogue note lists
"`indisp`/`indisppt` (unit unavailability)" by analogy with `pdbc`/`pdbcpt`.
Checked 2026-08-21: `indisppt`, `indispt` and `indisp_pt` all return a valid
page with **zero** monthly zips. The analogy does not hold and only `indisp` is
published. The default `--datasets` is `indisp` alone for that reason.

**The unit codes are a PHYSICAL namespace, not the market registry's.** Of
1,529 distinct codes, only **75 join `unit_registry.parquet`** — the rest are
wind farms, micro-hydro and cogeneration carrying names like `AEROGEN`,
`AGBAENA`, `98D-481` that never appear as OMIE programming units. Stripping a
trailing `B` recovers none of them, so this is a genuine namespace difference
and not a suffix convention.

That sounds fatal and is not, because of *which* 75 match: they are the large
conventional units — `ASC1` (Ascó 1), `ABO1`, `ARCOS1`, `BES3` — so coverage of
the fleet any markup design cares about is high while coverage of the register
as a whole is low:

| population | covered |
|---|---|
| all 1,529 `indisp` codes | 75 (4.9%) |
| the 68 plant-specific-efficiency marginal-cost units | **55 (80.9%)** |
| top 200 units by cleared volume | 41 (20.5%) |

**Measure coverage on the fleet you are using, not on the file.** The headline
15.4%-of-records figure is the wrong number for every design that would reach
for this dataset.

CAUTION: the reason field is free text and may itself contain a semicolon.
Lines whose field count is not 22 are counted and reported rather than
silently coerced; if that count is ever non-trivial the parser needs a
right-anchored split instead.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, omie_url, session  # noqa: E402

ROOT = DATA / "omie" / "indisp"
ZIPS = ROOT / "zips"
PARQ = ROOT / "parquet"
N_FIELDS = 22


def months(sess, dataset: str) -> list[str]:
    u = (f"https://www.omie.es/es/file-access-list?parents%5B0%5D={dataset}"
         f"&realdir={dataset}")
    r = sess.get(u, timeout=120)
    r.raise_for_status()
    return sorted(set(re.findall(rf"{dataset}_(\d{{6}})\.zip", r.text)))


def get_zip(sess, dataset: str, ym: str) -> Path:
    dest = ZIPS / f"{dataset}_{ym}.zip"
    # Deliberately NOT the `monthly_zip_may_grow` rule the other OMIE fetchers
    # use. 43 of 100 indisp zips stop short of their month's last day, and they
    # are short AT SOURCE, not frontier snapshots: re-fetched on 2026-09-28,
    # 202401 still held 20 days, 202403 one, and 202605 was byte-for-byte what
    # was fetched on 2026-08-21. Re-fetching would buy nothing.
    if dest.exists() and zipfile.is_zipfile(dest):
        return dest
    tmp = dest.with_suffix(".zip.part")
    with sess.get(omie_url(dataset, f"{dataset}_{ym}.zip"), timeout=900,
                  stream=True) as r:
        r.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
    if not zipfile.is_zipfile(tmp):
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{dataset}_{ym}.zip is not a zip")
    tmp.rename(dest)
    return dest


def parse_member(raw: str, member: str, dataset: str):
    """Returns (rows, n_bad). Rows are dicts; n_bad counts field-count misses."""
    lines = [l for l in raw.splitlines() if l.strip()]
    if not lines:
        return [], 0
    snap = None
    if len(lines) > 1:
        h = lines[1].split(";")
        if len(h) >= 5 and all(x.isdigit() for x in h[:5]):
            snap = pd.Timestamp(int(h[0]), int(h[1]), int(h[2]),
                                int(h[3]), int(h[4]))
    rows, bad = [], 0
    for line in lines[2:]:
        f = line.split(";")
        if f and f[-1] == "":
            f = f[:-1]
        if len(f) != N_FIELDS:
            bad += 1
            continue
        try:
            start = pd.Timestamp(int(f[1]), int(f[2]), int(f[3]),
                                 int(f[4]), int(f[5]))
            end = pd.Timestamp(int(f[7]), int(f[8]), int(f[9]),
                               int(f[10]), int(f[11]))
            decl = pd.Timestamp(int(f[17]), int(f[18]), int(f[19]),
                                int(f[20]), int(f[21]))
            mw = float(f[14])
        except (ValueError, TypeError):
            bad += 1
            continue
        rows.append({
            "snapshot": snap, "outage_id": f[0], "start": start, "end": end,
            "unit": f[13], "available_mw": mw, "reason": f[15].strip(),
            "declared": decl, "country": "PT" if dataset.endswith("pt") else "ES",
        })
    return rows, bad


def parse_month(zpath: Path, dataset: str) -> tuple[pd.DataFrame, int]:
    with zipfile.ZipFile(zpath) as z:
        names = [n for n in z.namelist() if re.search(r"_\d{8}\.\d+$", n)]
        # keep only the LAST snapshot of each calendar day
        by_day: dict[str, str] = {}
        for n in names:
            m = re.search(r"_(\d{8})\.(\d+)$", n)
            day, rev = m.group(1), int(m.group(2))
            if day not in by_day or rev > int(
                    re.search(r"\.(\d+)$", by_day[day]).group(1)):
                by_day[day] = n
        rows, bad = [], 0
        for day, n in sorted(by_day.items()):
            r, b = parse_member(z.read(n).decode("latin-1"), n, dataset)
            rows.extend(r)
            bad += b
    return pd.DataFrame(rows), bad


def verify() -> int:
    files = sorted(PARQ.glob("indisp_*.parquet"))
    if not files:
        print("nothing parsed yet")
        return 1
    d = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    d = d.drop_duplicates(subset=["outage_id", "unit", "start", "end"])
    d["lead_days"] = (d.start - d.declared).dt.total_seconds() / 86400
    print(f"{len(d):,} distinct outage records, {d.unit.nunique():,} units, "
          f"{d.snapshot.min().date()} to {d.snapshot.max().date()}\n")
    print("DECLARATION LEAD TIME — the field that makes this dataset useful")
    for q in (0.05, 0.25, 0.50, 0.75, 0.95):
        print(f"  p{int(q*100):>2}  {d.lead_days.quantile(q):>9.2f} days")
    short = d[d.lead_days < 1]
    print(f"  declared under 24h ahead: {len(short):,} "
          f"({len(short)/len(d):.1%}) — the tail any withholding question wants")
    print("\nREASON, top 12 (free text, inconsistently cased)")
    print(d.reason.str.upper().value_counts().head(12).to_string())
    reg = set(pd.read_parquet(DATA / "omie/registry/unit_registry.parquet",
                              columns=["unit"]).unit)
    mc = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                         columns=["unit", "eff_is_generic"])
    mcu = set(mc[~mc.eff_is_generic].unit)
    codes = set(d.unit)
    print("\nNAMESPACE — measure coverage on the fleet you use, not on the file")
    print(f"  all indisp codes joining the market registry: "
          f"{len(codes & reg)} of {len(codes)} ({len(codes & reg)/len(codes):.1%})")
    print(f"  marginal-cost units (plant-specific efficiency) covered: "
          f"{len(mcu & codes)} of {len(mcu)} "
          f"({len(mcu & codes)/max(len(mcu),1):.1%})  <- the number that matters")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--datasets", default="indisp",
                    help="indisppt is not published — see the docstring")
    args = ap.parse_args()
    ZIPS.mkdir(parents=True, exist_ok=True)
    PARQ.mkdir(parents=True, exist_ok=True)
    if args.verify:
        return verify()

    sess = session()
    for dataset in args.datasets.split(","):
        yms = months(sess, dataset)
        print(f"{dataset}: {len(yms)} monthly zips, {yms[0]} to {yms[-1]}")
        for ym in yms:
            out = PARQ / f"{dataset}_{ym}.parquet"
            if out.exists():
                continue
            z = get_zip(sess, dataset, ym)
            df, bad = parse_month(z, dataset)
            if df.empty:
                print(f"  {dataset} {ym}: EMPTY")
                continue
            df.to_parquet(out, index=False)
            flag = f"  ** {bad} malformed lines" if bad else ""
            print(f"  {dataset} {ym}: {len(df):>7,} rows, "
                  f"{df.unit.nunique():>4} units{flag}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
