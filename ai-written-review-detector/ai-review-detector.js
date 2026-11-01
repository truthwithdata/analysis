/* AI-written review detector: browser port of the compact model in
   data/ai-written-review-detector-analysis.py (word 1-2 gram TF-IDF, sublinear tf,
   l2 norm, logistic regression). Runs entirely on the visitor's device.
   The same scoring code is checked against Python's probabilities on 200 reviews. */
(function (root) {
    'use strict';

    function normText(t) {
        t = String(t).normalize('NFKC')
            .replace(/[‘’]/g, "'").replace(/[“”]/g, '"')
            .replace(/\s+/g, ' ').trim();
        if ((t.match(/"/g) || []).length === 2 && t.startsWith('"') && t.endsWith('"')) t = t.slice(1, -1).trim();
        return t;
    }

    function prepare(model) {
        const index = new Map();
        model.vocab.forEach((term, i) => index.set(term, i));
        model.index = index;
        return model;
    }

    // Returns {p, contributions:[{term, weight}]} where weight > 0 pushes towards "AI".
    function score(text, model) {
        const tokens = normText(text).toLowerCase().match(/[\p{L}\p{N}_]{2,}/gu) || [];
        const counts = new Map();
        const add = (term) => {
            const i = model.index.get(term);
            if (i !== undefined) counts.set(i, (counts.get(i) || 0) + 1);
        };
        tokens.forEach((tok, k) => {
            add(tok);
            if (k + 1 < tokens.length) add(tok + ' ' + tokens[k + 1]);
        });
        let norm = 0;
        const x = [];
        counts.forEach((tf, i) => {
            const v = (1 + Math.log(tf)) * model.idf[i];
            x.push([i, v]);
            norm += v * v;
        });
        norm = Math.sqrt(norm) || 1;
        let z = model.intercept;
        const contributions = [];
        x.forEach(([i, v]) => {
            const w = model.coef[i] * v / norm;
            z += w;
            contributions.push({ term: model.vocab[i], weight: w });
        });
        contributions.sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight));
        return { p: 1 / (1 + Math.exp(-z)), contributions: contributions, words: tokens.length };
    }

    const api = { normText: normText, prepare: prepare, score: score };
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.AIReviewDetector = api;
})(this);
