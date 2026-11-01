#!/usr/bin/env python3
"""Can a model tell AI-written reviews from human ones? (Truth with Data case study, Nov 2026)

Usage:  python3 analysis.py OUT_DIR [CACHE_DIR]

Data (downloaded on first run, cached in CACHE_DIR):
  * Human reviews: the 20,216 original Amazon reviews ("OR") in Salminen et al. (2022),
    "Creating and detecting fake reviews of online products", Journal of Retailing and
    Consumer Services 64. Written before 2019, so before modern chatbots existed.
  * Legacy AI reviews: the 20,216 GPT-2 reviews ("CG") from the same dataset.
  * Modern AI reviews: CRSD (Infinitode, 2026), 10,147 reviews written by nine chat models
    from Gemini 1.5 Flash to GPT-5.2 Instant (MIT-style licence).

Method:
  1. Normalise text (collapse whitespace, straighten quotes) so no model can win by
     spotting typography such as double spaces after full stops. Drop exact duplicates.
  2. Keep reviews of 50 words or fewer, then match human and AI reviews cell by cell on
     sentiment (negative / neutral / positive, human sentiment from the star rating) and
     length (5-word bins). Length and tone therefore carry no signal.
  3. Three detectors: (a) word + character n-gram TF-IDF logistic regression, (b) 24
     style-only features (no vocabulary) in gradient boosting, (c) a compact word-level
     TF-IDF logistic regression small enough to run in a web browser.
  4. Tests: 5-fold cross-validation; leave-one-generator-out (train on eight chat models,
     test on the ninth); a 2019-style detector trained on GPT-2 tested on modern models;
     the share of AI reviews caught when only 1% of real reviews may be wrongly flagged.
Writes CSVs, summary.json and the browser model (ai-review-model.json) to OUT_DIR.
"""
import json
import os
import re
import sys
import unicodedata
import urllib.request

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold

OUT = sys.argv[1]
CACHE = sys.argv[2] if len(sys.argv) > 2 else os.path.join(OUT, "cache")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)
SEED = 20261101
rng = np.random.default_rng(SEED)

URLS = {
    "crsd.csv": "https://raw.githubusercontent.com/infinitode/crsd/main/data.csv",
    "salminen.csv": "https://raw.githubusercontent.com/SayamAlt/Fake-Reviews-Detection/main/fake%20reviews%20dataset.csv",
}
for name, url in URLS.items():
    p = os.path.join(CACHE, name)
    if not os.path.exists(p):
        print("downloading", url)
        urllib.request.urlretrieve(url, p)


# ---------------------------------------------------------------- 1. load and clean
def norm(t):
    t = unicodedata.normalize("NFKC", str(t))
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\s+", " ", t).strip()
    return t.strip('"').strip() if t.count('"') == 2 and t.startswith('"') and t.endswith('"') else t


crsd = pd.read_csv(os.path.join(CACHE, "crsd.csv"))
crsd = pd.DataFrame({"text": crsd.review.map(norm), "source": crsd.model, "sentiment": crsd.sentiment, "group": "modern"})
sal = pd.read_csv(os.path.join(CACHE, "salminen.csv"))
sal["sentiment"] = np.select([sal.rating <= 2, sal.rating == 3], ["negative", "neutral"], "positive")
sal = pd.DataFrame({"text": sal.text_.map(norm), "source": np.where(sal.label == "OR", "Human", "GPT-2"),
                    "sentiment": sal.sentiment, "group": np.where(sal.label == "OR", "human", "legacy")})
raw_counts = {"crsd_rows": len(crsd), "human_rows": int((sal.group == "human").sum()), "gpt2_rows": int((sal.group == "legacy").sum())}

