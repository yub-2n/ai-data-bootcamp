"""조항 문구 점검 2 (2026-11-03) — 남은 문제: 조가 여러 개 / 문장 중간에서 시작.

사용:  python3 docs/조항문구_점검2.py
       처음 실행 때 직전 상태를 *_사람확인.csv로 한 번 복사해 두고, 항상 그 사본에서 시작한다(다시 돌려도 같은 결과).
입력:  data/interim/cases_사람확인.csv, cases_for_difficulty_사람확인.csv, difficulty_id_map.csv(읽기만), decisions.csv
출력:  data/interim/cases.csv, cases_for_difficulty.csv(갱신, diff_id·eval_pick 유지), docs/조항문구_점검2.csv

규칙(4-2 ④ '처음 언급된 조항', 4-2 ⑤ 조문 문구, 4-8 풀어 쓴 서술 정의)
 - '조가 여러 개': 문구 안에서 다른 조가 '새 조 머리'(제N조(제목) 뒤에 조사 없이 본문이 이어짐)로 나오면 그 앞에서 자른다.
   문구 안의 참조('제2조(피보험자의 범위)에서 정한', '의료법 제3조(의료기관)의')는 조문 안의 말이라 그대로 둔다.
 - '문장 중간 시작': 따옴표 인용이 닫는 따옴표를 잘못 짝지어 위원회 문장('…“한다고 하고,')이 붙은 경우 → 조항 처음(여는 따옴표 뒤)부터
   닫는 자리까지 다시 자른다. 풀어 쓴 서술 앞에 위원회 머리말('…살펴보면,')이 붙은 경우 → 그 조항을 말하는 절부터.
 - 고치면 문구가 없어지거나 clause_text_form이 바뀌는 행은 고치지 않고 '보고만' 목록에 남긴다.
"""
import os
import re
import shutil

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
DOCS = os.path.join(ROOT, "docs")


def snap(name):
    cur = os.path.join(INTERIM, name)
    base = cur.replace(".csv", "_사람확인.csv")
    if not os.path.exists(base):
        shutil.copyfile(cur, base)
    return base


C = pd.read_csv(snap("cases.csv"), dtype={"exclude_reason": str})
C["exclude_reason"] = C["exclude_reason"].fillna("")
D = pd.read_csv(snap("cases_for_difficulty.csv"))
MAP = pd.read_csv(os.path.join(INTERIM, "difficulty_id_map.csv"))

# diff_id → cases 행(같은 case_key 두 행인 제2009-29호는 문구로 맞춤)
DM = D.merge(MAP, on="diff_id")
row_of = {}
for _, r in DM.iterrows():
    cand = C.index[(C["case_key"] == r["case_key"]) & (C["clause_text"].fillna("") == str(r["clause_text"]) if pd.notna(r["clause_text"]) else "")]
    if len(cand) == 0:
        cand = C.index[C["case_key"] == r["case_key"]]
    used = set(row_of.values())
    row_of[r["diff_id"]] = next((i for i in cand if i not in used), cand[0])

NEW_HEAD = re.compile(r"(?:^|\n|[.。]\s|[□○◦ᄋ·■◇◆⦁•]\s*)\s*제\s?(\d+)\s?조(?:의\s?\d+)?\s*[\(（【][^)）】\n]{1,40}[\)）】]"
                      r"(?!\s*(?:에|를|을|의|및|와|과|로|은|는|이|가|제\s?\d|【|\(|,|·|ㆍ|에서|에\s?따))")
BROKEN_Q = re.compile(r"[“”\"](?=(?:한다고|라고|다고|이라고)\s?(?:하고|한\s?다음|하며|정하|규정))")
LEAD = re.compile(r"(?:살펴보면|살펴보건대|살피건대|판단컨대|보건대|에\s?대하여\s?보면)\s*,\s*")
FRAG_START = re.compile(r"^\s*(?:이라\s|이라고|라\s?한다|라고\s|한다고|다고\s|하며|며\s)")


def art_no(ref):
    m = re.search(r"제(\d+)조", str(ref))
    return int(m.group(1)) if m else None


