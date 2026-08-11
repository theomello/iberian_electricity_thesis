#!/usr/bin/env Rscript
# Exploratory look at the Spain / MIBEL datasets.
#
# Run it from a live R session -- RStudio, or `R` in a terminal -- started
# anywhere inside the repo:
#
#   source("scripts/analysis/descriptives.R")
#
# Note that `Rscript file.R` and `R -e 'source(...)'` are both NON-interactive
# (interactive() is FALSE in each), so neither will work; see the guard below.
#
# NOTHING IS WRITTEN TO DISK -- no figures, no tables, no directories. Every
# exhibit is printed to the active graphics device and every summary to the
# console. That is deliberate: the point right now is to see what the data
# looks like before committing to a research question, not to produce output.
#
# It refuses to run under `Rscript`, because a non-interactive session has no
# graphics device and ggplot would silently dump an Rplots.pdf into the working
# directory -- which is exactly the saving this script is meant to avoid.
#
# The objects it leaves in the global environment are the point of the
# exercise; see the closing message. `panel` in particular is an hourly
# price/load/VRE frame, the natural starting shape for a regression sample.
#
# The two bid archives are ~913 M rows combined, far past memory. They are
# opened with arrow::open_dataset() so that dplyr verbs are pushed down into
# Arrow and only the aggregated result is ever collected.
#
# Four data traps are handled explicitly here; see CLAUDE.md for the full set.
#   1. `O` and `C` bid rows are NOT additive -- `O` is the submitted curve,
#      `C` the cleared portion. Filter to one; never sum across both.
#   2. Energy is `power_mw * resolution_min / 60`, because the market moved
#      from hourly to 15-minute settlement on 2025-10-01.
#   3. REE's generation table includes `Total generation` as a *series*;
#      summing all series double-counts.
#   4. Local clocks differ (Madrid vs Lisbon) and DST days have 23/25 hours,
#      so anything joined across sources is joined on `utc_timestamp`.

suppressPackageStartupMessages({
  library(arrow); library(dplyr); library(ggplot2); library(tidyr); library(scales)
})

# ---- controls ----------------------------------------------------------------
# Edit these before sourcing, or set them in the console first -- they are only
# assigned here if they do not already exist.
if (!exists("SECTIONS")) SECTIONS <- 1:7   # which sections to run
if (!exists("PAUSE"))    PAUSE    <- TRUE  # wait for Enter between figures
if (!exists("HEAVY"))    HEAVY    <- FALSE # scan the full 913 M-row bid archive

if (!interactive()) {
  stop("this script displays plots instead of saving them, so it needs a live ",
       "R session.\n",
       "  Start R (or RStudio) and then:  source(\"scripts/analysis/descriptives.R\")\n",
       "  `Rscript` and `R -e` are both non-interactive -- they would write an ",
       "Rplots.pdf instead of drawing.")
}

# ---- repo root ---------------------------------------------------------------
# Under Rscript the script's own path is in `--file=`; when the file is sourced
# interactively there is no such argument, so fall back to walking up from the
# working directory. Both routes climb until a directory looks like the repo --
# resolving to plain getwd() instead pointed DATA at scripts/data when sourced
# from scripts/, and failed with a bare "No such file or directory".
find_root <- function(start) {
  d <- normalizePath(start, mustWork = FALSE)
  repeat {
    if (all(file.exists(file.path(d, c("CLAUDE.md", "scripts"))))) return(d)
    parent <- dirname(d)
    if (parent == d) return(NA_character_)
    d <- parent
  }
}
script_path <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
ROOT <- if (!is.na(script_path)) find_root(dirname(script_path)) else NA_character_
if (is.na(ROOT)) ROOT <- find_root(getwd())
if (is.na(ROOT)) stop("cannot locate the repo root above ", getwd(),
                      " -- run from inside the repo, or set ROOT by hand")
DATA <- file.path(ROOT, "data")
if (!dir.exists(DATA)) stop("no data/ under ", ROOT, " -- run the fetchers first")