df = pd.concat([crsd, sal], ignore_index=True)
df["words"] = df.text.str.split().str.len()
df = df[(df.words >= 3) & (df.words <= 50)]
df = df.drop_duplicates("text").reset_index(drop=True)  # also removes any text appearing in two sources
df["lenbin"] = np.minimum((df.words - 1) // 5, 9)
clean_counts = df.groupby("group").size().to_dict()
print("after cleaning:", clean_counts)


def match(ai, human, rng):
    """Equal numbers of AI and human reviews in every sentiment x length cell."""
    keep_ai, keep_h = [], []
    for key, a in ai.groupby(["sentiment", "lenbin"]):
        h = human[(human.sentiment == key[0]) & (human.lenbin == key[1])]
        n = min(len(a), len(h))
        if n:
            keep_ai.append(a.sample(n, random_state=int(rng.integers(1e9))))
            keep_h.append(h.sample(n, random_state=int(rng.integers(1e9))))
    return pd.concat(keep_ai), pd.concat(keep_h)


human = df[df.group == "human"]
modern = df[df.group == "modern"]
legacy = df[df.group == "legacy"]

# hold back 25% of human reviews for the cross-generator tests, so the legacy detector and
# the modern detector are scored on exactly the same unseen human reviews
h_idx = rng.permutation(human.index.to_numpy())
human_test_pool = human.loc[h_idx[: len(h_idx) // 4]]
human_train_pool = human.loc[h_idx[len(h_idx) // 4:]]

ai_m, hu_m = match(modern, human, rng)  # main matched set for cross-validation
main = pd.concat([ai_m.assign(y=1), hu_m.assign(y=0)], ignore_index=True)
print("matched set:", len(main), main.groupby("y").size().to_dict())


# ---------------------------------------------------------------- 2. features
FUNC = set("the a an and or but if of to in on at for with from by as is was are were be been it this that these those "
           "i me my we our you your he she they them their his her its not no so very too just really".split())
POS_EMO = set("love loved great amazing excellent fantastic perfect wonderful best awesome".split())


def style_features(texts):
    rows = []
    for t in texts:
        w = t.split()
        n = max(len(w), 1)
        low = [re.sub(r"[^\w']", "", x.lower()) for x in w]
        sents = [s for s in re.split(r"[.!?]+", t) if s.strip()]
        letters = sum(c.isalpha() for c in t) or 1
        rows.append([
            len(w), len(t), np.mean([len(x) for x in low if x] or [0]), len(set(low)) / n,
            len(sents), n / max(len(sents), 1),
            t.count(",") / n, t.count("!") / n, t.count("?") / n, t.count("'") / n, t.count('"') / n,
            t.count("-") / n, t.count("(") / n, t.count(":") / n + t.count(";") / n, t.count("...") / n,
            sum(c.isupper() for c in t) / letters, sum(c.isdigit() for c in t) / len(t),
            sum(x in FUNC for x in low) / n, sum(x in ("i", "me", "my", "i'm", "i've") for x in low) / n,
            sum(x in POS_EMO for x in low) / n, float(t[-1] in ".!?") if t else 0.0,
            float(bool(re.search(r"\b(i|im|dont|cant|wont|didnt|its)\b", t))),  # lower-case 'i', missing apostrophes
            float(bool(re.search(r"(.)\1\1", t.lower()))),  # 'sooo', '!!!'
            sum(1 for x in w if x.isupper() and len(x) > 1) / n,
        ])
    return np.array(rows, dtype=float)


STYLE_NAMES = ["words", "characters", "mean word length", "type-token ratio", "sentences", "words per sentence",
               "commas", "exclamation marks", "question marks", "apostrophes", "double quotes", "hyphens",
               "brackets", "colons/semicolons", "ellipses", "capital letters", "digits", "function words",
               "first person", "stock praise words", "ends with punctuation", "informal spelling",
               "repeated characters", "all-caps words"]


def ngram_vecs():
    return (TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True, max_features=150000))


def fit_ngram(train_text, y):
    vw, vc = ngram_vecs()
    X = hstack([vw.fit_transform(train_text), vc.fit_transform(train_text)]).tocsr()
    clf = LogisticRegression(C=4.0, max_iter=3000).fit(X, y)
    return lambda t: clf.predict_proba(hstack([vw.transform(t), vc.transform(t)]).tocsr())[:, 1]


def fit_style(train_text, y):
    clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06, random_state=SEED)
    clf.fit(style_features(train_text), y)
    return lambda t: clf.predict_proba(style_features(t))[:, 1]


BROWSER_VOCAB = 6000


def fit_browser(train_text, y):
    v = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True, max_features=BROWSER_VOCAB)
    clf = LogisticRegression(C=4.0, max_iter=3000).fit(v.fit_transform(train_text), y)
    f = lambda t: clf.predict_proba(v.transform(t))[:, 1]
    f.v, f.clf = v, clf
    return f


DETECTORS = {"ngram": ("Word and character patterns (full model)", fit_ngram),
             "style": ("Style only: 24 features, no vocabulary", fit_style),
             "browser": ("Compact model that runs in your browser", fit_browser)}


def recall_at_fpr(y, s, fpr_target):
    fpr, tpr, thr = roc_curve(y, s)
    ok = fpr <= fpr_target
    return float(tpr[ok].max()), float(thr[ok][np.argmax(tpr[ok])])


# ---------------------------------------------------------------- 3. cross-validation
skf = StratifiedKFold(5, shuffle=True, random_state=SEED)
oof = {k: np.zeros(len(main)) for k in DETECTORS}
for k, (label, fit) in DETECTORS.items():
    for tr, te in skf.split(main.text, main.y):
        f = fit(main.text.iloc[tr].tolist(), main.y.iloc[tr].to_numpy())
        oof[k][te] = f(main.text.iloc[te].tolist())
cv_rows = []
for k, (label, _) in DETECTORS.items():
    r1, _ = recall_at_fpr(main.y, oof[k], 0.01)
    r5, _ = recall_at_fpr(main.y, oof[k], 0.05)
    cv_rows.append({"detector": k, "label": label, "n": len(main), "roc_auc": roc_auc_score(main.y, oof[k]),
                    "accuracy": accuracy_score(main.y, oof[k] >= 0.5), "recall_at_1pct_fpr": r1, "recall_at_5pct_fpr": r5})
cv = pd.DataFrame(cv_rows)
print(cv.round(4).to_string())
cv.to_csv(os.path.join(OUT, "ai-written-review-detector-cross-validation.csv"), index=False)

# per generator, from the out-of-fold scores of the full model (human reviews shared)
gen_rows = []
hum_s = oof["ngram"][main.y.to_numpy() == 0]
_, thr1 = recall_at_fpr(main.y, oof["ngram"], 0.01)
for g, sub in main[main.y == 1].groupby("source"):
    s = oof["ngram"][sub.index]
    gen_rows.append({"generator": g, "n_ai": len(sub), "cv_roc_auc": roc_auc_score(np.r_[np.zeros(len(hum_s)), np.ones(len(s))], np.r_[hum_s, s]),
                     "cv_caught_at_1pct_fpr": float((s >= thr1).mean())})
gen = pd.DataFrame(gen_rows)

# ---------------------------------------------------------------- 4. leave one generator out
logo = []
for g in sorted(main[main.y == 1].source.unique()):
    tr = main[(main.y == 0) | (main.source != g)]
    # human reviews matched to generator g, held out of training
    g_ai = main[(main.y == 1) & (main.source == g)]
    hum_tr_idx = main[main.y == 0].sample(frac=0.8, random_state=SEED).index
    tr = tr[(tr.y == 1) | tr.index.isin(hum_tr_idx)]
    te_h = main[(main.y == 0) & ~main.index.isin(hum_tr_idx)]
    f = fit_ngram(tr.text.tolist(), tr.y.to_numpy())
    sh, sa = f(te_h.text.tolist()), f(g_ai.text.tolist())
    thr = np.quantile(sh, 0.99)  # threshold that wrongly flags 1% of unseen human reviews
    k, n = int((sa > thr).sum()), len(sa)
    z, ph = 1.96, k / n  # Wilson 95% interval for the share caught
    half = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    mid = (ph + z * z / (2 * n)) / (1 + z * z / n)
    logo.append({"generator": g, "n_ai": n, "n_human_test": len(te_h),
                 "logo_roc_auc": roc_auc_score(np.r_[np.zeros(len(sh)), np.ones(len(sa))], np.r_[sh, sa]),
                 "logo_caught_at_1pct_fpr": ph, "logo_caught_ci_low": mid - half, "logo_caught_ci_high": mid + half})
    print("LOGO", logo[-1])
gen = gen.merge(pd.DataFrame(logo), on=["generator", "n_ai"])
gen.to_csv(os.path.join(OUT, "ai-written-review-detector-by-generator.csv"), index=False)

# ---------------------------------------------------------------- 5. yesterday's detector, today's fakes
# Train on a human pool disjoint from the test humans; test both detectors on the same set.
ai_te, hu_te = match(modern, human_test_pool, rng)
mod_tr_ai = modern.drop(ai_te.index)
a1, h1 = match(mod_tr_ai, human_train_pool, rng)
a2, h2 = match(legacy, human_train_pool, rng)
lg_te_ai, lg_te_hu = match(legacy.drop(a2.index), human_test_pool, rng)
f_modern = fit_ngram(pd.concat([a1, h1]).text.tolist(), np.r_[np.ones(len(a1)), np.zeros(len(h1))])
f_legacy = fit_ngram(pd.concat([a2, h2]).text.tolist(), np.r_[np.ones(len(a2)), np.zeros(len(h2))])
cross = []
for tname, f in (("trained on GPT-2 (2019)", f_legacy), ("trained on modern chat models", f_modern)):
    for test, (ta, th) in (("GPT-2 reviews", (lg_te_ai, lg_te_hu)), ("modern chat-model reviews", (ai_te, hu_te))):
        sh, sa = f(th.text.tolist()), f(ta.text.tolist())
        thr = np.quantile(sh, 0.99)
        cross.append({"trained": tname, "tested": test, "n_ai": len(ta), "n_human": len(th),
                      "roc_auc": roc_auc_score(np.r_[np.zeros(len(sh)), np.ones(len(sa))], np.r_[sh, sa]),
                      "caught_at_1pct_fpr": float((sa > thr).mean())})
cross = pd.DataFrame(cross)
print(cross.round(4).to_string())
cross.to_csv(os.path.join(OUT, "ai-written-review-detector-legacy-vs-modern.csv"), index=False)

# ---------------------------------------------------------------- 6. what gives it away
fb = fit_browser(main.text.tolist(), main.y.to_numpy())
vocab = fb.v.get_feature_names_out()
coef = fb.clf.coef_[0]
dfreq = np.asarray((fb.v.transform(main.text) > 0).sum(axis=0)).ravel()
tell = pd.DataFrame({"term": vocab, "coef": coef, "docs": dfreq})
tell = tell[tell.docs >= 40]
top = pd.concat([tell.nlargest(15, "coef").assign(side="AI"), tell.nsmallest(15, "coef").assign(side="human")])
# share of AI vs human reviews using each term
X = fb.v.transform(main.text) > 0
for i, r in top.iterrows():
    j = fb.v.vocabulary_[r.term]
    col = np.asarray(X[:, j].todense()).ravel()
    top.loc[i, "pct_ai_reviews"] = col[main.y == 1].mean() * 100
    top.loc[i, "pct_human_reviews"] = col[main.y == 0].mean() * 100
top.to_csv(os.path.join(OUT, "ai-written-review-detector-telltale-terms.csv"), index=False)

# style features: AI vs human medians/means on the matched set
S = style_features(main.text.tolist())
style_cmp = pd.DataFrame({"feature": STYLE_NAMES, "mean_ai": S[main.y == 1].mean(0), "mean_human": S[main.y == 0].mean(0)})
style_cmp.to_csv(os.path.join(OUT, "ai-written-review-detector-style-features.csv"), index=False)

# plain-English tells: share of AI vs human reviews showing each one (matched set)
T = main.text
low = T.str.lower()
TELLS = {
    "Uses the word \"the\"": low.str.contains(r"\bthe\b"),
    "Opens with \"The ...\" or \"This ...\"": T.str.match(r"^(The|This)\b"),
    "Uses \"great\", \"good\" or \"nice\"": low.str.contains(r"\b(?:great|good|nice)\b"),
    "Uses \"not\"": low.str.contains(r"\bnot\b"),
    "Speaks to the reader (\"you\")": low.str.contains(r"\byou\b"),
    "No full stop, ! or ? at the end": ~T.str.contains(r"[.!?]\W*$"),
    "Lower-case \"i\" or a missing apostrophe": T.str.contains(r"\b(?:i|im|dont|cant|wont|didnt|doesnt|isnt)\b"),
    "Stretched letters or repeated punctuation (\"sooo\", \"!!\")": low.str.contains(r"([a-z!?.])\1\1|!!|\?\?"),
    "Contains a number": T.str.contains(r"\d"),
}
tells = pd.DataFrame([{"tell": k, "pct_ai": v[main.y == 1].mean() * 100, "pct_human": v[main.y == 0].mean() * 100}
                      for k, v in TELLS.items()])
print(tells.round(1).to_string())
tells.to_csv(os.path.join(OUT, "ai-written-review-detector-tells.csv"), index=False)

# ---------------------------------------------------------------- 7. browser model export
_, thr_b1 = recall_at_fpr(main.y, oof["browser"], 0.01)
_, thr_b5 = recall_at_fpr(main.y, oof["browser"], 0.05)
model = {
    "version": "2026-11-01", "vocab": list(vocab), "idf": [round(float(x), 4) for x in fb.v.idf_],
    "coef": [round(float(x), 4) for x in coef], "intercept": round(float(fb.clf.intercept_[0]), 5),
    "ngram": [1, 2], "sublinear_tf": True,
    "threshold_1pct_fpr": round(float(thr_b1), 4), "threshold_5pct_fpr": round(float(thr_b5), 4),
}
json.dump(model, open(os.path.join(OUT, "ai-review-model.json"), "w"), separators=(",", ":"))
# parity fixture: 200 texts with the Python probability, for checking the JavaScript port
fx = main.sample(200, random_state=SEED)
pd.DataFrame({"text": fx.text, "p_python": fb(fx.text.tolist())}).to_csv(os.path.join(OUT, "browser-parity-fixture.csv"), index=False)

# ---------------------------------------------------------------- 8. summary
summary = {
    "raw": raw_counts, "clean": {k: int(v) for k, v in clean_counts.items()},
    "matched_n": int(len(main)), "matched_ai": int(main.y.sum()), "generators": int(main[main.y == 1].source.nunique()),
    "cv": cv.set_index("detector").to_dict("index"),
    "logo_auc_min": float(gen.logo_roc_auc.min()), "logo_auc_max": float(gen.logo_roc_auc.max()),
    "logo_caught_min": float(gen.logo_caught_at_1pct_fpr.min()), "logo_caught_max": float(gen.logo_caught_at_1pct_fpr.max()),
    "logo_caught_median": float(gen.logo_caught_at_1pct_fpr.median()),
    "cross": cross.to_dict("records"),
    "browser_thresholds": {"fpr1": model["threshold_1pct_fpr"], "fpr5": model["threshold_5pct_fpr"]},
}
json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in summary.items() if k != "cross"}, indent=1))
