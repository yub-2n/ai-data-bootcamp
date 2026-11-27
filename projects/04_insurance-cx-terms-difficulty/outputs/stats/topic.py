# -*- coding: utf-8 -*-
"""BERTopic 탐색적 보조 분석 (docs/지시/버토픽_실행.md).

- 주 코퍼스: 안건명(title), 보조 코퍼스: 조항 문구(clause_text, 분석 포함 157건)
- 임베딩: jhgan/ko-sroberta-multitask (local_files_only=True), 정규화 임베딩을 topic_cache/에 저장해 재사용
- 토픽은 cited와 검정·회귀하지 않는다. 인용률은 Wilson 95% CI를 붙인 기술통계(5건 이상)만.
실행: py -3.10 outputs/stats/topic.py
"""
import os
import sys

# 같은 폴더의 profile.py가 표준 라이브러리 profile을 가리지 않도록 스크립트 폴더를 import 경로에서 뺀다.
_HERE0 = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if os.path.abspath(p or os.getcwd()) != _HERE0]

import re
import hashlib
import warnings
from itertools import combinations

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CASES = os.path.join(ROOT, "data", "interim", "cases.csv")
OUT = HERE
CACHE = os.path.join(HERE, "topic_cache")
FIGS = os.path.join(HERE, "figs")
ENC = "utf-8-sig"
MODEL = "jhgan/ko-sroberta-multitask"
SEEDS = [42, 43, 44, 45, 46]
MAIN_SEED = 42

STOPWORDS = {"여부", "경우", "해당", "관련", "사례", "보험", "보험금", "보험계약", "지급",
             "책임", "인정", "적용", "대한", "사고", "회사"}
CUES = ["면책", "보상하지 않", "지급하지 않", "면책사유", "책임이 없"]
MCS = {"title": 8, "clause": 5}

# 토픽 이름(4장). 이름 붙인 주체: 이 스크립트를 실행한 에이전트(Claude Opus 5.5, claude-opus-5-5).
# 지시 문구: "토픽마다 키워드 10개와 대표 안건명 3개를 보고 2~6단어 한국어 이름을 붙인다.
#            이름은 키워드와 대표 안건명에 있는 말로만 짓는다. 해석을 더하지 않는다."
LABELS = {
    "title": {
        0: "계약 해지·의무 위반·청구",
        1: "재해사망·장해 급여금 지급분쟁",
        2: "실손 의료비·입원 비용",
        3: "재해·상해로 인한 사망",
        4: "암 진단 확정·검사",
        5: "수술 해당·수술급여금",
        6: "교통재해·차량 운전",
        7: "계약전 알릴의무 위반·자필서명",
        8: "알리지 않은 사실·알릴의무 위반",
        9: "정신질환 상태 자살·재해사망",
    },
    "clause": {
        0: "보상하는 손해·배상책임",
        1: "계약전 알릴의무·청약 질문",
        2: "보험금을 지급하지 않는 사유",
        3: "재해장해급여금·농업 작업",
        4: "책임개시일 이후 진단확정·상피내암",
        5: "재해사망·장해 분류",
        6: "입원의료비 보상 한도",
        7: "의사·의료기관 진단 소견",
        8: "우발적 외래 사고·관절",
    },
}
OUTLIER_LABEL = "바깥값"

# 그림 제목(결과를 본 뒤 내용으로 적음)
FIG_TITLES = {
    "B1": "안건명 {n}건은 {k}개 토픽으로 묶였고, {o}건은 어느 토픽에도 들지 않았다(회색)",
    "B2": "안건명 토픽은 계약·알릴의무, 재해사망, 실손의료비, 암 진단, 수술 등으로 갈린다",
    "B3": "규칙 주제와 안건명 토픽은 잘 겹치지 않는다(ARI {ari}): '보험금 지급사유'가 여러 토픽에 흩어짐",
    "B4": "안건명 면책 단서는 issue_type '면책' 사건에만 나타났다",
}


# ---------------------------------------------------------------- 데이터
def clean_title(t):
    t = str(t)
    t = re.sub(r"^\s*\([^()]*사례\)\s*", "", t)                     # (손해보험사례) 등 앞머리 분류 표시
    t = re.sub(r"\s*\(\s*제?\s*\d{2,4}\s*-\s*\d+\s*호?\s*\)", "", t)  # (제2013-34호), (97-16), (2005-1)
    return re.sub(r"\s+", " ", t).strip()


