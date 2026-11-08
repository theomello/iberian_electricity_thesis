"""Split the gas-cap gain on France-bound exports between French buyers and the border's congestion rent.

The J welfare table books Δp × (scheduled export) to "exporters". Under market coupling, when the France line is export-full the
French price does not follow the Iberian fall, so that Δp × flow is collected as congestion rent (ESIOS 1118, gross, split 50/50
with France; the Spanish half reduced the cap's cost, RDL 10/2022 rule 51 bis.2). Only in open hours does the fall reach French
buyers through a lower French price. Section I1c of notes/rq-crisis-quantity.md.
"""
import sys
import zoneinfo
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from omie_common import day_periods_utc  # noqa: E402

TZ = zoneinfo.ZoneInfo("Europe/Madrid")


def esios(i):
    e = pd.read_parquet(ROOT / f"data/esios/esios_{i}.parquet")
    return e.assign(t=pd.to_datetime(e.utc_timestamp, utc=True)).groupby("t").value.sum()


def main():
    h = pd.read_parquet(ROOT / "outputs/tables/gas_cap_dispatch_welfare_hourly.parquet")
    h = h[h.ok]
    m = {}
    for d, g in h[["date", "period"]].drop_duplicates().groupby("date"):
        for p, t in enumerate(day_periods_utc(d.date(), int(g.period.max()), TZ), 1):
            m[(d, p)] = pd.Timestamp(t)
    h["t"] = pd.to_datetime([m[(d, p)] for d, p in zip(h.date, h.period)], utc=True)

    link = pd.read_parquet(ROOT / "outputs/tables/france_link_hours.parquet").set_index("utc")
    exp = -esios(32)
    rent_exp, rent_imp = esios(1118), esios(1117)

    # check: gross export rent against (p_fr - p_es) x scheduled export, hours with an export
    k = link.index.intersection(exp.index).intersection(rent_exp.index)
    k = k[(k >= "2022-06-15") & (k < "2023-03-01")]
    implied = ((link.price_fr - link.price_es).clip(lower=0) * exp).reindex(k)
    print(f"check, 2022-06-15 → 2023-02: ESIOS 1118 €{rent_exp.reindex(k).sum()/1e6:,.1f} m, "
          f"gap × scheduled export €{implied.sum()/1e6:,.1f} m, hourly corr {rent_exp.reindex(k).corr(implied):.3f}")

    idx = pd.DatetimeIndex(h[h.rho == 0.73].t)
    print(f"France line state in the {len(idx):,} valid hours: "
          + ", ".join(f"{s} {v:.1%}" for s, v in link.state.reindex(idx).value_counts(normalize=True).items()))
    print(f"ESIOS 1118 over the valid hours €{rent_exp.reindex(idx).sum()/1e6:,.1f} m gross "
          f"(Spanish half €{rent_exp.reindex(idx).sum()/2e6:,.1f} m); 1117 €{rent_imp.reindex(idx).sum()/1e6:,.1f} m")

    rows = []
    for rho in (0.55, 0.73, 1.0):
        x = h[h.rho == rho].set_index("t")
        g = (x.p_c - x.p_o) * exp.reindex(x.index).fillna(0)
        st = link.state.reindex(x.index)
        full = g[st == "export_full"].sum() / 1e6
        rows.append({"rho": rho, "gain_total_m": g.sum() / 1e6,
                     "export_full_to_rent_m": full, "spanish_half_m": full / 2, "french_tso_half_m": full / 2,
                     "open_to_french_buyers_m": g[st == "open"].sum() / 1e6,
                     "other_states_m": g[~st.isin(["export_full", "open"])].sum() / 1e6})
    out = pd.DataFrame(rows)
    print(out.round(1).to_string(index=False))
    out.to_csv(ROOT / "outputs/tables/gas_cap_france_rents.csv", index=False)


if __name__ == "__main__":
    main()
