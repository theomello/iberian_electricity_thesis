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
