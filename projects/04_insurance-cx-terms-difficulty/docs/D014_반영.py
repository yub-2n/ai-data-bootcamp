"""D014(제2020-9호) 조항 문구 확인 (2026-11-03).

사용:  python3 docs/D014_반영.py   (docs/수동연결_반영.py 다음에. 다시 돌려도 같은 결과: 메모는 한 번만 넣는다)
할 일: 원문 txt의 붙임에서 제4조 [종합입원형 보상하지 않는 사항] 제1항 전체 문구를 찾는다.
       지금 문구보다 긴 전체 문구가 있으면 cases.csv·cases_for_difficulty.csv(D014)·대조표본(있으면)을 바꾸고 출처 = 붙임.
       없으면 그대로 두고 needs_review.csv에 메모. 그 뒤 난이도 입력 금지 열·결과 표현 확인.
"""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
DOCS = os.path.join(ROOT, "docs")
KEY, DID = "2020-9", "D014"

C = pd.read_csv(os.path.join(INTERIM, "cases.csv"))
D = pd.read_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"))
R = pd.read_csv(os.path.join(INTERIM, "needs_review.csv"))
dec = pd.read_csv(os.path.join(INTERIM, "decisions.csv"))
row = dec[(dec["조정번호"] == KEY) & dec["오류"].isna()].iloc[0]
txt = open(os.path.join(INTERIM, "texts", os.path.splitext(row["파일명"])[0] + ".txt"), encoding="utf-8").read()
att = txt[txt.rfind("<붙임>"):] if "<붙임>" in txt else ""

i = C.index[C["case_key"] == KEY][0]
before = str(C.at[i, "clause_text"])
# 제4조 안 [종합입원형 보상하지 않는 사항] 머리 다음부터 다음 '[' 머리 앞까지가 이 항의 붙임 문구 전부
m = re.search(r"\[종합입원형 보상하지 않는 사항\]\s*\n(.*?)(?=\n\s*\[|\n\s*제\s?5\s?조|\Z)", att, re.S)
found_text = m.group(1).strip() if m else ""
found_full = bool(found_text) and len(found_text) > len(before.strip())
if found_full:
    C.at[i, "clause_text"] = found_text
    C.at[i, "clause_text_source"] = "붙임"
    D.loc[D["diff_id"] == DID, "clause_text"] = found_text
    K = pd.read_csv(os.path.join(DOCS, "대조표본.csv"))
    if KEY in set(K["case_key"]):
        K.loc[K["case_key"] == KEY, ["clause_text", "clause_text_source"]] = [found_text, "붙임"]
        K.to_csv(os.path.join(DOCS, "대조표본.csv"), index=False, encoding="utf-8-sig")
    C.to_csv(os.path.join(INTERIM, "cases.csv"), index=False, encoding="utf-8-sig")
    D.to_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"), index=False, encoding="utf-8-sig")
else:
    memo = "조항 문구 21자, 붙임에서 전체 못 찾음"
    if not ((R["case_key"] == KEY) & (R["이유"] == memo)).any():
        R = pd.concat([R, pd.DataFrame([dict(case_key=KEY, 항목="조항", 이유=memo,
                                             근거_문장=f"붙임 [종합입원형 보상하지 않는 사항] 아래 문구: {found_text}")])], ignore_index=True)
        R.to_csv(os.path.join(INTERIM, "needs_review.csv"), index=False, encoding="utf-8-sig")
    C.at[i, "needs_review"] = 1
    items = [x for x in str(C.at[i, "review_items"]).split("; ") if x and x != "nan"]
    if "조항" not in items:
        items.append("조항")
    C.at[i, "review_items"] = "; ".join(items)
    C.to_csv(os.path.join(INTERIM, "cases.csv"), index=False, encoding="utf-8-sig")
after = str(C.at[i, "clause_text"])
print("찾음(지금보다 긴 전체 문구):", found_full, " 붙임에서 찾은 문구:", repr(found_text))
print("바뀌기 전 글자 수:", len(before), " 바뀐 뒤 글자 수:", len(after))

# 확인
d = pd.read_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"))
allowed = ["diff_id", "issue_type", "clause_level", "clause_text_form", "clause_text", "clause_text_article", "eval_pick"]
banned = re.compile(r"case_key|nttId|cited|partial|outcome|period|decision|year|date|title|exclude|evidence|needs_review|review|result|주문|결론")
print("열:", list(d.columns))
print("허용 열과 정확히 같은가:", list(d.columns) == allowed)
print("금지 열 이름:", [c for c in d.columns if banned.search(c)] or "없음")
t = d.clause_text.fillna("") + " " + d.clause_text_article.fillna("")
for lab, rx in [("이유없", r"이유\s?없"), ("결정한다", r"결정한다"), ("인용", r"인용"), ("기각", r"기각"), ("주문과 같이", r"주문과\s?같이")]:
    print(f'문구 속 결과 표현 "{lab}" 행 수:', int(t.str.contains(rx).sum()))
print("문구 속 조정번호 꼴 행 수:", int(t.str.contains(r"제?\s?(?:19|20)\d{2}\s?-\s?\d{1,3}\s?호").sum()))
print("D014 행:", d[d.diff_id == DID][["diff_id", "clause_text", "eval_pick"]].to_dict("records"))
