# -*- coding: utf-8 -*-
"""
difficulty_colab.py — 약관 조항 난이도 지표 계산 (파일럿용, 코랩·로컬 공용)

PROJECT.md 3장(기준값 12·13), 4-3, 4-7(가림 규칙), 5장, 7장을 따른다.
- 입력은 조항 문구뿐이다. 결과(cited)·사건 번호·시기는 읽지 않는다.
- 지표 정의와 사전은 아래 [고정 설정]에 모두 적혀 있다. 결과를 본 뒤 바꾸지 않는다.
  바꾸려면 팀 회의에서 정하고 PROJECT.md 변경 기록에 남긴다.

실행 단계
  1) build-dict : 표준약관 PDF의 '용어의 정의'에서 전문용어 사전을 만든다
                  → outputs/stats/term_dict.csv, docs/전문용어사전.md
  2) pilot      : blind 파일(21건)의 지표 4개와 종합 지수를 계산한다
                  → data/processed/difficulty_pilot.csv,
                    outputs/stats/지표상관_pilot.csv, outputs/stats/difficulty_pilot_요약.md
  3) full       : 본 분석. cases_for_difficulty.csv의 조항 난이도
                  → data/processed/difficulty.csv, outputs/stats/지표상관.csv, outputs/stats/difficulty_요약.md
  4) eval-sheet : 평가 시트 25개 → data/processed/eval_sheet.csv (+ outputs/stats/eval_map.csv, 팀원B만 보관)
  5) selftest   : 표준약관 문장으로 코드가 도는지만 확인한다(실제 데이터 사용 안 함)

사용법(로컬)
  python difficulty_colab.py build-dict
  python difficulty_colab.py pilot
코랩: 노트북(difficulty_colab.ipynb)의 셀을 위에서부터 차례로 실행한다.
필요 패키지: pandas numpy kiwipiepy pdfplumber
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd

# =====================================================================
# [고정 설정] — 회의에서 정한 뒤에는 바꾸지 않는다
# =====================================================================
BASE = os.environ.get("CX_BASE", ".")          # insurance-cx 폴더
PDF_GLOB = "data/raw/standard_terms/*.pdf"
BLIND_CSV = "data/interim/pilot_for_difficulty_blind.csv"
FULL_CSV = "data/interim/cases_for_difficulty.csv"   # 본 분석 입력(결과 열 없음, diff_id 사용)
OUT_FULL = "data/processed/difficulty.csv"
OUT_FULL_CORR = "outputs/stats/지표상관.csv"
OUT_FULL_SUM = "outputs/stats/difficulty_요약.md"
OUT_EVAL = "data/processed/eval_sheet.csv"        # 평가자에게 보내는 시트(문구 + 임시 번호만)
OUT_EVAL_MAP = "outputs/stats/eval_map.csv"       # eval_id ↔ diff_id (팀원B만 보관)
SEED = 42
TERM_CSV = "outputs/stats/term_dict.csv"
TERM_MD = "docs/전문용어사전.md"
OUT_PILOT = "data/processed/difficulty_pilot.csv"
OUT_CORR = "outputs/stats/지표상관_pilot.csv"
OUT_SUM = "outputs/stats/difficulty_pilot_요약.md"

# 표준약관 3종의 '용어의 정의' 위치 (PDF 쪽 번호, 1부터)
#   형식 list  : "가. 용어: 정의" 목록
#   형식 table : <붙임> 표 (첫 열 = 용어)
TERM_SOURCES = [
    ("생명보험", "list", [2, 3]),
    ("질병·상해보험(손해보험 회사용)", "list", [144, 145]),
    ("실손의료보험 기본형", "table", [250, 251, 252]),
    ("실손의료보험 특별약관1(중증 비급여)", "table", [258]),
    ("실손의료보험 특별약관2(비중증 비급여)", "table", [287]),
]
TERM_MIN_LEN, TERM_MAX_LEN = 2, 15             # 공백 뺀 글자 수
GENERIC_TERMS = {"회사", "계약", "의사", "약국", "입원"}   # 흔한 말이라 사전에서 뺌(2026-11-03 확정)

# 예외·단서 표현 사전 (정규식). 두 버전을 모두 계산하고, 어느 쪽을 쓸지는 회의에서 정한다.
#   v7       : 계획서 v7·agents/difficulty.md에 적힌 표현만
#   expanded : v7 + 회의 후보 표현 (팀원B 파일럿에서 v7은 0이 86%)
EXC_V7 = [r"다만", r"제외(?!\s*금액)", r"한하여", r"하지\s*아니한"]   # "보장제외금액" 같은 명사 속 "제외"는 세지 않음(4-8)
EXC_EXPANDED = EXC_V7 + [
    r"한해", r"불구하고", r"예외", r"아니합니다", r"않습니다", r"아니한다", r"않는다",
    r"그러하지\s*아니", r"이외의", r"를?\s*빼고", r"단,",
]
EXC_MAIN = "expanded"    # 2026-11-03 확정(PROJECT.md 4-8)

# 참조 표현. 'each' = 제3조 제2항을 2개로, 'chain' = 붙어 있는 조·항·호 묶음을 1개로
REF_PAT = r"제\s*\d+\s*조(?:\s*의\s*\d+)?|제\s*\d+\s*항|제\s*\d+\s*호|별\s*표|부\s*표|붙\s*임"
REF_MAIN = "each"        # 2026-11-03 확정(PROJECT.md 4-8)

NOUN_TAGS = {"NNG", "NNP"}
ZERO_RULE = 0.5          # 기준값 12: term_ratio가 0인 조항이 50% 이상이면 지수에서 제외
CORR_RULE = 0.7          # |r| ≥ 0.7이면 합치지 않고 대표 지표 하나 또는 PCA


def p(*parts):
    return os.path.join(BASE, *parts)


# ---------------------------------------------------------------------
# 1) 전문용어 사전
# ---------------------------------------------------------------------
def clean_term(s):
    s = re.sub(r"\s+", "", s or "")
    s = s.strip("‘’'\"「」·ㆍ:：")
    return s


def ok_term(s):
    return (TERM_MIN_LEN <= len(s) <= TERM_MAX_LEN
            and re.fullmatch(r"[가-힣·ㆍ]+", s) is not None
            and "정의" not in s and s not in GENERIC_TERMS)


def build_dict():
    import pdfplumber
    pdfs = glob.glob(p(PDF_GLOB))
    if not pdfs:
        sys.exit("표준약관 PDF가 없습니다: " + p(PDF_GLOB))
    rows = []
    with pdfplumber.open(pdfs[0]) as pdf:
        for name, kind, pages in TERM_SOURCES:
            if kind == "list":
                text = "\n".join(pdf.pages[i - 1].extract_text() or "" for i in pages)
                m = re.search(r"제\s*2\s*조\s*\(\s*용어의\s*정의\s*\)", text)
                end = re.search(r"제\s*3\s*조\s*\(", text[m.end():]) if m else None
                body = text[m.end(): m.end() + end.start()] if end else (text[m.end():] if m else "")
                for mm in re.finditer(r"(?m)^\s*[가-하]\.\s*([^:：\n]{1,25}?)\s*[:：]", body):
                    t = clean_term(mm.group(1))
                    if ok_term(t):
                        rows.append((t, name, pages[0] if mm.start() < len(body) else pages[-1]))
            else:
                for i in pages:
                    for tb in pdf.pages[i - 1].extract_tables():
                        if not tb or "용" not in (tb[0][0] or ""):
                            continue
                        for r in tb[1:]:
                            if not r or not r[0]:
                                continue
                            rest = [c for c in r[1:] if c and c.strip()]
                            if not rest:
                                continue
                            t = clean_term(r[0])
                            if ok_term(t):
                                rows.append((t, name, i))
    d = pd.DataFrame(rows, columns=["term", "source", "page"])
    d = d.groupby("term", as_index=False).agg(
        source=("source", lambda x: " / ".join(dict.fromkeys(x))),
        page=("page", lambda x: ", ".join(str(v) for v in dict.fromkeys(x))))
    d = d.sort_values("term").reset_index(drop=True)
    os.makedirs(os.path.dirname(p(TERM_CSV)), exist_ok=True)
    os.makedirs(os.path.dirname(p(TERM_MD)), exist_ok=True)
    d.to_csv(p(TERM_CSV), index=False, encoding="utf-8-sig")
    with open(p(TERM_MD), "w", encoding="utf-8") as f:
        f.write("# 전문용어사전\n\n")
        f.write("출처: 국가법령정보센터 「보험업감독업무시행세칙」 [별표 15] 표준약관"
                "(시행 2026. 9. 10.) PDF. 각 표준약관의 '용어의 정의' 조항(제2조 또는 <붙임1>)에서 "
                "코드(`difficulty_colab.py build-dict`)로 뽑았다. 쪽은 PDF 쪽 번호다.\n\n")
        f.write(f"- 용어 수: {len(d)}\n")
        f.write(f"- 흔한 말이라 뺀 용어(2026-11-03 확정): {', '.join(sorted(GENERIC_TERMS))}\n")
        for name, _, _ in TERM_SOURCES:
            f.write(f"- {name}: {int(d['source'].str.contains(re.escape(name)).sum())}개\n")
        f.write("\n| 용어 | 출처 | 쪽 |\n|---|---|---|\n")
        for _, r in d.iterrows():
            f.write(f"| {r.term} | {r.source} | {r.page} |\n")
    print(f"용어 {len(d)}개 → {TERM_CSV}, {TERM_MD}")
    return d


# ---------------------------------------------------------------------
# 2) 지표
# ---------------------------------------------------------------------
_KIWI = None


def kiwi(terms):
    global _KIWI
    if _KIWI is None:
        from kiwipiepy import Kiwi
        _KIWI = Kiwi()
        for t in terms:                      # 전문용어를 한 단어로 인식하게 등록
            _KIWI.add_user_word(t, "NNP", 0.0)
    return _KIWI


def norm(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def count_pats(text, pats):
    return sum(len(re.findall(x, text)) for x in pats)


def ref_counts(text):
    hits = list(re.finditer(REF_PAT, text))
    each = len(hits)
    chain = 0
    prev_end = None
    for h in hits:                           # 사이에 공백만 있으면 같은 묶음
        if prev_end is None or text[prev_end:h.start()].strip() != "":
            chain += 1
        prev_end = h.end()
    return each, chain


def indicators(text, terms):
    t = norm(text)
    k = kiwi(terms)
    sents = [s.text for s in k.split_into_sents(t)] or [t]
    n_words = len(t.split())
    toks = k.tokenize(t)
    nouns = [x.form for x in toks if x.tag in NOUN_TAGS]
    term_set = set(terms)
    n_term = sum(1 for x in nouns if x in term_set)
    each, chain = ref_counts(t)
    return {
        "n_chars": len(t),
        "n_sents": len(sents),
        "n_words": n_words,
        "words_per_sentence": n_words / len(sents) if sents else np.nan,
        "max_sentence_words": max(len(s.split()) for s in sents) if sents else np.nan,
        "exception_count_v7": count_pats(t, EXC_V7),
        "exception_count_expanded": count_pats(t, EXC_EXPANDED),
        "n_nouns": len(nouns),
        "n_term_nouns": n_term,
        "term_ratio": n_term / len(nouns) if nouns else 0.0,
        "ref_count_each": each,
        "ref_count_chain": chain,
    }


def zscore(s):
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd and not np.isnan(sd) else s * 0.0


def add_index(df):
    df["exception_count"] = df[f"exception_count_{EXC_MAIN}"]
    df["ref_count"] = df[f"ref_count_{REF_MAIN}"]
    zero_share = float((df["term_ratio"] == 0).mean())
    use = ["words_per_sentence", "exception_count", "ref_count"]
    if zero_share < ZERO_RULE:
        use.append("term_ratio")
    for c in use:
        df[f"z_{c}"] = zscore(df[c])
    df["difficulty_index"] = df[[f"z_{c}" for c in use]].mean(axis=1)
    if "issue_type" in df:
        df["diff_z_within_type"] = df.groupby("issue_type")["difficulty_index"].transform(zscore)
    return df, use, zero_share


def md_table(df, index=False):
    """tabulate 없이 마크다운 표를 만든다."""
    d = df.reset_index() if index else df
    fmt = lambda v: f"{v:.3f}" if isinstance(v, (float, np.floating)) else str(v)
    lines = ["| " + " | ".join(map(str, d.columns)) + " |", "|" + "---|" * len(d.columns)]
    lines += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in d.itertuples(index=False)]
    return "\n".join(lines)


def describe(df, cols):
    rows = []
    for c in cols:
        s = df[c].astype(float)
        rows.append({"지표": c, "평균": s.mean(), "표준편차": s.std(ddof=1), "최소": s.min(),
                     "최대": s.max(), "0 비율": float((s == 0).mean())})
    return pd.DataFrame(rows)


def run_pilot():
    terms = pd.read_csv(p(TERM_CSV))["term"].tolist()
    src = pd.read_csv(p(BLIND_CSV))
    forbidden = {"case_key", "cited", "period", "decision_date", "outcome_raw", "nttId"}
    bad = forbidden & set(src.columns)
    if bad:
        sys.exit(f"가림 규칙 위반: 입력에 {bad} 열이 있습니다. 멈춥니다.")
    src = src[["blind_id", "issue_type", "clause_level", "clause_text_form", "clause_text"]]
    ind = pd.DataFrame([indicators(x, terms) for x in src["clause_text"]])
    df = pd.concat([src.drop(columns=["clause_text"]), ind], axis=1)
    df, use, zero_share = add_index(df)

    base_cols = ["words_per_sentence", "exception_count_v7", "exception_count_expanded",
                 "term_ratio", "ref_count_each", "ref_count_chain"]
    desc = describe(df, base_cols)
    corr = df[["words_per_sentence", "exception_count", "term_ratio", "ref_count"]].corr()
    high = [(a, b, corr.loc[a, b]) for i, a in enumerate(corr.columns)
            for b in corr.columns[i + 1:] if abs(corr.loc[a, b]) >= CORR_RULE]

    for f in (OUT_PILOT, OUT_CORR, OUT_SUM):
        os.makedirs(os.path.dirname(p(f)), exist_ok=True)
    df.to_csv(p(OUT_PILOT), index=False, encoding="utf-8-sig")
    corr.to_csv(p(OUT_CORR), encoding="utf-8-sig")

    wps_max = df.loc[df["words_per_sentence"].idxmax()]
    wps_min = df.loc[df["words_per_sentence"].idxmin()]
    with open(p(OUT_SUM), "w", encoding="utf-8") as f:
        f.write("# 파일럿 난이도 지표 요약 (difficulty_colab.py pilot)\n\n")
        f.write(f"- 처리 건수: {len(df)} (blind_id 기준, 결과·사건 정보 없음)\n")
        f.write(f"- 전문용어 사전: {len(terms)}개 (`{TERM_CSV}`)\n")
        f.write(f"- 예외 표현 사전 기본값: {EXC_MAIN}, 참조 세기 기본값: {REF_MAIN} (회의에서 확정)\n\n")
        f.write("## 지표별 분포\n\n" + md_table(desc) + "\n\n")
        f.write(f"## 기준값 12\n\n- term_ratio가 0인 조항 비율: {zero_share:.3f} → "
                + ("50% 이상이라 **종합 지수에서 제외**(보조로만)" if zero_share >= ZERO_RULE
                   else "50% 미만이라 **종합 지수에 포함**") + "\n\n")
        f.write("## 상관행렬 (지수에 쓰는 버전)\n\n" + md_table(corr, index=True) + "\n\n")
        f.write("- |r| ≥ 0.7인 쌍: " + (", ".join(f"{a}–{b} ({r:.3f})" for a, b, r in high) if high else "없음") + "\n\n")
        if high:
            f.write("- **주의**: 위 쌍이 있으면 합치지 않고 대표 지표 하나 또는 PCA 첫 성분을 쓴다(agents/difficulty.md 4번). "
                    "어느 쪽을 쓸지는 회의에서 정하며, 아래 지수는 그 전의 임시값이다.\n\n")
        f.write(f"## 종합 지수\n\n- 사용 지표: {', '.join(use)} (각 z점수의 평균)\n\n")
        f.write("## 문장 나누기 점검 (원문은 적지 않음)\n\n")
        for lab, r in (("최대", wps_max), ("최소", wps_min)):
            f.write(f"- words_per_sentence {lab}: {r.blind_id} — {r.words_per_sentence:.1f} "
                    f"(문장 {int(r.n_sents)}개, 어절 {int(r.n_words)}개, 가장 긴 문장 {int(r.max_sentence_words)}어절, "
                    f"문구 형태 {r.clause_text_form})\n")
    print(desc.to_string(index=False))
    print(f"\n기준값 12: term_ratio 0 비율 = {zero_share:.3f}")
    print("\n상관행렬\n", corr.round(3))
    print("\n|r|≥0.7:", [(a, b, round(float(r), 3)) for a, b, r in high] or "없음", "\n지수 사용 지표:", use)
    print(f"\n저장: {OUT_PILOT}, {OUT_CORR}, {OUT_SUM}")
    return df


FORBIDDEN = {"case_key", "cited", "partial", "period", "decision_date", "outcome_raw", "nttId",
             "explained_duty", "ambiguity", "evidence_snippet", "title", "exclude_reason"}


def compute(texts, terms):
    return pd.DataFrame([indicators(x, terms) for x in texts])


def run_full():
    """본 분석: cases_for_difficulty.csv의 모든 조항 난이도를 계산한다."""
    terms = pd.read_csv(p(TERM_CSV))["term"].tolist()
    src = pd.read_csv(p(FULL_CSV))
    bad = FORBIDDEN & set(src.columns)
    if bad:
        sys.exit(f"가림 규칙 위반: 입력에 {bad} 열이 있습니다. 멈춥니다.")
    src = src[src["clause_text"].fillna("").str.strip() != ""].reset_index(drop=True)
    ind = compute(src["clause_text"], terms)
    df = pd.concat([src[["diff_id", "issue_type", "clause_level", "clause_text_form"]], ind], axis=1)
    df, use, zero_share = add_index(df)
    # 조 전체 문구 버전(필수 민감도 ③). 없으면 원래 문구를 쓴다.
    art_text = src.get("clause_text_article", src["clause_text"]).fillna("")
    art_text = art_text.where(art_text.str.strip() != "", src["clause_text"])
    art = compute(art_text, terms)
    art["exception_count"] = art[f"exception_count_{EXC_MAIN}"]
    art["ref_count"] = art[f"ref_count_{REF_MAIN}"]
    art_idx = pd.concat([zscore(art[c]) for c in use], axis=1).mean(axis=1)
    df["difficulty_index_article"] = art_idx
    keep = ["diff_id", "issue_type", "clause_level", "clause_text_form", "words_per_sentence",
            "exception_count", "term_ratio", "ref_count", "exception_count_v7",
            "exception_count_expanded", "ref_count_each", "ref_count_chain", "n_sents",
            "max_sentence_words", "difficulty_index", "diff_z_within_type", "difficulty_index_article"]
    for f in (OUT_FULL, OUT_FULL_CORR, OUT_FULL_SUM):
        os.makedirs(os.path.dirname(p(f)), exist_ok=True)
    df[keep].to_csv(p(OUT_FULL), index=False, encoding="utf-8-sig")
    corr = df[["words_per_sentence", "exception_count", "term_ratio", "ref_count"]].corr()
    corr.to_csv(p(OUT_FULL_CORR), encoding="utf-8-sig")
    high = [(a, b, float(corr.loc[a, b])) for i, a in enumerate(corr.columns)
            for b in corr.columns[i + 1:] if abs(corr.loc[a, b]) >= CORR_RULE]
    desc = describe(df, ["words_per_sentence", "exception_count", "term_ratio", "ref_count",
                         "difficulty_index", "difficulty_index_article"])
    with open(p(OUT_FULL_SUM), "w", encoding="utf-8") as f:
        f.write("# 본 분석 난이도 요약 (difficulty_colab.py full)\n\n")
        f.write(f"- 처리 건수: {len(df)} (diff_id 기준, 결과·사건 정보 없음). 문구가 빈 행은 계산하지 않음\n")
        f.write(f"- 전문용어 사전: {len(terms)}개, 예외 표현: {EXC_MAIN}, 참조: {REF_MAIN}\n\n")
        f.write("## 지표별 분포\n\n" + md_table(desc) + "\n\n")
        f.write(f"## 기준값 12\n\n- term_ratio 0 비율: {zero_share:.3f} → "
                + ("50% 이상이라 종합 지수에서 제외" if zero_share >= ZERO_RULE else "50% 미만이라 종합 지수에 포함") + "\n")
        f.write(f"- 예외 표현 0 비율: {float((df['exception_count'] == 0).mean()):.3f}"
                + (" → 50% 이상이라 한계에 적는다(4-8)" if (df['exception_count'] == 0).mean() >= 0.5 else "") + "\n\n")
        f.write("## 상관행렬\n\n" + md_table(corr, index=True) + "\n\n")
        f.write("- |r| ≥ 0.7인 쌍: " + (", ".join(f"{a}–{b} ({r:.3f})" for a, b, r in high) if high else "없음") + "\n")
        if high:
            f.write("- **주의**: 대표 지표 하나 또는 PCA 첫 성분을 쓸지 팀이 정한다(agents/difficulty.md 4번). 아래 지수는 임시값이다.\n")
        f.write(f"\n## 종합 지수\n\n- 사용 지표: {', '.join(use)} (각 z점수의 평균). `difficulty_index_article`은 조 전체 문구로 같은 방식 계산\n")
    print(desc.to_string(index=False))
    print("\n|r|≥0.7:", [(a, b, round(r, 3)) for a, b, r in high] or "없음", "\n지수 사용 지표:", use)
    print(f"저장: {OUT_FULL}, {OUT_FULL_CORR}, {OUT_FULL_SUM}")


def run_eval_sheet():
    """평가 시트: eval_pick = 1인 25개(case-parser가 시기별로 고르게, 파일럿·대조 표본 제외로 뽑음)."""
    src = pd.read_csv(p(FULL_CSV))
    bad = FORBIDDEN & set(src.columns)
    if bad:
        sys.exit(f"가림 규칙 위반: 입력에 {bad} 열이 있습니다. 멈춥니다.")
    pick = src[src["eval_pick"] == 1].sample(frac=1, random_state=SEED).reset_index(drop=True)
    pick["eval_id"] = [f"E{i + 1:02d}" for i in range(len(pick))]
    sheet = pd.DataFrame({"eval_id": pick["eval_id"], "clause_text": pick["clause_text"],
                          "정유빈(1~5)": "", "팀원C(1~5)": ""})
    for f in (OUT_EVAL, OUT_EVAL_MAP):
        os.makedirs(os.path.dirname(p(f)), exist_ok=True)
    sheet.to_csv(p(OUT_EVAL), index=False, encoding="utf-8-sig")
    pick[["eval_id", "diff_id"]].to_csv(p(OUT_EVAL_MAP), index=False, encoding="utf-8-sig")
    print(f"평가 시트 {len(sheet)}개 → {OUT_EVAL} (평가자에게 보냄)")
    print(f"대응표 → {OUT_EVAL_MAP} (팀원B만 보관, 평가자에게 보내지 않음)")
    print("점수: 1 = 아주 쉬움 … 5 = 아주 어려움. 결과·사건 정보 없이 문구만 보고 매긴다.")


def selftest():
    """표준약관 본문 몇 문장으로만 시험한다. 실제 결정례 데이터는 쓰지 않는다."""
    terms = pd.read_csv(p(TERM_CSV))["term"].tolist()
    samples = [
        "회사는 피보험자에게 다음 중 어느 하나의 사유가 발생한 경우에는 보험수익자에게 약정한 보험금을 지급합니다.",
        "다만, 제3조(보험금의 지급사유) 제2항에도 불구하고 피보험자가 고의로 자신을 해친 경우에는 보험금을 지급하지 아니합니다.",
        "보장대상의료비는 실제 부담액에서 보장제외금액을 뺀 금액으로 하며, 별표 1에 한하여 적용합니다.",
    ]
    for s in samples:
        print(indicators(s, terms))


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "pilot"
    {"build-dict": build_dict, "pilot": run_pilot, "full": run_full,
     "eval-sheet": run_eval_sheet, "selftest": selftest}[step]()
