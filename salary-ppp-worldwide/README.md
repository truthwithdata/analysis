# How far does your salary really go in another country?

Article: https://truthwithdata.com/blog/how-far-does-your-salary-go-in-another-country.html · Converter: https://truthwithdata.com/tools/salary-purchasing-power-converter.html

Compares salaries at market exchange rates and at purchasing power parity (PPP) for 164 countries (2025 data for 157, 2024 for 7). It computes each country's price level and what $1,000 changed at the market rate buys at US prices. It sets salaries against ILOSTAT median monthly earnings of employees for 108 countries (latest survey 2018 or later, uprated with CPI), and works through India to UK, US, UAE and Germany case studies. The method is described at the top of `salary-ppp-analysis.py`. The R script re-implements it independently from the same input tables as a cross-check (it matches to within CSV rounding, relative differences below 0.05%).

## Source data (downloaded into `raw/` by `salary-ppp-build-panel.py --fetch`)

| Series | Publisher | Licence |
| --- | --- | --- |
| `PA.NUS.PRVT.PP` PPP conversion factor, private consumption (LCU per international $) | World Bank, [World Development Indicators](https://data.worldbank.org/indicator/PA.NUS.PRVT.PP), API v2, last updated 11 November 2026 | CC BY 4.0 |
| `PA.NUS.PPP` PPP conversion factor, GDP | World Bank, [WDI](https://data.worldbank.org/indicator/PA.NUS.PPP) | CC BY 4.0 |
| `PA.NUS.FCRF` Official exchange rate (LCU per US$, period average) | World Bank, [WDI](https://data.worldbank.org/indicator/PA.NUS.FCRF) | CC BY 4.0 |
| `FP.CPI.TOTL` Consumer price index (2010 = 100), to uprate earnings | World Bank, [WDI](https://data.worldbank.org/indicator/FP.CPI.TOTL) | CC BY 4.0 |
| Country list, regions and income groups | World Bank API `/v2/country` | CC BY 4.0 |
| `EAR_EMTM_SEX_NB_A`, `EAR_EMTA_SEX_NB_A`, `EAR_EMTM_SEX_CUR_NB_A` median and mean monthly earnings of employees | ILO, [ILOSTAT earnings](https://ilostat.ilo.org/data/snapshots/earnings), bulk API `rplumber.ilo.org`, updated 23–24 November 2026 | CC BY 4.0 |
| `EAR_EMTM_SEX_OCU_CUR_NB_A` median monthly earnings by occupation (only the "2021 PPP $" rows for both sexes are kept) | ILO, ILOSTAT | CC BY 4.0 |

Downloaded on 25 November 2026. Raw files are not redistributed here. The two `salary-ppp-wdi-countries.csv`, `salary-ppp-ilostat-median-earnings.csv` and `salary-ppp-ilostat-occupations.csv` tables in `data/` are the build step's output, the input to the analysis.

Corrections made in the analysis (all listed in the script header):
- ILOSTAT reports EU-SILC earnings in euros for ten non-euro countries. These are converted back with that year's exchange rates and every country is checked against ILOSTAT's own US$ series (5% tolerance).
- Bulgaria: WDI PPP factors are in euros but the 2025 exchange rate is in leva, so the PPP factors are converted to leva.
- Sierra Leone (÷1000) and Mauritania (÷10) earnings are rescaled from old currency units.
- Liberia (PPP and exchange rate on different bases), Zimbabwe, Somalia and Madagascar (earnings) are dropped. Countries whose latest PPP year is before 2024 are excluded (for example Argentina and Iran).

## Run

```bash
pip install pandas numpy matplotlib requests cairosvg
python salary-ppp-build-panel.py --fetch raw          # World Bank API (one call per indicator-year) and ILOSTAT bulk files
python salary-ppp-build-panel.py raw data             # builds the three input tables
python salary-ppp-analysis.py data                    # writes the output CSVs and summary JSON in data/
python salary-ppp-charts.py data charts TWD_Logo_white.png   # bubble chart, poster, share image and supporting charts
Rscript salary-ppp-analysis.R data                    # independent R cross-check (base R)
```

## Outputs (`data/`)

| File | Contents |
| --- | --- |
| `salary-ppp-wdi-countries.csv` | Input: latest year with both the PPP factor and the exchange rate, for 203 countries |
| `salary-ppp-ilostat-median-earnings.csv` | Input: ILOSTAT median and mean monthly earnings (latest survey 2018+), survey, notes, survey-year exchange rate and CPI |
| `salary-ppp-ilostat-occupations.csv` | Input: ILOSTAT median monthly earnings by ISCO-08 major group, PPP $ |
| `salary-ppp-price-levels-by-country.csv` | 164 countries: PPP factor, exchange rate, price level, value of $1,000, GDP-based price level, median earnings (local, US$, PPP $) |
| `salary-ppp-median-earnings-by-country.csv` | Earnings checks: euro conversion, unit check, CPI uprating, exclusions |
| `salary-ppp-price-levels-by-region.csv` | Median price level by World Bank region |
| `salary-ppp-india-case-studies.csv` | ₹50,000, ₹1 lakh and ₹2 lakh a month in the UK, US, UAE and Germany |
| `salary-ppp-india-sensitivity-traded-share.csv` | ₹1 lakh a month with 0–100% of spending valued at market rates |
| `salary-ppp-occupation-earnings-ppp.csv` | Professionals and other groups vs all employees, latest year 2022+ |
| `salary-ppp-summary.json` | Headline numbers used in the article |