def load():
    d = pd.read_csv(CASES, encoding=ENC)
    n_all = len(d)
    log = {"n_all": n_all}
    log["drop_auto"] = int((d.is_auto == 1).sum())
    log["drop_dup"] = int((d.exclude_reason == "중복").sum())
    t = d[(d.is_auto != 1) & (d.exclude_reason != "중복")].copy()
    n0 = len(t)
    t = t.drop_duplicates("case_key", keep="first")
    log["drop_same_key"] = n0 - len(t)
    log["drop_same_key_keys"] = sorted(set(d[(d.is_auto != 1) & (d.exclude_reason != "중복")]
                                         .case_key[lambda s: s.duplicated()]))
    t["text_clean"] = t.title.map(clean_title)
    casebook = t.title.str.contains("사례집", na=False)
    log["drop_casebook"] = t.loc[casebook, "title"].tolist()
    t = t[~casebook].copy()
    t["in_analysis"] = t.exclude_reason.isna().astype(int)
    t["exemption_cue"] = t.text_clean.map(lambda s: int(any(c in s for c in CUES)))
    t = t.reset_index(drop=True)
    log["n_title"] = len(t)
    examples = t[t.title != t.text_clean][["title", "text_clean"]]
    c = d[d.exclude_reason.isna()].drop_duplicates("case_key", keep="first").copy()
    c = c[c.clause_text.notna()].reset_index(drop=True)
    c["text_clean"] = c.clause_text.astype(str).str.strip()
    c["in_analysis"] = 1
    cue = t.set_index("case_key").exemption_cue
    c["exemption_cue"] = c.case_key.map(cue).fillna(0).astype(int)
    log["n_clause"] = len(c)
    return t, c, log, examples


# ---------------------------------------------------------------- 임베딩
def embed(texts, name):
    os.makedirs(CACHE, exist_ok=True)
    h = hashlib.sha256(("\n".join(texts) + MODEL).encode("utf-8")).hexdigest()[:16]
    f = os.path.join(CACHE, f"emb_{name}_{h}.npy")
    if os.path.exists(f):
        return np.load(f)
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MODEL, local_files_only=True, device="cpu")
    e = m.encode(list(texts), batch_size=32, normalize_embeddings=True, show_progress_bar=False)
    e = np.asarray(e, dtype=np.float32)
    np.save(f, e)
    return e


# ---------------------------------------------------------------- 모형
_KIWI = None


def kiwi_nouns(text):
    global _KIWI
    if _KIWI is None:
        from kiwipiepy import Kiwi
        _KIWI = Kiwi()
    return [tk.form for tk in _KIWI.tokenize(text)
            if tk.tag in ("NNG", "NNP") and len(tk.form) >= 2 and tk.form not in STOPWORDS]


def make_model(seed, mcs):
    from bertopic import BERTopic
    from umap import UMAP
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    umap_model = UMAP(n_neighbors=10, n_components=5, min_dist=0.0, metric="cosine", random_state=seed)
    hdb = HDBSCAN(min_cluster_size=mcs, metric="euclidean", cluster_selection_method="eom",
                  prediction_data=True)
    vec = CountVectorizer(tokenizer=kiwi_nouns, lowercase=False, token_pattern=None)
    return BERTopic(embedding_model=None, umap_model=umap_model, hdbscan_model=hdb,
                    vectorizer_model=vec, nr_topics=None, top_n_words=10, language=None)


def fit(docs, emb, seed, mcs):
    tm = make_model(seed, mcs)
    topics, probs = tm.fit_transform(docs, embeddings=emb)
    return tm, np.asarray(topics), np.asarray(probs, dtype=float)


# ---------------------------------------------------------------- 보조
def wilson(k, n):
    from statsmodels.stats.proportion import proportion_confint
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
    return float(lo), float(hi)


def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


def label_of(corpus, k):
    if k == -1:
        return OUTLIER_LABEL
    return LABELS[corpus].get(int(k), f"T{int(k)}")


def run_corpus(name, df):
    from sklearn.metrics import adjusted_rand_score as ari
    docs = df.text_clean.tolist()
    emb = embed(docs, name)
    tm, topics, probs = fit(docs, emb, MAIN_SEED, MCS[name])
    reduced = np.asarray(tm.reduce_outliers(docs, topics, strategy="c-tf-idf"))
    info = tm.get_topic_info()
    rows = []
    for k in sorted(info.Topic):
        n = int((topics == k).sum())
        kw = [w for w, _ in tm.get_topic(k)] if k != -1 else []
        rep = tm.get_representative_docs(k) if k != -1 else []
        rows.append({"corpus": name, "topic": int(k), "label": label_of(name, k), "n": n,
                     "keywords": ", ".join(kw), "rep_docs": " | ".join(rep[:3])})
    tlist = pd.DataFrame(rows)
    # 안정성
    assign = {MAIN_SEED: topics}
    for s in SEEDS:
        if s != MAIN_SEED:
            assign[s] = fit(docs, emb, s, MCS[name])[1]
    stab = pd.DataFrame([{"corpus": name, "seed_a": a, "seed_b": b,
                          "ari": r4(ari(assign[a], assign[b]))} for a, b in combinations(SEEDS, 2)])
    out = df.copy()
    out["corpus"] = name
    out["topic"] = topics
    out["prob"] = [r4(p) for p in probs]
    out["topic_reduced"] = reduced
    return tm, out, tlist, stab, emb