# ---- palette -----------------------------------------------------------------
# Fixed categorical order; hues are assigned by slot and never cycled.
PAL <- c("#2a78d6", "#eb6834", "#1baf7a", "#eda100",
         "#e87ba4", "#008300", "#4a3aa7", "#e34948")
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUTED <- "#8a8983"
SURFACE <- "#fcfcfb"; GRID <- "#e6e5e1"

theme_vre <- function(base = 11) {
  theme_minimal(base_size = base) +
    theme(
      plot.background   = element_rect(fill = SURFACE, colour = NA),
      panel.background  = element_rect(fill = SURFACE, colour = NA),
      panel.grid.major  = element_line(colour = GRID, linewidth = 0.35),
      panel.grid.minor  = element_blank(),
      axis.title        = element_text(colour = INK2, size = rel(0.88)),
      axis.text         = element_text(colour = INK2, size = rel(0.85)),
      plot.title        = element_text(colour = INK, face = "bold", size = rel(1.18)),
      plot.subtitle     = element_text(colour = INK2, size = rel(0.92)),
      plot.caption      = element_text(colour = MUTED, size = rel(0.75), hjust = 0),
      legend.title      = element_blank(),
      legend.text       = element_text(colour = INK2, size = rel(0.85)),
      legend.position   = "top",
      legend.justification = "left",
      strip.text        = element_text(colour = INK, face = "bold", size = rel(0.9))
    )
}

# ---- display helpers (these replace the old save_fig / save_tab) -------------
FIGN <- 0L
show_fig <- function(p, note = "") {
  FIGN <<- FIGN + 1L
  print(p)
  cat("  [fig ", FIGN, "] ", note, "\n", sep = "")
  if (isTRUE(PAUSE)) invisible(readline("        press Enter for the next exhibit "))
}
show_tab <- function(d, digits = 4) print(as.data.frame(d), digits = digits)
rule <- function(x) cat("\n", strrep("=", 70), "\n", x, "\n", strrep("=", 70), "\n", sep = "")
run  <- function(n) n %in% SECTIONS

# Floor a UTC instant to its hour. Used for every cross-source join: local
# clocks differ between Madrid and Lisbon and DST days are 23 or 25 hours long,
# so UTC is the only safe key.
floor_hour <- function(t) {
  as.POSIXct(as.numeric(t) %/% 3600 * 3600, origin = "1970-01-01", tz = "UTC")
}

# ==============================================================================
# Prices, generation and the 5-minute series are all small enough to hold in
# memory, and later sections reuse them, so they load unconditionally. Only the
# bid archive is gated (section 4).
rule("LOADING")

px <- read_parquet(file.path(DATA, "omie/prices/omie_day_ahead_prices.parquet")) |>
  mutate(year = as.integer(format(date, "%Y")),
         month = as.Date(format(date, "%Y-%m-01")))
cat("  px   day-ahead prices     ", format(nrow(px), big.mark = ","), " rows\n", sep = "")

gen <- read_parquet(file.path(DATA, "ree/ree_generation_daily.parquet")) |>
  # `Total generation` is itself one of the 17 series -- summing all
  # double-counts and roughly halves any share computed from it.
  filter(series != "Total generation") |>
  mutate(year = as.integer(format(local_date, "%Y")))
cat("  gen  REE daily generation ", format(nrow(gen), big.mark = ","), " rows\n", sep = "")

rt <- read_parquet(
  file.path(DATA, "ree/ree_realtime_5min.parquet"),
  col_select = c("utc_timestamp", "local_date", "demand", "wind", "solar_pv",
                 "solar_total", "hydro", "nuclear", "combined_cycle")) |>
  mutate(
    # Local Madrid hour derived from the UTC instant. The older approach of
    # slicing the local timestamp string dropped the autumn DST hour, which is
    # written `2A`/`2B` and is not numeric.
    hour_local = as.integer(format(utc_timestamp, "%H", tz = "Europe/Madrid")),
    month_num  = as.integer(format(local_date, "%m")),
    year       = as.integer(format(local_date, "%Y")))
cat("  rt   REE 5-minute         ", format(nrow(rt), big.mark = ","), " rows\n", sep = "")

