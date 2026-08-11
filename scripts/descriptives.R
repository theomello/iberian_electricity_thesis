#!/usr/bin/env Rscript
# Descriptive statistics and exhibits for the Spain / MIBEL datasets.
#
#   Rscript scripts/descriptives.R
#
# Writes tables to outputs/tables/ and figures to outputs/figures/.
#
# The two bid archives are ~913 M rows combined, far past memory. They are
# opened with arrow::open_dataset() so that dplyr verbs are pushed down into
# Arrow and only the aggregated result is ever collected.
#
# Three data traps are handled explicitly here; see CLAUDE.md for the full set.
#   1. `O` and `C` bid rows are NOT additive -- `O` is the submitted curve,
#      `C` the cleared portion. Filter to one; never sum across both.
#   2. Energy is `power_mw * resolution_min / 60`, because the market moved
#      from hourly to 15-minute settlement on 2025-10-01.
#   3. REE's generation table includes `Total generation` as a *series*;
#      summing all series double-counts.

suppressPackageStartupMessages({
  library(arrow); library(dplyr); library(ggplot2); library(tidyr); library(scales)
})

ROOT    <- normalizePath(file.path(dirname(sub("--file=", "",
             grep("--file=", commandArgs(FALSE), value = TRUE)[1])), ".."))
if (is.na(ROOT) || !dir.exists(ROOT)) ROOT <- normalizePath(".")
DATA    <- file.path(ROOT, "data")
FIGS    <- file.path(ROOT, "outputs", "figures")
TABLES  <- file.path(ROOT, "outputs", "tables")
dir.create(FIGS, recursive = TRUE, showWarnings = FALSE)
dir.create(TABLES, recursive = TRUE, showWarnings = FALSE)

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
save_fig <- function(p, name, w = 10, h = 5.6) {
  ggsave(file.path(FIGS, paste0(name, ".png")), p, width = w, height = h,
         dpi = 200, bg = SURFACE)
  cat("  figure ->", name, ".png\n", sep = "")
}
save_tab <- function(d, name) {
  write.csv(d, file.path(TABLES, paste0(name, ".csv")), row.names = FALSE)
  cat("  table  ->", name, ".csv\n", sep = "")
}
rule <- function(x) cat("\n", strrep("=", 70), "\n", x, "\n", strrep("=", 70), "\n", sep = "")

# ==============================================================================
rule("1. DAY-AHEAD PRICES")

px <- read_parquet(file.path(DATA, "omie/prices/omie_day_ahead_prices.parquet")) |>
  mutate(year = as.integer(format(date, "%Y")),
         month = as.Date(format(date, "%Y-%m-01")))

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
print(as.data.frame(price_year), digits = 4)
save_tab(price_year, "price_by_year")

pm <- px |> group_by(month) |> summarise(ES = mean(price_es), PT = mean(price_pt),
                                         .groups = "drop") |>
  pivot_longer(c(ES, PT), names_to = "zone", values_to = "eur")

p1 <- ggplot(pm, aes(month, eur, colour = zone)) +
  geom_line(linewidth = 0.7) +
  scale_colour_manual(values = c(ES = PAL[1], PT = PAL[2])) +
  scale_y_continuous(labels = label_number(suffix = " EUR")) +
  labs(title = "MIBEL day-ahead price, monthly mean",
       subtitle = "Spain and Portugal clear jointly; the two diverge only when the interconnection binds",
       x = NULL, y = "EUR/MWh",
       caption = "Source: OMIE marginalpdbc. Monthly mean of hourly (to 2025-09) then 15-minute prices.") +
  theme_vre()
save_fig(p1, "price_monthly")

# Zero and negative prices: a structural feature of high-VRE systems.
zn <- px |> group_by(year) |>
  summarise(`negative (< 0)` = mean(price_es < 0) * 100,
            `zero (= 0)`     = mean(price_es == 0) * 100, .groups = "drop") |>
  pivot_longer(-year, names_to = "kind", values_to = "pct")

p2 <- ggplot(zn, aes(factor(year), pct, fill = kind)) +
  geom_col(width = 0.62, position = position_stack()) +
  scale_fill_manual(values = c(`negative (< 0)` = PAL[1], `zero (= 0)` = PAL[3])) +
  scale_y_continuous(labels = label_number(suffix = "%")) +
  labs(title = "Share of periods at or below zero, Spain",
       subtitle = "Zero and negative prices are the visible symptom of surplus renewable supply",
       x = NULL, y = "share of periods",
       caption = "Source: OMIE. 2026 covers January-May only.") +
  theme_vre()
