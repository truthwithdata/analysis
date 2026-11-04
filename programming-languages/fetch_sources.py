"""Download and aggregate the public sources behind the programming-language article.

  python3 fetch_sources.py survey        Stack Overflow Developer Survey 2017-2026 (~1.4 GB, processed one year at a time)
  python3 fetch_sources.py stackoverflow Stack Exchange API: questions per tag, Jan-Oct each year + quarterly totals (~300 calls)
  python3 fetch_sources.py hn            Hacker News "Who is hiring?" threads via the Algolia API (languages)
  python3 fetch_sources.py hn_skills     the same threads, counting skill keywords (AI, cloud, data), by year
  ADZUNA_APP_ID=... ADZUNA_APP_KEY=... python3 fetch_sources.py adzuna   current IT job ads (24 calls)

Google Trends has no API: the CSVs in data/inputs/google-trends/ were exported by hand from
trends.google.com on 5 Nov 2026 ("programming language" topics, 2004-present, web search,
all categories). Java appears in every batch so the four batches share one scale.

Outputs are written to data/inputs/ in the formats analysis.py reads. Data licences: survey ODbL;
Stack Exchange CC BY-SA; HN posts belong to their authors (we keep counts only); Adzuna data
must be credited to "The Adzuna API".
"""
import datetime as dt
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAW = Path(__file__).parent / "data/inputs"
TMP = Path(os.environ.get("TMPDIR", "/tmp")) / "twd-langs"
TMP.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "truthwithdata.com research (contact via site)"}

SURVEY_LANGS = ["Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "C", "Go", "Rust", "Kotlin", "Swift", "PHP",
                "Ruby", "R", "SQL", "Dart", "Scala", "Julia", "Lua", "Zig", "Bash/Shell"]
SURVEY_COLS = {2017: ("HaveWorkedLanguage", "WantWorkLanguage"),
               **{y: ("LanguageWorkedWith", "LanguageDesireNextYear") for y in (2018, 2019, 2020)},
               **{y: ("LanguageHaveWorkedWith", "LanguageWantToWorkWith") for y in range(2021, 2026)},
               2026: ("LanguagesHaveWorkedWith", "LanguagesWantToWorkWith")}
GEO = {"United Kingdom": "GB", "United Kingdom of Great Britain and Northern Ireland": "GB",
       "United States": "US", "United States of America": "US", "India": "IN"}


def survey():
    lines = ["geo,year,n,metric," + ",".join(SURVEY_LANGS)]
    for y, (hc, wc) in SURVEY_COLS.items():
        fn = "survey_results_public.csv" if y == 2026 else "results.csv"
        url = f"https://media.githubusercontent.com/media/StackExchange/Survey/main/packages/archive/{y}/{fn}"
        path = TMP / f"so-{y}.csv"
        if not path.exists():
            with requests.get(url, stream=True, timeout=300, headers=UA) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for ch in r.iter_content(1 << 20):
                        f.write(ch)
        d = pd.read_csv(path, usecols=lambda c: c in {hc, wc, "Country"}, dtype=str, low_memory=False)
        d = d[d[hc].notna()]
        geo = d["Country"].map(GEO).fillna("OTHER").values
        tok = lambda s: re.sub(r";Bash/Shell[^;]*;", ";Bash/Shell;", ";" + str(s).replace("; ", ";") + ";")
        H, W = d[hc].map(tok).values, d[wc].fillna("").map(tok).values
        U = {L: np.array([f";{L};" in s for s in H]) for L in SURVEY_LANGS}
        Wm = {L: np.array([f";{L};" in s for s in W]) for L in SURVEY_LANGS}
        for g in ["ALL", "GB", "IN", "US"]:
            m = np.ones(len(d), bool) if g == "ALL" else geo == g
            n = int(m.sum())
            u = [100 * (U[L] & m).sum() / n for L in SURVEY_LANGS]
            w = [100 * (Wm[L] & m).sum() / n for L in SURVEY_LANGS]
            lines.append(f"{g},{y},{n},u," + ",".join(f"{v:.1f}" for v in u))
            lines.append(f"{g},{y},{n},w," + ",".join(f"{v:.1f}" for v in w))
            if g == "ALL":
                adm = [100 * (U[L] & Wm[L]).sum() / U[L].sum() if U[L].sum() else np.nan for L in SURVEY_LANGS]
                lines.append(f"{g},{y},{n},adm," + ",".join("" if np.isnan(v) else f"{v:.1f}" for v in adm))
        path.unlink()
        print(y, len(d))
    # same row order as the committed file: ALL, GB, IN, US within year order
    df = pd.DataFrame([l.split(",", 4) for l in lines[1:]], columns=["geo", "year", "n", "metric", "rest"])
    df["o"] = df.geo.map({"ALL": 0, "GB": 1, "IN": 2, "US": 3})
    df = df.sort_values(["o", "year"], kind="stable")
    (RAW / "so-survey-language-shares.csv").write_text("\n".join([lines[0]] + [",".join(r[:5]) for r in df.values]) + "\n")


