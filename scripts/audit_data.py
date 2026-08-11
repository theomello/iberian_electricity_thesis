"""Audit every dataset on disk: coverage, integrity, duplicates, sanity.

Checks what is actually in `data/`, not what the fetch logs claimed. Several
problems in this project were silent -- a fetcher exiting 0 having parsed a
fraction of a month, a timestamp column quietly full of NaT -- so this
re-derives the facts from the files themselves.

    .venv/bin/python scripts/audit_data.py
"""

from __future__ import annotations

import glob
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omie_common import DATA, END, START, month_range  # noqa: E402

WINDOW = {START + timedelta(d) for d in range((END - START).days + 1)}

# Days OMIE never published, verified by inspecting the source zips: each has
# **zero members** named for that date, so no intraday session ran (or none
# was published). Listed explicitly rather than tolerated by a threshold, so
# that any *new* gap still fails the audit.
KNOWN_ABSENT = {
    "OMIE intraday bids": {date(2021, 7, 30), date(2025, 4, 29), date(2026, 2, 28)},
}

PROBLEMS: list[str] = []
NOTES: list[str] = []


def ok(label: str, passed: bool, detail: str = "", note_if_fail: bool = True) -> None:
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))
    if not passed and note_if_fail:
        PROBLEMS.append(f"{label}: {detail}")


def note(msg: str) -> None:
    print(f"  [note] {msg}")
    NOTES.append(msg)


def gaps(days: set[date], expect: set[date]) -> list[str]:
    """Contiguous runs of missing days, as compact strings."""
    miss = sorted(expect - days)
    if not miss:
        return []
    runs, s = [], miss[0]
    for a, b in zip(miss, miss[1:]):
        if (b - a).days != 1:
            runs.append((s, a))
            s = b
    runs.append((s, miss[-1]))
    return [f"{a}..{b} ({(b-a).days+1}d)" if a != b else f"{a}" for a, b in runs]


def audit_monthly_archive(name: str, pattern: str, expect_end: date) -> None:
    print(f"\n── {name}")
    files = sorted(glob.glob(pattern))
    want = month_range(START, END)
    have = {Path(f).stem.split("_")[-1] for f in files}
    ok("all months present", len(files) == len(want),
       f"{len(files)}/{len(want)}, missing {sorted(set(want)-have) or 'none'}")

    schemas = {tuple(pq.ParquetFile(f).schema_arrow.names) for f in files}
    ok("schema uniform", len(schemas) == 1, f"{len(schemas)} distinct schemas")

    total, days = 0, set()
    for f in files:
        total += pq.ParquetFile(f).metadata.num_rows
        # Take distinct values inside Arrow. Calling .to_pylist() on the raw
        # column would materialise ~900 M Python date objects across the
        # archive, which is both far slower and far larger than the data.
        col = pq.read_table(f, columns=["date"]).column("date").combine_chunks()
        days.update(pc.unique(col).to_pylist())
    print(f"  [info] rows={total:,}  distinct days={len(days):,}")

    absent = KNOWN_ABSENT.get(name, set())
    expect = {d for d in WINDOW if d <= expect_end} - absent
    g = gaps(days, expect)
    ok("no unexplained missing days", not g,
       f"{len(g)} gap run(s): {g[:5]}")
    if absent:
        note(f"{name}: {len(absent)} day(s) absent at source, verified "
             f"(zero members in the zip): {sorted(absent)}")
    stray = sorted(d for d in days if d not in WINDOW)
    if stray:
        note(f"{len(stray)} day(s) outside the study window: {stray[:4]}")


