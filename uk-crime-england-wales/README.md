# Is crime really going up in the UK? Two official measures, two different stories

Article: https://truthwithdata.com/blog/is-crime-going-up-in-the-uk.html · Lookup tool: https://truthwithdata.com/tools/crime-in-your-area-lookup.html

Compares the two official measures of crime in **England and Wales** from 1981 to the year ending June 2026: Crime Survey for England and Wales (CSEW) incidents and police recorded crime. It shows which offences are really rising (with the ONS's own significance flags), where the rise in police records since 2013/14 came from, the gap between perceived national and local crime, and police recorded crime per 1,000 residents by police force (2022–2026) and Community Safety Partnership (2024–2026). Scotland and Northern Ireland publish separate statistics and are not included. The method is described at the top of `uk-crime-analysis.py`; the R script recomputes the headline figures independently from the tidy tables as a cross-check.

## Source data (downloaded into `raw/` by `uk-crime-build-tables.py --fetch`)

| File | Publisher | Released / downloaded | Licence |
| --- | --- | --- | --- |
| `appendix-yejun2026.xlsx` | ONS, [Crime in England and Wales: Appendix tables](https://www.ons.gov.uk/peoplepopulationandcommunity/crimeandjustice/datasets/crimeinenglandandwalesappendixtables), year ending June 2026 (tables A1a, A1b, A5a) | 22 Oct 2026 / 25 Nov 2026 | OGL v3.0 |
| `pfa-yejun2022.xlsx` … `pfa-yejun2026.xlsx` | ONS, [Police force area data tables](https://www.ons.gov.uk/peoplepopulationandcommunity/crimeandjustice/datasets/policeforceareadatatables), years ending June 2022–2026 (P3; C2 and C4 from 2024) | 2022–2026 / 25 Nov 2026 | OGL v3.0 |
| `other-yemar2024.xlsx` | ONS, [Other related tables](https://www.ons.gov.uk/peoplepopulationandcommunity/crimeandjustice/datasets/crimeinenglandandwalesotherrelatedtables), year ending March 2024 (F17, perceptions) | 2024 / 25 Nov 2026 | OGL v3.0 |
| `trend-yemar2024.xlsx` | ONS, [Annual trend and demographic tables](https://www.ons.gov.uk/peoplepopulationandcommunity/crimeandjustice/datasets/crimeinenglandandwalesannualtrendanddemographictables), year ending March 2024 (D10, reporting to the police) | 2024 / 25 Nov 2026 | OGL v3.0 |
| `rec-crime-1898-2002.xls` | Home Office, [Historical crime data](https://www.gov.uk/government/statistics/historical-crime-data): recorded crime 1898 to 2001/02 | 2016 / 25 Nov 2026 | OGL v3.0 |

Bulletin: [Crime in England and Wales: year ending June 2026](https://www.ons.gov.uk/peoplepopulationandcommunity/crimeandjustice/bulletins/crimeinenglandandwales/yearendingjune2026) (22 October 2026). Raw files are not redistributed here. The ONS site rate-limits quick successive downloads; the fetch step waits and retries.

Notes: survey "significant" changes are the ONS's flags (5% level) from table A1b; we don't re-test. Police series have breaks (April 1998 counting rules, April 2002 NCRS); 1981–2001/02 Home Office totals have fraud and forgery removed. In the YE June 2026 CSP tables Kent Police left 44.5% of crimes unassigned to a CSP, so Kent CSP 2026 values are blanked; each CSP row carries its force's unassigned share.

## Run

```bash
pip install pandas openpyxl xlrd matplotlib requests pillow
python uk-crime-build-tables.py --fetch raw     # download the nine source files
python uk-crime-build-tables.py raw data        # tidy tables in data/
python uk-crime-analysis.py data                # derived CSVs and uk-crime-summary.json (add a path to also write the tool's JS data)
python uk-crime-charts.py data charts           # SVG charts and posters (PNG exports rendered from the SVGs with Playwright)
Rscript uk-crime-analysis.R data                # independent R cross-check (base R)
```

## Outputs (`data/`)

| File | Contents |
| --- | --- |
| `uk-crime-csew-incidents-1981-2026.csv` | CSEW incidents (thousands) by offence, 1981 to YE June 2026, plus interview counts (tidy, from A1a) |
| `uk-crime-csew-significance-ye-jun-2026.csv` | ONS % change to YE June 2026 and significance vs 1995, 2016/17, 2019/20, 2023/24, 2024/25 (A1b) |
| `uk-crime-police-recorded-by-offence-2003-2026.csv` | Police recorded crime by offence, 2002/03 to YE June 2026 (A5a) |
| `uk-crime-police-recorded-historical-1981-2002.csv` | Home Office recorded crime totals 1981–2001/02, both 1998/99 rule sets |
| `uk-crime-rates-by-police-force-2022-2026.csv` | Recorded crime per 1,000 residents by force and 14 offence groups, YE June 2022–2026 (P3) |
| `uk-crime-rates-by-csp-2024-2026.csv` | Per 1,000 by Community Safety Partnership: totals 2024–2026 and 14 groups for 2026, with the force's unassigned share (C2, C4) |
| `uk-crime-perceptions-2017-2024.csv` | Share saying crime rose nationally / locally (F17) |
| `uk-crime-csew-reported-to-police-1981-2024.csv` | Share of CSEW incidents reported to the police (D10) |
| `uk-crime-two-measures-1981-2026.csv` | The poster's two series, 1981 to YE June 2026 |
| `uk-crime-which-crimes-are-rising-2017-2026.csv` | Survey vs police change by offence, 2016/17 to YE June 2026, with verdicts |
| `uk-crime-police-rise-decomposition-2014-2026.csv` | Change in police recorded crime by offence group since 2013/14 |
| `uk-crime-force-summary-2026.csv` | Force totals 2022 and 2026, ratio to England and Wales |
| `uk-crime-summary.json` | Headline numbers used in the article |