SE_TAGS = ["python", "javascript", "typescript", "java", "c#", "c++", "c", "go", "rust", "kotlin", "swift", "php", "ruby",
           "r", "sql", "dart", "scala", "julia", "lua", "zig", "bash"]


def se_total(a, b, tag=None):
    p = {"site": "stackoverflow", "fromdate": int(a.timestamp()), "todate": int(b.timestamp()), "filter": "total"}
    if tag:
        p["tagged"] = tag
    r = requests.get("https://api.stackexchange.com/2.3/questions", params=p, timeout=30, headers=UA).json()
    if r.get("backoff"):
        time.sleep(r["backoff"])
    return r["total"]


def stackoverflow():
    rows = []
    for y in range(2015, 2027):
        a, b = dt.datetime(y, 1, 1), dt.datetime(y, 11, 1)        # 1 Jan - 31 Oct, comparable every year
        rows.append([y] + [se_total(a, b, t) for t in SE_TAGS] + [se_total(a, b)])
        time.sleep(0.2)
    pd.DataFrame(rows, columns=["year"] + SE_TAGS + ["ALL"]).to_csv(RAW / "stackoverflow-questions-jan-oct-by-tag.csv", index=False)
    q = []
    for y in range(2019, 2027):
        for k in range(4):
            if (y, k) >= (2026, 3):
                break
            a, b = dt.datetime(y, 3 * k + 1, 1), dt.datetime(y + (k == 3), (3 * k + 3) % 12 + 1, 1)
            q.append((f"{y}Q{k + 1}", se_total(a, b)))
    pd.DataFrame(q, columns=["quarter", "questions"]).to_csv(RAW / "stackoverflow-questions-quarterly.csv", index=False)


HN_PAT = {"Python": (r"\bpython\b", re.I), "JavaScript": (r"\bjavascript\b|\bnode\.?js\b|\bjs\b", re.I),
          "TypeScript": (r"\btypescript\b", re.I), "Java": (r"\bjava\b(?!\s*script)", re.I), "C#": (r"c#|\.net\b", re.I),
          "C++": (r"c\+\+|\bcpp\b", re.I), "Go": (r"\bgolang\b|\bGo\b(?! to\b)", 0), "Rust": (r"\brust\b", re.I),
          "Kotlin": (r"\bkotlin\b", re.I), "Swift": (r"\bswift\b", re.I), "PHP": (r"\bphp\b|laravel", re.I),
          "Ruby": (r"\bruby\b|\brails\b", re.I), "SQL": (r"\w*sql\b", re.I), "Dart": (r"\bdart\b|\bflutter\b", re.I),
          "Scala": (r"\bscala\b", re.I), "Julia": (r"\bJulia\b", 0), "Lua": (r"\blua\b", re.I), "Zig": (r"\bzig\b", re.I),
          "Elixir": (r"\belixir\b", re.I)}


