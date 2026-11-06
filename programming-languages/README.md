# Which programming language is genuinely growing?

Code and data behind [Which Programming Language Is Genuinely Growing? We Checked Five Signals](https://truthwithdata.com/blog/which-programming-language-is-genuinely-growing.html) (Truth with Data, 5 November 2026) and the [Programming Language Momentum Checker](https://truthwithdata.com/tools/programming-language-momentum-checker.html).

17 languages, four growth signals measured as changes in **share** (12 months to Oct 2022 vs 12 months to Oct 2026), plus Stack Overflow questions as a fifth signal that turned out to be broken:

| Signal | Source | File in `data/inputs/` |
| --- | --- | --- |
| Usage | GitHub Innovation Graph, developers pushing code by economy and language (CC0) | `github-innovation-graph-pushers.csv` |
| Hiring | Hacker News "Who is hiring?" posts naming each language, Dec 2014–Nov 2026 | `hn-whos-hiring-language-mentions.csv` |
| Learning | Stack Overflow Developer Survey 2017–2026, % using / wanting each language (ODbL) | `so-survey-language-shares.csv` |
| Interest | Google Trends "programming language" topics, UK, US, India (manual exports) | `google-trends/` |
| Q&A | Stack Exchange API, questions per tag Jan–Oct, and quarterly totals | `stackoverflow-questions-*.csv` |
| Job ads now | The Adzuna API, 24 counts and mean advertised salaries, 5 Nov 2026 | `adzuna-it-jobs-2026-11-05.csv` |
| Skills | HN hiring posts naming AI, cloud and data skills, by year | `hn-whos-hiring-skill-mentions-by-year.csv` |

The inputs are aggregates (counts and percentages), not raw posts or survey responses.

## Run

```bash
pip install pandas numpy matplotlib requests
python3 analysis.py                  # every number in the article -> data/processed/
Rscript analysis.R                   # independent check of signals, ranking and backtest (base R)
python3 charts.py OUT_DIR TWD_Logo.png   # the eight SVG figures and the 1200x630 OG image
python3 export_tool_data.py language-momentum-data.js   # data file for the checker
```

To refresh the inputs: `python3 prepare_github.py innovationgraph/data/languages.csv` (after cloning
[github/innovationgraph](https://github.com/github/innovationgraph)), then
`python3 fetch_sources.py survey|stackoverflow|hn|hn_skills|adzuna` (Adzuna needs `ADZUNA_APP_ID` and
`ADZUNA_APP_KEY`). Re-export Google Trends by hand: four batches of five languages, Java in every batch so
they share a scale.

## Method in brief

- Each signal is the log change in a language's share; standardised across languages and averaged into a momentum score (three or more signals needed).
- Verdict: *real demand* (mean of usage and hiring) vs *attention* (mean of learning and interest). Both up = genuinely growing; demand only = quiet workhorse; attention only = hype; neither = fading.
- Forecast: log(want / use) in survey year t predicts log(use_{t+2} / use_t) with year fixed effects. 131 language-years 2017–2024: slope 0.33 (95% cluster-bootstrap interval 0.19–0.45); out-of-sample direction right 71% of the time; positive rank correlation in all 8 years and against GitHub in all 5 testable years.

## Licence

Code MIT. Processed data CC BY 4.0, credit "Truth with Data (truthwithdata.com)". GitHub Innovation Graph CC0; Stack Overflow survey ODbL; Adzuna data must be credited to [The Adzuna API](https://www.adzuna.co.uk/).