reg <- read_parquet(file.path(DATA, "omie/registry/unit_registry.parquet"))
cat("  reg  unit registry        ", format(nrow(reg), big.mark = ","), " rows\n", sep = "")

# ==============================================================================
if (run(1)) {
rule("1. DAY-AHEAD PRICES")

price_year <- px |>
  group_by(year) |>
  summarise(
    periods      = n(),
    mean_es      = mean(price_es), median_es = median(price_es),
    sd_es        = sd(price_es),
    p05          = quantile(price_es, .05), p95 = quantile(price_es, .95),
    min_es       = min(price_es), max_es = max(price_es),
    pct_zero_neg = mean(price_es <= 0) * 100,
    pct_split    = mean(price_es != price_pt) * 100,
    .groups = "drop"
  )
show_tab(price_year)

pm <- px |> group_by(month) |> summarise(ES = mean(price_es), PT = mean(price_pt),
                                         .groups = "drop") |>
  pivot_longer(c(ES, PT), names_to = "zone", values_to = "eur")

show_fig(
  ggplot(pm, aes(month, eur, colour = zone)) +
    geom_line(linewidth = 0.7) +
    scale_colour_manual(values = c(ES = PAL[1], PT = PAL[2])) +
    scale_y_continuous(labels = label_number(suffix = " EUR")) +
    labs(title = "MIBEL day-ahead price, monthly mean",
         subtitle = "Spain and Portugal clear jointly; the two diverge only when the interconnection binds",
         x = NULL, y = "EUR/MWh",
         caption = "Source: OMIE marginalpdbc. Monthly mean of hourly (to 2025-09) then 15-minute prices.") +
    theme_vre(),
  "the 2021-22 gas shock dominates the series -- any level regression needs a fuel-cost control")

# Zero and negative prices: a structural feature of high-VRE systems, and the
# reason a plain linear model of the price level will be misspecified at the
# bottom of the distribution.
zn <- px |> group_by(year) |>
  summarise(`negative (< 0)` = mean(price_es < 0) * 100,
            `zero (= 0)`     = mean(price_es == 0) * 100, .groups = "drop") |>
  pivot_longer(-year, names_to = "kind", values_to = "pct")

show_fig(
  ggplot(zn, aes(factor(year), pct, fill = kind)) +
    geom_col(width = 0.62, position = position_stack()) +
    scale_fill_manual(values = c(`negative (< 0)` = PAL[1], `zero (= 0)` = PAL[3])) +
    scale_y_continuous(labels = label_number(suffix = "%")) +
    labs(title = "Share of periods at or below zero, Spain",
         subtitle = "Zero and negative prices are the visible symptom of surplus renewable supply",
         x = NULL, y = "share of periods",
         caption = "Source: OMIE. 2026 covers January-May only.") +
    theme_vre(),
  "the mass at exactly zero is censoring, not noise -- it concentrates in the recent years")

# Where the distribution actually sits, year by year. The tail runs to the
# +/-500 EUR/MWh technical bounds, so the x-axis is clipped.
show_fig(
  ggplot(px, aes(price_es)) +
    geom_histogram(bins = 80, fill = PAL[1], colour = NA) +
    geom_vline(xintercept = 0, colour = PAL[2], linewidth = 0.4) +
    facet_wrap(~year, scales = "free_y") +
    coord_cartesian(xlim = c(-20, 300)) +
    labs(title = "Price distribution by year, Spain",
         subtitle = "Shape changes far more than the mean does -- 2021-22 is a different distribution, not a shifted one",
         x = "EUR/MWh", y = "periods",
         caption = "Source: OMIE. X clipped to [-20, 300]; offers and prices reach the +/-500 bounds.") +
    theme_vre(),
  "a spike at zero plus a long right tail: consider logs, quantile regression, or a censored model")
}

