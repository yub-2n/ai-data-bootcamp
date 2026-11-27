"""수동 연결 사람 검토 반영 (2026-11-03) — PROJECT.md 4-8 조항 추출 보완 ③, docs/수동연결_후보.csv 검토 결과.

사용:  python3 docs/수동연결_반영.py
       처음 실행 때 직전 상태를 *_수동연결전.csv로 한 번 복사하고, 항상 그 사본에서 시작한다(다시 돌려도 같은 결과).
입력:  data/interim/cases_수동연결전.csv, needs_review_수동연결전.csv, cases_for_difficulty_수동연결전.csv,
       difficulty_id_map_수동연결전.csv, decisions.csv, texts/*.txt('오류' 빈 행만)
출력:  data/interim/cases.csv, needs_review.csv, cases_for_difficulty.csv, difficulty_id_map.csv
       (그 뒤 docs/제외사유_계산.py를 다시 돌려 docs/제외사유.md, docs/제외사유_비교표.csv 갱신)

사람이 정한 것(그대로 코드에 적음)
 - 따옴표 인용: 2000-48, 2005-100, 2001-53, 2021-22
 - 조문 그대로: 2006-3, 1998-37, 2007-25, 2009-14, 2018-2(붙임 별표4), 2021-16(붙임 제17조②), 2021-18(붙임 제11조), 2021-19(붙임 제8조)
 - 조문 그대로, '이 보험에서 교통사고라 함은'부터: 1998-36, 1998-42
 - 풀어 쓴 서술로 연결(주 분석 제외): 1998-5, -10, -12, -13, -16, -17, -19, -43
 - 연결 안 함: 2021-21(법령, 4-2 ③), 후보 없음 13건 → 조항 미추출 유지
 - 보고서 A: D060(2018-8) 제2조만, D117·D138·D247 풀어 쓴 서술, D014(2020-9) 붙임에 같은 항이 있으면 교체
 사람이 확정한 라벨(cited, partial, explained_duty, ambiguity)은 건드리지 않는다.
"""
import os
import re
import shutil
import subprocess
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
DOCS = os.path.join(ROOT, "docs")
SEED = 42


def snap(name):
    cur = os.path.join(INTERIM, name)
    base = cur.replace(".csv", "_수동연결전.csv")
    if not os.path.exists(base):
        shutil.copyfile(cur, base)
    return base


C = pd.read_csv(snap("cases.csv"), dtype={"exclude_reason": str, "clause_source": str, "clause_text_source": str,
                                          "clause_text_form": str, "clause_ref": str, "clause_title": str, "clause_level": str})
C["exclude_reason"] = C["exclude_reason"].fillna("")
R = pd.read_csv(snap("needs_review.csv"))
D = pd.read_csv(snap("cases_for_difficulty.csv"))
M = pd.read_csv(snap("difficulty_id_map.csv"))
LABELS_BEFORE = C[["case_key", "nttId", "cited", "partial", "explained_duty", "ambiguity"]].copy()

_src = open(os.path.join(DOCS, "본실행_계산.py"), encoding="utf-8").read()
_src = _src[: _src.index("# =========================================================================== 7. 실행")]
G = {"__file__": os.path.join(DOCS, "본실행_계산.py")}
exec(_src, G)
s, dec = G["s"], G["dec"]
rows_by_key = {}
for _, r in dec.iterrows():
    if not s(r["오류"]):
        rows_by_key.setdefault(G["case_key_of"](r)[0], r)


def judg(k):
    return s(rows_by_key[k]["위원회_판단"])


def att(k):
    return G["strip_law_segments"](s(rows_by_key[k]["붙임"]))


def cut(src, start, end, include_start=True, from_after=None):
    """src에서 start 정규식이 처음 맞는 곳부터 end 정규식 앞까지."""
    m = re.search(start, src)
    assert m, f"start 못 찾음: {start}"
    st = m.start() if include_start else m.end()
    e = re.search(end, src[m.end():]) if end else None
    en = m.end() + e.start() if e else len(src)
    return src[st:en].strip()


