# Which jobs is AI actually replacing?

Article: https://truthwithdata.com/blog/which-jobs-is-ai-actually-replacing.html · Lookup tool: https://truthwithdata.com/tools/ai-job-exposure-checker.html

Matches AI exposure scores to US employment for 722 occupations (May 2019 to May 2025) and tests whether exposure predicts job change, with a pre-ChatGPT placebo (2015–2019).

`model.py` and `model.R` are the regression models from the article. They read the harmonised occupation table `ai-exposure-employment-change-by-occupation.csv`. **That processed file is being added to this repository and the site shortly.**

## Source data

| Source | Link |
| --- | --- |
| BLS Occupational Employment and Wage Statistics (OEWS), national, May 2015, 2019, 2025 | https://www.bls.gov/oes/ |
| Anthropic Economic Index: job exposure and task penetration | https://huggingface.co/datasets/Anthropic/EconomicIndex |
| Felten, Raj and Seamans (2021), AI Occupational Exposure (AIOE) | https://github.com/AIOE-Data/AIOE |
| Dingel and Neiman (2020), teleworkable occupations | https://github.com/jdingel/DingelNeiman-workathome |
| BLS SOC 2010 to 2018 crosswalk | https://www.bls.gov/soc/2018/crosswalks.htm |
