# Is crime really going up in the UK? Independent R re-implementation (Truth with Data, Nov 2026).
# Recomputes the long-run survey vs police changes, the "which crimes are rising" panel, the breakdown of the
# police-recorded rise since 2013/14 and the local extremes from the tidy tables, and checks them against the
# CSVs written by uk-crime-analysis.py.
#
# Usage: Rscript uk-crime-analysis.R DATA_DIR      (base R only)

args <- commandArgs(trailingOnly = TRUE)
dir <- if (length(args)) args[1] else "."
rd <- function(f) read.csv(file.path(dir, f), check.names = FALSE, stringsAsFactors = FALSE)
inc <- rd("uk-crime-csew-incidents-1981-2026.csv"); rownames(inc) <- inc$offence
prc <- rd("uk-crime-police-recorded-by-offence-2003-2026.csv"); rownames(prc) <- prc$offence
hist <- rd("uk-crime-police-recorded-historical-1981-2002.csv")
sig <- rd("uk-crime-csew-significance-ye-jun-2026.csv")
pfa <- rd("uk-crime-rates-by-police-force-2022-2026.csv")
csp <- rd("uk-crime-rates-by-csp-2024-2026.csv")
pct <- function(a, b) 100 * (b / a - 1)
L <- "YE Jun 2026"

cs <- unlist(inc["all_excl_fraud", -1]); pr <- unlist(prc["total_excl_fraud", -1])
old <- hist[hist$rules == "old counting rules", ]
p81 <- old$total_excl_fraud[old$period == "YE Dec 1981"]; p95 <- old$total_excl_fraud[old$period == "YE Dec 1995"]
cat(sprintf("CSEW (excl. fraud): %.2fm in 1981 -> %.2fm in 1995 (%+.1f%%) -> %.2fm YE Mar 2014 -> %.2fm %s (%+.1f%% since 1995)\n",
            cs["YE Dec 1981"] / 1e3, cs["YE Dec 1995"] / 1e3, pct(cs["YE Dec 1981"], cs["YE Dec 1995"]), cs["YE Mar 2014"] / 1e3,
            cs[L] / 1e3, L, pct(cs["YE Dec 1995"], cs[L])))
cat(sprintf("Police (excl. fraud): %.2fm in 1981 -> %.2fm in 1995 (%+.1f%%); %.2fm 2002/03 -> %.2fm low (%s) -> %.2fm %s (%+.1f%%)\n",
            p81 / 1e6, p95 / 1e6, pct(p81, p95), pr["YE Mar 2003"] / 1e6, min(pr) / 1e6, names(pr)[which.min(pr)],
            pr[L] / 1e6, L, pct(min(pr), pr[L])))
cat(sprintf("CSEW since 2013/14: %+.1f%%; including fraud since YE Mar 2017: %+.1f%%\n", pct(cs["YE Mar 2014"], cs[L]),
            pct(inc["all_incl_fraud", "YE Mar 2017"], inc["all_incl_fraud", L])))

# Panel: police changes and ONS significance flags
py <- rd("uk-crime-which-crimes-are-rising-2017-2026.csv")
pk <- c("Shoplifting" = "shoplifting", "Theft from the person (pickpocketing, snatches)" = "theft_from_person",
        "Violence" = "violence_against_person", "Robbery" = "robbery", "Domestic / residential burglary" = "residential_burglary",
        "Vehicle theft" = "vehicle_offences", "Bicycle theft" = "bicycle_theft", "Criminal damage" = "criminal_damage_arson")
mx <- 0
for (lab in names(pk)) {
  base <- py$police_base_period[py$offence == lab]
  r <- pct(prc[pk[lab], base], prc[pk[lab], L])
  mx <- max(mx, abs(r - py$police_change_pct[py$offence == lab]))
  cat(sprintf("%-48s police %s -> %s: %+6.1f%%\n", lab, base, L, r))
}
cat(sprintf("Panel police changes: max |R - Python| = %.3f pts\n", mx))
s17 <- sig[sig$compared_with == "YE Mar 2017", ]
up <- s17$offence[s17$significant_5pct == "True" & s17$pct_change_to_ye_jun_2026 > 0]
down <- s17$offence[s17$significant_5pct == "True" & s17$pct_change_to_ye_jun_2026 < 0]
cat("CSEW significant rises since YE Mar 2017:", paste(up, collapse = ", "), "\n")
cat("CSEW significant falls since YE Mar 2017:", paste(down, collapse = ", "), "\n")

# Where the police-recorded rise came from
g <- c("violence_against_person", "sexual_offences", "public_order", "weapons", "drug_offences", "robbery", "theft",
       "criminal_damage_arson")
ch <- prc[g, L] - prc[g, "YE Mar 2014"]; names(ch) <- g
net <- pr[L] - pr["YE Mar 2014"]
ch["other"] <- net - sum(ch)
dpy <- rd("uk-crime-police-rise-decomposition-2014-2026.csv")
cat(sprintf("Net police rise since YE Mar 2014: %s; violence %.1f%%, sexual %.1f%%, public order %.1f%% of it; theft %+d\n",
            format(net, big.mark = ","), 100 * ch[1] / net, 100 * ch[2] / net, 100 * ch[3] / net, ch["theft"]))
cat(sprintf("Decomposition: max |R - Python| = %d offences\n", max(abs(ch - dpy$change))))

# Local extremes
f <- pfa[grepl("^(E23|W15)", pfa$area_code) & !is.na(pfa$total_2026), ]
ew <- pfa[pfa$area_code == "K04000001", ]
cat(sprintf("Forces: %d with rates; lowest %s %.1f, highest %s %.1f per 1,000; E&W %.1f (2022: %.1f); %d forces up since YE Jun 2022\n",
            nrow(f), f$area_name[which.min(f$total_2026)], min(f$total_2026), f$area_name[which.max(f$total_2026)],
            max(f$total_2026), ew$total_2026, ew$total_2022, sum(f$total_2026 > f$total_2022)))
c2 <- csp[csp$population_mid2024 >= 10000 & !is.na(csp$total_2026), ]
cat(sprintf("CSPs: %d with rates; lowest %s %.1f, highest %s %.1f, median %.1f\n", nrow(c2), c2$csp_name[which.min(c2$total_2026)],
            min(c2$total_2026), c2$csp_name[which.max(c2$total_2026)], max(c2$total_2026), median(c2$total_2026)))
