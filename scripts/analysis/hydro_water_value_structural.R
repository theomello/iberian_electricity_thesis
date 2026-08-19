#!/usr/bin/env Rscript
# The structural hydro opportunity-cost model, end to end, in R.
#
#   Rscript scripts/analysis/hydro_water_value_structural.R
#
# Self-contained: builds the estimation panel from the raw OMIE/MITECO/OMIP
# archives itself, no dependency on `hydro_water_value_structural.py`. That
# script remains in the repo as the original, faster prototype (pyarrow's
# dataset filters push predicates into the file scan); this port trades some
# of that speed for two fixes made along the way -- see below.
#
# THE MODEL
#
# Arzhintar, Leslie, Neill & Wyrwoll's template (`papers/md/ssrn-5736763.md`,
# see `notes/hydro-water-value-design.md`), fit on Spain's storage-hydro
# cascades. For periods where a hydro unit is the marginal price setter, the
# profit-maximising FOC (Hortacsu & Puller 2008 eq. 2) rearranges to an
# implied opportunity cost
#
#   c_it = p*_t - (q_it - QC_it) / |RD'_it(p*_t)|
#
# regressed on the front-quarter OMIP forward price (`pf`, national,
# monthly) and basin-aggregate MITECO reservoir volume (`vol`, monthly):
#
#   c_it = b0 + b1*pf_t + b2*Vol_it + e_it
#
# no interaction (checked in the source paper's own appendix -- pf and Vol
# are never multiplied together in any specification they run). Two
# specifications: pooled (their own spec) and with unit fixed effects (this
# repo's robustness check; Spain has several cascades, Snowy Hydro is one).
#
# WHAT CHANGED FROM hydro_water_value_structural.py -- TWO FIXES
#
# 1. RESIDUAL DEMAND IS NOW NETTED FOR THE MARGINAL UNIT'S OWN OFFERS.
#    The Python build used `residual_demand_slope.py`'s aggregate-market
#    slope as-is -- density of ALL offers (every unit, both sides) within
#    +/-5 EUR of the clearing price -- explicitly documented there as a
#    LOWER bound on any single participant's true price impact, because a
#    large cascade's own offers are part of that density and make the
#    aggregate curve look flatter than the curve it actually faces once its
#    own supply is removed. Fixed here: for each marginal-hydro period, the
#    unit's own offered MW inside the +/-5 EUR band is subtracted from the
#    band total before dividing by 2h, so `slope` is that unit's own
#    residual-demand slope, not the whole market's.
# 2. FEW-CLUSTER INFERENCE. 14 hydro cascades survive the outlier filter --
#    thin for the asymptotic cluster-robust standard errors
#    `hydro_water_value_structural.py` reports (and this script also
#    reports, for comparability). A nonparametric CLUSTER (pairs) BOOTSTRAP
#    is added alongside: resample the 14 cascades with replacement (not
#    individual rows -- that would break the within-unit dependence the
#    correction exists to respect), refit, repeat 2,000 times, and report
#    the bootstrap SE and percentile CI for b1 and b2. This is the standard
#    fix for exactly this problem (Cameron, Gelbach & Miller 2008) and needs
#    no extra package beyond base R's `boot`.
#
# OUTLIERS, FIXED AT THE SOURCE (same diagnosis as the Python build)
#
# (a) Periods where the (now netted) residual-demand slope sits in its
#     thinnest 1% -- a near-zero denominator blows `c` up into an
#     implausible range and reflects a residual-demand estimate too thin to
#     trust, not a real opportunity cost.
# (b) Periods clearing at or below 1 EUR/MWh (`ZERO_PRICE`, the same
#     threshold `residual_demand_slope.py` already uses for "eta is not
#     meaningful here") -- a hydro unit setting the price there is typically
#     being curtailed or forced to run, not revealing an opportunity cost
#     this FOC describes.

