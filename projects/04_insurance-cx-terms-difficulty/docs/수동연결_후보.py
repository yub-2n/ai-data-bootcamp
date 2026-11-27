"""수동 연결 후보표 (2026-11-03) — PROJECT.md 4-8 조항 추출 보완 ③. 반영하지 않고 사람 확인용 표만 만든다.

사용:  python3 docs/수동연결_후보.py
입력:  data/interim/needs_review.csv(항목 '수동 연결'), decisions.csv, texts/*.txt('오류' 빈 행만)  — 읽기만
출력:  docs/수동연결_후보.csv  (cases.csv는 바꾸지 않는다)

후보 찾는 법
 - 별칭이 별표·분류표('재해분류표', '별표 2' 등)면: 붙임 → 기초 사실 → 판단 순으로 그 이름이 나오고 바로 뒤에 정의·목록
   ('…라 함은', '…에 의하면', '…에 의거', '다음', 줄바꿈 목록)이 이어지는 곳을 후보로. 위치별로 첫 곳 하나.
 - 별칭이 면책조항·'이 사건 면책사유'면: 붙임·기초 사실에서 조 제목에 '보상하지/지급하지/면책'이 든 조(제N조(제목))를 모두 후보로,
   판단 안에서 '면책' 조항 문구를 옮겨 적은 곳(따옴표 인용 또는 '…라고 규정')을 '판단 안 관련 약관 규정' 후보로.
 - 후보가 없으면 '후보 없음' 한 행.
"""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
DOCS = os.path.join(ROOT, "docs")
_src = open(os.path.join(DOCS, "본실행_계산.py"), encoding="utf-8").read()
_src = _src[: _src.index("# =========================================================================== 7. 실행")]
G = {"__file__": os.path.join(DOCS, "본실행_계산.py")}
exec(_src, G)
dec, s, facts_section, strip_law_segments, case_key_of = G["dec"], G["s"], G["facts_section"], G["strip_law_segments"], G["case_key_of"]
ALIAS = G["ALIAS"]

R = pd.read_csv(os.path.join(INTERIM, "needs_review.csv"))
keys = R.loc[R["항목"] == "수동 연결", "case_key"].tolist()
rows_by_key = {}
for _, r in dec.iterrows():
    if s(r["오류"]):
        continue
    rows_by_key.setdefault(case_key_of(r)[0], r)


def flat(t, n):
    return re.sub(r"\s+", " ", t).strip()[:n]


def sentences(t):
    return [x.strip() for x in re.split(r"(?<=[다음함됨])\.\s+|\n\s*\n|\n(?=\s*[□○◦ᄋ◆\-]\s)", t) if x.strip()]


def context(judg, alias):
    sl = sentences(judg)
    for i, x in enumerate(sl):
        if alias in x:
            seg = " ".join(sl[max(0, i - 1): i + 2])
            seg = re.sub(r"\s+", " ", seg)
            p = seg.find(alias)
            st = max(0, min(p - 90, len(seg) - 200))
            return seg[st: st + 200]
    return ""


DEF_AFTER = re.compile(r"^.{0,60}?(?:라\s?함은|이라\s?함은|에\s?의하면|에\s?의거|에서\s?정하|는\s?다음|다음과\s?같|:|\n\s*(?:\d|[가-하]|[①-⑳])[\.\)\s])", re.S)
EXEMPT_TITLE = re.compile(r"보상하지|지급하지|면책|보험금을\s?지급하지")
HEAD = re.compile(r"(?m)^\s*(?:[□○◦ᄋ·■◇◆⦁•\-]\s*)?(제\s?(\d+)\s?조(?:의\s?\d+)?)\s*[\(（【]\s*([^)）】\n]{1,40})\s*[\)）】]")

