"""사람 확인 결과 반영 (case-parser, 2026-11-03) — PROJECT.md 4-8 '본 실행 후 보완'과 docs/needs_review_확인표_오늘.md.

사용:  python3 docs/사람확인_반영.py
       (처음 실행 때 직전 단계(조항 문구 점검) 결과를 *_조항점검.csv로 한 번 복사해 두고, 항상 그 사본에서 시작한다
        → 다시 돌려도 같은 결과)
입력:  data/interim/cases_조항점검.csv, needs_review_조항점검.csv, cases_for_difficulty_조항점검.csv,
       difficulty_id_map_조항점검.csv, decisions.csv, texts/*.txt('오류' 빈 행만)
출력:  data/interim/cases.csv, needs_review.csv, cases_for_difficulty.csv, difficulty_id_map.csv(갱신)

할 일
 1) 확인표의 사람 판정 반영(A·B 20건 자동값 확정, C 5건 partial = 1·cited = 1, D 3건 explained_duty, 2017-19 ambiguity = 1).
    반영한 항목은 needs_review.csv에서 빼고, 남은 항목이 없으면 needs_review = 0.
 2) 1998년 '각하' 12건: cited = 0, exclude_reason을 비우고 조항 규칙(조항 미추출 → 조항 문구 없음 → 풀어 쓴 서술)을 다시 적용.
    2001-31, 2003-46, 2010-41은 '본안 아님(각하)' 유지(확인표 E: 사람이 제외 유지로 확정).
 3) explained_duty·ambiguity 키워드를 띄어쓰기와 상관없이 찾게 고쳐 전체 재판정. 값이 바뀌는 사건은 값은 그대로 두고
    needs_review = 1 + 근거 문장(needs_review.csv). 사람이 확정한 사건(D 3건, 4-8-1 5건)은 건드리지 않는다.
 4) 분석에 새로 들어오고 문구가 있는데 난이도 입력에 없는 사건만 D251부터 추가(eval_pick = 0, 시드 42 순서).
금지: PROJECT.md 수정, 난이도·통계 계산, 대조표본·평가 표본 다시 뽑기.
"""
import os
import re
import shutil

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
DOCS = os.path.join(ROOT, "docs")
SEED = 42


def snap(name):
    cur = os.path.join(INTERIM, name)
    base = cur.replace(".csv", "_조항점검.csv")
    if not os.path.exists(base):
        shutil.copyfile(cur, base)
    return base


C = pd.read_csv(snap("cases.csv"), dtype={"exclude_reason": str})
C["exclude_reason"] = C["exclude_reason"].fillna("")
R = pd.read_csv(snap("needs_review.csv"))
D_OLD = pd.read_csv(snap("cases_for_difficulty.csv"))
M_OLD = pd.read_csv(snap("difficulty_id_map.csv"))
C0 = C.copy()

# ------------------------------------------------------------------ 1) 확인표(docs/needs_review_확인표_오늘.md)와 지시가 같은지 코드로 대조
md = open(os.path.join(DOCS, "needs_review_확인표_오늘.md"), encoding="utf-8").read()


def table_rows(section_title):
    sec = md.split(section_title, 1)[1].split("\n## ", 1)[0]
    rows = []
    for ln in sec.split("\n"):
        if ln.startswith("| ") and not ln.startswith("| 사건") and not ln.startswith("|---"):
            rows.append([x.strip() for x in ln.strip().strip("|").split("|")])
    return rows


A = {r[0]: r[3] for r in table_rows("## A.")}
B = {r[0]: r[3] for r in table_rows("## B.")}
Cc = {r[0]: r[3] for r in table_rows("## C.")}
Dd = {r[0]: r[4] for r in table_rows("## D.")}
E = {r[0]: r[2] for r in table_rows("## E.")}
INSTR_C = ["2000-38", "2001-33", "2006-87", "2018-7", "2020-8"]
INSTR_D = {"2005-34": 2, "2016-8": 1, "2017-19": 0}
KAHA98 = [k for k, v in E.items() if k.startswith("1998-")]
KEEP_KAHA = ["2001-31", "2003-46", "2010-41"]
mismatch = []
if len(A) + len(B) != 20 or any(v != "그대로" for v in list(A.values()) + list(B.values())):
    mismatch.append(f"A·B: {len(A) + len(B)}건, 값 {set(A.values()) | set(B.values())}")