suppressPackageStartupMessages({
  library(arrow); library(dplyr); library(tidyr); library(sandwich)
  library(lmtest); library(boot); library(purrr)
})

# Resolve the repo root by walking up from the working directory looking for
# CLAUDE.md, rather than trusting getwd() -- getwd() is only correct if R was
# launched from the repo root, and breaks silently (wrong DATA path, opaque
# "file not found" errors) the moment someone runs this from scripts/analysis/
# or pastes it into a session started elsewhere. Same discipline the Python
# scripts already use (`Path(__file__).resolve().parent.parent.parent`) --
# R has no reliable equivalent of `__file__` when code is source()'d or
# pasted rather than run via `Rscript`, so this walks up from wherever R
# actually is instead.
find_repo_root <- function(start = getwd(), marker = "CLAUDE.md", max_up = 6) {
  d <- normalizePath(start, mustWork = FALSE)
  for (i in 0:max_up) {
    if (file.exists(file.path(d, marker))) return(d)
    parent <- dirname(d)
    if (parent == d) break  # reached the filesystem root without finding it
    d <- parent
  }
  stop(sprintf(
    "Could not find the repo root (looked for '%s' walking up from '%s'). ",
    marker, start),
    "Run this from inside the repo -- Rscript scripts/analysis/hydro_water_value_structural.R ",
    "from the repo root, or source() it from an R session started there.")
}

ROOT <- find_repo_root()
DATA <- file.path(ROOT, "data")
cat(sprintf("repo root: %s\n\n", ROOT))

BANDWIDTH_H  <- 5     # EUR/MWh, matches residual_demand_slope.py's h=5
SLOPE_PCTL   <- 0.01  # drop the thinnest 1% of (netted) slope estimates
ZERO_PRICE   <- 1.0   # EUR/MWh, residual_demand_slope.py's own convention
IDENTITY_TOL <- 0.001 # matched-buy-vs-sell gap tolerance
N_BOOT       <- 2000  # cluster bootstrap replications

# ---- basin matching, ported from hydro_water_value_precip.py --------------

# Two fixes made 2026-08-19 (mirrored from hydro_water_value_precip.py --
# see that file for the checks run before adding either): AG[UÚÜ]ERA now
# accepts both accents (was missing ASIAGU on a character mismatch), and
# \bTER\b added for TERE ("UGH. TER", 150.3 MW, the Ter river in Catalonia).
BASIN_PATTERNS <- list(
  c("\\bDUERO\\b|\\bESLA\\b|\\bTERA\\b", "duero"),
  c("\\bEBRO\\b", "ebro"),
  c("\\bTAJO\\b", "tajo"),
  c("\\bGUADIANA\\b", "guadiana"),
  c("\\bGUADALQUIVIR\\b", "guadalquivir"),
  c("\\bJUCAR\\b|J[UÚ]CAR", "jucar"),
  c("\\bSIL\\b|\\bMI[NÑ]O\\b|\\bBIBEY\\b|\\bEUME\\b|GALICIA", "galicia_sil_mino"),
  c("\\bVIESGO\\b|\\bAG[UÚÜ]ERA\\b|HIDROCANT[AÁ]BRICO|CANT[AÁ]BRICO", "cantabrico"),
  c("\\bABAR[AÁ]N\\b|\\bARCHENA\\b|\\bULEA\\b|\\bSEGURA\\b", "segura"),
  c("\\bTER\\b", "cataluna_interna")
)

basin_from_descr <- function(descr) {
  d <- toupper(descr)
  for (p in BASIN_PATTERNS) if (grepl(p[1], d, perl = TRUE)) return(p[2])
  NA_character_
}

hydro_units_with_basin <- function() {
  ua <- read_parquet(file.path(DATA, "omie/registry/unit_agents.parquet"),
                      col_select = c("unit", "country", "tech", "descr"))
  hy <- ua |> filter(country == "ES", tech == "hydro_ugh")
  hy$basin <- vapply(hy$descr, basin_from_descr, character(1))
  hy
}

