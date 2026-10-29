# Is renting really 'dead money' in the UK?  Truth with Data, October 2026.
# Independent R re-implementation of the rent-vs-buy model. It reads only the
# published CSVs (no Python output beyond the data), rebuilds the baseline growth
# rates, re-runs every regional break-even and the historical backtest, and
# prints the same key numbers as uk-rent-vs-buy-analysis.py.
#
# Usage: Rscript uk-rent-vs-buy-analysis.R DATA_DIR
# DATA_DIR holds uk-rent-vs-buy-breakeven-by-region-2026.csv and
# uk-rent-vs-buy-monthly-panel-2005-2026.csv (from truthwithdata.com/data/).
# Base R only; no packages needed.

args <- commandArgs(trailingOnly = TRUE)
dir <- if (length(args)) args[1] else "."

A <- list(term_years = 25, fix_months = 24, product_fee = 1141, conveyancing_house = 1420,
          conveyancing_flat = 1825, agent_fee_pct = 1.42, conveyancing_sell = 950,
          maintenance_house_pct = 1.0, maintenance_flat_pct = 0.5, buildings_insurance = 306,
          service_charge_ew = 2405, service_charge_london = 2801, cost_inflation_pct = 2.0,
          invest_return_pct = 5.0, horizon_years = 30)
survey_x <- c(150000, 250000, 400000, 750000); survey_y <- c(400, 600, 800, 1200)

# --- Transaction taxes in force in October 2026 -------------------------------
banded <- function(price, upper, rate) {
  lower <- c(0, head(upper, -1))
  sum(pmax(0, pmin(price, upper) - lower) * rate / 100)
}
transaction_tax <- function(price, nation, ftb = TRUE) {
  if (nation %in% c("england", "ni")) {
    if (ftb && price <= 500000) return(banded(price, c(300000, 500000), c(0, 5)))
    return(banded(price, c(125000, 250000, 925000, 1500000, Inf), c(0, 2, 5, 10, 12)))
  }
  if (nation == "scotland") {
    nil <- if (ftb) 175000 else 145000
    return(banded(price, c(nil, 250000, 325000, 750000, Inf), c(0, 2, 5, 10, 12)))
  }
  if (nation == "wales") return(banded(price, c(225000, 400000, 750000, 1500000, Inf), c(0, 6, 7.5, 10, 12)))
  stop(nation)
}
survey_cost <- function(p) approx(survey_x, survey_y, xout = p, rule = 2)$y

# --- The model ------------------------------------------------------------------
# value, cidx: months 0..M (R index 1..M+1); rent, ret: month m stored at index m+1
simulate <- function(value, rent, mrate, ret, cidx, deposit_pct, nation, is_flat, code) {
  M <- length(value) - 1; P <- value[1]
  maint <- if (is_flat) A$maintenance_flat_pct else A$maintenance_house_pct
  sc <- if (is_flat) (if (code == "E12000007") A$service_charge_london else A$service_charge_ew) else 0
  ins <- if (is_flat) 0 else A$buildings_insurance
  conv <- if (is_flat) A$conveyancing_flat else A$conveyancing_house
  deposit <- P * deposit_pct / 100; bal <- P - deposit
  buy_costs <- transaction_tax(P, nation) + (conv + A$product_fee) * cidx[1] + survey_cost(P)
  renter <- deposit + buy_costs; buyer <- 0
  n_left <- A$term_years * 12; i <- mrate[1] / 1200
  pmt <- bal * i / (1 - (1 + i)^-n_left)
  sell_cost <- function(v, c) v * A$agent_fee_pct / 100 + A$conveyancing_sell * c
  bw <- rw <- numeric(M + 1)
  bw[1] <- value[1] - bal - sell_cost(value[1], cidx[1]); rw[1] <- renter
  for (m in 1:M) {
    g <- (1 + ret[m + 1] / 100)^(1 / 12); renter <- renter * g; buyer <- buyer * g
    pay <- 0
    if (bal > 0) {
      interest <- bal * i; principal <- min(pmt - interest, bal)
      pay <- interest + principal; bal <- bal - principal; n_left <- n_left - 1
      if (bal < 1e-6) bal <- 0
    }
    out <- pay + maint / 100 * value[m] / 12 + (ins + sc) / 12 * cidx[m + 1]
    if (m %% A$fix_months == 0 && bal > 0 && m < M) {
      i <- mrate[m + 1] / 1200; pmt <- bal * i / (1 - (1 + i)^-n_left)
      out <- out + A$product_fee * cidx[m + 1]
    }
    d <- out - rent[m + 1]
    if (d > 0) renter <- renter + d else buyer <- buyer - d
    bw[m + 1] <- value[m + 1] - bal - sell_cost(value[m + 1], cidx[m + 1]) + buyer
    rw[m + 1] <- renter
  }
  list(bw = bw, rw = rw)
}
breakeven_years <- function(s) {           # first month from which the buyer stays ahead
  behind <- which(s$bw[-1] < s$rw[-1]); n <- length(s$bw) - 1
  if (!length(behind)) return(1 / 12)
  if (max(behind) == n) return(NA)
  (max(behind) + 1) / 12
}
run_forward <- function(P, R0, rate, gp, gr, r_inv, dep, nation, is_flat, code) {
  M <- A$horizon_years * 12; m <- 0:M
  simulate(P * (1 + gp / 100)^(m / 12), R0 * (1 + gr / 100)^((m - 1) %/% 12), rep(rate, M + 1),
           rep(r_inv, M + 1), (1 + A$cost_inflation_pct / 100)^(m / 12), dep, nation, is_flat, code)
}