# ==============================================================================
if (run(2)) {
rule("2. GENERATION MIX")

gen_year <- gen |> group_by(year, series) |>
  summarise(twh = sum(value) / 1e6, .groups = "drop")
gen_tot <- gen_year |> group_by(year) |> summarise(total = sum(twh), .groups = "drop")

vre_es <- gen_year |>
  filter(series %in% c("Wind", "Solar photovoltaic", "Thermal solar")) |>
  group_by(year) |> summarise(vre = sum(twh), .groups = "drop") |>
  left_join(gen_tot, by = "year") |> mutate(share = vre / total * 100, zone = "Spain")

prod_pt <- read_parquet(file.path(DATA, "ren/ren_production_15min.parquet")) |>
  mutate(year = as.integer(format(local_date, "%Y")))
GEN_PT <- c("Hydro", "Wind", "Solar", "Natural Gas", "Coal", "Biomass",
            "Wave", "Other Thermal")
pt_year <- prod_pt |> filter(series %in% GEN_PT) |> group_by(year, series) |>
  summarise(twh = sum(value_mw) * 0.25 / 1e6, .groups = "drop")
vre_pt <- pt_year |> filter(series %in% c("Wind", "Solar")) |>
  group_by(year) |> summarise(vre = sum(twh), .groups = "drop") |>
  left_join(pt_year |> group_by(year) |> summarise(total = sum(twh), .groups = "drop"),
            by = "year") |>
  mutate(share = vre / total * 100, zone = "Portugal")

vre <- bind_rows(vre_es, vre_pt) |> filter(year < 2026)
show_tab(vre |> select(zone, year, vre, total, share))

show_fig(
  ggplot(vre, aes(year, share, colour = zone)) +
    geom_line(linewidth = 0.8) + geom_point(size = 2.1) +
    scale_colour_manual(values = c(Spain = PAL[1], Portugal = PAL[2])) +
    scale_y_continuous(labels = label_number(suffix = "%"), limits = c(0, NA)) +
    scale_x_continuous(breaks = unique(vre$year)) +
    labs(title = "Wind and solar share of generation",
         subtitle = "Both markets roughly doubled VRE penetration over the window",
         x = NULL, y = "share of generation",
         caption = "Sources: REE estructura-generacion (ES), REN production breakdown (PT). 2026 excluded (partial year).") +
    theme_vre(),
  "the trend is smooth and slow -- identification off the annual trend alone will be weak")

mix <- gen_year |> filter(year < 2026) |>
  mutate(tech = case_when(
    series %in% c("Wind") ~ "Wind",
    series %in% c("Solar photovoltaic", "Thermal solar") ~ "Solar",
    series == "Hydro" ~ "Hydro",
    series == "Nuclear" ~ "Nuclear",
    series == "Combined cycle" ~ "Combined cycle",
    series == "Coal" ~ "Coal",
    TRUE ~ "Other")) |>
  group_by(year, tech) |> summarise(twh = sum(twh), .groups = "drop") |>
  mutate(tech = factor(tech, levels = c("Wind", "Solar", "Hydro", "Nuclear",
                                        "Combined cycle", "Coal", "Other")))

show_fig(
  ggplot(mix, aes(factor(year), twh, fill = tech)) +
    geom_col(width = 0.68, colour = SURFACE, linewidth = 0.4) +
    scale_fill_manual(values = setNames(PAL[1:7], levels(mix$tech))) +
    labs(title = "Spanish generation mix", subtitle = "TWh per year, components only",
         x = NULL, y = "TWh",
         caption = "Source: REE. `Total generation` excluded -- it is published as a series alongside its own components.") +
    theme_vre() + guides(fill = guide_legend(nrow = 1)),
  "coal exits and solar enters mid-window: two structural breaks a pooled model would have to absorb")
}