def hn(out=None):
    threads, page = [], 0
    while True:
        r = requests.get("https://hn.algolia.com/api/v1/search_by_date", timeout=30, headers=UA,
                         params={"tags": "story,author_whoishiring", "hitsPerPage": 1000, "page": page,
                                 "numericFilters": "created_at_i>1417000000"}).json()
        threads += [(h["objectID"], h["created_at"][:10]) for h in r["hits"]
                    if "who is hiring" in h["title"].lower()]
        page += 1
        if page >= r["nbPages"]:
            break
    pc = {k: re.compile(p, f) for k, (p, f) in HN_PAT.items()}
    rows = []
    for oid, date in sorted(set(threads), key=lambda x: x[1]):
        d = requests.get(f"https://hn.algolia.com/api/v1/items/{oid}", timeout=60, headers=UA).json()
        posts = [html.unescape(re.sub("<[^>]+>", " ", c["text"])) for c in d.get("children", []) if c.get("text")]
        row = {"month": date[:7], "posts": len(posts), **{k: sum(1 for p in posts if c.search(p)) for k, c in pc.items()}}
        row["remote"] = sum(1 for p in posts if re.search(r"\bremote\b", p, re.I))
        rows.append(row)
    pd.DataFrame(rows).to_csv(out or RAW / "hn-whos-hiring-language-mentions.csv", index=False)


HN_SKILLS = {"LLM / generative AI": (r"\bLLMs?\b|large language model|generative ai|\bgenai\b|\bgpt-?\d|\bRAG\b|prompt engineering", re.I),
             "AI agents": (r"\bagents?\b|\bagentic\b", re.I), "Machine learning": (r"machine learning|\bML\b|deep learning", 0),
             "PyTorch": (r"pytorch", re.I), "TensorFlow": (r"tensorflow", re.I), "React": (r"\breact\b(?!ive)", re.I),
             "Kubernetes": (r"kubernetes|\bk8s\b", re.I), "Docker": (r"\bdocker\b", re.I), "AWS": (r"\bAWS\b|amazon web services", 0),
             "Terraform": (r"terraform", re.I), "PostgreSQL": (r"postgres", re.I),
             "Data engineering": (r"data engineer|\bspark\b|airflow|\bdbt\b|snowflake", re.I),
             "Blockchain / crypto": (r"blockchain|crypto|web3|solidity", re.I), "Remote": (r"\bremote\b", re.I)}


def hn_skills():
    global HN_PAT
    HN_PAT = HN_SKILLS
    hn(out=RAW / "hn-skills-monthly.csv")
    m = pd.read_csv(RAW / "hn-skills-monthly.csv").drop(columns=["remote"])
    m = m.groupby("month", as_index=False).sum()
    m["year"] = m.month.str[:4].astype(int)
    y = m.drop(columns="month").groupby("year").sum()
    y.to_csv(RAW / "hn-whos-hiring-skill-mentions-by-year.csv")
    (RAW / "hn-skills-monthly.csv").unlink()


def adzuna():
    key = dict(app_id=os.environ["ADZUNA_APP_ID"], app_key=os.environ["ADZUNA_APP_KEY"])
    q = {"Python": "python", "JavaScript": "javascript", "TypeScript": "typescript", "Java": "java", "C#": "c#",
         "C++": "c++", "Go": "golang", "Rust": "rust"}
    cur = {"gb": "GBP", "us": "USD", "in": "INR"}
    rows = []
    for cc in cur:
        for L, w in q.items():
            j = requests.get(f"https://api.adzuna.com/v1/api/jobs/{cc}/search/1", timeout=30,
                             params=dict(key, results_per_page=1, category="it-jobs", what_and=w)).json()
            rows.append(dict(country=cc.upper(), currency=cur[cc], language=L, query=w, ads=j["count"],
                             mean_advertised_salary=round(j["mean"])))
            time.sleep(0.5)
    pd.DataFrame(rows).to_csv(RAW / f"adzuna-it-jobs-{dt.date.today()}.csv", index=False)


if __name__ == "__main__":
    {"survey": survey, "stackoverflow": stackoverflow, "hn": hn, "hn_skills": hn_skills, "adzuna": adzuna}[sys.argv[1]]()