# --- Baseline growth: England, July 2005 -> July 2026 ---------------------------
panel <- read.csv(file.path(dir, "uk-rent-vs-buy-monthly-panel-2005-2026.csv"))
eng <- panel[panel$area_code == "E92000001", ]
ratio <- function(col) eng[eng$month == "2026-07", col] / eng[eng$month == "2005-07", col]
G_PRICE <- (ratio("avg_price")^(1 / 21) - 1) * 100
G_RENT <- (ratio("rent_index")^(1 / 21) - 1) * 100
cat(sprintf("Baseline growth, England Jul 2005-Jul 2026: prices %.2f%%/yr, rents %.2f%%/yr\n", G_PRICE, G_RENT))

# --- Regional break-even ----------------------------------------------------------
reg <- read.csv(file.path(dir, "uk-rent-vs-buy-breakeven-by-region-2026.csv"))
reg$be_R <- mapply(function(P, R0, rate, dep, nation, type, code)
  breakeven_years(run_forward(P, R0, rate, G_PRICE, G_RENT, A$invest_return_pct, dep, nation, type == "flat", code)),
  reg$price_jul2026, reg$monthly_rent_jul2026, reg$mortgage_rate_pct, reg$deposit_pct,
  reg$nation, reg$property_type, reg$area_code)
allt <- reg[reg$property_type == "all", ]
cat("Break-even years, all property types (10% and 25% deposit):\n")
print(reshape(allt[, c("region", "deposit_pct", "be_R")], idvar = "region", timevar = "deposit_pct",
              direction = "wide"), row.names = FALSE)
cat(sprintf("Largest |R - Python| difference across %d region x type x deposit cases: %.4f years\n",
            nrow(reg), max(abs(round(reg$be_R, 2) - reg$breakeven_years), na.rm = TRUE)))
cat("Cases with no break-even in 30 years agree:", identical(is.na(reg$be_R), is.na(reg$breakeven_years)), "\n")

# One sensitivity cell: flat house prices at today's 90% LTV rate, median across regions
b10 <- allt[allt$deposit_pct == 10, ]
flat <- mapply(function(P, R0, rate, nation, code)
  breakeven_years(run_forward(P, R0, rate, 0, G_RENT, A$invest_return_pct, 10, nation, FALSE, code)),
  b10$price_jul2026, b10$monthly_rent_jul2026, b10$mortgage_rate_pct, b10$nation, b10$area_code)
cat("Break-even with flat house prices, by region:", paste(round(flat, 2), collapse = ", "), "\n")

# --- Historical backtest: buy in July of year X, sell in July of year Y, 25% deposit --
bt <- list()
for (code in setdiff(unique(panel$area_code), "E92000001")) {
  d <- panel[panel$area_code == code, ]
  d$year <- as.integer(substr(d$month, 1, 4)); d$mon <- as.integer(substr(d$month, 6, 7))
  first <- d[!is.na(d$rent_index), ][1, ]
  start <- first$year + (first$mon > 7)
  for (x in start:2025) {
    s <- d[which(d$year == x & d$mon == 7):nrow(d), ]
    M <- nrow(s) - 1; m <- 0:M
    rent <- s$monthly_rent[pmax(1, ((m - 1) %/% 12) * 12 + 1)]
    cidx <- (1 + A$cost_inflation_pct / 100)^((m + (x - 2026) * 12) / 12)
    for (ra in c("bank_rate", "fixed_5pct")) {
      ret <- if (ra == "bank_rate") s$bank_rate else rep(5, M + 1)
      sim <- simulate(s$avg_price, rent, s$rate_2y_fixed_75ltv, ret, cidx, 25, s$nation[1], FALSE, code)
      for (y in (x + 1):2026) {
        k <- (y - x) * 12 + 1
        bt[[length(bt) + 1]] <- data.frame(area_code = code, ra = ra, buy = x, held = y - x,
                                           gap = sim$bw[k] - sim$rw[k])
      }
    }
  }
}
bt <- do.call(rbind, bt)
for (h in c(2, 5, 10)) {
  s <- bt[bt$ra == "fixed_5pct" & bt$held == h, ]
  cat(sprintf("Backtest (5%% return), held %dy: buying ahead in %.0f%% of %d cases\n", h, 100 * mean(s$gap > 0), nrow(s)))
}
for (h in c(2, 5, 10)) {
  s <- bt[bt$ra == "bank_rate" & bt$held == h, ]
  cat(sprintf("Backtest (Bank Rate cash), held %dy: buying ahead in %.0f%% of %d cases\n", h, 100 * mean(s$gap > 0), nrow(s)))
}