# ==============================================================================
if (run(3)) {
rule("3. DIURNAL SHAPE (5-minute)")

prof <- rt |>
  mutate(season = factor(ifelse(month_num %in% c(12, 1, 2), "Winter",
                         ifelse(month_num %in% 3:5, "Spring",
                         ifelse(month_num %in% 6:8, "Summer", "Autumn"))),
                         levels = c("Winter", "Spring", "Summer", "Autumn"))) |>
  group_by(season, hour_local) |>
  summarise(Demand = mean(demand, na.rm = TRUE),
            Wind = mean(wind, na.rm = TRUE),
            `Solar PV` = mean(solar_pv, na.rm = TRUE),
            `Net load` = mean(demand - wind - solar_total, na.rm = TRUE),
            .groups = "drop") |>
  pivot_longer(c(Demand, Wind, `Solar PV`, `Net load`),
               names_to = "series", values_to = "mw")

show_fig(
  ggplot(prof, aes(hour_local, mw, colour = series)) +
    geom_line(linewidth = 0.7) +
    facet_wrap(~season, nrow = 1) +
    scale_colour_manual(values = c(Demand = PAL[1], Wind = PAL[3],
                                   `Solar PV` = PAL[4], `Net load` = PAL[8])) +
    scale_x_continuous(breaks = c(0, 6, 12, 18)) +
    scale_y_continuous(labels = label_number(scale = 1e-3, suffix = " GW")) +
    labs(title = "Average day, Spain",
         subtitle = "Mean MW by local hour, 2018-2026. Net load = demand - wind - solar",
         x = "hour (local Madrid)", y = "MW",
         caption = "Source: REE demanda.ree.es, 5-minute. Hour derived from utc_timestamp, so DST days are kept.") +
    theme_vre(),
  "the midday net-load trough is the duck curve -- hour-of-day fixed effects are unavoidable")

# How much the shape has moved. Same object, split by year rather than season.
prof_yr <- rt |>
  filter(year %in% c(2018, 2021, 2024, 2025)) |>
  group_by(year, hour_local) |>
  summarise(net = mean(demand - wind - solar_total, na.rm = TRUE), .groups = "drop")

show_fig(
  ggplot(prof_yr, aes(hour_local, net, colour = factor(year))) +
    geom_line(linewidth = 0.8) +
    scale_colour_manual(values = PAL[c(1, 3, 4, 2)]) +
    scale_x_continuous(breaks = c(0, 6, 12, 18)) +
    scale_y_continuous(labels = label_number(scale = 1e-3, suffix = " GW")) +
    labs(title = "Net load by local hour, selected years",
         subtitle = "The midday trough deepens as solar builds out -- the variation a design would exploit",
         x = "hour (local Madrid)", y = "net load (MW)",
         caption = "Source: REE 5-minute. Net load = demand - wind - solar_total.") +
    theme_vre(),
  "midday and evening hours move in opposite directions: pooling them would average the effect away")
}