def fix(t, form, n):
    """반환: (고친 문구, 문제 목록, 처리) — 고칠 것이 없으면 문구 그대로."""
    probs, out = [], t
    # 조가 여러 개(새 조 머리)
    for m in NEW_HEAD.finditer(out):
        if n is not None and int(m.group(1)) != n and m.start() > 0:
            probs.append("조가 여러 개")
            out = out[: m.start()].rstrip(" □○◦ᄋ·■⦁•\n")
            break
    # 따옴표 짝이 잘못돼 위원회 문장이 붙음
    bm = BROKEN_Q.search(out)
    if bm and form == "따옴표 인용":
        probs.append("문장 중간 시작(따옴표 짝 오류로 위원회 문장 섞임)")
        out = out[: bm.start()].strip()
    # 풀어 쓴 서술 앞의 위원회 머리말
    if form == "풀어 쓴 서술" and n is not None:
        mm = re.search(rf"제\s?{n}\s?조", out)
        leads = [x for x in LEAD.finditer(out[: mm.start()])] if mm else []
        if leads:
            probs.append("문장 중간 시작(위원회 머리말)")
            out = out[leads[-1].end():].strip()
    if FRAG_START.match(out):
        probs.append("문장 중간 시작(조항 앞부분 없음)")
    return out, probs


log, report_only = [], []
for did in D["diff_id"]:
    i = row_of[did]
    r = C.loc[i]
    n = art_no(r["clause_ref"])
    form = r["clause_text_form"]
    changes = {}
    probs_all = []
    for col in ["clause_text", "clause_text_article"]:
        t = r[col] if isinstance(r[col], str) else ""
        if not t:
            continue
        new, probs = fix(t, form, n)
        if not probs:
            continue
        probs_all += [p for p in probs if p not in probs_all]
        frag = any(p.endswith("(조항 앞부분 없음)") for p in probs)
        if frag:
            # 조항 처음부터 다시 자르려면 판단의 '…에 의하면 … 규정' 문장으로 돌아가야 해서 형태가 풀어 쓴 서술로 바뀜 → 보고만
            report_only.append(dict(diff_id=did, case_key=r["case_key"], 열=col, 문제="; ".join(probs),
                                    이유="조항 처음부터 다시 자르면 판단 문장('…라 한다) 하며 …'/'…이라 함은 … 규정')이 되어 "
                                         "clause_text_form이 풀어 쓴 서술로 바뀜 — 고치지 않음",
                                    지금_앞60자=t[:60].replace("\n", " ")))
            continue
        if not new or len(re.sub(r"\s", "", new)) == 0:
            report_only.append(dict(diff_id=did, case_key=r["case_key"], 열=col, 문제="; ".join(probs),
                                    이유="고치면 문구가 없어짐 — 고치지 않음", 지금_앞60자=t[:60].replace("\n", " ")))
            continue
        changes[col] = (t, new)
    for col, (t, new) in changes.items():
        C.at[i, col] = new
        D.loc[D["diff_id"] == did, col] = new
        log.append(dict(diff_id=did, case_key=r["case_key"], 열=col, 문제="; ".join(probs_all),
                        **{"고치기 전 앞 60자": t[:60].replace("\n", " "), "고친 뒤 앞 60자": new[:60].replace("\n", " ")},
                        고친_뒤_글자수=len(new)))

L = pd.DataFrame(log, columns=["diff_id", "case_key", "열", "문제", "고치기 전 앞 60자", "고친 뒤 앞 60자", "고친_뒤_글자수"])
L.to_csv(os.path.join(DOCS, "조항문구_점검2.csv"), index=False, encoding="utf-8-sig")
C.to_csv(os.path.join(INTERIM, "cases.csv"), index=False, encoding="utf-8-sig")
D.to_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"), index=False, encoding="utf-8-sig")

pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 90)
print("== 고친 행:", L["diff_id"].nunique(), "(열 단위", len(L), ")")
print(L[["diff_id", "case_key", "열", "문제", "고친_뒤_글자수"]].to_string(index=False) if len(L) else "(없음)")
print("\n== 고치지 않고 보고만:", len({x["diff_id"] for x in report_only}))
for x in report_only:
    print(" ", x)
print("\n분석 포함:", int((C["exclude_reason"] == "").sum()), " clause_text_form 변화 없음(이 단계에서 형태는 바꾸지 않음)")