# ---- MITECO reservoir volume, ported from hydro_water_value_reservoir.py --

AMBITO_TO_BASIN <- c(
  "Duero" = "duero", "Ebro" = "ebro", "Tajo" = "tajo", "Guadiana" = "guadiana",
  "Guadalquivir" = "guadalquivir", "Júcar" = "jucar",
  "Miño - Sil" = "galicia_sil_mino", "Galicia Costa" = "galicia_sil_mino",
  "Cantábrico Occidental" = "cantabrico", "Cantábrico Oriental" = "cantabrico",
  "Segura" = "segura",
  "Cuencas Internas de Cataluña" = "cataluna_interna")  # added 2026-08-19, see reservoir.py

basin_volume_level <- function() {
  r <- read_parquet(file.path(DATA, "miteco/embalses_historico.parquet"))
  r$basin <- AMBITO_TO_BASIN[r$ambito]
  r <- r |> filter(!is.na(basin), !is.na(capacity_hm3), !is.na(stored_hm3), capacity_hm3 > 0)
  weekly <- r |> group_by(basin, date) |> summarise(stored = sum(stored_hm3), .groups = "drop")
  weekly$month <- format(weekly$date, "%Y-%m")
  weekly |> group_by(basin, month) |> summarise(vol = mean(stored), .groups = "drop")
}

# ---- OMIP front-quarter forward, ported from levy_contract_exposure_forward.py

front_quarter_forward <- function() {
  files <- list.files(file.path(DATA, "omip/parquet"),
                       pattern = "^omip_forwards_ES_.*\\.parquet$", full.names = TRUE)
  q <- map_dfr(files, ~ read_parquet(.x, col_select = c(
    "trade_date", "maturity", "contract", "price_ref_eur_mwh", "price_ref_prev_eur_mwh")))
  q <- q |> filter(maturity == "Quarter")
  q$price <- ifelse(is.na(q$price_ref_eur_mwh), q$price_ref_prev_eur_mwh, q$price_ref_eur_mwh)
  q <- q |> filter(!is.na(price))

  m <- regmatches(q$contract, regexec("Q(\\d)-(\\d\\d)", q$contract))
  q$qtr <- vapply(m, function(x) as.integer(x[2]), integer(1))
  q$yr  <- vapply(m, function(x) 2000L + as.integer(x[3]), integer(1))
  q$qstart <- as.Date(sprintf("%d-%02d-01", q$yr, (q$qtr - 1) * 3 + 1))
  q <- q |> filter(qstart > trade_date)

  front <- q |> group_by(trade_date) |> slice_min(qstart, n = 1, with_ties = FALSE) |> ungroup()
  front$month <- format(front$trade_date, "%Y-%m")
  front |> group_by(month) |> summarise(pf = mean(price), .groups = "drop")
}

# ---- PDBF contract position (role 4), ported from
#      hydro_water_value_structural.py's contract_position() -------------

contract_position <- function(units) {
  files <- list.files(file.path(DATA, "omie/pdbf/parquet"),
                       pattern = "^pdbf_.*\\.parquet$", full.names = TRUE)
  frames <- map(files, function(f) {
    t <- read_parquet(f, col_select = c("date", "period", "unit", "schedule_mw",
                                         "resolution_min", "role_code"))
    t <- t |> filter(unit %in% units, role_code == "4")
    if (nrow(t) == 0) return(NULL)
    t |> mutate(qc = schedule_mw * resolution_min / 60) |> select(date, period, unit, qc)
  })
  bind_rows(frames)
}

# ---- day-ahead prices ------------------------------------------------------

load_prices <- function() {
  px <- read_parquet(file.path(DATA, "omie/prices/omie_day_ahead_prices.parquet"),
                      col_select = c("date", "period", "price_es", "price_pt"))
  px$split <- px$price_es != px$price_pt
  px
}