# ==============================================================================
if (run(4)) {
rule("4. BID CURVES -- the distinctive dataset")

# One hour, submitted curves. `status == 'O'` is the full submitted curve;
# `C` rows are the cleared portion and must never be summed with `O`.
# Reading the single month file rather than the whole archive keeps this fast.
DAY <- as.Date("2024-01-15"); PERIOD <- 12L
one <- open_dataset(file.path(DATA, "omie/bids/parquet",
                              sprintf("bids_%s.parquet", format(DAY, "%Y%m")))) |>
  filter(date == DAY, period == PERIOD, status == "O") |>
  select(side, power_mw, price_eur_mwh) |>
  collect()

# Supply is cumulated cheapest-first, demand most-valuable-first. Sorting on a
# signed key does both in one arrange -- a conditional inside arrange() would
# be evaluated once for the whole frame, not per side, and silently sort the
# demand curve backwards.
curve <- one |>
  mutate(sort_key = ifelse(side == "V", price_eur_mwh, -price_eur_mwh)) |>
  group_by(side) |>
  arrange(sort_key, .by_group = TRUE) |>
  mutate(cum_gw = cumsum(power_mw) / 1000) |>
  ungroup() |>
  mutate(curve = ifelse(side == "V", "Supply (sell offers)", "Demand (buy bids)"))

clear <- px |> filter(date == DAY, period == PERIOD) |> pull(price_es)

show_fig(
  ggplot(curve, aes(cum_gw, price_eur_mwh, colour = curve)) +
    geom_step(linewidth = 0.8) +
    geom_hline(yintercept = clear, colour = MUTED, linetype = "dashed", linewidth = 0.5) +
    annotate("text", x = max(curve$cum_gw) * 0.98, y = clear, vjust = -0.7, hjust = 1,
             label = paste0("clearing price ", format(clear, nsmall = 2), " EUR/MWh"),
             colour = INK2, size = 3.1) +
    scale_colour_manual(values = c(`Supply (sell offers)` = PAL[1],
                                   `Demand (buy bids)` = PAL[2])) +
    coord_cartesian(ylim = c(-10, 200)) +
    labs(title = paste0("Submitted bid curves, ", format(DAY), " hour ", PERIOD),
         subtitle = "Every offer from every unit, accepted and rejected -- the object a bid-based market makes observable",
         x = "cumulative GW offered", y = "EUR/MWh",
         caption = "Source: OMIE curva_pbc_uof, status == 'O' (submitted). Y clipped to [-10, 200]; offers run to the +/-500 bounds.") +
    theme_vre(),
  "the slope around the crossing is the residual supply elasticity -- unit-level and estimable")

if (isTRUE(HEAVY)) {
  # Offered vs cleared volume, monthly -- the gap is unaccepted supply. This
  # sweeps all 101 files (~350 M rows) and takes minutes; HEAVY gates it.
  cat("  scanning the full bid archive -- this takes a few minutes ...\n")
  bids <- open_dataset(file.path(DATA, "omie/bids/parquet"))
  supply <- bids |>
    filter(side == "V") |>
    mutate(ym = strftime(date, "%Y-%m")) |>
    group_by(ym, status) |>
    summarise(twh = sum(power_mw * resolution_min / 60, na.rm = TRUE) / 1e6,
              .groups = "drop") |>
    collect() |>
    mutate(month = as.Date(paste0(ym, "-01")),
           status = ifelse(status == "O", "Offered", "Cleared"))

  show_fig(
    ggplot(supply, aes(month, twh, colour = status)) +
      geom_line(linewidth = 0.7) +
      scale_colour_manual(values = c(Offered = PAL[1], Cleared = PAL[2])) +
      labs(title = "Sell-side volume offered vs cleared, day-ahead",
           subtitle = "The gap between the two is unaccepted supply -- invisible in markets that publish only outcomes",
           x = NULL, y = "TWh per month",
           caption = "Source: OMIE curva_pbc_uof. Energy = power_mw x resolution_min / 60. Archive stops 2026-05-08.") +
      theme_vre(),
    "offered volume is itself a choice variable -- a dependent variable, not just a control")
} else {
  cat("  HEAVY is FALSE -- skipping the full-archive offered-vs-cleared sweep.\n",
      "  Set HEAVY <- TRUE before sourcing to include it (a few minutes).\n", sep = "")
}
}

# ==============================================================================
if (run(5)) {
rule("5. UNIT REGISTRY")

# role separates generators from retailers, which is what any supply-curve or
# bidding work needs. There is no fuel or technology here, and no capacity.
show_tab(reg |> count(country, role, name = "units") |> arrange(desc(units)))

show_fig(
  ggplot(reg |> filter(!is.na(role), !is.na(country)) |> count(country, role),
         aes(reorder(role, n), n, fill = country)) +
    geom_col(width = 0.65) +
    coord_flip() +
    scale_fill_manual(values = c(ES = PAL[1], PT = PAL[2])) +
    labs(title = "Units by role and country",
         subtitle = "ES and PT unit sets are disjoint, so country is a clean assignment",
         x = NULL, y = "units",
         caption = "Source: unit_registry.parquet, built from pdbc / pdbcpt / pdbce on a 2-day-per-month sample.") +
    theme_vre(),
  "3,673 generation units is the cross-sectional dimension a panel would run over")

# How long each unit is actually observed -- the binding constraint on any
# unit-level panel is not the calendar but entry and exit.
show_fig(
  ggplot(reg, aes(days_observed)) +
    geom_histogram(bins = 60, fill = PAL[1], colour = NA) +
    labs(title = "Days each unit is observed",
         subtitle = "A balanced unit panel would be far smaller than the 5,049 units the registry lists",
         x = "days observed (of the sampled days)", y = "units",
         caption = "Source: unit_registry.parquet. Sampling is 2 days per month, so this is a relative measure.") +
    theme_vre(),
  "heavy entry/exit -- decide early whether the panel is balanced, and at what cost")
}