def main():
    from sklearn.metrics import adjusted_rand_score as ari, normalized_mutual_info_score as nmi
    t, c, log, examples = load()
    tm_t, at, lt, st_t, emb_t = run_corpus("title", t)
    tm_c, ac, lc, st_c, _ = run_corpus("clause", c)

    # 17
    tl = pd.concat([lt, lc], ignore_index=True)
    tl.to_csv(os.path.join(OUT, "17_토픽목록.csv"), index=False, encoding=ENC)

    # 18
    cols = ["case_key", "corpus", "text_clean", "topic", "prob", "topic_reduced",
            "rule_topic", "issue_type", "in_analysis", "exemption_cue"]
    asg = pd.concat([at, ac], ignore_index=True).rename(columns={"topic_x": "topic"})
    asg["rule_topic"] = pd.concat([t.topic, c.topic], ignore_index=True)
    asg[cols].to_csv(os.path.join(OUT, "18_토픽배정.csv"), index=False, encoding=ENC)

    # 19 (분석 포함 157건)
    a157 = at[at.in_analysis == 1].copy()
    a157["bt"] = a157.topic.map(lambda k: f"{k}:{label_of('title', k)}")
    rows = []
    for tab, col in [("rule_topic", "rule_topic_src"), ("issue_type", "issue_type")]:
        src = t.loc[a157.index, "topic"] if tab == "rule_topic" else a157.issue_type
        ct = pd.crosstab(src.values, a157.bt.values)
        for r in ct.index:
            for cc in ct.columns:
                rows.append({"table": tab, "row": r, "col": cc, "n": int(ct.loc[r, cc])})
    rule = t.loc[a157.index, "topic"].values
    met = [
        ("ARI", "title(157) vs rule_topic", ari(rule, a157.topic.values)),
        ("NMI", "title(157) vs rule_topic", nmi(rule, a157.topic.values)),
        ("ARI", "title_reduced(157) vs rule_topic", ari(rule, a157.topic_reduced.values)),
        ("NMI", "title_reduced(157) vs rule_topic", nmi(rule, a157.topic_reduced.values)),
        ("ARI", "clause(157) vs rule_topic", ari(c.topic.values, ac.topic.values)),
        ("NMI", "clause(157) vs rule_topic", nmi(c.topic.values, ac.topic.values)),
    ]
    for m, what, v in met:
        rows.append({"table": "metric", "row": m, "col": what, "n": r4(v)})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "19_토픽비교.csv"), index=False, encoding=ENC)

    # 20
    pd.concat([st_t, st_c], ignore_index=True).to_csv(os.path.join(OUT, "20_토픽안정성.csv"),
                                                      index=False, encoding=ENC)

    # 21 (주 코퍼스 중 issue_type이 있는 사건; 안건명만 봄)
    r21 = []
    sub = at[at.issue_type.notna()]
    for it, g in sub.groupby("issue_type", sort=True):
        r21.append({"issue_type": it, "n": len(g), "n_cue": int(g.exemption_cue.sum()),
                    "share_cue": r4(g.exemption_cue.mean())})
    r21.append({"issue_type": "전체(issue_type 있음)", "n": len(sub), "n_cue": int(sub.exemption_cue.sum()),
                "share_cue": r4(sub.exemption_cue.mean())})
    t21 = pd.DataFrame(r21)
    t21.to_csv(os.path.join(OUT, "21_면책단서.csv"), index=False, encoding=ENC)

    # 22 (기술통계만, 분석 포함 사건 5건 이상 토픽)
    r22 = []
    for k, g in a157.groupby("topic", sort=True):
        g = g[g.cited.notna()]
        n = len(g)
        if n < 5:
            continue
        kc = int(g.cited.sum())
        lo, hi = wilson(kc, n)
        r22.append({"topic": int(k), "label": label_of("title", k), "n": n, "n_cited": kc,
                    "cited_rate": r4(kc / n), "ci_low": r4(lo), "ci_high": r4(hi)})
    pd.DataFrame(r22).to_csv(os.path.join(OUT, "22_토픽인용률.csv"), index=False, encoding=ENC)

    figures(tm_t, at, emb_t, a157, t, t21)

    # 실행 기록(콘솔)
    print("LOG", {k: v for k, v in log.items()})
    print("EXAMPLES"); print(examples.head(8).to_string())
    print(tl.to_string())
    for name, st in [("title", st_t), ("clause", st_c)]:
        print(name, "ARI mean/min/max", r4(st.ari.mean()), st.ari.min(), st.ari.max())
    for name, a in [("title", at), ("clause", ac)]:
        print(name, "n", len(a), "topics", len(set(a.topic) - {-1}), "outlier share", r4((a.topic == -1).mean()))
    for m in met:
        print(m[0], m[1], r4(m[2]))


