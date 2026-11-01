# Can a model spot an AI-written review?

Case study: https://truthwithdata.com/case-studies/detecting-ai-written-reviews.html (includes a live version of the browser model)

Detectors trained on short human reviews versus reviews from nine chat models, tested on models they had never seen, and against a 2019-style detector trained on GPT-2 fakes.

## Data

`analysis.py` downloads both sources on first run and caches them. Raw review texts are not redistributed here.

| Source | Used as | After cleaning |
| --- | --- | --- |
| Salminen et al. (2022), *Creating and detecting fake reviews of online products*, Journal of Retailing and Consumer Services 64. Original Amazon reviews ("OR") | Human reviews (written before 2019) | 11,380 |
| Same dataset, GPT-2 reviews ("CG") | Older AI reviews | 12,698 |
| [CRSD](https://github.com/infinitode/crsd) (Infinitode, 2026), nine chat models from Gemini 1.5 Flash to GPT-5.2 Instant | Modern AI reviews | 7,475 |

Cleaning: NFKC normalisation, whitespace collapsed and quotes straightened (so typography such as double spaces after full stops carries no signal), 3–50 words, exact duplicates dropped. Human and modern AI reviews are then matched cell by cell on sentiment (human sentiment from star rating) and 5-word length bins: 4,018 of each.

## Run

```bash
pip install numpy pandas scipy scikit-learn matplotlib
python analysis.py out            # about a minute; writes CSVs, summary.json and the browser model to out/
python charts.py out charts       # three SVG charts
```

Seed 20261101. Rerunning reproduces every file in `data/` exactly.

## Results

Five-fold cross-validation on the matched set:

| Detector | ROC AUC | Accuracy | Caught at 1% false flags | Caught at 5% false flags |
| --- | --- | --- | --- | --- |
| Word 1–2 grams + character 2–5 grams, logistic regression | 0.990 | 95.3% | 86% | 95% |
| Compact 6,000-term word model (runs in the browser) | 0.986 | 94.2% | 81% | 93% |
| 24 style features, no vocabulary, gradient boosting | 0.960 | 88.9% | 60% | 80% |

A detector trained on 2019 GPT-2 fakes catches **1%** of modern chat-model reviews at a 1% false-flag rate (AUC 0.56). One trained on modern models catches 80%.

Leave-one-generator-out (train on eight chat models, test on the ninth), share caught at 1% false flags on unseen human reviews:

| Model | Seen in training (CV) | Held out |
| --- | --- | --- |
| Llama 3 8B | 95% | 87% |
| Gemini 1.5 Flash | 90% | 86% |
| Gemini 2.0 Flash-Lite | 95% | 80% |
| Mixtral 8x7B | 92% | 74% |
| Grok 4.1 Fast | 81% | 73% |
| GPT-4o mini | 89% | 63% |
| Gemini 3 Flash | 62% | 37% |
| GPT-5 mini | 90% | 35% |
| GPT-5.2 Instant | 55% | 29% |

Wilson 95% intervals are in `data/ai-written-review-detector-by-generator.csv`.

## Files

| File | Contents |
| --- | --- |
| `analysis.py` | Cleaning, matching, three detectors, all tests, browser-model export |
| `charts.py` | The three charts in the case study |
| `ai-review-detector.js` | JavaScript port of the compact model (scores match Python within 0.00002 on 200 reviews) |
| `data/ai-review-model.json` | The compact model: vocabulary, IDF weights, coefficients, thresholds for 1% and 5% false flags |
| `data/ai-written-review-detector-cross-validation.csv` | Table above |
| `data/ai-written-review-detector-by-generator.csv` | Per-model results, seen and held out, with intervals |
| `data/ai-written-review-detector-legacy-vs-modern.csv` | GPT-2-trained vs modern-trained detectors on both kinds of fake |
| `data/ai-written-review-detector-tells.csv` | Plain-English tells: share of AI vs human reviews showing each |
| `data/ai-written-review-detector-telltale-terms.csv` | Strongest words and phrases in the compact model |
| `data/ai-written-review-detector-style-features.csv` | Mean of each style feature, AI vs human |
| `data/ai-written-review-detector-summary.json` | Counts and headline numbers |

## Limits

- The CRSD reviews come from generic prompts ("write a positive review for a product, be descriptive and human-like"). Fakes written for a specific product, or edited by hand, will be harder to catch. Treat the numbers as a best case for unsophisticated fakes.
- The AI reviews cover products, films and venues; the human reviews are all Amazon products. Topic words help the full model for the wrong reason. The style-only model, with no vocabulary, still reaches AUC 0.96.
- English only, 50 words or fewer, one human platform. Small samples for some models after matching (110 for Llama 3, 134 for GPT-5.2 Instant).
- The demo model is for illustration. It is not evidence that any person used AI.
