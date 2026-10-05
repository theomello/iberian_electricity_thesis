# Own-basin rainfall as a shifter of n — first-stage probe

Run 2026-10-02. Script: `analysis/hydro_rain_first_stage.py`. Results:
`outputs/tables/hydro_rain_first_stage.csv`. Rain: `fetch/fetch_hydro_precipitation.py`
(18 ERA5 points; nine added 2026-10-02 for Portugal, the Pyrenees, Catalonia's
Ter and coastal Galicia).

**Status: a proof of concept on single-point rainfall, to be replaced by
complete coverage** (every basin of the peninsula, area-averaged; every hydro
unit and owner in MIBEL; dated capacity).

## The idea

A firm's hydro sits in its own river basins, and the firms' basins differ:
EDP's are almost all in Portugal (Lima, Douro, Tejo-Mondego, Cávado, Guadiana),
Iberdrola's on the plateau (Duero, Tajo, Sil, Tâmega, Júcar), Endesa's in the
Pyrenees and Catalonia, Naturgy's in Galicia, Repsol's in Cantabria. Rain in a
firm's own basins makes it sell more, moving its net position n for a reason it
does not choose. Used on the firm's **thermal** offers, whose cost rain does not
change, it identifies β: a price-taking firm offers its gas plant at that plant's
cost whatever water it has elsewhere. Splitting by the predicted sign of n gives
β⁺ and β⁻ from shifts within each firm.

## The probe

Water index: precipitation over the 90 (or 30) days before the week, z-scored by
basin and calendar month, weighted by the firm's hydro capacity per basin (GW,
`cab` max power by month; pumped storage excluded). Weekly panel of six firms
(the five and Movhera), 2018-04 → 2026-05, 2,377 firm-weeks; week effects absorb
everything common, firm × calendar-month effects the seasons. Errors clustered
by month of sample (98).

| index | y | coefficient (se) | F |
|---|---|---|---|
| GW-weighted, 90 days | n | +38.8 MW per GW·sd (9.9) | 15.4 (9.4 with quarter clusters) |
| GW-weighted, 90 days | sell volume | +39.6 (7.5) | 28.2 |
| GW-weighted, 30 days | n | +41.0 (9.7) | 18.0 |
| **basin mix only (capacity shares), 90 days** | n | +170 MW per sd (33) | **26.7** |
| basin mix only, 30 days | n | +152 (33) | 21.1 |

**The basin mix alone identifies the first stage** (F 27): with week effects, the
share-weighted index has no size, so the firms' different rivers carry it, not
common rain times hydro size.

**The indices are correlated**: EDP, Iberdrola and Naturgy 0.87–0.91, Endesa
0.74–0.84 with them; only Repsol (Cantabria) moves apart (0.20–0.37).

Per firm, without week effects (size, not identification): EDP +40 (F 32),
Movhera +44 (F 25), Iberdrola +22 (F 5), Endesa −38 (F 4.5; common wet weeks
lower the price its thermal sells at), Naturgy and Repsol ≈ 0.

## Limits

