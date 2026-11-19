# E-REDES consumption by voltage level (Portugal)

Fetched 2026-11-18 by `scripts/fetch/fetch_eredes_voltage.py` from the E-REDES open-data portal
(`e-redes.opendatasoft.com`, API explore v2.1, CSV export), licence CC BY 4.0. Raw CSVs in `data/eredes/raw/`,
parquet in `data/eredes/` (gitignored, re-fetchable). E-REDES is the mainland distribution operator.

## Verified facts (from the files, 2026-11-18)
- **`consumo-total-nacional`** → `national_15min_by_voltage.parquet`: 15-minute energy in **kWh** by `bt` (low), `mt`
  (medium), `at` (high), `mat` (very high voltage) and `total`; **2023-01-01 00:00 UTC → 2026-11-16**, 135,761 rows.
  `datahora` is UTC (the export was requested with `timezone=UTC`). **35 duplicate timestamps** in the raw file: drop
  duplicates before resampling. Annual TWh 2023 / 2024 / 2025: BT 25.8 / 26.0 / 27.2, MT 15.8 / 15.8 / 16.0,
  AT 6.8 / 7.1 / 6.9, MAT 2.4 / 2.6 / 2.6.
- **`3-consumos-faturados-por-municipio-ultimos-10-anos`** → `monthly_parish_by_voltage.parquet`: monthly **billed**
  active energy, kWh, by parish, **2020-11 → 2026-07**, 310,745 rows. Despite the name ("last 10 years") it starts in
  November 2020. **Only two voltage classes:** "Baixa Tensão" and "Muito Alta, Alta e Média Tensões" (MAT, AT and MT
  combined). National MAT+AT+MT about 1.8–2.2 TWh a month.
- **Nothing hourly before 2023 and nothing by voltage before 2020-11** in the public catalogue (70 datasets checked
  2026-11-18, see `notes/idea-portugal-access-tariff-swing.md`).

## Check: OMIE retailer schedules as a Portuguese business control (2026-11-18, descriptive, no estimate)
Candidate: PDBF schedules (all role codes, so bilateral contracts included) of Iberdrola Portugal (`IGESC2`) and
Endesa Portugal (`ENDPC2`), the retailers ERSE names as dominant in the industrial segments. Compared on 2023-01 →
2026-05 hourly (29,468 hours) with E-REDES MT+AT+MAT ("HV") and BT:
- **Day-to-day level:** daily deviations from a 28-day mean correlate 0.976 with HV (0.78 with BT). Monthly m/m changes
  2020-11 → 2026-04: 0.73 with HV, 0.21 HV with BT. The two retailers schedule about 0.60–0.68 of billed HV energy.
- **Within-day shape (what the triple difference uses):** worse than the national total. Daily evening (18–21h Lisbon)
  over night (0–7h) contrast, deviations from a 28-day mean: candidate vs HV **0.71**; national total (BT+HV) vs HV
  **0.95**. Shape regression: candidate = 0.28 BT + 0.51 HV; total = 0.52 BT + 0.44 HV.
- **Reading:** retailer schedules follow business *levels* but not the business *hourly shape* (they are forecasts and
  contract blocks). For the within-day design the national total is already a closer proxy for Portuguese HV than the
  candidate, at least in 2023–26. Script: scratch only (not kept); re-derivable from the two sources above.
