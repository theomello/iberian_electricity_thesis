# R replication of the first estimates: Enrich, Li, Mizrahi and Reguant (2024) for E0 (ESIOS 1201) against Portugal (REN).
#   Rscript scripts/analysis/tou_replication.R
# Independent implementation of tou_lasso_paper.py (first step) and tou_elasticity_paper.py (Equation 4, Table 6 columns 1-4), so the Python numbers can be checked in a second language.
# Step 1: one LASSO per country and hour of the day on pre-policy days (2018-01-01 -> 2020-12-31 without 2020-03-01 -> 2020-06-30): month dummies, weekend, national holiday, the hour's
#   temperature, the day's minimum and maximum temperature, all squares and pairwise products; 10-fold cross-validation, one-standard-error rule (glmnet, 50 lambdas, ratio 1e-3);
#   errors = log load minus prediction, in and out of sample.
# Step 2: (a) triple difference of the Spain-minus-Portugal errors, evening peak (18-21h) against night (0-7h), working days against weekends and holidays, window 2021-06-01 -> 2021-09-30,
#   standard errors clustered by week; (b) Equation 4: 2SLS of the error on ln PVPC price (instrument ln(charge + average pre-policy energy cost)), fixed effects as in the paper's columns 1-4,
#   standard errors clustered by area x month-of-sample.
# Reads the same parquet files as the Python scripts; writes outputs/tables/tou_replication_R.csv and prints the Python values beside the R ones.
suppressMessages({library(arrow); library(data.table); library(glmnet); library(fixest)})
root <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(FALSE), value = TRUE))), "..", ".."))
rd <- function(p, ...) as.data.table(read_parquet(file.path(root, p), ...))
COVID <- as.Date(c("2020-03-01", "2020-06-30")); POST0 <- as.Date("2021-06-01"); LAST <- as.Date("2021-12-31"); OLD <- 44

# ---------------------------------------------------------------- data
hol <- rd("data/holidays/holidays_es_pt.parquet")
hes <- as.Date(hol[area == "AN" & mark == "national", date]); hpt <- as.Date(hol[area == "PT", date])
t <- rd("data/weather/temperature_population_hourly.parquet", col_select = c("city", "country", "utc_timestamp", "temperature_2m"))
loc_frame <- function(utc, val, tz) {
  d <- data.table(utc = utc, v = val)
  d[, lt := as.POSIXct(format(utc, tz = tz, usetz = FALSE), tz = "UTC")]
  d[, `:=`(date = as.Date(lt), hour = as.integer(format(lt, "%H")))]
  d[!duplicated(d[, .(date, hour)]), ]
}
es <- rd("data/esios/esios_1201.parquet", col_select = c("utc_timestamp", "value")); es <- es[!duplicated(utc_timestamp)]
pt <- rd("data/ren/ren_production_15min.parquet"); pt <- pt[series == "Consumption"][!duplicated(utc_timestamp)]
pt[, hr := as.POSIXct(trunc(utc_timestamp, "hours"), tz = "UTC")]
pt <- pt[, .(value = mean(value_mw)), by = hr]
tes <- t[country == "ES", .(temp = mean(temperature_2m)), by = utc_timestamp]; tpt <- t[country == "PT", .(temp = mean(temperature_2m)), by = utc_timestamp]
mk <- function(load_utc, load_val, temp, tz) {
  d <- merge(data.table(utc = load_utc, load = load_val), temp[, .(utc = utc_timestamp, temp)], by = "utc")
  d <- d[utc >= as.POSIXct("2017-12-31", tz = "UTC") & utc < as.POSIXct(LAST + 2, tz = "UTC")]
  l <- loc_frame(d$utc, d$load, tz); l[, temp := d$temp[match(utc, d$utc)]]
  setnames(l, "v", "load"); l[, .(date, hour, load, temp)]
}
ES <- mk(es$utc_timestamp, es$value, tes, "Europe/Madrid"); PT <- mk(pt$hr, pt$value, tpt, "Europe/Lisbon")
x <- merge(ES, PT, by = c("date", "hour"), suffixes = c("_es", "_pt")); x <- x[complete.cases(x) & date <= LAST]
setorder(x, date, hour)
x[, `:=`(dow = (as.integer(format(date, "%u")) - 1L), hol_es = as.integer(date %in% hes), hol_pt = as.integer(date %in% hpt), month = as.integer(format(date, "%m")))]
x[, weekend := (dow >= 5) | hol_es == 1]
cat("hourly rows:", nrow(x), " days:", uniqueN(x$date), "\n")

