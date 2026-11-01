# Truth with Data: analysis code and data

Code and processed data behind the articles and [case studies](https://truthwithdata.com/case-studies.html) on **[truthwithdata.com](https://truthwithdata.com)**, which answers questions people actually ask with original, reproducible analysis of public data.

Every published number on the site should be traceable to a script or a file here. If you find a mistake, please [open an issue](https://github.com/truthwithdata/analysis/issues) or email truthwithdata@gmail.com. Corrections are noted at the end of the article.

| Folder | Article | What's here |
| --- | --- | --- |
| [`rent-vs-buy-uk/`](rent-vs-buy-uk) | [Is renting really 'dead money' in the UK?](https://truthwithdata.com/blog/is-renting-dead-money-uk.html) · [calculator](https://truthwithdata.com/tools/rent-vs-buy-calculator.html) | Full Python model, an independent R re-implementation, chart script, and all processed outputs (12 regions, 316 local authorities, 2005–2026 backtest, sensitivity tables) |
| [`ai-jobs/`](ai-jobs) | [Which jobs is AI actually replacing?](https://truthwithdata.com/blog/which-jobs-is-ai-actually-replacing.html) · [lookup tool](https://truthwithdata.com/tools/ai-job-exposure-checker.html) | The regression models in Python and R |
| [`ab-testing-peeking/`](ab-testing-peeking) | [A/B testing peeking case study](https://truthwithdata.com/case-studies/ab-testing-peeking-simulation.html) · [guide](https://truthwithdata.com/blog/statistical-significance-ab-testing.html) | Simulations of how "peeking" inflates false winners, and Pocock and O'Brien-Fleming boundaries that fix it (100,000 tests, six stopping plans) |
| [`ai-written-review-detector/`](ai-written-review-detector) | [Can a model spot an AI-written review?](https://truthwithdata.com/case-studies/detecting-ai-written-reviews.html) | Detectors for AI-written reviews from nine chat models, leave-one-generator-out tests, a 2019-vs-today comparison, and the compact model behind the live demo (Python + JavaScript) |

## Reproducing

Each folder has its own README with the exact source files and commands. Raw source data is not redistributed here. Download it from the publishers linked in each README, which keeps you on the official, current release.

## Licence

- **Code**: [MIT](LICENSE).
- **Processed data and charts**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit "Truth with Data (truthwithdata.com)" and link to the article.
- Source data remains under its publishers' terms (mostly the UK Open Government Licence or US public domain), as listed in each folder.