# ---- one month of the bid archive: slope (netted), marginal unit, own q --

process_month <- function(f, px, target_units) {
  b <- read_parquet(f, col_select = c("date", "period", "side", "status",
                                       "power_mw", "price_eur_mwh", "unit",
                                       "resolution_min"))
  ym_lo <- min(b$date); ym_hi <- max(b$date)
  px_m <- px |> filter(date >= ym_lo, date <= ym_hi)
  if (nrow(px_m) == 0) return(NULL)

  mat <- b |> filter(status == "C")
  matV <- mat |> filter(side == "V")
  if (nrow(matV) == 0) return(NULL)

  side_tot <- mat |> group_by(date, period, side) |>
    summarise(mw = sum(power_mw), .groups = "drop") |>
    pivot_wider(names_from = side, values_from = mw, values_fill = 0)
  if (!"V" %in% names(side_tot)) side_tot$V <- 0
  if (!"C" %in% names(side_tot)) side_tot$C <- 0
  side_tot <- side_tot |> rename(sell_matched = V, buy_matched = `C`) |>
    filter(sell_matched > 0)
  side_tot$identity_gap <- abs(side_tot$sell_matched - side_tot$buy_matched) / side_tot$sell_matched

  out <- side_tot |> inner_join(px_m, by = c("date", "period")) |>
    rename(p_star = price_es)

  # marginal unit: highest-priced accepted sell offer, per period
  marg <- matV |> group_by(date, period) |>
    slice_max(price_eur_mwh, n = 1, with_ties = FALSE) |>
    ungroup() |> select(date, period, marginal_unit = unit)

  out <- out |> inner_join(marg, by = c("date", "period")) |>
    filter(marginal_unit %in% target_units)
  if (nrow(out) == 0) return(NULL)

  # own cleared quantity of the marginal unit that period
  own <- matV |> filter(unit %in% target_units) |>
    mutate(q = power_mw * resolution_min / 60) |>
    group_by(date, period, unit) |> summarise(q_i = sum(q), .groups = "drop")
  out <- out |> left_join(own, by = c("date" = "date", "period" = "period",
                                       "marginal_unit" = "unit"))
  out$q_i <- ifelse(is.na(out$q_i), 0, out$q_i)

  # residual-demand slope, NETTED for the marginal unit's own offers (fix 1)
  off <- b |> filter(status == "O") |>
    inner_join(out |> select(date, period, p_star), by = c("date", "period"))
  off$dev <- abs(off$price_eur_mwh - off$p_star)
  inband <- off |> filter(dev <= BANDWIDTH_H)

  band_tot <- inband |> group_by(date, period) |>
    summarise(mw_tot = sum(power_mw), .groups = "drop")
  band_own <- inband |> filter(unit %in% target_units) |>
    group_by(date, period, unit) |> summarise(mw_own = sum(power_mw), .groups = "drop")

  out <- out |> left_join(band_tot, by = c("date", "period")) |>
    left_join(band_own, by = c("date" = "date", "period" = "period",
                                "marginal_unit" = "unit"))
  out$mw_tot <- ifelse(is.na(out$mw_tot), 0, out$mw_tot)
  out$mw_own <- ifelse(is.na(out$mw_own), 0, out$mw_own)
  out$mw_net <- pmax(out$mw_tot - out$mw_own, 0)
  out$slope  <- out$mw_net / (2 * BANDWIDTH_H)

  out |> select(date, period, marginal_unit, p_star, q_i, slope, split, identity_gap)
}

# ============================================================================
# BUILD
# ============================================================================

hy <- hydro_units_with_basin()
mapped <- hy |> filter(!is.na(basin))
target_units <- mapped$unit
basin_of <- setNames(mapped$basin, mapped$unit)

cat(sprintf("target set: %d hydro_ugh units with an identified basin\n\n",
            length(target_units)))