if sorted(Cc) != sorted(INSTR_C) or any(v != "1" for v in Cc.values()):
    mismatch.append(f"C: {Cc}")
if {k: int(v) for k, v in Dd.items()} != INSTR_D:
    mismatch.append(f"D: {Dd}")
if "ambiguity = 1" not in md.split("## D.", 1)[1].split("## E.", 1)[0]:
    mismatch.append("D: 2017-19 ambiguity = 1 문구 없음")
if len(KAHA98) != 12 or any(not E[k].startswith("기각") for k in KAHA98) or any(not E[k].startswith("제외 유지") for k in KEEP_KAHA):
    mismatch.append(f"E: {E}")
print("확인표 ↔ 지시 대조:", mismatch if mismatch else "일치")
assert not mismatch, "확인표와 지시가 다름 — 바꾸지 않고 보고"

done = []  # (case_key, 항목) 사람이 확정한 리뷰 항목


def resolve(key, items):
    for it in items:
        done.append((key, it))


for k in list(A) + list(B):
    resolve(k, ["cited"])                      # 자동값 그대로 확정
for k in INSTR_C:
    idx = C["case_key"] == k
    C.loc[idx, "cited"] = 1
    C.loc[idx, "partial"] = 1
    resolve(k, ["cited", "일부인용"])
for k, v in INSTR_D.items():
    C.loc[C["case_key"] == k, "explained_duty"] = v
    resolve(k, ["explained_duty"])
C.loc[C["case_key"] == "2017-19", "ambiguity"] = 1
resolve("2017-19", ["ambiguity"])
C["neg_source"] = C["neg_source"].astype(object)
for k in INSTR_D:
    C.loc[C["case_key"] == k, "neg_source"] = "사람 확인(2026-11-03, docs/needs_review_확인표_오늘.md)"

# ------------------------------------------------------------------ 2) 1998년 '각하' 12건 → 기각 포함
for k in KAHA98:
    i = C.index[C["case_key"] == k]
    C.loc[i, "cited"] = 0
    C.loc[i, "partial"] = 0
    C.loc[i, "outcome_type"] = "기각(옛 결정의 '각하결정사항', 4-8 본 실행 후 보완)"
    for j in i:
        r = C.loc[j]
        if not isinstance(r["clause_ref"], str) or not r["clause_ref"]:
            C.at[j, "exclude_reason"] = "조항 미추출"
        elif not isinstance(r["clause_text"], str) or not r["clause_text"]:
            C.at[j, "exclude_reason"] = "조항 문구 없음"
        elif r["clause_text_form"] == "풀어 쓴 서술":
            C.at[j, "exclude_reason"] = "풀어 쓴 서술"
        else:
            C.at[j, "exclude_reason"] = ""
    resolve(k, ["cited"])
for k in KEEP_KAHA:
    resolve(k, ["cited"])                      # 사람이 '제외 유지'로 확정

# ------------------------------------------------------------------ 3) 키워드 띄어쓰기 무시로 재판정
_src = open(os.path.join(DOCS, "본실행_계산.py"), encoding="utf-8").read()
_src = _src[: _src.index("# =========================================================================== 7. 실행")]
# 키워드 판정 함수가 띄어쓰기 섞인 키워드도 같은 키워드로 보게(공백을 지운 키워드로 비교)
_src_new = _src.replace("        kwd = m.group(0)\n        if kwd.startswith(\"설명하지\")",
                        "        kwd = re.sub(r\"\\s\", \"\", m.group(0))\n        if kwd.startswith(\"설명하지\")")
_src_new = _src_new.replace("    kwd = m.group(0)\n    if re.match(r\"명백하지",
                            "    kwd = re.sub(r\"\\s\", \"\", m.group(0))\n    if re.match(r\"명백하지")
assert _src_new.count('re.sub(r"\\s", "", m.group(0))') == 2
# 2017-19를 놓친 실제 원인: '작성자불이익'처럼 키워드 자체가 약관 해석의 모호함을 뜻하는데도 '앞 80자 안에 약관 관련어'
# 점검(본실행 구현 세부)에 걸려 0이 됨. 이런 인정형 키워드는 그 점검을 건너뛴다(새로 바뀌는 값은 사람 확인으로만 올림).
_old_line = "    if not TERMS_SUBJ.search(sent[max(0, m.start() - 80): m.end() + 10]):"
assert _old_line in _src_new
_src_new = _src_new.replace(_old_line, "    if not re.match(r\"작성자|다의적|명백하지|고객에게\", re.sub(r\"\\s\", \"\", m.group(0))) and \\\n            not TERMS_SUBJ.search(sent[max(0, m.start() - 80): m.end() + 10]):")
G_old = {"__file__": os.path.join(DOCS, "본실행_계산.py")}
exec(_src, G_old)
G_new = {"__file__": os.path.join(DOCS, "본실행_계산.py")}
exec(_src_new, G_new)