# ==============================================================================
if (run(6)) {
rule("6. COVERAGE -- what window is jointly usable")

span <- function(name, from, to, kind = "series") {
  tibble::tibble(dataset = name, from = as.Date(from), to = as.Date(to), kind = kind)
}
bid_files <- list.files(file.path(DATA, "omie/bids/parquet"), "\\.parquet$")
bid_last  <- open_dataset(file.path(DATA, "omie/bids/parquet",
                                    tail(sort(bid_files), 1))) |>
  summarise(m = max(date)) |> collect() |> pull(m)

cover <- bind_rows(
  span("OMIE day-ahead bids", min(px$date), bid_last),
  span("OMIE prices",         min(px$date), max(px$date)),
  span("REE 5-minute",        min(rt$local_date), max(rt$local_date)),
  span("REE daily generation", min(gen$local_date), max(gen$local_date)),
  # The registry is an attribute table built from a 2-day-per-month sample, so
  # its last_seen is the last sampled day (the 1st or 16th), not a publication
  # frontier. It must not enter the joint-window calculation.
  span("Unit registry (sampled)", min(reg$first_seen), max(reg$last_seen), "attribute")
) |> mutate(dataset = factor(dataset, levels = rev(dataset)))

joint_end <- min(cover$to[cover$kind == "series"])
show_tab(cover |> mutate(days = as.integer(to - from)))
cat("\n  Jointly usable window ends ", format(joint_end),
    " -- the bid archive's ~3-month publication lag is the binding constraint.\n",
    "  (The registry is excluded: its end date is a sampling artefact.)\n", sep = "")

show_fig(
  ggplot(cover, aes(y = dataset)) +
    geom_segment(aes(x = from, xend = to, yend = dataset, colour = kind),
                 linewidth = 4, lineend = "round") +
    scale_colour_manual(values = c(series = PAL[1], attribute = MUTED)) +
    geom_vline(xintercept = joint_end, colour = PAL[2], linetype = "dashed") +
    annotate("text", x = joint_end, y = 0.6, label = paste(" joint end", format(joint_end)),
             hjust = 0, colour = PAL[2], size = 3.1) +
    labs(title = "Dataset coverage",
         subtitle = "Everything else runs to 2026-05-31; the bid archive stops short and sets the estimation window",
         x = NULL, y = NULL,
         caption = "Source: the files themselves. Bid frontier read from the last month file.") +
    theme_vre(),
  "any design using bids is capped at the shorter window -- worth fixing the sample now")
}

