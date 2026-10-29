# Is renting really 'dead money' in the UK?

Article: https://truthwithdata.com/blog/is-renting-dead-money-uk.html · Calculator: https://truthwithdata.com/tools/rent-vs-buy-calculator.html

Compares renting and buying the same home in 12 UK regions and 316 local authorities (July 2026 prices and rents), with a backtest of every purchase month from 2005 to 2026. The model is described at the top of `uk-rent-vs-buy-analysis.py`; the R script re-implements it independently from the processed panel as a cross-check.

## Source data (download into `raw/`)

| File | Publisher |
| --- | --- |
| `UK-HPI-full-file-2026-07.csv` | HM Land Registry, [UK House Price Index data downloads, July 2026](https://www.gov.uk/government/statistical-data-sets/uk-house-price-index-data-downloads-july-2026) |
| `priceindexofprivaterentsukmonthlypricestatistics.xlsx` | ONS, [Price Index of Private Rents, monthly price statistics](https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/priceindexofprivaterentsukmonthlypricestatistics) (21 October 2026 edition) |
| `priceindexofprivaterentsukhistoricalseries.xlsx` | ONS, Price Index of Private Rents historical series (26 March 2025) |
| `Bank_of_England__Database.xlsx` | Bank of England [database](https://www.bankofengland.co.uk/boeapps/database/): quoted 2-year fixed mortgage rates (IUMBV34, IUMB482, …), monthly |

UK HPI and ONS data: Open Government Licence v3.0. Bank of England data: see the Bank's terms of use.

## Run

```bash
pip install pandas numpy openpyxl matplotlib
python uk-rent-vs-buy-analysis.py raw out      # writes the CSVs in data/ (and summary.json)
python uk-rent-vs-buy-charts.py out charts      # the article's charts
Rscript uk-rent-vs-buy-analysis.R data          # independent R cross-check
```

## Outputs (`data/`)

| File | Contents |
| --- | --- |
| `uk-rent-vs-buy-breakeven-by-region-2026.csv` | Break-even years and wealth gaps by region, deposit and property type |
| `uk-rent-vs-buy-breakeven-by-local-authority-2026.csv` | Break-even years for 316 local authorities |
| `uk-rent-vs-buy-backtest-2005-2026.csv` | Historical backtest by purchase month and holding period |
| `uk-rent-vs-buy-sensitivity-2026.csv` | Sensitivity to mortgage rate and price growth |
| `uk-rent-vs-buy-first-year-costs-2026.csv` | First-year cost of owning vs renting by region |
| `uk-rent-vs-buy-monthly-panel-2005-2026.csv` | The monthly regional price, rent and rate panel the model runs on |