def sp(word):
    """글자 사이에 띄어쓰기가 있어도 맞게(가운뎃점류도 허용)."""
    return r"\s*".join(re.escape(ch) for ch in word)


DOT = r"\s*[·ㆍ․‧∙・]?\s*"
G_new["KW"] = {
    "explained_duty": re.compile("|".join([sp("설명의무"), sp("명시") + DOT + sp("설명"), sp("설명하지") + r"\s*않",
                                           sp("설명을") + r"\s*" + sp("하지")])),
    "ambiguity": re.compile("|".join([sp("모호"), sp("불명확"), sp("불분명"), sp("명백하지") + r"\s*(?:아니|않)",
                                      sp("다의적"), sp("작성자") + r"\s*" + sp("불이익"),
                                      sp("고객에게") + r"\s*" + sp("유리하게")])),
}
dec = G_old["dec"]
s = G_old["s"]


def fields_of(r):
    text = open(os.path.join(INTERIM, "texts", os.path.splitext(s(r["파일명"]))[0] + ".txt"), encoding="utf-8").read()
    judg, concl = s(r["위원회_판단"]), s(r["결론"])
    if s(r["형식"]) == "pdf":
        text, _ = G_old["clean_pdf_text"](text)
        f = G_old["split_pdf_sections"](text)
        judg, concl = f["위원회_판단"], f["결론"]
    if not judg.strip():  # 본실행과 같은 대체(제1999-11호)
        judg = G_old["section"](text, [r"쟁점사항에\s*대한\s*검토", r"위원회\s*판단", r"판\s*단"], [r"\n\s*\d\.\s*결\s*론"]) \
            or text[int(len(text) * 0.5):]
    return text, judg, concl


HUMAN_NEG = set(INSTR_D) | {"2006-3", "2017-18", "2021-16", "2017-2", "2026-9"}
new_review, repro_bad, changed_neg = [], 0, []
key_of = {}
for _, r in dec.iterrows():
    if s(r["오류"]):
        continue
    key_of[(G_old["case_key_of"](r)[0], int(r["nttId"]))] = r
for i, row in C[C["converted"] == 1].iterrows():
    k, n = row["case_key"], int(row["nttId"])
    r = key_of[(k, n)]
    text, judg, concl = fields_of(r)
    old = G_old["neg_label"](text, judg, concl)
    new = G_new["neg_label"](text, judg, concl)
    if k not in HUMAN_NEG:
        # 재현 점검: 옛 키워드로 다시 돌리면 지금 값과 같아야 한다
        if (old["explained_duty"]["val"], old["ambiguity"]["val"]) != (row["explained_duty"], row["ambiguity"]):
            repro_bad += 1
    if k in HUMAN_NEG:
        continue
    for var in ["explained_duty", "ambiguity"]:
        if new[var]["val"] != old[var]["val"]:
            changed_neg.append((k, var, old[var]["val"], new[var]["val"]))
            new_review.append(dict(case_key=k, 항목=var,
                                   이유=f"키워드 재판정(띄어쓰기 무시 + '작성자불이익' 등 인정형 키워드는 약관 관련어 점검 생략)에서 값이 {old[var]['val']} → {new[var]['val']}로 바뀜(값은 그대로 두고 사람 확인)",
                                   근거_문장=G_old["one_line"](new[var]["evidence"], 400)))

# ------------------------------------------------------------------ needs_review 정리
done_set = set(done)
R2 = R[[(k, it) not in done_set for k, it in zip(R["case_key"], R["항목"])]].copy()
R2 = pd.concat([R2, pd.DataFrame(new_review)], ignore_index=True)
ORDER = {"cited": 0, "일부인용": 1, "수동 연결": 2, "조항": 2, "is_auto": 3, "판단 범위": 4, "결정일": 5,
         "explained_duty": 6, "ambiguity": 7}