- One ERA5 point per basin, not an area average; no snowmelt model (Pyrenees).
- Six firms only; the fringe's hydro has no index.
- Ownership static (Repsol owns Viesgo's hydro only from 2018-11-02).
- A first stage only: no thermal outcome yet. Wet weeks are often windy: the
  second stage needs the firm's own wind and solar controlled.

## Rerun on owners by date and share (2026-10-03)

Same probe (single ERA5 points per basin, 2018–2026); n now on dated ownership.
Static → dated:

| sample | b (MW per mm/day) | F |
|---|---|---|
| pooled, 90 days | 38.8 → 31.1 | 15.4 → 11.6 |
| pooled, 30 days | 41.0 → 38.5 | 18.0 → 19.9 |
| pooled, 90 days, quarter clusters | 38.8 → 31.1 | 9.4 → 6.6 |
| pooled, 90 days, without Movhera | 43.9 → 35.8 | 17.6 → 13.6 |
| basin mix only, 90 / 30 days | 170 / 152 → 139 / 132 | 26.7 / 21.1 → 18.5 / 20.9 |
| EDP, 90 days | 39.7 → 33.5 | 32.3 → 24.9 |
| Iberdrola, 90 days | 21.6 → 20.9 | 5.2 → 6.4 |
| Endesa, 90 days | −37.5 → −34.3 | 4.5 → 3.3 |
| Naturgy / Repsol, 90 days | ≈ 0 | ≈ 0 |
| Movhera | 43.7 | 24.9 (unchanged) |

The 90-day pooled first stage weakens and falls below 10 with quarter clusters.
The next version is the complete-data one (catchment rain per plant × the owner's
share that day; handoff 2026-10-05 job 4).

## Complete data: catchment rain × ownership by date (2026-10-05)

`analysis/hydro_rain_catchment_first_stage.py`; results
`outputs/tables/hydro_rain_catchment_first_stage.csv`. Same panel, fixed effects and
clusters as the probe; three things change:

- **Rain** over each plant's whole upstream catchment (E-OBS, 0.25°; 387 JRC plants,
  `build_catchment_rain.py`) instead of one ERA5 point per basin.
- **Anomalies against 1991–2020**: each plant's K-day sum z-scored against its own
  normal for that calendar month, not against 2018–2026.
- **Exposure by date and share**: H_ft = Σ plants GW × the firm's share of the plant's
  OMIE unit that day × z (`build_hydro_plant_units.owners_of_plants`). 155 linked
  plants; mean linked GW: Iberdrola 7.1, EDP 6.1, Endesa 2.9, Naturgy 1.3, Movhera
  0.9, Repsol 0.6. Mixed pumped storage stays in (natural inflow); a row drops it.

| sample (n on H, week effects) | b (MW per GW·sd) | F | other |
|---|---|---|---|
| **pooled, 90 days** | **+56.4 (12.2)** | **21.3** | wild bootstrap over firms p 0.044 |
| pooled, 30 days | +46.8 (9.9) | 22.5 | wild bootstrap over firms p 0.098 |
| pooled, 90 days, sell volume q | +48.0 (7.9) | 37.1 | |
| 90 days, quarter clusters | +56.4 (16.4) | 11.9 | |
| 90 days, without Movhera | +60.9 (12.7) | 23.0 | |
| 90 / 30 days, catchment mix only (no size) | +227 / +200 | 11.1 / 22.3 | |
| 90 / 30 days, rescaled to REE capacity | +48.5 / +40.7 | 19.6 / 21.3 | |
| 90 / 30 days, without pumped storage | +122 / +95 | 20.5 / 20.0 | |

By firm (no week effects, size only): EDP +43.5 (F 37), Movhera +71.6 (F 66),
Iberdrola +28.4 (F 8.4); Endesa, Naturgy and Repsol negative and insignificant.

**Reading.**

- **Complete data roughly doubles the first stage**: pooled 90-day F 11.6 → 21.3,
  and with quarter clusters 6.6 → 11.9. It survives rescaling to REE capacity and
  dropping pumped storage.
- **It is thin across firms.** Six clusters; the wild bootstrap over firms gives
  p 0.044 at 90 days and 0.098 at 30. The response comes from EDP, Movhera and
  Iberdrola, whose catchments lie in the wet north-west.
- **The firms' rain is highly correlated.** The share-weighted 90-day indices of
  EDP, Iberdrola, Movhera and Naturgy correlate 0.94–0.98; only Repsol (0.55–0.70)
  and Endesa (0.80–0.85) differ. Within a week, most of the contrast is hydro size
  × common north-west rain. The no-size index still gives F 11.1 / 22.3, so catchment
  differences carry some of it.
- **Next**, as designed: X instrumented by own rain in the thermal-offer equation,
  split by the sign of n, with the size-versus-mix question answered by using S
  (mix) and H (size) separately as instruments.