def norm(t):
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()


# ------------------------------------------------------------------ 1) 수동 연결 문구(사람이 정한 형태 그대로)
LINK = {}
# 따옴표 인용
LINK["2000-48"] = dict(text=cut(judg("2000-48"), r'재해분류표상\s*"', r'"\s*라고\s*규정', include_start=False),
                       ref="재해분류표", title="재해분류표", level="조", src="본문 인용", form="따옴표 인용")
LINK["2005-100"] = dict(text=cut(judg("2005-100"), r"재해분류표상에는\s*“", r"”\s*라고\s*규정", include_start=False),
                        ref="재해분류표", title="재해분류표", level="조", src="본문 인용", form="따옴표 인용")
# 2001-53: 판단에 장해등급분류표 항목 두 개가 따옴표로 나온다 → 4-2 ④ 처음 언급된 것(제4급 항목)만
LINK["2001-53"] = dict(text=cut(judg("2001-53"), r'장해등급분류표에\s*의하면\s*"', r'"', include_start=False),
                       ref="장해등급분류표 제4급", title="장해등급분류표", level="호", src="본문 인용", form="따옴표 인용")
LINK["2021-22"] = dict(text=cut(judg("2021-22"), r"수술분류표\s*사용지침\)“에서는\s*”", r"“\s*라고\s*규정", include_start=False),
                       ref="수술분류표 사용지침", title="수술분류표 사용지침", level="조", src="본문 인용", form="따옴표 인용")
# 조문 그대로(판단 안 관련 약관 규정)
LINK["2006-3"] = dict(text=cut(judg("2006-3"), r"1\.\s*이 보험에서 교통사고라 함은", r"\(2\)\s*교통재해\s*인정"),
                      ref="교통재해분류표", title="교통재해분류표", level="조", src="본문 인용", form="조문 그대로")
for k in ["1998-36", "1998-42", "1998-37"]:
    LINK[k] = dict(text=cut(judg(k), r"이 보험에서 교통사고라 함은", r"고\s*규정(?:되어|하고)"),
                   ref="교통재해분류표", title="교통재해분류표", level="조", src="본문 인용", form="조문 그대로")
LINK["2007-25"] = dict(text=cut(judg("2007-25"), r"▹\s*한팔 및 한다리", r"□\s*장해등급분류해설"),
                       ref="장해등급분류표", title="장해등급분류표", level="조", src="본문 인용", form="조문 그대로")
LINK["2009-14"] = dict(text=cut(judg("2009-14"), r"제ㅇㅇ조\(보험금의 지급사유\)", r"○\s*장해등급분류표"),
                       ref="제ㅇㅇ조(조 번호 가려짐)", title="보험금의 지급사유", level="조", src="본문 인용", form="조문 그대로")
# 조문 그대로(붙임)
LINK["2018-2"] = dict(text=cut(att("2018-2"), r"\[별표4\]", r"\n\s*<\s*붙임\s*2\s*>|\n\s*\[별표\s*\d"),
                      ref="별표4", title="‘중대한 질병’의 정의", level="조", src="붙임", form="조문 그대로")
a17 = G["article_block"](att("2021-16")[re.search(r"(?m)^\s*제17조", att("2021-16")).start():], 17)
LINK["2021-16"] = dict(text=cut(a17, r"②", r"\n\s*③|$"), article=a17,
                       ref="제17조 제2항", title="보험금을 지급하지 아니하는 사유", level="항", src="붙임", form="조문 그대로")
for k, n, title in [("2021-18", 11, "보험금을 지급하지 아니하는 보험사고"), ("2021-19", 8, "보험금을 지급하지 않는 사유")]:
    a = att(k)
    blk = G["article_block"](a[re.search(rf"(?m)^\s*제{n}조", a).start():], n)
    LINK[k] = dict(text=blk, ref=f"제{n}조", title=title, level="조", src="붙임", form="조문 그대로")