# ---------------------------------------------------------------- step 1: LASSO per country and hour
poly2 <- function(B) {
  p <- ncol(B); idx <- which(upper.tri(diag(p), diag = TRUE), arr.ind = TRUE)
  P <- cbind(B, B[, idx[, 1], drop = FALSE] * B[, idx[, 2], drop = FALSE])
  P[, !duplicated(t(round(P, 10))), drop = FALSE]
}
errors <- function(x, load, temp, hol) {
  x[, tmin := min(get(temp)), by = date][, tmax := max(get(temp)), by = date]
  err <- rep(NA_real_, nrow(x))
  for (h in 0:23) {
    s <- which(x$hour == h)
    d <- x[s]
    M <- model.matrix(~ 0 + factor(month, levels = 1:12), d)
    B <- cbind(M, wk = as.numeric(d$dow >= 5), hol = d[[hol]], t = d[[temp]], tmin = d$tmin, tmax = d$tmax)
    P <- poly2(B)
    tr <- d$date <= as.Date("2020-12-31") & !(d$date >= COVID[1] & d$date <= COVID[2])
    mu <- colMeans(P[tr, , drop = FALSE]); sdv <- apply(P[tr, , drop = FALSE], 2, sd); keep <- sdv > 0
    Z <- sweep(sweep(P[, keep, drop = FALSE], 2, mu[keep]), 2, sdv[keep], "/")
    y <- log(d[[load]])
    set.seed(0); foldid <- sample(rep(1:10, length.out = sum(tr)))
    cv <- cv.glmnet(Z[tr, ], y[tr], foldid = foldid, nlambda = 50, lambda.min.ratio = 1e-3, standardize = FALSE, alpha = 1)
    err[s] <- y - as.numeric(predict(cv, Z, s = "lambda.1se"))
  }
  err
}
x[, e_es := errors(x, "load_es", "temp_es", "hol_es")]
x[, e_pt := errors(x, "load_pt", "temp_pt", "hol_pt")]
cat("LASSO errors done\n")

# ---------------------------------------------------------------- step 2a: triple difference of the errors
w <- x[date >= POST0 & date <= as.Date("2021-09-30") & !(date >= COVID[1] & date <= COVID[2]) & (hour < 8 | hour %in% 18:21)]
w[, `:=`(err = e_es - e_pt, cls = ifelse(hour < 8, "off", "peak"), kind = ifelse(weekend, "wknd", "work"))]
w[, cell := paste(cls, kind, sep = "_")]
m <- feols(err ~ 0 + factor(cell), data = w, cluster = ~ format(date, "%G-%V"), ssc = ssc(adj = FALSE, cluster.adj = FALSE))
b <- coef(m); names(b) <- sub("factor\\(cell\\)", "", names(b)); V <- vcov(m); rownames(V) <- colnames(V) <- names(b)
cw <- c(peak_work = 1, off_work = -1, peak_wknd = -1, off_wknd = 1)[names(b)]
ddd <- sum(cw * b); ddd_se <- sqrt(as.numeric(t(cw) %*% V %*% cw))
cat(sprintf("DDD evening peak vs night (errors, Spain minus Portugal, Jun-Sep 2021): %.4f (se %.4f)  [Python: tou_evening_ddd / paper-LASSO block in tou_ddd]\n", ddd, ddd_se))