px <- load_prices()
files <- sort(list.files(file.path(DATA, "omie/bids/parquet"),
                          pattern = "^bids_.*\\.parquet$", full.names = TRUE))

cat("BUILDING PANEL — one pass over the bid archive (this is the slow part)\n")
panel <- map_dfr(seq_along(files), function(i) {
  r <- process_month(files[i], px, target_units)
  cat(sprintf("  [%3d/%3d] %s  %s periods\n", i, length(files),
              basename(files[i]), ifelse(is.null(r), 0, nrow(r))))
  r
})

n_raw <- nrow(panel)
panel <- panel |> filter(!split, identity_gap <= IDENTITY_TOL, slope > 0)
cat(sprintf("\nperiods: %d marginal-hydro raw -> %d after dropping split/identity/zero-slope periods\n",
            n_raw, nrow(panel)))

qc <- contract_position(target_units)
panel <- panel |> left_join(qc, by = c("date" = "date", "period" = "period",
                                        "marginal_unit" = "unit"))
panel$qc <- ifelse(is.na(panel$qc), 0, panel$qc)
cat(sprintf("contract position (PDBF role 4) matched: %.1f%% of unit-periods\n\n",
            100 * mean(panel$qc > 0)))

panel$c <- panel$p_star - (panel$q_i - panel$qc) / panel$slope

panel$basin <- basin_of[panel$marginal_unit]
panel$month <- format(panel$date, "%Y-%m")
vol <- basin_volume_level()
pf  <- front_quarter_forward()
panel <- panel |> left_join(vol, by = c("basin", "month")) |>
  left_join(pf, by = "month") |>
  filter(!is.na(vol), !is.na(pf), !is.na(c))

cat(sprintf("pre-filter sample: %d unit-periods, %d units\n", nrow(panel),
            n_distinct(panel$marginal_unit)))
cat("implied opportunity cost c, EUR/MWh, before the outlier fix:\n")
print(summary(panel$c))

# ---- outlier fix, at the source (same diagnosis as the Python build) ------

n_pre <- nrow(panel)
slope_floor <- quantile(panel$slope, SLOPE_PCTL)
n_thin <- sum(panel$slope < slope_floor)
n_lowp <- sum(panel$p_star <= ZERO_PRICE)
panel <- panel |> filter(slope >= slope_floor, p_star > ZERO_PRICE)

cat(sprintf("\ndropped %d periods with slope below its p%d (%.2f MW/EUR) -- the near-zero-slope blowups\n",
            n_thin, as.integer(SLOPE_PCTL * 100), slope_floor))
cat(sprintf("dropped %d periods with p_star <= %g EUR/MWh -- curtailment/must-run, not a cost-revealing bid\n",
            n_lowp, ZERO_PRICE))
cat(sprintf("final estimation sample: %d of %d unit-periods\n\n",
            nrow(panel), n_pre))

cat("implied opportunity cost c, EUR/MWh, after the fix:\n")
print(summary(panel$c))
cat(sprintf("negative c remaining: %.2f%%\n\n", 100 * mean(panel$c < 0)))

panel$marginal_unit <- factor(panel$marginal_unit)
cat(sprintf("units retained: %d\n\n", n_distinct(panel$marginal_unit)))

# ============================================================================
# REGRESSION
# ============================================================================

cat(strrep("=", 72), "\n")
cat("REGRESSION: c_it = b0 + b1*pf_t + b2*Vol_it + e_it\n")
cat("(residual-demand slope now netted for the marginal unit's own offers)\n")
cat(strrep("=", 72), "\n")

report_cluster <- function(fit, label, vars) {
  ct <- coeftest(fit, vcov = vcovCL(fit, cluster = panel$marginal_unit, type = "HC1"))
  cat(sprintf("\n%s\n", label))
  print(ct[vars, , drop = FALSE])
}