# 풀어 쓴 서술로 연결(주 분석 제외)
PARA_START = r"(?:별표\s?2의\s*)?재해분류표(?:에\s*의하면|에\s*의거|에)"
for k in ["1998-5", "1998-10", "1998-12", "1998-13", "1998-16", "1998-17", "1998-19", "1998-43"]:
    j = judg(k)
    m = re.search(r"(?:동\s*보험약관\s*|당해보험약관\s*|위 보험약관\s*|동 약관\s*)?" + PARA_START, j)
    t = j[m.start():]
    e = re.search(r"(?:말한다|말합니다)?\s*(?:라고|고)?\s*규정(?:하고\s*있|되어\s*있)[^\s,]*|사실,|\n\s*\n", t)
    LINK[k] = dict(text=t[: e.end() if e else 400].strip().rstrip(","), ref="재해분류표", title="재해분류표", level="조",
                   src="본문 인용", form="풀어 쓴 서술")
NOT_LINKED_NOTE = "2021-21: 후보가 법령(국민건강보험 요양급여 비급여대상)이라 연결 안 함(4-2 ③)"

for k, v in LINK.items():
    v["text"] = norm(v["text"])
    v.setdefault("article", v["text"] if v["level"] == "조" else "")
    v["article"] = norm(v["article"])
    assert len(re.sub(r"\s", "", v["text"])) >= 15, (k, v["text"])


def issue_from(t):
    return G["issue_from"](t)


for k, v in LINK.items():
    idx = C.index[C["case_key"] == k]
    for i in idx:
        C.at[i, "clause_ref"] = v["ref"]
        C.at[i, "clause_title"] = v["title"]
        C.at[i, "clause_level"] = v["level"]
        C.at[i, "clause_source"] = "수동 연결"
        C.at[i, "clause_text_source"] = v["src"]
        C.at[i, "clause_text_form"] = v["form"]
        C.at[i, "clause_text"] = v["text"]
        C.at[i, "clause_text_article"] = v["article"]
        C.at[i, "clause_evidence"] = "수동 연결(docs/수동연결_후보.csv 사람 검토, 2026-11-03)"
        # 4-8 배정 규칙 다시: 안건명 → 조 제목 → 보상범위·정의 / topic: 조 제목(없으면 안건명)
        agenda = s(rows_by_key[k]["안건명"])
        it = issue_from(agenda)
        it_src = "안건명"
        if not it:
            it, it_src = issue_from(v["title"]), "조 제목"
        if not it:
            it, it_src = "보상범위·정의", "기본값"
        C.at[i, "issue_type"], C.at[i, "issue_type_source"] = it, it_src
        tp, tps = G["topic_of"](re.sub(r"\s+", "", v["title"]), agenda)
        C.at[i, "topic"], C.at[i, "topic_source"] = tp, tps

# ------------------------------------------------------------------ 2) 보고서 A 남은 항목
dmap = D.merge(M, on="diff_id")


def row_idx_of(did):
    r = dmap[dmap["diff_id"] == did].iloc[0]
    cand = C.index[(C["case_key"] == r["case_key"]) & (C["clause_text"].fillna("") == s(r["clause_text"]))]
    return cand[0] if len(cand) else C.index[C["case_key"] == r["case_key"]][0]


i = row_idx_of("D060")  # 2018-8: 제2조(용어의 정의)만
for col in ["clause_text", "clause_text_article"]:
    t = s(C.at[i, col])
    m = re.search(r"\n\s*제\s?3\s?조\s", t)
    C.at[i, col] = t[: m.start()].strip() if m else t
for did in ["D117", "D138", "D247"]:
    C.at[row_idx_of(did), "clause_text_form"] = "풀어 쓴 서술"