out = []
for k in keys:
    r = rows_by_key[k]
    text = open(os.path.join(INTERIM, "texts", os.path.splitext(s(r["파일명"]))[0] + ".txt"), encoding="utf-8").read()
    judg = s(r["위원회_판단"])
    srcs = [("붙임", strip_law_segments(s(r["붙임"]))), ("기초 사실", facts_section(text)), ("판단 안 관련 약관 규정", judg)]
    am = ALIAS.search(judg)
    alias = am.group(0).strip() if am else ""
    ctx = context(judg, alias) if alias else ""
    cands = []
    if re.search(r"면책|사유", alias):
        for loc, src in srcs[:2]:
            for m in HEAD.finditer(src):
                if EXEMPT_TITLE.search(m.group(3)):
                    blk = G["article_block"](src[m.start():], int(m.group(2)))
                    cands.append((loc, f"{m.group(1)}({m.group(3).strip()})", flat(blk, 300)))
        for m in re.finditer(r"[“\"]([^”\"]{20,})[”\"]", judg):
            pre = judg[max(0, m.start() - 80): m.start()]
            if re.search(r"면책|보상하지|지급하지", pre + m.group(1)[:40]) and "약관" in pre:
                cands.append(("판단 안 관련 약관 규정", flat(pre.split("\n")[-1], 60) or "(조 번호 없음)", flat(m.group(1), 300)))
                break
    else:
        name = re.sub(r"\s+", " ", alias)
        pat = re.compile(re.escape(name).replace(r"\ ", r"\s?") if name.strip() not in ("별표", "") else r"별표\s?\d*")
        for loc, src in srcs:
            for m in pat.finditer(src):
                tail = src[m.end(): m.end() + 400]
                snippet = src[m.start(): m.start() + 160]
                if re.search(r"사료|진단\*?\s?된\s?사실|주장|판단되|해당될\s?것", snippet):
                    continue  # 사실관계·의견 문장이지 조문이 아님
                if DEF_AFTER.match(tail) or loc != "판단 안 관련 약관 규정" and re.match(r"^[^\n]{0,40}\n", tail):
                    title_m = re.match(r"^\s*[\(（]?([^)）\n]{0,30})[\)）]?", tail)
                    label = (m.group(0) + ((" " + title_m.group(1).strip()) if title_m and title_m.group(1).strip() and not DEF_AFTER.match(tail[:5]) else "")).strip()
                    cands.append((loc, flat(label, 60), flat(src[m.start(): m.start() + 340], 300)))
                    break
    # 같은 위치·같은 조항 중복 제거
    seen, uniq = set(), []
    for c in cands:
        if (c[0], c[1]) not in seen:
            seen.add((c[0], c[1]))
            uniq.append(c)
    if not uniq:
        out.append(dict(case_key=k, 판단_문장=ctx, 후보_위치="후보 없음", 후보_조항="", 후보_문구="", 별칭=alias))
    for loc, lab, txt in uniq:
        out.append(dict(case_key=k, 판단_문장=ctx, 후보_위치=loc, 후보_조항=lab, 후보_문구=txt, 별칭=alias))

O = pd.DataFrame(out)
O = O.rename(columns={"판단_문장": "판단에서 조항을 가리킨 문장(앞뒤 1문장)", "후보_위치": "후보 조문 위치",
                      "후보_조항": "후보 조항 번호와 제목", "후보_문구": "후보 조문 문구(앞 300자)"})
O.to_csv(os.path.join(DOCS, "수동연결_후보.csv"), index=False, encoding="utf-8-sig")

per = O.groupby("case_key")["후보 조문 위치"].apply(lambda x: 0 if (x == "후보 없음").all() else len(x))
print("대상 사건:", len(keys), " 표 행:", len(O))
print("후보 1개:", int((per == 1).sum()), " 여러 개:", int((per > 1).sum()), " 후보 없음:", int((per == 0).sum()))
print("후보 위치별 행:", O["후보 조문 위치"].value_counts().to_dict())

# 개인정보 점검(이름·주민번호·전화·이메일 꼴). 마스킹(○○, ∀, ◎ 등)된 것은 제외
txt = O.astype(str).apply(lambda col: col.str.cat(sep=" ")).str.cat(sep=" ")
pi = {"주민번호": r"\d{6}\s?-\s?[1-4]\d{6}", "전화": r"0\d{1,2}-\d{3,4}-\d{4}", "이메일": r"[\w.]+@[\w.]+\.\w+",
      "이름+씨/님": r"(?<![가-힣])[가-힣]{2,3}\s?(?:씨|님)(?![가-힣])"}
print("개인정보 꼴:", {k_: sorted(set(re.findall(v, txt)))[:10] for k_, v in pi.items() if re.findall(v, txt)} or "없음")
