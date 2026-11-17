# Has gold beaten the Sensex for Indian investors?

Article: https://truthwithdata.com/blog/has-gold-beaten-the-sensex.html · Backtester: https://truthwithdata.com/tools/gold-vs-sensex-sip-backtester.html

Compares gold in rupees with the BSE Sensex from April 1993 to October 2026 (403 months of monthly averages): returns over every 5, 10, 15 and 20-year window, with and without an assumed Sensex dividend yield, inflation-adjusted returns, drawdowns, and SIP and lump-sum backtests of gold/Sensex mixes rebalanced once a year. The method is described at the top of `gold-vs-sensex-analysis.py`; the R script re-implements it independently from the monthly panel as a cross-check.

## Source data (downloaded into `raw/` by `gold-vs-sensex-build-panel.py --fetch`)

| File | Publisher | Licence |
| --- | --- | --- |
| `CMO-Historical-Data-Monthly.xlsx` | World Bank, [Commodity Price Data (Pink Sheet)](https://www.worldbank.org/en/research/commodity-markets), monthly prices, gold (US$/troy oz), updated 3 November 2026 | CC BY 4.0 |
| `EXINUS.csv` | Federal Reserve H.10, Indian rupees to one US dollar, monthly average, via [FRED](https://fred.stlouisfed.org/series/EXINUS) | Public domain (Federal Reserve) |
| `SPASTT01INM661N.csv` | OECD Main Economic Indicators, share prices, India, 2015 = 100 (follows the BSE Sensex), via [FRED](https://fred.stlouisfed.org/series/SPASTT01INM661N) | OECD terms |
| `INDCPIALLMINMEI.csv` | OECD Main Economic Indicators, consumer prices, India, via [FRED](https://fred.stlouisfed.org/series/INDCPIALLMINMEI) (to March 2025) | OECD terms |
| `mospi-cpi-combined-general.csv` | MOSPI, CPI (base 2012), All India, Combined, General index, via the [eSankhyiki API](https://esankhyiki.mospi.gov.in/) | MOSPI terms of use |

Raw files are not redistributed here. Re-running the fetch and build steps on 17 November 2026 reproduced `data/india-gold-sensex-monthly-panel-1990-2026.csv` byte for byte.

The Sensex series is a price index. Dividends are added as an **assumption** (1.25% a year, with 0% and 1.5% reported), not data.

## Run

```bash
pip install pandas numpy openpyxl matplotlib requests
python gold-vs-sensex-build-panel.py --fetch raw         # download the five source files
python gold-vs-sensex-build-panel.py raw data            # build the monthly panel
python gold-vs-sensex-analysis.py data                   # writes the CSVs in data/ (and summary JSON)
python gold-vs-sensex-charts.py data charts              # the article's charts
Rscript gold-vs-sensex-analysis.R data                   # independent R cross-check (base R)
```

## Outputs (`data/`)

| File | Contents |
| --- | --- |
| `india-gold-sensex-monthly-panel-1990-2026.csv` | The source series, monthly, January 1990 to October 2026 (input to the analysis) |
| `gold-vs-sensex-monthly-1990-2026.csv` | Gold in rupees per 10 g, Sensex-tracking index, rupee rate and chained CPI |
| `gold-vs-sensex-trailing-returns-2026-10.csv` | Returns for 1 to 30 years ending October 2026, and since April 1993 |
| `gold-vs-sensex-rolling-returns-1993-2026.csv` | Every 5, 10, 15 and 20-year window: nominal and real returns |
| `gold-vs-sensex-win-rates.csv` | How often gold won, by holding period and dividend assumption |
| `gold-vs-sensex-risk-1993-2026.csv` | Volatility, largest fall, longest spell below a high, worst 12 months |
| `gold-vs-sensex-mix-and-sip-backtest.csv` | 10 and 15-year lump sums and monthly SIPs for every start month and gold share (0–100%) |
| `gold-vs-sensex-mix-summary.csv` | Median, 10th-percentile and worst outcomes by gold share |
| `gold-vs-sensex-summary.json` | Headline numbers used in the article |