i = row_idx_of("D014")  # 2020-9: 붙임 제4조의 [종합입원형 보상하지 않는 사항] ①
a = s(rows_by_key["2020-9"]["붙임"])  # 법령 부분 빼기 필터가 약관 표 안의 '의료법 제3조…' 줄에서 뒤를 잘라 내서, 여기서는 붙임 원문을 쓴다
# article_block은 '[…]' 줄에서 멈추므로 여기서는 제4조부터 제5조 앞까지 붙임 원문을 그대로 쓴다
_st = re.search(r"(?m)^\s*제4조\s*\(", a).start()
_en = re.search(r"(?m)^\s*제5조\s*\(", a[_st:])
a4 = a[_st: _st + _en.start()] if _en else a[_st:]
m = re.search(r"\[종합입원형 보상하지 않는 사항\]\s*\n\s*(①[^\n]+)", a4)
D014_NOTE = ""
if m:
    C.at[i, "clause_text"] = m.group(1).strip()
    C.at[i, "clause_text_article"] = norm(a4)
    C.at[i, "clause_text_source"] = "붙임"
else:
    D014_NOTE = "붙임에 같은 항 문구 없음 — 그대로 둠"

# ------------------------------------------------------------------ 3) 제외 사유 다시(조항 관련 사유만; 다른 사유는 그대로)
CLAUSE_REASONS = {"", "조항 미추출", "조항 문구 없음", "풀어 쓴 서술"}
for i, r in C.iterrows():
    if r["exclude_reason"] not in CLAUSE_REASONS or r.get("post_level_only", 0) == 1 or r["converted"] != 1:
        continue
    if not s(r["clause_ref"]):
        er = "조항 미추출"
    elif not s(r["clause_text"]):
        er = "조항 문구 없음"
    elif s(r["clause_text_form"]) == "풀어 쓴 서술":
        er = "풀어 쓴 서술"
    else:
        er = ""
    C.at[i, "exclude_reason"] = er

# needs_review: '수동 연결' 36건은 사람 확인 완료로 정리
R2 = R[R["항목"] != "수동 연결"].copy()
if D014_NOTE:
    R2 = pd.concat([R2, pd.DataFrame([dict(case_key="2020-9", 항목="조항", 이유=D014_NOTE, 근거_문장=s(C.at[row_idx_of("D014"), "clause_text"]))])])
R2.to_csv(os.path.join(INTERIM, "needs_review.csv"), index=False, encoding="utf-8-sig")
left = R2.groupby("case_key")["항목"].apply(lambda x: "; ".join(dict.fromkeys(x))).to_dict()
C["needs_review"] = C["case_key"].map(lambda k: int(k in left)).astype(int)
C["review_items"] = C["case_key"].map(lambda k: left.get(k, ""))

# 사람 확정 라벨이 바뀌지 않았는지 확인
chk = LABELS_BEFORE.merge(C[["case_key", "nttId", "cited", "partial", "explained_duty", "ambiguity"]], on=["case_key", "nttId"], suffixes=("_b", "_a"))
for col in ["cited", "partial", "explained_duty", "ambiguity"]:
    assert ((chk[col + "_b"] == chk[col + "_a"]) | (chk[col + "_b"].isna() & chk[col + "_a"].isna())).all(), col
