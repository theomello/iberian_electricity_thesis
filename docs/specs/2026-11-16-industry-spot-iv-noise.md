# Industrial load against the hourly spot price, instrumented by D-1 wind and solar forecasts: step zero

**Status: proposed and checked 2026-11-16; thresholds were set in the script header before the run; no slope was printed.** Script `scripts/analysis/industry_iv_noise.py`, output `outputs/tables/industry_iv_noise.csv`.

**Idea.** Many industrial contracts are indexed to the hourly spot price, and the intraday spread in 2019-23 was far larger than the 2021 tariff change (dose 0.04-0.07). REE's D-1 wind and solar forecasts move the spot price and were known to bidders. Regress hourly ln load of E3-E6 (ESIOS 1204-1207) on the spot price, instrumented by the forecasts, with year-month and hour-by-weekday effects and temperature terms.

**Sample.** Non-holiday weekdays 2019-01-01 → 2023-12-31, lockdown (2020-03-01 → 2020-06-30) out: 27,136 hours, 1,172 days, mean price €98.2/MWh.

**Rules set before the run.** First-stage F (date-clustered, controls partialled) at least 10, and detectable elasticity (2.8 × the date-clustered standard error of the elasticity at the mean price) at most 0.25.

**Result.** First-stage F **296** (pass): the forecasts move the price strongly. Standard error of the elasticity **1.59**, detectable elasticity **4.46** (**fail**, bar 0.25). Stop: the design cannot detect an industrial elasticity of any plausible size (the 95% interval would be about ±3). The weak link is the outcome, not the instrument: hourly industrial load is noisy relative to what the price explains, and the instruments' strength cannot fix that.

**What it leaves.** Nothing is registered or estimated. An industrial elasticity would need a much lower-noise outcome (a sector panel with firm or process-level load, or contract-level data with known indexation), which this repo does not have. The earlier tariff-dose result stands: no industrial elasticity is identified, IND and 6.3 excluding zero are descriptive only (their placebo years disagree).