# ---------------------------------------------------------------- step 2b: Equation 4
hrly <- function(i) {
  d <- rd(sprintf("data/esios/esios_%d.parquet", i))
  d <- d[geo_name %in% c("Pen\u00ednsula", "Espa\u00f1a")][!duplicated(utc_timestamp)]
  l <- loc_frame(d$utc_timestamp, d$value, "Europe/Madrid")
  out <- l[, .(date, hour, v)]
  setnames(out, "v", paste0("v", i))
  out
}
p <- Reduce(function(a, b) merge(a, b, by = c("date", "hour"), all = TRUE), list(hrly(1013), hrly(1001), hrly(1876)))
post <- p$date >= POST0
p[, `:=`(price = ifelse(post, v1001, v1013), charge = ifelse(post, v1876, OLD))]
ebar <- mean(p[date >= "2019-01-01" & date <= "2021-05-31", v1013] - OLD, na.rm = TRUE)
cat(sprintf("average pre-policy energy cost: %.2f\n", ebar))
d <- x[((date >= "2018-01-01" & date <= "2020-12-31") | (date >= POST0 & date <= LAST)) & !(date >= COVID[1] & date <= COVID[2])]
d <- merge(d, p[, .(date, hour, price, charge)], by = c("date", "hour"), all.x = TRUE)
s <- rbind(d[, .(area = 0L, date, hour, wk = as.integer(weekend), e = e_es, lnp = log(price), z = log(charge + ebar), hdh = pmax(18 - temp_es, 0), cdh = pmax(temp_es - 18, 0))],
           d[, .(area = 1L, date, hour, wk = as.integer(dow >= 5 | hol_pt == 1), e = e_pt, lnp = 0, z = 0, hdh = pmax(18 - temp_pt, 0), cdh = pmax(temp_pt - 18, 0))])
s <- s[complete.cases(e, lnp, z)]
s[, `:=`(ym = format(date, "%Y-%m"), moy = as.integer(format(date, "%m")), hw = hour * 2L + wk)]
s[, cl := paste(area, ym)]
cat("stack rows:", nrow(s), " clusters:", uniqueN(s$cl), "\n")
ss <- ssc(K.adj = FALSE, G.adj = TRUE, G.df = "conventional")
fit <- function(fe, ctrl = NULL) {
  f <- as.formula(sprintf("e ~ %s | %s | lnp ~ z", if (is.null(ctrl)) "1" else ctrl, fe))
  feols(f, data = s, cluster = ~cl, ssc = ss)
}
fe1 <- "hour^wk^area + hour^wk^ym"; fe2 <- paste(fe1, "+ hour^wk^area^moy"); fe4 <- paste(fe2, "+ wk^area^ym")
cols <- list(`1` = fit(fe1), `2` = fit(fe2), `3` = fit(fe2, "i(hw, hdh) + i(hw, cdh)"), `4` = fit(fe4, "i(hw, hdh) + i(hw, cdh)"))
res <- rbindlist(lapply(names(cols), function(k) { m <- cols[[k]]; cf <- coeftable(m)["fit_lnp", ]
  data.table(col = as.integer(k), eta = cf[1], se = cf[2], t = cf[3], first_stage_F = fitstat(m, "ivwald1", vcov = ~cl)[[1]]$stat, n = nobs(m), clusters = uniqueN(s$cl)) }))
py <- fread(file.path(root, "outputs/tables/tou_elasticity_paper.csv"))[col %in% 1:4, .(col = as.integer(col), eta_py = eta, se_py = se, F_py = first_stage_F)]
res <- merge(res, py, by = "col")
print(res[, lapply(.SD, function(v) if (is.numeric(v)) round(v, 4) else v)])
out <- rbind(data.table(item = "DDD evening vs night (errors)", value = ddd, se = ddd_se), res[, .(item = paste0("eta column ", col), value = eta, se = se)])
fwrite(out, file.path(root, "outputs/tables/tou_replication_R.csv"))
cat("column 4 (the within-day comparison): R", round(res[col == 4, eta], 4), "vs Python", round(res[col == 4, eta_py], 4), "\n")