m_pooled <- lm(c ~ pf + vol, data = panel)
report_cluster(m_pooled, "POOLED (Arzhintar et al.'s own spec, asymptotic cluster SE)",
                c("(Intercept)", "pf", "vol"))

m_fe <- lm(c ~ pf + vol + marginal_unit, data = panel)
report_cluster(m_fe, "WITH UNIT FIXED EFFECTS, asymptotic cluster SE",
                c("(Intercept)", "pf", "vol"))

# ---- cluster (pairs) bootstrap, fix 2: too few clusters for the asymptotic
#      cluster-robust SE above to be fully trusted -----------------------

cat(sprintf("\n%s\nCLUSTER BOOTSTRAP (%d reps, resampling the %d cascades with replacement)\n%s\n",
            strrep("-", 72), N_BOOT, n_distinct(panel$marginal_unit), strrep("-", 72)))

units_list <- levels(panel$marginal_unit)
panel_by_unit <- split(panel, panel$marginal_unit)

boot_stat <- function(formula) {
  function(data_ignored, idx) {
    resampled <- bind_rows(panel_by_unit[units_list[idx]])
    resampled$marginal_unit <- factor(resampled$marginal_unit)
    fit <- tryCatch(lm(formula, data = resampled), error = function(e) NULL)
    if (is.null(fit) || !all(c("pf", "vol") %in% names(coef(fit))))
      return(c(NA_real_, NA_real_))
    coef(fit)[c("pf", "vol")]
  }
}

set.seed(20260819)
idx_dummy <- seq_along(units_list)
b_pooled <- boot(idx_dummy, boot_stat(c ~ pf + vol), R = N_BOOT)
b_fe     <- boot(idx_dummy, boot_stat(c ~ pf + vol + marginal_unit), R = N_BOOT)

summarise_boot <- function(b, label) {
  ok <- complete.cases(b$t)
  cat(sprintf("\n%s (%d/%d valid replications, %d resamples had <2 unique clusters and were skipped)\n",
              label, sum(ok), N_BOOT, N_BOOT - sum(ok)))
  for (j in 1:2) {
    nm <- c("pf", "vol")[j]
    est <- b$t0[j]
    se  <- sd(b$t[ok, j])
    ci  <- quantile(b$t[ok, j], c(0.025, 0.975))
    cat(sprintf("  %-4s point est %8.4f   boot SE %7.4f   95%% percentile CI [%8.4f, %8.4f]\n",
                nm, est, se, ci[1], ci[2]))
  }
}

summarise_boot(b_pooled, "POOLED")
summarise_boot(b_fe, "WITH UNIT FIXED EFFECTS")

cat("\nREAD: the cluster bootstrap resamples whole cascades (not rows), so it\n",
    "respects the within-unit dependence the correction exists to address --\n",
    "the standard fix for few-cluster inference (Cameron, Gelbach & Miller\n",
    "2008). Compare its SE/CI to the asymptotic cluster-robust ones above: if\n",
    "they broadly agree, the small number of clusters was not distorting\n",
    "inference much; if the bootstrap interval is much wider, trust it over\n",
    "the asymptotic one.\n",
    "\nb1 > 0: opportunity cost rises with the forward price (near-complete\n",
    "passthrough of expectations, as Arzhintar et al. find, b1~1.26). b2 < 0:\n",
    "fuller reservoirs imply a LOWER opportunity cost -- the textbook\n",
    "scarcity prediction. See `notes/hydro-water-value-design.md` for the\n",
    "full comparison across specifications.\n", sep = "")

OUT <- file.path(ROOT, "outputs", "tables")
if (!dir.exists(OUT)) dir.create(OUT, recursive = TRUE)
write_parquet(panel, file.path(OUT, "hydro_water_value_structural_panel_R.parquet"))
cat(sprintf("\nwrote %s\n", file.path(OUT, "hydro_water_value_structural_panel_R.parquet")))
