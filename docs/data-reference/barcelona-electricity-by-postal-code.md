# Barcelona electricity consumption by postal code, sector and six-hour band

Fetched 2026-11-16 by `scripts/fetch/fetch_barcelona_electricity.py` (7 CSVs, 2019-2025, 98.9 MB, `data/barcelona_electricity/raw/`, gitignored). Source: Barcelona City Council open data, "Consum d'electricitat per codi postal, sector econòmic i tram horari" (Datadis data), licence CC BY 4.0, metadata last modified 2026-05-06, refreshed monthly with a 2-3 month lag. Sizes of all seven files match the CKAN metadata.

## Verified facts (from the files, 2026-11-16)
- **Columns:** `Any` (year), `Data` (date, YYYY-MM-DD), `Codi_Postal` (integer, e.g. 8001 for 08001), `Sector_Economic`, `Tram_Horari`, `Valor` (integer). 1,665,130 rows; no duplicates on (date, postal code, sector, band); no nulls.
- **Unit is kWh, not MWh.** The metadata title and field description say MWh, but the annual totals are 5.5-6.9 billion units (6.95 billion in 2019); read as kWh that is 5.5-6.9 TWh, plausible for the city; read as MWh it would be a thousand times Spain's consumption. A single industrial postal-code cell on 1 January 2019 at midnight-6 am has value 727, plausible only as kWh.
- **42 postal codes**, all present in every year. **Sectors:** Serveis (about 56% of consumption), Residencial (about 35%), Indústria (6-10%), No especificat (0-0.3%; absent in 2024).
- **Time bands (five values):** 00:00-05:59, 06:00-11:59, 12:00-17:59, 18:00-23:59, and "No consta" (not stated), which is 97% zeros and carries about 0% of the value: drop it. Zeros elsewhere are 0.1% of cells. The bands are local clock time (not verified at daylight-saving days).
- **Coverage:** 2019-01-01 to 2025-11-30, every calendar day present except 2025-08-19 (missing day); December 2025 absent (publication lag). Rows per day vary (mode 670, minimum 405): some postal code-sector-band combinations are absent on some days (not yet characterised).
- **Weekday pattern:** services' 12-18h consumption in 2019 averages 3.61 million kWh on weekdays against 2.53 million on weekends (-30%), so the weekday-minus-weekend contrast the calendar-boundary design needs is visible in the series.

## Traps
- The title and the description say MWh; divide by nothing, treat as kWh.
- Six-hour bands do not align with the six price periods: 0-6 is P6 on every day (clean control band), 6-12 mixes P6 (6-8), P2 (8-9) and the top period (9-12), 12-18 mixes the top period (12-14) with P2, 18-24 the top period (18-22) with P2 (22-24). Doses must be averaged over the hours in each band.
- Services mixes 2.0TD shops, 3.0TD and some 6.1TD buildings; sector is by economic activity, not by tariff.
- Datadis covers consumers who have enabled data sharing or are distributor-reported; coverage by postal code against the Barcelona total is unknown.
- Late files are revised (2019-2023 files have `last_modified` dates in 2023-2026); refetch rather than assume stability.