R2["_o"] = R2["항목"].map(ORDER).fillna(9)
R2 = R2.sort_values(["_o", "case_key"]).drop(columns="_o")
R2.to_csv(os.path.join(INTERIM, "needs_review.csv"), index=False, encoding="utf-8-sig")
left = R2.groupby("case_key")["항목"].apply(lambda x: "; ".join(dict.fromkeys(x))).to_dict()
C["needs_review"] = C["case_key"].map(lambda k: int(k in left)).astype(int)
C["review_items"] = C["case_key"].map(lambda k: left.get(k, ""))
C.to_csv(os.path.join(INTERIM, "cases.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 4) 난이도 입력: 새로 분석에 들어온 사건 중 파일에 없는 것만 추가
inc = C[C["exclude_reason"] == ""]
inc0 = C0[C0["exclude_reason"] == ""]
newly = inc[~inc.set_index(["case_key", "nttId"]).index.isin(inc0.set_index(["case_key", "nttId"]).index)]
in_file = set(M_OLD["case_key"])
to_add = newly[(newly["clause_text"].fillna("") != "") & ~newly["case_key"].isin(in_file)]
to_add = to_add.sample(frac=1, random_state=SEED) if len(to_add) else to_add
nums = [int(x[1:]) for x in M_OLD["diff_id"]] + [250]
start = max(nums) + 1
add_rows = []
for j, (_, r) in enumerate(to_add.iterrows()):
    add_rows.append(dict(diff_id=f"D{start + j:03d}", case_key=r["case_key"], issue_type=r["issue_type"],
                         clause_level=r["clause_level"], clause_text_form=r["clause_text_form"], clause_text=r["clause_text"],
                         clause_text_article=r["clause_text_article"], eval_pick=0))
DCOLS = ["diff_id", "issue_type", "clause_level", "clause_text_form", "clause_text", "clause_text_article", "eval_pick"]
D_NEW = pd.concat([D_OLD, pd.DataFrame(add_rows, columns=DCOLS + ["case_key"])[DCOLS]], ignore_index=True)
M_NEW = pd.concat([M_OLD, pd.DataFrame(add_rows, columns=["diff_id", "case_key"])[["diff_id", "case_key"]]], ignore_index=True)
D_NEW.to_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"), index=False, encoding="utf-8-sig")
M_NEW.to_csv(os.path.join(INTERIM, "difficulty_id_map.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 표준출력
P = ["~2009", "2010-2016", "2017-2026"]
print("키워드 재현 점검(옛 키워드로 다시 돌린 값 ≠ 지금 값, 사람 확정 제외):", repro_bad, "건")
print("키워드 띄어쓰기 무시로 값이 새로 바뀐 사건:", len({k for k, *_ in changed_neg}), "건 /", len(changed_neg), "항목")
for z in changed_neg:
    print("  ", z)
print("사람 확정으로 needs_review.csv에서 뺀 항목:", int(len(R) - (len(R2) - len(new_review))), "/ 새로 넣은 항목:", len(new_review))
print("분석 포함:", len(inc0), "→", len(inc), " 새로 포함:", newly["case_key"].tolist(),
      " 빠짐:", inc0[~inc0["case_key"].isin(inc["case_key"])]["case_key"].tolist())
print("cited(분석 포함):", inc["cited"].value_counts().to_dict(), " partial=1:", int((inc["partial"] == 1).sum()))
print("시기별:", inc["period"].value_counts().reindex(P).to_dict())
print("제외 사유:", C["exclude_reason"].replace("", "(분석 포함)").value_counts().to_dict())
print("1998년 '각하' 12건 처리:", C[C["case_key"].isin(KAHA98)][["case_key", "cited", "exclude_reason"]].to_dict("records"))
print("needs_review 사건 수(전체):", int(C["needs_review"].sum()), " 분석 포함 중:", int(inc["needs_review"].sum()))
print("항목별 사건 수(전체):", R2.groupby("항목")["case_key"].nunique().to_dict())
print("항목별 사건 수(분석 포함):", R2[R2["case_key"].isin(inc["case_key"])].groupby("항목")["case_key"].nunique().to_dict())
print("난이도 입력 새 diff_id:", [r["diff_id"] for r in add_rows], " 행:", len(D_NEW), " eval_pick=1:", int(D_NEW["eval_pick"].sum()))
print("새로 포함된 사건 중 이미 난이도 입력에 있는 것:", newly[newly["case_key"].isin(in_file)]["case_key"].tolist())