save_fig(p2, "price_zero_negative", h = 5.0)

# ==============================================================================
rule("2. GENERATION MIX")

gen <- read_parquet(file.path(DATA, "ree/ree_generation_daily.parquet")) |>
  # `Total generation` is itself one of the 17 series -- summing all
  # double-counts and roughly halves any share computed from it.
  filter(series != "Total generation") |>
  mutate(year = as.integer(format(as.Date(local_date), "%Y")))

gen_year <- gen |> group_by(year, series) |>
  summarise(twh = sum(value) / 1e6, .groups = "drop")
gen_tot <- gen_year |> group_by(year) |> summarise(total = sum(twh), .groups = "drop")

vre_es <- gen_year |>
  filter(series %in% c("Wind", "Solar photovoltaic", "Thermal solar")) |>
  group_by(year) |> summarise(vre = sum(twh), .groups = "drop") |>
  left_join(gen_tot, by = "year") |> mutate(share = vre / total * 100, zone = "Spain")

prod_pt <- read_parquet(file.path(DATA, "ren/ren_production_15min.parquet")) |>
  mutate(year = as.integer(format(as.Date(local_date), "%Y")))
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
print(as.data.frame(vre |> select(zone, year, vre, total, share)), digits = 4)
save_tab(vre, "vre_share_by_year")

p3 <- ggplot(vre, aes(year, share, colour = zone)) +
  geom_line(linewidth = 0.8) + geom_point(size = 2.1) +
  scale_colour_manual(values = c(Spain = PAL[1], Portugal = PAL[2])) +
  scale_y_continuous(labels = label_number(suffix = "%"), limits = c(0, NA)) +
  scale_x_continuous(breaks = unique(vre$year)) +
  labs(title = "Wind and solar share of generation",
       subtitle = "Both markets roughly doubled VRE penetration over the window",
       x = NULL, y = "share of generation",
       caption = "Sources: REE estructura-generacion (ES), REN production breakdown (PT). 2026 excluded (partial year).") +
  theme_vre()
save_fig(p3, "vre_share", h = 5.0)

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

p4 <- ggplot(mix, aes(factor(year), twh, fill = tech)) +
  geom_col(width = 0.68, colour = SURFACE, linewidth = 0.4) +
  scale_fill_manual(values = setNames(PAL[1:7], levels(mix$tech))) +
  labs(title = "Spanish generation mix", subtitle = "TWh per year, components only",
       x = NULL, y = "TWh",
       caption = "Source: REE. `Total generation` excluded -- it is published as a series alongside its own components.") +
  theme_vre() + guides(fill = guide_legend(nrow = 1))
save_fig(p4, "generation_mix", h = 5.4)

# ==============================================================================
rule("3. DIURNAL SHAPE (5-minute)")

rt <- read_parquet(file.path(DATA, "ree/ree_realtime_5min.parquet"),
                   col_select = c("ts", "local_date", "demand", "wind",
                                  "solar_pv", "hydro")) |>
  mutate(
    # Local Madrid clock. The autumn DST hour is written `2A`/`2B`, which is
    # not numeric -- those 8 days x 12 records drop out of the profile.
    hour  = suppressWarnings(as.integer(substr(ts, 12, 13))),
    month = as.integer(format(as.Date(local_date), "%m")),
    season = factor(ifelse(month %in% c(12, 1, 2), "Winter",
                    ifelse(month %in% 3:5, "Spring",
                    ifelse(month %in% 6:8, "Summer", "Autumn"))),
                    levels = c("Winter", "Spring", "Summer", "Autumn"))) |>
  filter(!is.na(hour))

prof <- rt |> group_by(season, hour) |>
  summarise(Demand = mean(demand), Wind = mean(wind),
            `Solar PV` = mean(solar_pv), .groups = "drop") |>
  pivot_longer(c(Demand, Wind, `Solar PV`), names_to = "series", values_to = "mw")

