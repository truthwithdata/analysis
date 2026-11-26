# Does "Sell in May and go away" beat buy-and-hold?

Article: https://truthwithdata.com/blog/does-sell-in-may-and-go-away-work.html · Backtester: https://truthwithdata.com/tools/sell-in-may-backtester.html

Tests the "Sell in May" / Halloween calendar rule on US stocks from February 1871 to August 2026 (1,867 monthly returns): average and median May–October vs November–April real total returns with bootstrap confidence intervals, how often each half won and how often summer stocks beat cash, a backtest of switching to cash every May against buy-and-hold (with trading costs and a stylised tax), a half-stocks/half-cash benchmark, results by era (before 1950, 1951–2001, after Bouman & Jacobsen's 2002 paper) and by decade, every six-month "out" window, and averages by calendar month (September and January effects). The method is described at the top of `sell-in-may-analysis.py`; the R script re-implements it independently from the monthly panel as a cross-check.

## Source data (downloaded into `raw/` by `sell-in-may-build-panel.py --fetch`)

| File | Publisher | Licence |
| --- | --- | --- |
| `shiller/data.csv` | Robert J. Shiller, [U.S. Stock Markets 1871–Present and CAPE Ratio](http://www.econ.yale.edu/~shiller/data.htm) (`ie_data.xls`): S&P Composite monthly average price, 12-month dividend, CPI. Read from the unchanged republication by Open Knowledge, [datasets/s-and-p-500](https://github.com/datasets/s-and-p-500) (`data/data.csv`, prices to September 2026). If `raw/ie_data.xls` (Shiller's own workbook) is present, the builder uses it instead. | Freely published by Shiller for research; please cite. The datasets repository is ODC-PDDL. |
| `TB3MS.csv` | Federal Reserve, 3-month Treasury bill secondary market rate, monthly, via [FRED](https://fred.stlouisfed.org/series/TB3MS) (from January 1934) | Public domain |
| `M13002US35620M156NNBR.csv` | NBER Macrohistory Database, commercial paper rates for New York, monthly 1857–1971, via [FRED](https://fred.stlouisfed.org/series/M13002US35620M156NNBR). Used as the cash rate before 1934. | NBER / FRED terms |
| `CPIAUCNS.csv` | US Bureau of Labor Statistics, CPI-U all items, not seasonally adjusted, via [FRED](https://fred.stlouisfed.org/series/CPIAUCNS). Extends Shiller's CPI after September 2023. | Public domain |

Raw files are not redistributed here. They were downloaded on 25 November 2026.

Gaps filled by the builder and flagged in the panel's `*_source` columns:

* Shiller's file stops reporting dividends after June 2023; they are extended at their own trailing five-year growth rate (6.15% a year).
* October 2025 CPI was never published (US government shutdown); it is the geometric mean of September and November 2025.

Limitations: Shiller's prices are monthly averages of daily closes, which smooths returns and shifts each "month" by about half a month (the analysis re-runs everything with months shifted one later as a check). Commercial paper paid more than T-bills would have, which slightly flatters switching before 1934. No UK (FTSE All-Share) or India (Nifty 50) check: free, republishable long-run monthly data were not available.

## Run

```bash
pip install pandas numpy matplotlib xlrd
python sell-in-may-build-panel.py --fetch raw        # download the four source files
python sell-in-may-build-panel.py raw data           # build data/us-stocks-cash-monthly-panel-1871-2026.csv
python sell-in-may-analysis.py data [tool-data.js]   # writes the CSVs in data/, the summary JSON and (optionally) the backtester's data file
python sell-in-may-charts.py data charts             # the article's charts (the poster and share image are SVGs rendered to PNG with Playwright)
Rscript sell-in-may-analysis.R data                  # independent R cross-check (base R)
```

## Outputs (`data/`)

| File | Contents |
| --- | --- |
| `us-stocks-cash-monthly-panel-1871-2026.csv` | Input panel, January 1871 to August 2026: S&P Composite price, 12-month dividend, CPI, cash rate, and the source of each value |
| `sell-in-may-monthly-returns-1871-2026.csv` | Monthly stock total return (nominal and real), price-only return, cash return and inflation |
| `sell-in-may-half-years-1871-2026.csv` | May–October and November–April returns for stocks and cash, every year |
| `sell-in-may-month-averages.csv` | Mean (with bootstrap 95% CI), median and share positive by calendar month; means before and after 2002 |
| `sell-in-may-backtest-scenarios.csv` | Switching vs buy-and-hold vs half-and-half for costs of 0–0.5% per switch and tax of 0% or 20%: real and nominal CAGR, final values, drawdowns, volatility, share of years won |
| `sell-in-may-by-period.csv` | Seasonal statistics (with CIs) and backtests by era and by decade |
| `sell-in-may-summary.json` | Headline numbers used in the article, robustness checks and all twelve six-month windows |

Code: MIT. Processed data and charts: CC BY 4.0, credit "Truth with Data (truthwithdata.com)".