C.to_csv(os.path.join(INTERIM, "cases.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 난이도 입력: 기존 diff_id·eval_pick 유지, 바뀐 행은 문구·형태·단위·유형만, 새 행은 D251~
UPD = ["issue_type", "clause_level", "clause_text_form", "clause_text", "clause_text_article"]
for did in D["diff_id"]:
    i = row_idx_of(did)
    for col in UPD:
        D.loc[D["diff_id"] == did, col] = C.at[i, col]
in_file = set(M["case_key"])
new = C[(C["clause_text"].fillna("") != "") & ~C["case_key"].isin(in_file)]
new = new.sample(frac=1, random_state=SEED)
start = max(int(x[1:]) for x in M["diff_id"])
start = max(start, 250) + 1
add = []
for j, (_, r) in enumerate(new.iterrows()):
    add.append(dict(diff_id=f"D{start + j:03d}", case_key=r["case_key"], eval_pick=0, **{c: r[c] for c in UPD}))
A = pd.DataFrame(add)
DCOLS = ["diff_id", "issue_type", "clause_level", "clause_text_form", "clause_text", "clause_text_article", "eval_pick"]
D2 = pd.concat([D[DCOLS], A[DCOLS]] if len(A) else [D[DCOLS]], ignore_index=True)
M2 = pd.concat([M, A[["diff_id", "case_key"]]] if len(A) else [M], ignore_index=True)
D2.to_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"), index=False, encoding="utf-8-sig")
M2.to_csv(os.path.join(INTERIM, "difficulty_id_map.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 확인(금지 열·결과 표현·조정번호 꼴)
allowed = DCOLS
banned = re.compile(r"case_key|nttId|cited|partial|outcome|period|decision|year|date|title|exclude|evidence|needs_review|review|result|주문|결론")
d = pd.read_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"))
print("열:", list(d.columns))
print("허용 열과 정확히 같은가:", list(d.columns) == allowed)
print("금지 열 이름:", [c for c in d.columns if banned.search(c)] or "없음")
print("행:", len(d), " diff_id 중복:", int(d.diff_id.duplicated().sum()), " map과 일치:", set(d.diff_id) == set(M2.diff_id))
txt = d.clause_text.fillna("") + " " + d.clause_text_article.fillna("")
for lab, rx in [("이유없", r"이유\s?없"), ("결정한다", r"결정한다"), ("인용", r"인용"), ("기각", r"기각"), ("주문과 같이", r"주문과\s?같이")]:
    print(f'문구 속 결과 표현 "{lab}" 행 수:', int(txt.str.contains(rx).sum()))
print("문구 속 조정번호 꼴 행 수:", int(txt.str.contains(r"제?\s?(?:19|20)\d{2}\s?-\s?\d{1,3}\s?호").sum()))
old = pd.read_csv(os.path.join(INTERIM, "cases_for_difficulty_수동연결전.csv"))
jj = d.merge(old[["diff_id", "eval_pick"]], on="diff_id", suffixes=("", "_old"))
print("기존 diff_id·eval_pick 그대로:", len(jj) == len(old) and bool((jj.eval_pick == jj.eval_pick_old).all()), " eval_pick=1:", int(d.eval_pick.sum()))

# ------------------------------------------------------------------ 요약
inc = C[C["exclude_reason"] == ""]
print("\n분석 포함:", len(inc), " 인용:", int((inc.cited == 1).sum()), " 기각:", int((inc.cited == 0).sum()), " 일부 인용:", int((inc.partial == 1).sum()))
print("시기별:", inc["period"].value_counts().reindex(["~2009", "2010-2016", "2017-2026"]).to_dict())
print("제외 사유:", C["exclude_reason"].replace("", "(분석 포함)").value_counts().to_dict())
print("수동 연결 반영:", {k: (C[C.case_key == k].iloc[0]["clause_text_form"], C[C.case_key == k].iloc[0]["exclude_reason"] or "분석 포함") for k in LINK})
print("새 diff_id:", [x["diff_id"] + "=" + x["case_key"] for x in add])
print("D014:", D014_NOTE or "붙임 문구로 교체")
print(NOT_LINKED_NOTE)

# ------------------------------------------------------------------ 제외사유 표 다시
subprocess.run([sys.executable, os.path.join(DOCS, "제외사유_계산.py")], check=True, stdout=subprocess.DEVNULL)
print("docs/제외사유.md, docs/제외사유_비교표.csv 갱신")