p5 <- ggplot(prof, aes(hour, mw, colour = series)) +
  geom_line(linewidth = 0.7) +
  facet_wrap(~season, nrow = 1) +
  scale_colour_manual(values = c(Demand = PAL[1], Wind = PAL[3], `Solar PV` = PAL[4])) +
  scale_x_continuous(breaks = c(0, 6, 12, 18)) +
  scale_y_continuous(labels = label_number(scale = 1e-3, suffix = " GW")) +
  labs(title = "Average day, Spain",
       subtitle = "Mean MW by local hour, 2018-2026. Solar reshapes the net-load problem seasonally",
       x = "hour (local)", y = "MW",
       caption = "Source: REE demanda.ree.es, 5-minute resolution.") +
  theme_vre()
save_fig(p5, "diurnal_profile", w = 11, h = 4.6)

# ==============================================================================
rule("4. BID CURVES -- the distinctive dataset")

bids <- open_dataset(file.path(DATA, "omie/bids/parquet"))

# One hour, submitted curves. `status == 'O'` is the full submitted curve;
# `C` rows are the cleared portion and must never be summed with `O`.
DAY <- as.Date("2024-01-15"); PERIOD <- 12L
one <- bids |>
  filter(date == DAY, period == PERIOD, status == "O") |>
  select(side, power_mw, price_eur_mwh) |>
  collect()

curve <- one |> group_by(side) |>
  arrange(if (first(side) == "V") price_eur_mwh else desc(price_eur_mwh),
          .by_group = TRUE) |>
  mutate(cum_gw = cumsum(power_mw) / 1000) |> ungroup() |>
  mutate(curve = ifelse(side == "V", "Supply (sell offers)", "Demand (buy bids)"))

clear <- px |> filter(date == DAY, period == PERIOD) |> pull(price_es)

p6 <- ggplot(curve, aes(cum_gw, price_eur_mwh, colour = curve)) +
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
       caption = "Source: OMIE curva_pbc_uof, status == 'O' (submitted). Y-axis clipped to +/-200 EUR/MWh; offers run to the +/-500 price bounds.") +
  theme_vre()
save_fig(p6, "bid_curves", h = 5.4)

# Offered vs cleared volume, monthly -- the gap is unaccepted supply.
supply <- bids |>
  filter(side == "V") |>
  mutate(ym = strftime(date, "%Y-%m")) |>
  group_by(ym, status) |>
  summarise(twh = sum(power_mw * resolution_min / 60, na.rm = TRUE) / 1e6,
            .groups = "drop") |>
  collect() |>
  mutate(month = as.Date(paste0(ym, "-01")),
         status = ifelse(status == "O", "Offered", "Cleared"))
save_tab(supply, "supply_offered_vs_cleared")

p7 <- ggplot(supply, aes(month, twh, colour = status)) +
  geom_line(linewidth = 0.7) +
  scale_colour_manual(values = c(Offered = PAL[1], Cleared = PAL[2])) +
  labs(title = "Sell-side volume offered vs cleared, day-ahead",
       subtitle = "The gap between the two is unaccepted supply -- invisible in markets that publish only outcomes",
       x = NULL, y = "TWh per month",
       caption = "Source: OMIE curva_pbc_uof. Energy = power_mw x resolution_min / 60. Archive stops 2026-05-08.") +
  theme_vre()
save_fig(p7, "offered_vs_cleared", h = 5.0)

# ==============================================================================
rule("5. UNIT REGISTRY")

reg <- read_parquet(file.path(DATA, "omie/registry/unit_registry.parquet"))
reg_summary <- reg |> count(country, role, name = "units") |> arrange(desc(units))
print(as.data.frame(reg_summary))
save_tab(reg_summary, "registry_composition")

# ==============================================================================
rule("6. DATASET INVENTORY")

inv <- tibble::tibble(
  dataset = c("OMIE day-ahead bids", "OMIE intraday bids", "OMIE prices",
              "Unit registry", "REE 5-minute", "REE daily generation",
              "REN production 15-min", "REN capacity monthly"),
  rows = c(
    open_dataset(file.path(DATA, "omie/bids/parquet")) |> nrow(),
    open_dataset(file.path(DATA, "omie/intraday/parquet")) |> nrow(),
    nrow(px), nrow(reg), nrow(rt),
    nrow(gen),
    nrow(prod_pt),
    nrow(read_parquet(file.path(DATA, "ren/ren_installed_power_monthly.parquet")))
  ))
print(as.data.frame(inv))
save_tab(inv, "dataset_inventory")

cat("\nDone. Figures in outputs/figures/, tables in outputs/tables/\n")