def main() -> int:
    print("=" * 74)
    print("DATA AUDIT — " + str(date.today()))
    print("=" * 74)

    # ---------- 1. leftover temp files ----------
    print("\n── housekeeping")
    parts = glob.glob(str(DATA / "**" / "*.part"), recursive=True) + \
        glob.glob(str(DATA / "**" / "*.tmp"), recursive=True)
    ok("no partial/temp files", not parts, f"{len(parts)} found: {parts[:3]}")
    stubs = glob.glob(str(DATA / "**" / ".*.icloud"), recursive=True)
    ok("no iCloud-evicted stubs", not stubs, f"{len(stubs)} found")

    # ---------- 2. the two big archives ----------
    audit_monthly_archive("OMIE day-ahead bids",
                          str(DATA / "omie/bids/parquet/bids_*.parquet"),
                          date(2026, 5, 8))
    audit_monthly_archive("OMIE intraday bids",
                          str(DATA / "omie/intraday/parquet/intraday_*.parquet"),
                          date(2026, 5, 11))

    # ---------- 3. prices ----------
    print("\n── OMIE day-ahead prices")
    p = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet")
    ok("all 3,073 days", p["date"].nunique() == 3073, f"{p['date'].nunique()} days")
    ok("no missing days", not gaps(set(p["date"]), WINDOW))
    ok("no null timestamps", p["utc_timestamp"].isna().sum() == 0,
       f"{p['utc_timestamp'].isna().sum()} NaT")
    ok("no duplicate (date, period)", not p.duplicated(["date", "period"]).any())
    per = p.groupby("date")["period"].max().value_counts().to_dict()
    ok("period counts are legal", set(per) <= {23, 24, 25, 92, 96, 100}, str(per))
    ok("prices within market bounds",
       p[["price_es", "price_pt"]].stack().between(-500, 3000).all(),
       f"range {p['price_es'].min():.2f}..{p['price_es'].max():.2f}")

    # ---------- 4. registry ----------
    print("\n── OMIE unit registry")
    r = pd.read_parquet(DATA / "omie/registry/unit_registry.parquet")
    ok("units unique", not r["unit"].duplicated().any())
    ok("no ES/PT overlap", not (r["country"] == "BOTH").any(),
       f"{(r['country']=='BOTH').sum()} dual-country units")
    unk = r["country"].isna().sum()
    ok("country assigned", unk == 0, f"{unk} units without a country", note_if_fail=False)
    if unk:
        note(f"{unk} units have no country (present in pdbce only) — "
             "expected from the 2-day/month sample")
    norole = r["role"].isna().sum()
    if norole:
        note(f"{norole} units without a role code")

    b = pd.read_parquet(DATA / "omie/bids/parquet/bids_202401.parquet",
                        columns=["unit", "side", "power_mw", "status"])
    bu = set(b["unit"].astype(str).unique())
    cov = len(bu & set(r["unit"])) / len(bu)
    m = b[b["status"] == "C"]
    volcov = m[m["unit"].astype(str).isin(set(r["unit"]))]["power_mw"].sum() / \
        m["power_mw"].sum()
    ok("registry covers >=99% of bid units", cov >= 0.99, f"{cov:.1%}")
    ok("registry covers >=95% of cleared volume", volcov >= 0.95, f"{volcov:.2%}")

    # ---------- 5. REE ----------
    print("\n── REE 5-minute")
    rt = pd.read_parquet(DATA / "ree/ree_realtime_5min.parquet",
                         columns=["utc_timestamp", "local_date", "demand", "wind"])
    rt["d"] = pd.to_datetime(rt["local_date"]).dt.date
    core = rt[rt["d"].isin(WINDOW)]
    ok("all 3,073 days", core["d"].nunique() == 3073, f"{core['d'].nunique()}")
    cnt = core.groupby("d").size().value_counts().to_dict()
    ok("records/day are legal", set(cnt) <= {276, 288, 300}, str(cnt))
    ok("no duplicate instants", not core["utc_timestamp"].duplicated().any())
    ok("monotonic in UTC",
       core.sort_values("utc_timestamp")["utc_timestamp"].is_monotonic_increasing)
    ok("demand plausible (MW)", core["demand"].between(10_000, 50_000).mean() > 0.99,
       f"mean {core['demand'].mean():,.0f} MW")

    print("\n── REE daily")
    for stem, series_expect in (("generation", 17), ("demand", 1), ("balance", 25)):
        f = DATA / f"ree/ree_{stem}_daily.parquet"
        d = pd.read_parquet(f)
        dd = set(pd.to_datetime(d["local_date"]).dt.date)
        ok(f"{stem}: no missing days", not gaps(dd, WINDOW),
           f"{len(gaps(dd, WINDOW))} gap run(s)")
        ok(f"{stem}: series count", d["series"].nunique() == series_expect,
           f"{d['series'].nunique()} (expected {series_expect})")
        ok(f"{stem}: no null values", d["value"].isna().sum() == 0,
           f"{d['value'].isna().sum()} nulls", note_if_fail=False)

    # ---------- 6. REN ----------
    print("\n── REN Portugal")
    prod = pd.read_parquet(DATA / "ren/ren_production_15min.parquet",
                           columns=["local_date", "utc_timestamp", "series"])
    pd_ = set(pd.to_datetime(prod["local_date"]).dt.date)
    ok("production: all 3,073 days", len(pd_ & WINDOW) == 3073, f"{len(pd_ & WINDOW)}")
    ppd = prod.groupby("local_date")["utc_timestamp"].nunique().value_counts().to_dict()
    ok("production: points/day legal", set(ppd) <= {92, 96, 100}, str(ppd))
    ok("production: 15 series", prod["series"].nunique() == 15,
       f"{prod['series'].nunique()}")
    cap = pd.read_parquet(DATA / "ren/ren_installed_power_monthly.parquet")
    ok("capacity: 101 months", cap.groupby(["year", "month"]).ngroups == 101,
       f"{cap.groupby(['year','month']).ngroups}")

    # ---------- 7. cross-source consistency ----------
    print("\n── cross-source checks")
    ren = pd.read_parquet(DATA / "ren/ren_market_prices.parquet")
    rp = ren.pivot_table(index="utc_timestamp", columns="series", values="value")
    op = p[p["resolution_min"] == 60].set_index("utc_timestamp")[["price_pt", "price_es"]]
    j = rp.join(op, how="inner").dropna()
    dpt = (j["PT"] - j["price_pt"]).abs().max()
    des = (j["ES"] - j["price_es"]).abs().max()
    ok("REN vs OMIE prices identical", max(dpt, des) < 1e-6,
       f"max diff PT {dpt:.4f}, ES {des:.4f}, on {len(j):,} instants")

    es_days = set(pd.to_datetime(
        pd.read_parquet(DATA / "ree/ree_demand_daily.parquet")["local_date"]).dt.date)
    ok("ES and PT day coverage match", es_days == (pd_ & WINDOW),
       f"ES {len(es_days)} vs PT {len(pd_ & WINDOW)}")

    # ---------- verdict ----------
    print("\n" + "=" * 74)
    if PROBLEMS:
        print(f"{len(PROBLEMS)} PROBLEM(S):")
        for x in PROBLEMS:
            print(f"  - {x}")
    else:
        print("No problems found.")
    if NOTES:
        print(f"\n{len(NOTES)} note(s):")
        for x in NOTES:
            print(f"  - {x}")
    print("=" * 74)
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    raise SystemExit(main())
