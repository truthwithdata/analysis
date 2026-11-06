"""Which programming language is genuinely growing? Five signals, 2015-2026.

Inputs (data/inputs/):
  github-innovation-graph-pushers.csv      usage: unique developers pushing code, quarterly (prepare_github.py)
  so-survey-language-shares.csv            learning: Stack Overflow Developer Survey, % used / % want (fetch_sources.py)
  hn-whos-hiring-language-mentions.csv     hiring: HN "Who is hiring?" posts mentioning each language (fetch_sources.py)
  google-trends/{GB,US,IN}-batch{1-4}.csv  interest: Google Trends, "programming language" topics, monthly
  stackoverflow-questions-*.csv            Q&A: Stack Overflow questions asked (fetch_sources.py)
  adzuna-it-jobs-2026-11-05.csv            current job ads and mean advertised salary (fetch_sources.py)

Outputs: data/processed/*.csv and data/processed/summary.json
Run: python3 analysis.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW, OUT = HERE / "data/inputs", HERE / "data/processed"
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261105)

# The 17 languages present in all four signals' sources (Google Trends batches define the set).
LANGS = ["Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust", "Kotlin",
         "Swift", "PHP", "Ruby", "R", "SQL", "Dart", "Scala", "Julia"]
GEOS = ["WORLD", "GB", "US", "IN"]
SIGNALS = ["usage", "learning", "hiring", "interest"]
# Before = the 12 months to Oct 2022 (ChatGPT launched 30 Nov 2022); after = the 12 months to Oct 2026.
BEFORE, AFTER = ("2021-11", "2022-10"), ("2025-11", "2026-10")


def logratio(after, before):
    return np.log(after / before) if (before > 0 and after > 0) else np.nan


# ---------- 1. Usage: GitHub Innovation Graph ----------
gh = pd.read_csv(RAW / "github-innovation-graph-pushers.csv")
gh["period"] = gh.year.astype(str) + "Q" + gh.quarter.astype(str)
gh_long = gh.melt(id_vars=["geo", "year", "quarter", "period", "ALL_PROGRAMMING"], var_name="language", value_name="pushers")
gh_long["share"] = gh_long.pushers / gh_long.ALL_PROGRAMMING
gh_long.to_csv(OUT / "github-share-quarterly.csv", index=False, float_format="%.6g")
# Four-quarter windows: Q3 2021-Q2 2022 (before) vs Q3 2025-Q2 2026 (latest available)
def gh_window(y0):
    m = ((gh_long.year == y0) & (gh_long.quarter >= 3)) | ((gh_long.year == y0 + 1) & (gh_long.quarter <= 2))
    w = gh_long[m].groupby(["geo", "language"])[["pushers", "ALL_PROGRAMMING"]].sum()
    return w.pushers / w.ALL_PROGRAMMING, w.pushers / 4
gh_b, gh_b_n = gh_window(2021)
gh_a, gh_a_n = gh_window(2025)
usage = pd.DataFrame({"share_before": gh_b, "share_after": gh_a, "pushers_after": gh_a_n}).reset_index()
usage["usage"] = [logratio(a, b) for a, b in zip(usage.share_after, usage.share_before)]
usage["pushers_growth_pct"] = 100 * (gh_a_n / gh_b_n - 1).values

# ---------- 2. Learning: Stack Overflow Developer Survey ----------
sv = pd.read_csv(RAW / "so-survey-language-shares.csv")
sv = sv.melt(id_vars=["geo", "year", "n", "metric"], var_name="language", value_name="pct")
# A share of exactly 0.0 means the language was not offered as an answer that year
not_offered = sv[(sv.geo == "ALL") & (sv.metric == "u") & (sv.pct == 0)][["year", "language"]]
sv = sv.merge(not_offered.assign(drop=1), on=["year", "language"], how="left")
sv.loc[sv["drop"] == 1, "pct"] = np.nan
sv = sv.drop(columns="drop").pivot_table(index=["geo", "year", "n", "language"], columns="metric", values="pct").reset_index()
sv["geo"] = sv.geo.replace({"ALL": "WORLD"})
core = sv[sv.language.isin(LANGS)].copy()
# Relative desire: a language's share of all "want to work with" ticks among the 17 languages.
# (Every language's raw "want" % fell in 2025-26 as the survey changed, so levels are not comparable.)
core["want_rel"] = core.w / core.groupby(["geo", "year"]).w.transform("sum")
core["used_rel"] = core.u / core.groupby(["geo", "year"]).u.transform("sum")
core.to_csv(OUT / "survey-language-shares-long.csv", index=False, float_format="%.5g")
lb = core[core.year == 2022].set_index(["geo", "language"])
la = core[core.year == 2026].set_index(["geo", "language"])
learning = pd.DataFrame({"want_2022": lb.w, "want_2026": la.w, "used_2022": lb.u, "used_2026": la.u,
                         "survey_n_2026": la.n})
learning["learning"] = np.log(la.want_rel / lb.want_rel)
learning = learning.reset_index()

# ---------- 3. Hiring: Hacker News "Who is hiring?" ----------
hn = pd.read_csv(RAW / "hn-whos-hiring-language-mentions.csv")
hn = hn.groupby("month", as_index=False).sum()      # March 2020 had two threads
hn_cols = [c for c in hn.columns if c not in ("month", "posts", "remote")]
hn_year = hn.assign(year=hn.month.str[:4].astype(int)).groupby("year")[["posts"] + hn_cols].sum()
(hn_year[hn_cols].div(hn_year.posts, axis=0) * 100).round(2).assign(posts=hn_year.posts).to_csv(OUT / "hn-share-by-year.csv")
hn_core = [c for c in hn_cols if c in LANGS]
def hn_window(a, b):
    w = hn[(hn.month >= a) & (hn.month <= b)][["posts"] + hn_cols].sum()
    w["mentions"] = w[hn_core].sum()
    return w
hb, ha = hn_window(*BEFORE), hn_window(*AFTER)
rows = []
for L in hn_core:
    pb, pa = hb[L] / hb.posts, ha[L] / ha.posts
    # signal = change in the language's share of all language mentions (posts mention fewer languages over time)
    mb, ma = hb[L] / hb.mentions, ha[L] / ha.mentions
    # bootstrap the share change (binomial resampling of posts in each window)
    bb = rng.binomial(int(hb.posts), pb, 4000) / hb.posts
    ba = rng.binomial(int(ha.posts), pa, 4000) / ha.posts
    diff = 100 * (ba - bb)
    rows.append(dict(language=L, hn_share_before=100 * pb, hn_share_after=100 * pa,
                     hn_change_pp=100 * (pa - pb), hn_change_lo=np.percentile(diff, 2.5), hn_change_hi=np.percentile(diff, 97.5),
                     hiring=logratio(ma, mb) if min(hb[L], ha[L]) >= 20 else np.nan, hn_mentions_before=int(hb[L]), hn_mentions_after=int(ha[L]), hn_posts_before=int(hb.posts), hn_posts_after=int(ha.posts)))
hiring = pd.DataFrame(rows)

# ---------- 4. Interest: Google Trends ----------
tr = []
for geo in ["GB", "US", "IN"]:
    parts = [pd.read_csv(RAW / f"google-trends/{geo}-batch{i}.csv", parse_dates=["Time"]).set_index("Time") for i in range(1, 5)]
    parts = [p[p.index < "2026-11-01"] for p in parts]       # drop the partial month (exports ran on 5 Nov 2026)
    # Java is in every batch, so all batches share one scale; check, then keep one Java column
    for p in parts[1:]:
        assert (p["Java"] == parts[0]["Java"]).all(), f"{geo}: batches are not on a common scale"
    df = pd.concat([parts[0]] + [p.drop(columns="Java") for p in parts[1:]], axis=1)
    df.insert(0, "geo", geo)
    tr.append(df)
tr = pd.concat(tr).reset_index().rename(columns={"Time": "month"})
tr["month"] = tr.month.dt.strftime("%Y-%m")
tr.to_csv(OUT / "google-trends-monthly.csv", index=False)
def tr_window(a, b):
    w = tr[(tr.month >= a) & (tr.month <= b)].groupby("geo")[LANGS].sum()
    return w.div(w.sum(axis=1), axis=0)
tb, ta = tr_window(*BEFORE), tr_window(*AFTER)
tb_raw = tr[(tr.month >= BEFORE[0]) & (tr.month <= BEFORE[1])].groupby("geo")[LANGS].sum()
interest = []
for geo in tb.index:
    for L in LANGS:
        ok = tb_raw.loc[geo, L] >= 24        # need an average of >= 2 index points a month to be measurable
        interest.append(dict(geo=geo, language=L, trends_share_before=100 * tb.loc[geo, L], trends_share_after=100 * ta.loc[geo, L],
                             interest=logratio(ta.loc[geo, L], tb.loc[geo, L]) if ok else np.nan))
interest = pd.DataFrame(interest)
# WORLD interest = mean of GB and US log-ratios (India's index is too coarse for small languages)
wi = interest[interest.geo.isin(["GB", "US"])].groupby("language", as_index=False).interest.mean().assign(geo="WORLD")
interest = pd.concat([interest, wi])
# Total search interest across the 17 languages, all-time and recent
tot = tr.groupby(["geo", "month"])[LANGS].sum().sum(axis=1).unstack(0)
tot_change = {g: 100 * (tot.loc[AFTER[0]:AFTER[1], g].sum() / tot.loc[BEFORE[0]:BEFORE[1], g].sum() - 1) for g in tot.columns}

# ---------- 5. Q&A: Stack Overflow questions ----------
so = pd.read_csv(RAW / "stackoverflow-questions-jan-oct-by-tag.csv").set_index("year")
soq = pd.read_csv(RAW / "stackoverflow-questions-quarterly.csv")
so_fall = 100 * (1 - so.loc[2026, "ALL"] / so.loc[2019, "ALL"])

# ---------- Combine ----------
sig = []
for geo in GEOS:
    u = usage[usage.geo == geo].set_index("language")
    l = learning[learning.geo == geo].set_index("language")
    i = interest[interest.geo == geo].set_index("language")
    h = hiring.set_index("language")        # HN is one global market (US-heavy); used for every geography
    for L in LANGS:
        sig.append(dict(geo=geo, language=L,
                        usage=u.usage.get(L, np.nan) if L != "SQL" else np.nan,   # GitHub does not count .sql files as a language
                        learning=l.learning.get(L, np.nan),
                        hiring=h.hiring.get(L, np.nan) if L in h.index else np.nan,
                        interest=i.interest.get(L, np.nan)))
sig = pd.DataFrame(sig)
for s in SIGNALS:
    g = sig.groupby("geo")[s]
    sig[s + "_z"] = (sig[s] - g.transform("mean")) / g.transform("std")
zc = [s + "_z" for s in SIGNALS]
sig["n_signals"] = sig[SIGNALS].notna().sum(axis=1)
sig["n_up"] = (sig[SIGNALS] > 0).sum(axis=1)
sig["momentum"] = sig[zc].mean(axis=1).where(sig.n_signals >= 3)
sig["demand"] = sig[["usage", "hiring"]].mean(axis=1)          # what developers push and employers ask for
sig["attention"] = sig[["learning", "interest"]].mean(axis=1)   # what people want to learn / search for


def verdict(r):
    # Every signal is a change in share, so > 0 means gaining ground on the other 16 languages
    if r.n_signals < 3:
        return "Not enough data"
    if r.demand > 0 and r.attention > 0:
        return "Genuinely growing"
    if r.demand > 0:
        return "Quiet workhorse"     # used and hired more, talked about less
    if r.attention > 0:
        return "Hype"                # talked about more, used and hired less
    return "Fading"


sig["verdict"] = sig.apply(verdict, axis=1)
sig["rank"] = sig.groupby("geo").momentum.rank(ascending=False, method="min")
sig = sig.merge(usage[["geo", "language", "share_before", "share_after", "pushers_after", "pushers_growth_pct"]], on=["geo", "language"], how="left")
sig = sig.merge(learning[["geo", "language", "want_2022", "want_2026", "used_2022", "used_2026", "survey_n_2026"]], on=["geo", "language"], how="left")
sig = sig.merge(hiring[["language", "hn_share_before", "hn_share_after", "hn_change_pp", "hn_change_lo", "hn_change_hi"]], on="language", how="left")
sig = sig.merge(interest[["geo", "language", "trends_share_before", "trends_share_after"]], on=["geo", "language"], how="left")
sig = sig.sort_values(["geo", "rank"])
sig.to_csv(OUT / "momentum-by-language-and-country.csv", index=False, float_format="%.4g")

# Signal agreement: do the four signals move together? (Spearman across languages, WORLD)
w = sig[sig.geo == "WORLD"].set_index("language")
agree = w[SIGNALS].corr(method="spearman").round(2)
agree.to_csv(OUT / "signal-agreement-spearman.csv")

# ---------- Forecast: does "want" predict future "use"? (survey panel backtest) ----------
p = core[core.geo == "WORLD"].pivot(index="language", columns="year", values=["u", "w"])
rows = []
for t in range(2017, 2025):
    for L in LANGS:
        u0, w0, u2 = p.get(("u", t), {}).get(L, np.nan), p.get(("w", t), {}).get(L, np.nan), p.get(("u", t + 2), {}).get(L, np.nan)
        if all(np.isfinite([u0, w0, u2])) and u0 > 0 and u2 > 0:
            rows.append(dict(year=t, language=L, gap=np.log(w0 / u0), growth=np.log(u2 / u0)))
bt = pd.DataFrame(rows)
bt["gap_c"] = bt.gap - bt.groupby("year").gap.transform("mean")         # year fixed effects (demean)
bt["growth_c"] = bt.growth - bt.groupby("year").growth.transform("mean")
slope = (bt.gap_c * bt.growth_c).sum() / (bt.gap_c ** 2).sum()
# cluster bootstrap by language for the slope
langs_bt = bt.language.unique()
boots = []
for _ in range(4000):
    pick = rng.choice(langs_bt, len(langs_bt), replace=True)
    b = pd.concat([bt[bt.language == x] for x in pick])
    boots.append((b.gap_c * b.growth_c).sum() / (b.gap_c ** 2).sum())
slope_ci = np.percentile(boots, [2.5, 97.5])
# out-of-sample: predict each year from the other years only
oos = []
for t in sorted(bt.year.unique()):
    tr_ = bt[bt.year != t]
    b = (tr_.gap_c * tr_.growth_c).sum() / (tr_.gap_c ** 2).sum()
    te = bt[bt.year == t]
    pred = b * te.gap_c
    hit = np.mean(np.sign(pred) == np.sign(te.growth_c))
    rho = pd.Series(pred.values).corr(pd.Series(te.growth_c.values), method="spearman")
    oos.append(dict(year=t, n=len(te), direction_hit_rate=hit, spearman=rho))
oos = pd.DataFrame(oos)
oos.to_csv(OUT / "forecast-backtest-by-year.csv", index=False, float_format="%.3f")
bt.to_csv(OUT / "forecast-backtest-panel.csv", index=False, float_format="%.4f")

# 2028 forecast from the 2026 survey: relative growth vs the average language, with bootstrap interval
f = []
gap26 = np.log(p[("w", 2026)] / p[("u", 2026)]).dropna()
gap26_c = gap26 - gap26.mean()
resid_sd = np.std(bt.growth_c - slope * bt.gap_c, ddof=1)
for L in gap26.index:
    mid = slope * gap26_c[L]
    draws = np.array(boots) * gap26_c[L] + rng.normal(0, resid_sd, len(boots))
    f.append(dict(language=L, used_2026=p[("u", 2026)][L], want_2026=p[("w", 2026)][L], gap=gap26[L],
                  rel_growth_pct=100 * (np.exp(mid) - 1),
                  lo=100 * (np.exp(np.percentile(draws, 10)) - 1), hi=100 * (np.exp(np.percentile(draws, 90)) - 1),
                  p_gain=np.mean(draws > 0)))
fc = pd.DataFrame(f).sort_values("rel_growth_pct", ascending=False)
fc.to_csv(OUT / "forecast-2028-relative-usage.csv", index=False, float_format="%.4g")

# Cross-source check: does the survey gap in year t predict GitHub share growth from Q2 t to Q2 t+2?
ghw = gh_long[(gh_long.geo == "WORLD") & (gh_long.quarter == 2)].pivot(index="language", columns="year", values="share")
xv = []
for t in range(2020, 2025):
    g = np.log(p[("w", t)] / p[("u", t)])
    gr = np.log(ghw[t + 2] / ghw[t])
    both = pd.concat([g.rename("gap"), gr.rename("gh_growth")], axis=1).dropna()
    both = both[both.index.isin(LANGS) & (both.index != "SQL")]
    xv.append(dict(year=t, n=len(both), spearman=both.gap.corr(both.gh_growth, method="spearman"),
                   direction_hit_rate=np.mean(np.sign(both.gap - both.gap.mean()) == np.sign(both.gh_growth - both.gh_growth.mean()))))
xv = pd.DataFrame(xv)
xv.to_csv(OUT / "forecast-check-against-github.csv", index=False, float_format="%.3f")

# ---------- Trending now: last 12 months vs the 12 months before ----------
NOW_B, NOW_A = ("2024-11", "2025-10"), AFTER
gh_nb, _ = gh_window(2024)
hb2, ha2 = hn_window(*NOW_B), hn_window(*NOW_A)
tb2, ta2 = tr_window(*NOW_B), tr_window(*NOW_A)
tb2_raw = tr[(tr.month >= NOW_B[0]) & (tr.month <= NOW_B[1])].groupby("geo")[LANGS].sum()
lb2 = core[core.year == 2025].set_index(["geo", "language"])
now = []
for L in LANGS:
    gi = ("WORLD", L)
    ints = [logratio(ta2.loc[g, L], tb2.loc[g, L]) for g in ["GB", "US"] if tb2_raw.loc[g, L] >= 24]
    now.append(dict(language=L,
                    usage=np.log(gh_a[gi] / gh_nb[gi]) if L != "SQL" else np.nan,
                    learning=np.log(la.want_rel.get(gi, np.nan) / lb2.want_rel.get(gi, np.nan)),
                    hiring=logratio(ha2[L] / ha2.mentions, hb2[L] / hb2.mentions) if (L in hn_core and min(ha2[L], hb2[L]) >= 20) else np.nan,
                    interest=np.mean(ints) if ints else np.nan))
now = pd.DataFrame(now).set_index("language")
now["n_up"] = (now[SIGNALS] > 0).sum(axis=1)
now["n_signals"] = now[SIGNALS].notna().sum(axis=1)
now["score"] = ((now[SIGNALS] - now[SIGNALS].mean()) / now[SIGNALS].std()).mean(axis=1).where(now.n_signals >= 3)
now = now.sort_values("score", ascending=False)
now.to_csv(OUT / "trending-now-last-12-months.csv", float_format="%.4g")

# ---------- Summary ----------
adz = pd.read_csv(RAW / "adzuna-it-jobs-2026-11-05.csv")
summary = dict(
    windows=dict(before=BEFORE, after=AFTER, github_before="2021Q3-2022Q2", github_after="2025Q3-2026Q2", survey="2022 vs 2026"),
    world_ranking=w.sort_values("rank")[["rank", "momentum", "verdict", "n_up", "n_signals"] + SIGNALS].round(3).reset_index().to_dict("records"),
    verdict_counts={g: sig[sig.geo == g].verdict.value_counts().to_dict() for g in GEOS},
    signal_agreement=agree.to_dict(),
    trends_total_change_pct={k: round(v, 1) for k, v in tot_change.items()},
    so_questions_fall_2019_2026_pct=round(so_fall, 1),
    so_questions_jan_oct=dict(y2019=int(so.loc[2019, "ALL"]), y2022=int(so.loc[2022, "ALL"]), y2026=int(so.loc[2026, "ALL"])),
    hn_posts=dict(before=int(hb.posts), after=int(ha.posts)),
    backtest=dict(slope=round(slope, 3), ci95=[round(x, 3) for x in slope_ci], n_obs=len(bt), n_langs=int(bt.language.nunique()),
                  oos_mean_hit_rate=round(oos.direction_hit_rate.mean(), 3), oos_mean_spearman=round(oos.spearman.mean(), 3),
                  oos_years_positive_spearman=int((oos.spearman > 0).sum()), oos_years=len(oos)),
    survey_n=core.groupby(["geo", "year"]).n.first().unstack().to_dict(),
    adzuna_rows=len(adz),
    github_all_programming_pushers=dict(before=float(gh_window(2021)[1].groupby("geo").sum().get("WORLD", np.nan)),
                                        after=float(gh[(gh.geo == "WORLD") & (gh.year == 2026) & (gh.quarter == 2)].ALL_PROGRAMMING.iloc[0])),
    github_check=xv.round(3).to_dict("records"),
)
(OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
print(w.sort_values("rank")[["rank", "momentum", "verdict", "demand", "attention"] + SIGNALS].round(3).to_string())
print(hiring.round(2).to_string())
print(agree)
print("slope", round(slope, 3), slope_ci.round(3), "\n", oos.round(3))
print(fc.round(1).to_string())
print("trends total change", tot_change, "SO fall", so_fall)
print(xv.round(3))
print(now.round(3).to_string())
for g in ["GB", "US", "IN"]:
    print(g, sig[sig.geo == g].sort_values("rank")[["language", "momentum", "verdict"]].head(6).round(2).values.tolist())
