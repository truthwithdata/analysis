# How far does your salary really go in another country? Independent R re-implementation (Truth with Data, Nov 2026).
# Rebuilds the price levels, the "$1,000" values, the rankings, the uprated ILOSTAT medians and the India case
# studies from the three input tables, and checks them against the CSVs written by salary-ppp-analysis.py.
#
# Usage: Rscript salary-ppp-analysis.R DATA_DIR      (base R only)

args <- commandArgs(trailingOnly = TRUE)
dir <- if (length(args)) args[1] else "."
w <- read.csv(file.path(dir, "salary-ppp-wdi-countries.csv"), stringsAsFactors = FALSE)
ppp <- w$ppp_private_consumption_lcu_per_intl_usd
ppp[w$iso3 == "BGR"] <- ppp[w$iso3 == "BGR"] * 1.95583      # PPP in euros, exchange rate in leva
w$pl <- ppp / w$exchange_rate_lcu_per_usd
w$ppp <- ppp
keep <- w$wdi_year >= 2024 & w$iso3 != "LBR" & w$pl >= 0.1 & w$pl <= 2.5
k <- w[keep, ]
k$v1000 <- 1000 / k$pl
cat(sprintf("%d countries; median price level %.3f; median value of $1,000 = $%.0f; dearer than the US: %d\n",
            nrow(k), median(k$pl), median(k$v1000), sum(k$pl > 1)))
o <- k[order(-k$v1000), ]
cat("Furthest:", paste(sprintf("%s %.0f", head(o$country, 10), head(o$v1000, 10)), collapse = "; "), "\n")
cat("Least far:", paste(sprintf("%s %.0f", tail(o$country, 10), tail(o$v1000, 10)), collapse = "; "), "\n")

py <- read.csv(file.path(dir, "salary-ppp-price-levels-by-country.csv"), stringsAsFactors = FALSE)
m <- merge(k[, c("iso3", "pl")], py[, c("iso3", "price_level")], by = "iso3")
cat(sprintf("Price levels: %d matched, max relative difference vs Python %.2e\n", nrow(m),
            max(abs(m$pl / m$price_level - 1))))

# ILOSTAT medians: euro conversion, redenominations, unit check, CPI uprating
e <- read.csv(file.path(dir, "salary-ppp-ilostat-median-earnings.csv"), stringsAsFactors = FALSE)
e <- e[!(e$iso3 %in% c("ZWE", "SOM", "MDG")), ]
noneuro <- grepl("Euro (EUR)", e$currency_note, fixed = TRUE) & abs(e$fx_survey_year - e$eur_per_usd_survey_year) > 1e-6
f <- ifelse(noneuro, e$fx_survey_year / e$eur_per_usd_survey_year, 1)
f <- f / ifelse(e$iso3 == "SLE", 1000, ifelse(e$iso3 == "MRT", 10, 1))
e$med <- e$median_monthly_lcu * f
chk <- e$med / e$fx_survey_year / e$ilo_median_usd
e <- merge(e, k[, c("iso3", "wdi_year", "ppp", "exchange_rate_lcu_per_usd")], by = "iso3")
chk <- e$med / e$fx_survey_year / e$ilo_median_usd
up <- ifelse(e$year >= e$wdi_year, 1, e$cpi_latest / e$cpi_survey_year)
ok <- (is.na(chk) | abs(chk - 1) <= 0.05) & !is.na(up) & up <= 2
e <- e[ok, ]
e$med_now <- e$med * up[ok]
e$med_ppp <- e$med_now / e$ppp
cat(sprintf("Median earnings for %d countries; survey years: %s\n", nrow(e),
            paste(names(table(e$year)), table(e$year), sep = ":", collapse = " ")))
pe <- read.csv(file.path(dir, "salary-ppp-median-earnings-by-country.csv"), stringsAsFactors = FALSE)
pe <- pe[pe$note == "" | is.na(pe$note), ]
mm <- merge(e[, c("iso3", "med_ppp")], pe[, c("iso3", "median_monthly_intl_usd_ppp")], by = "iso3")
cat(sprintf("Median earnings in PPP $: %d matched, max relative difference %.2e\n", nrow(mm),
            max(abs(mm$med_ppp / mm$median_monthly_intl_usd_ppp - 1))))
for (iso in c("IND", "GBR", "USA", "DEU")) {
  r <- e[e$iso3 == iso, ]
  cat(sprintf("  %s %d: median %.0f local a month (uprated), %.0f PPP $\n", iso, r$year, r$med_now, r$med_ppp))
}

# India case studies: Rs 1 lakh a month
ind <- k[k$iso3 == "IND", ]
for (iso in c("GBR", "USA", "ARE", "DEU")) {
  b <- k[k$iso3 == iso, ]
  fx_eq <- 100000 / ind$exchange_rate_lcu_per_usd * b$exchange_rate_lcu_per_usd
  ppp_eq <- 100000 / ind$ppp * b$ppp
  cat(sprintf("Rs 1 lakh/month -> %s: market rate %.0f, PPP %.0f (x%.2f), 30%% at market prices %.0f\n",
              b$country, fx_eq, ppp_eq, ppp_eq / fx_eq, 0.7 * ppp_eq + 0.3 * fx_eq))
}