# ==============================================================================
if (run(7)) {
rule("7. TOWARD A REGRESSION SAMPLE")

# An hourly panel joined on UTC. Prices are averaged within the hour, which is
# exact for the hourly era and the correct equal-weight mean over the four MTUs
# after 2025-10-01. REE 5-minute MW are averaged, so the column is mean MW over
# the hour -- numerically MWh for a one-hour step.
px_h <- px |>
  mutate(hour_utc = floor_hour(utc_timestamp)) |>
  group_by(hour_utc) |>
  summarise(price_es = mean(price_es), price_pt = mean(price_pt),
            split = as.integer(any(price_es != price_pt)), .groups = "drop")

rt_h <- rt |>
  mutate(hour_utc = floor_hour(utc_timestamp)) |>
  group_by(hour_utc) |>
  summarise(demand = mean(demand, na.rm = TRUE),
            wind   = mean(wind, na.rm = TRUE),
            solar  = mean(solar_total, na.rm = TRUE),
            hydro  = mean(hydro, na.rm = TRUE),
            nuclear = mean(nuclear, na.rm = TRUE),
            ccgt   = mean(combined_cycle, na.rm = TRUE),
            n_obs  = n(), .groups = "drop") |>
  filter(n_obs >= 10)   # drop part-hours at the edges of the archive

panel <- inner_join(px_h, rt_h, by = "hour_utc") |>
  mutate(net_load  = demand - wind - solar,
         vre_share = (wind + solar) / demand * 100,
         hour_local = as.integer(format(hour_utc, "%H", tz = "Europe/Madrid")),
         date       = as.Date(format(hour_utc, "%Y-%m-%d", tz = "Europe/Madrid")),
         year       = as.integer(format(hour_utc, "%Y", tz = "Europe/Madrid")),
         dow        = format(hour_utc, "%a", tz = "Europe/Madrid")) |>
  arrange(hour_utc)

cat("  panel: ", format(nrow(panel), big.mark = ","), " hourly rows, ",
    format(min(panel$date)), " to ", format(max(panel$date)), "\n", sep = "")
show_tab(panel |>
  summarise(across(c(price_es, demand, wind, solar, net_load, vre_share),
                   list(mean = ~mean(.x), sd = ~sd(.x), min = ~min(.x), max = ~max(.x)))) |>
  pivot_longer(everything(), names_to = "stat") |>
  separate(stat, c("variable", "stat"), sep = "_(?=[^_]+$)") |>
  pivot_wider(names_from = stat, values_from = value))

# The merit-order relationship, binned rather than scattered so 70k points stay
# legible. Colouring by year separates the level shift (gas costs) from the
# slope (the thing a merit-order design is actually after).
bins <- panel |>
  mutate(nl_bin = cut(net_load, breaks = seq(0, 45000, by = 2500))) |>
  filter(!is.na(nl_bin)) |>
  group_by(year, nl_bin) |>
  summarise(net_load = mean(net_load), price = median(price_es), n = n(),
            .groups = "drop") |>
  filter(n >= 30)

show_fig(
  ggplot(bins, aes(net_load, price, colour = factor(year))) +
    geom_line(linewidth = 0.7) + geom_point(size = 1.3) +
    scale_colour_manual(values = rep(PAL, 2)[seq_len(length(unique(bins$year)))]) +
    scale_x_continuous(labels = label_number(scale = 1e-3, suffix = " GW")) +
    labs(title = "Price against net load, by year",
         subtitle = "Median price within 2.5 GW net-load bins. The curve shifts vertically with fuel costs and steepens at the top",
         x = "net load (demand - wind - solar)", y = "EUR/MWh",
         caption = "Sources: OMIE prices + REE 5-minute, joined hourly on UTC. Bins with fewer than 30 hours dropped.") +
    theme_vre(),
  "same slope, different intercepts -- year (or fuel-cost) controls are doing real work here")

# Hour-of-day x year heat map of the mean price: the seasonal-plus-diurnal
# structure any specification has to absorb before it can claim a causal effect.
hm <- panel |> group_by(year, hour_local) |>
  summarise(price = mean(price_es), .groups = "drop")

show_fig(
  ggplot(hm, aes(hour_local, factor(year), fill = price)) +
    geom_tile(colour = SURFACE, linewidth = 0.3) +
    scale_fill_gradient(low = SURFACE, high = PAL[1], labels = label_number(suffix = " EUR")) +
    scale_x_continuous(breaks = c(0, 6, 12, 18, 23)) +
    labs(title = "Mean price by local hour and year",
         subtitle = "The midday dip appears late in the window -- solar rewrote the intraday price shape",
         x = "hour (local Madrid)", y = NULL,
         caption = "Sources: OMIE prices + REE, hourly panel.") +
    theme_vre() + theme(legend.title = element_blank()),
  "the treatment-like variation is within-day and recent, not across the whole 2018-2026 span")
}

# ==============================================================================
cat("\n", strrep("-", 70), "\n", sep = "")
cat("Nothing was written to disk. Objects left in the environment:\n\n")
cat("  px     day-ahead prices, period level, with year/month\n")
cat("  gen    REE daily generation, `Total generation` already excluded\n")
cat("  rt     REE 5-minute, with a DST-correct local hour\n")
cat("  reg    unit registry, 5,049 units with country and role\n")
if (run(7)) cat("  panel  hourly price + load + VRE frame, joined on UTC -- the regression base\n")
cat("\nControls:  SECTIONS <- ", deparse(SECTIONS), "   PAUSE <- ", PAUSE,
    "   HEAVY <- ", HEAVY, "\n", sep = "")
cat("Re-run one section only, e.g.:  SECTIONS <- 7; source(\"scripts/analysis/descriptives.R\")\n")