def figures(tm, at, emb, a157, t, t21):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from umap import UMAP
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["svg.hashsalt"] = "topic"
    os.makedirs(FIGS, exist_ok=True)
    meta = {"Software": None}

    ks = sorted(k for k in set(at.topic) if k != -1)
    cmap = plt.get_cmap("tab20")
    # B1
    xy = UMAP(n_neighbors=10, n_components=2, min_dist=0.0, metric="cosine",
              random_state=MAIN_SEED).fit_transform(emb)
    fig, ax = plt.subplots(figsize=(9, 6.5))
    m = at.topic.values == -1
    ax.scatter(xy[m, 0], xy[m, 1], s=10, c="#d0d0d0", label=f"{OUTLIER_LABEL} ({m.sum()}건)")
    for i, k in enumerate(ks):
        mk = at.topic.values == k
        ax.scatter(xy[mk, 0], xy[mk, 1], s=14, color=cmap(i % 20), label=f"{label_of('title', k)} ({mk.sum()}건)")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(FIG_TITLES["B1"].format(n=len(at), k=len(ks), o=int(m.sum())), fontsize=10)
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(FIGS, "fig_B1_토픽지도.png"), dpi=200, metadata=meta); plt.close(fig)

    # B2
    nc = 3
    nr = int(np.ceil(len(ks) / nc))
    fig, axes = plt.subplots(nr, nc, figsize=(10, 2.2 * nr), squeeze=False)
    for i, k in enumerate(ks):
        ax = axes[i // nc][i % nc]
        kw = tm.get_topic(k)[:5][::-1]
        ax.barh([w for w, _ in kw], [s for _, s in kw], color=cmap(i % 20))
        ax.set_title(f"{label_of('title', k)}", fontsize=9)
        ax.tick_params(labelsize=8); ax.set_xticks([])
    for j in range(len(ks), nr * nc):
        axes[j // nc][j % nc].axis("off")
    fig.suptitle(FIG_TITLES["B2"], fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(FIGS, "fig_B2_토픽키워드.png"), dpi=200, metadata=meta); plt.close(fig)

    # B3
    rule = t.loc[a157.index, "topic"]
    order_c = [k for k in [-1] + ks]
    ct = pd.crosstab(rule.values, a157.topic.values).reindex(columns=order_c, fill_value=0)
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(1.0 + 0.75 * ct.shape[1], 0.9 + 0.45 * ct.shape[0]))
    ax.imshow(ct.values, cmap="Blues", aspect="auto")
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            v = ct.values[i, j]
            if v:
                ax.text(j, i, str(v), ha="center", va="center", fontsize=8,
                        color="white" if v > ct.values.max() * 0.6 else "black")
    ax.set_xticks(range(ct.shape[1]), [label_of("title", k) for k in ct.columns], rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(ct.shape[0]), ct.index, fontsize=8)
    ax.set_xlabel("BERTopic 토픽(안건명)", fontsize=9); ax.set_ylabel("규칙 주제", fontsize=9)
    from sklearn.metrics import adjusted_rand_score as _ari
    ax.set_title(FIG_TITLES["B3"].format(ari=f"{_ari(rule.values, a157.topic.values):.2f}"), fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(FIGS, "fig_B3_규칙주제대비.png"), dpi=200, metadata=meta); plt.close(fig)

    # B4
    g = t21[~t21.issue_type.str.startswith("전체")]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(g.issue_type, g.share_cue, color=["#4c72b0" if x != "면책" else "#c44e52" for x in g.issue_type])
    for i, r in enumerate(g.itertuples()):
        ax.text(i, r.share_cue + 0.01, f"{r.n_cue}/{r.n}건", ha="center", fontsize=9)
    ax.set_ylabel("안건명에 면책 단서가 있는 비율")
    ax.set_ylim(0, max(0.1, float(g.share_cue.max()) * 1.25))
    ax.set_title(FIG_TITLES["B4"], fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIGS, "fig_B4_면책단서.png"), dpi=200, metadata=meta); plt.close(fig)


if __name__ == "__main__":
    main()
