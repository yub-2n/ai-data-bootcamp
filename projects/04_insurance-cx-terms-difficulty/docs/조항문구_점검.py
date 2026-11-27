"""조항 문구 점검 (case-parser, 2026-11-03) — PROJECT.md 4-2 "조항 문구 = 약관 조문"을 제대로 적용하는 수정만 한다.

사용:  python3 docs/조항문구_점검.py   (docs/본실행_계산.py를 먼저 돌린 뒤. 다시 돌려도 같은 결과가 나오도록
       항상 본실행이 만든 상태에서 시작하려고, 처음 실행 때 원래 파일을 *_본실행.csv로 한 번 복사해 두고 그것을 입력으로 쓴다)
입력:  data/interim/cases_본실행.csv(없으면 cases.csv를 복사해 만든다), decisions.csv, texts/*.txt('오류' 빈 행만),
       data/interim/difficulty_id_map_본실행.csv, cases_for_difficulty_본실행.csv(같은 방식)
출력:  data/interim/cases.csv(갱신), docs/조항문구_점검.csv, data/interim/cases_for_difficulty.csv(다시 만들기),
       data/interim/difficulty_id_map.csv(갱신), docs/대조표본.csv(문구 열만 갱신)

점검 대상: clause_text가 있는 모든 행. 문제 유형
  1 위원회·당사자 문장 섞임   2 '(생략)'만 있거나 끝에 다음 항목 제목·생략 표시   3 조가 여러 개   4 문장 중간 시작·20자 미만
고치는 순서: ① 붙임 → 기초 사실에서 같은 조(항·호)의 조문을 다시 찾아 깨끗하면 교체(clause_text_source 갱신)
            ② 없으면 지금 문구에서 위원회·당사자 문장, 제목, 생략 표시, 다음 조를 잘라 냄
            ③ 따옴표 없이 '…라고 규정/정하고 있'으로 옮긴 문구는 풀어 쓴 서술(4-8 정의), 그 문장만 남김
            ④ 약관 조문이 전혀 없으면 exclude_reason = "조항 문구 없음"
금지: 난이도·통계 계산, 결과(cited) 사용, 대조표본·평가 표본 다시 뽑기.
"""
import os
import re
import shutil

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
DOCS = os.path.join(ROOT, "docs")

# 본실행 스크립트의 함수(조항 블록 찾기·항/호 자르기·법령 부분 빼기·pdf 정리)를 그대로 쓴다(7장 실행부 앞까지만).
_src = open(os.path.join(DOCS, "본실행_계산.py"), encoding="utf-8").read()
_src = _src[: _src.index("# =========================================================================== 7. 실행")]
G = {"__file__": os.path.join(DOCS, "본실행_계산.py")}
exec(_src, G)
dec, s, one_line = G["dec"], G["s"], G["one_line"]
article_title, cut_level, strip_law_segments, facts_section = G["article_title"], G["cut_level"], G["strip_law_segments"], G["facts_section"]
case_key_of = G["case_key_of"]


def snapshot(name):
    """처음 실행 때 본실행 결과를 *_본실행.csv로 복사해 두고 그것을 입력으로 쓴다(다시 돌려도 같은 결과)."""
    cur = os.path.join(INTERIM, name)
    base = cur.replace(".csv", "_본실행.csv")
    if not os.path.exists(base):
        shutil.copyfile(cur, base)
    return base


C = pd.read_csv(snapshot("cases.csv"), dtype={"exclude_reason": str, "clause_text_source": str, "clause_text_form": str})
C["exclude_reason"] = C["exclude_reason"].fillna("")
OLD_MAP = pd.read_csv(snapshot("difficulty_id_map.csv"))
OLD_DIFF = pd.read_csv(snapshot("cases_for_difficulty.csv"))

# ------------------------------------------------------------------ 패턴
# 판례 인용은 인용 꼴(… 선고 2003다… 판결, 대법원)로만 본다: 약관 조문 안의 '파산 선고', '판단할 수 있는' 같은 말은 남긴다
CITE = r"\d\s?선고|선고\s?\d|\d{2,4}\s?[가-힣]{1,2}\s?\d+\s?판결|대법원|판시"
COMMITTEE = re.compile(r"신청인|피신청인|살피건대|살펴보건대|보건대|주장하|주장은|판단됨|판단된다|판단컨대|판단하건대|결정한다|결정함|이유\s?없|"
                       r"사료됨|사료된다|봄이\s?상당|할\s?것이다|할\s?것임|그렇다면|따라서|이 사건|본\s?건(?![강물])|이\s?건\s|동\s?건|"
                       + CITE + r"|조정결정|당\s?위원회|우리\s?원")
REPORTING = re.compile(r"(?:라고|다고|고|도록|함을|것으로)\s?(?:규정|정하|정한|명시)|에\s?의하면|에\s?따르면|에\s?의거|"
                       r"정하고\s?있|규정하고\s?있|규정되어\s?있|규정함으로써")
OMIT = re.compile(r"\(\s*(?:이하\s*)?생\s*략\s*\)|\(\s*중\s*략\s*\)|^[\s①-⑳\d\.~∼제조항,\-]*\(?\s*생\s*략\s*\)?\s*$")
HEAD_LINE = re.compile(r"^\s*(?:\(\d{1,2}\)|[가-하]\.|\d{1,2}\.|[①-⑳]|[□◦○ᄋ◆■])?\s*[^\n]{0,60}?"
                       r"(?:여부|검토|쟁점|다툼이\s?없는\s?사실|사실관계|판단|소결|결론|당사자\s?주장|위원회)\s*$")
ART_HEAD = re.compile(r"(?m)(?:^|[□○◦ᄋ·■◇◆⦁•]\s*)제\s?(\d+)\s?조(?:의\s?\d+)?\s*[\(（【]")
MID_START = re.compile(r"^\s*(?:는|은|를|을|에|에서|의|고|며|및|하여|하고|으로|로|와|과)\s")
LAWNAME = re.compile(r"상법|법률|시행령|시행규칙|[가-힣]+법\s?제")


def art_no_of(ref):
    m = re.search(r"제(\d+)조", s(ref))
    return int(m.group(1)) if m else None


def problems(t, art_no=None):
    """문제 유형 목록(1~4)."""
    p = []
    if not t.strip():
        return p
    body = re.sub(r"“[^”]*”|\"[^\"]*\"|「[^」]*」|『[^』]*』", "", t)  # 따옴표 안 조문은 빼고 본다
    if COMMITTEE.search(body):
        p.append("1")
    lines = [ln for ln in t.split("\n") if ln.strip()]
    if OMIT.search(t) or (lines and HEAD_LINE.match(lines[-1]) and not re.search(r"니다\.?\s*$", lines[-1])):
        p.append("2")
    heads = [(mm.start(), int(mm.group(1))) for mm in ART_HEAD.finditer(t)]
    if len({n for _, n in heads}) > 1 or (art_no is not None and any(n != art_no and pos > 0 for pos, n in heads)):
        p.append("3")
    if len(re.sub(r"\s", "", t)) < 20 or MID_START.match(t):
        p.append("4")
    return p


def strip_tail(t):
    """끝에 붙은 다음 항목 제목·생략 표시 줄을 뗀다."""
    lines = t.rstrip().split("\n")
    while lines:
        last = lines[-1].strip()
        if not last:
            lines.pop()
            continue
        if OMIT.search(last) and len(re.sub(OMIT, "", last).strip()) < 25:
            lines.pop()
            continue
        if HEAD_LINE.match(last) and not re.search(r"니다\.?\s*$", last):
            lines.pop()
            continue
        break
    t = "\n".join(lines)
    t = re.sub(r"\s*\(\s*(?:이하\s*)?생\s*략\s*\)\s*$", "", t)
    return t.strip()


def cut_other_articles(t, art_no):
    for m in ART_HEAD.finditer(t):
        if art_no is not None and int(m.group(1)) != art_no and m.start() > 0:
            return t[: m.start()].rstrip(" □○◦ᄋ·■\n")
    return t


def cut_committee(t):
    """조문 뒤에 이어진 위원회·당사자 문장을 그 문장부터 잘라 낸다. 첫 문장부터 섞여 있으면 None."""
    units = re.split(r"(?<=[다음함됨])\.\s+|\n", t)
    out, pos = [], 0
    for u in units:
        uu = re.sub(r"“[^”]*”|\"[^\"]*\"|「[^」]*」|『[^』]*』", "", u)
        if COMMITTEE.search(uu) or REPORTING.search(uu):
            break
        out.append(u)
    if not out:
        return None
    # 원문 줄바꿈을 살리려고 원문에서 잘라 낸다
    keep_len = 0
    for u in out:
        i = t.find(u, keep_len)
        keep_len = i + len(u)
    return t[:keep_len].rstrip(" ,\n") + ("." if t[keep_len:keep_len + 1] == "." else "")


def strip_lead(t, art_no):
    """첫 줄에서 '제N조' 앞의 머리말('□ 당해보험 △△특약 약관 ')을 뗀다."""
    if art_no is None:
        return t
    first = t.split("\n", 1)[0]
    m = re.search(rf"제\s?{art_no}\s?조", first)
    if m and m.start() > 0 and not re.match(r"^\s*[①-⑳\d]", first):
        return t[m.start():]
    return re.sub(r"^\s*[□○◦ᄋ·■◇◆\-]\s*", "", t)


def clean_verbatim(t, art_no):
    t = strip_tail(t)
    t = cut_other_articles(t, art_no)
    t2 = cut_committee(t)
    if t2 is None:
        return None
    t2 = strip_tail(strip_lead(t2, art_no))
    return t2


def ok_text(t, n=None):
    return bool(t) and len(re.sub(r"\s", "", t)) >= 20 and not problems(t, n) and not OMIT.search(t)


def quote_in(text, art_no):
    """조항 언급 뒤의 인용 하나: 여는 따옴표(“, 『, ', ‘ 짝)부터 닫는 따옴표나 '…라고 규정' 앞까지. 약관 문체(…니다)일 때만."""
    for m in re.finditer(r"“|『|(?<![가-힣A-Za-z])'|‘", text):
        opener = m.group(0)
        closer = {"“": r"[”“\"]", "『": r"』", "'": r"'", "‘": r"[’']"}[opener]
        rest = text[m.end():]
        if MID_START.match(rest) or re.match(r"^\s*(라|이라)\s", rest):
            continue
        cm = re.search(closer + r"|\s*(?:라고|고)\s?(?:규정|명시|정하)", rest)
        q = rest[: cm.start()] if cm else rest
        q = strip_tail(cut_other_articles(q, art_no)).strip()
        if len(re.sub(r"\s", "", q)) >= 20 and "니다" in q and not COMMITTEE.search(q) and not problems(q, art_no):
            return q
    return ""


def paraphrase_sentence(t, art_no):
    """풀어 쓴 서술: 조항을 언급한 문장 하나만(전달 동사 끝까지). 당사자·판례 문장이거나 괄호 속 인용뿐이면 None."""
    t = strip_tail(t)
    m = re.search(rf"제\s?{art_no}\s?조", t) if art_no is not None else None
    st = t.rfind("\n", 0, m.start()) + 1 if m else 0
    rest = t[st:]
    # 같은 줄 앞의 다른 문장·절(법령 설명 등)은 떼고 이 조항을 말하는 절부터
    if m:
        mm = re.search(rf"제\s?{art_no}\s?조", rest)
        cuts = [x.end() for x in re.finditer(r"(?:있고|하고|이며|으며|있으며|되어\s?있고|사실),\s+|[.;]\s+", rest[: mm.start()])]
        if cuts:
            rest = rest[max(cuts):]
    em = re.search(r"(?:규정|정하)(?:하)?고\s?있(?:음|으며|고|는\s?바|는\s?사실|다)|규정되어\s?있(?:음|고|다)|"
                   r"규정(?:하면서|함으로써|하고|함)|(?:라고|다고|고|도록)\s?규정|도록\s?정하(?:고|며)|정하(?:면서|며)", rest)
    if em:
        sent = rest[: em.end()]
    else:
        e2 = re.search(r"(?<=[다음함됨])\.(?:\s|$)|\n\s*\n|\n\s*[□○◦ᄋ]", rest)
        sent = rest[: e2.start() + 1] if e2 else rest
    sent = re.sub(r"^\s*[□○◦ᄋ·■◇◆\-]\s*", "", sent).strip()
    if m:
        ms = sent.find(re.search(rf"제\s?{art_no}\s?조", sent).group(0)) if re.search(rf"제\s?{art_no}\s?조", sent) else -1
        if ms >= 0 and sent[:ms].count("(") > sent[:ms].count(")"):
            return None, "괄호 속 출처 표시뿐(조문 내용 없음)"
    party = re.search(r"신청인|피신청인|주장|판단(?:됨|된다|컨대|하건대|이)|쟁점|사료|해석해\s?보면|" + CITE, sent)
    if party:
        return None, f"조항 언급 문장이 위원회·당사자·판례 문장('{party.group(0)}')이고 약관 조문 내용이 없음"
    q = quote_in(t[st:], art_no)
    if q and m and t[st:].find(q[:15]) < len(sent) + 5:
        return "QUOTE:" + q, ""
    body = re.sub(rf"^.*?제\s?{art_no}\s?조[^\s]*", "", sent) if art_no is not None else sent
    if len(re.sub(r"\s", "", body)) < 20:
        return None, "조문 내용 20자 미만"
    return sent, ""


# ------------------------------------------------------------------ 원문(붙임·기초 사실) 다시 찾기
dec_rows = {}
for _, r in dec.iterrows():
    if s(r["오류"]):
        continue
    k, _ = case_key_of(r)
    dec_rows[(k, int(r["nttId"]))] = r


def sources_for(key, ntt):
    r = dec_rows.get((key, ntt))
    if r is None:
        return None
    text = open(os.path.join(INTERIM, "texts", os.path.splitext(s(r["파일명"]))[0] + ".txt"), encoding="utf-8").read()
    att = s(r["붙임"])
    if s(r["형식"]) == "pdf":
        text, _ = G["clean_pdf_text"](text)
        att = G["split_pdf_sections"](text)["붙임"]
    return [(strip_law_segments(att), "붙임"), (facts_section(text), "본문 인용")]


def all_blocks(src, art_no):
    """src 안의 줄머리 '제N조' 블록을 모두(처음 것만이 아니라) 돌려준다."""
    out = []
    for m in re.finditer(rf"(?m)^\s*(?:[□○◦ᄋ·\-\*■◇◆▢]\s*)?제\s?{art_no}\s?조(?!\s*의)", src):
        blk = G["article_block"](src[m.start():], art_no)
        if blk:
            out.append(blk)
    return out


def relookup(key, ntt, ref, level):
    n = art_no_of(ref)
    srcs = sources_for(key, ntt)
    if n is None or not srcs:
        return None
    for src, name in srcs:
        if not src:
            continue
        for blk in all_blocks(src, n):
            if REPORTING.search(blk[:200]):
                continue
            art = clean_verbatim(blk, n)
            if not art or not ok_text(art):
                continue
            txt = clean_verbatim(cut_level(blk, level, ref), n) if level != "조" else art
            if txt and ok_text(txt):
                return txt, art, name
    return None


def judgment_of(key, ntt):
    r = dec_rows.get((key, ntt))
    if r is None:
        return ""
    if s(r["형식"]) == "pdf":
        text = open(os.path.join(INTERIM, "texts", os.path.splitext(s(r["파일명"]))[0] + ".txt"), encoding="utf-8").read()
        return G["split_pdf_sections"](G["clean_pdf_text"](text)[0])["위원회_판단"]
    return s(r["위원회_판단"])


def from_judgment(key, ntt, n):
    """판단에서 처음 언급된 그 조항(4-2 ④)의 문장으로 다시: 20자 이상 따옴표 인용이 있으면 따옴표 인용, 아니면 풀어 쓴 서술."""
    j = judgment_of(key, ntt)
    for mm in G["ART"].finditer(j):
        if int(mm.group(1)) == n and G["is_clause_ref"](j, mm.start())[0]:
            st = j.rfind("\n", 0, mm.start()) + 1
            chunk = j[st: mm.end() + 900]
            sent, why = paraphrase_sentence(chunk, n)
            if sent is None:
                return None, None, why
            if sent.startswith("QUOTE:"):
                return sent[6:], "따옴표 인용", ""
            if OMIT.search(sent) or re.search(r"생\s*략", sent):
                return None, None, "인용된 항·호가 결정문에서 '(생략)'됨"
            q = G["quoted_text"](sent)
            if q and len(q) >= 20 and not problems(q):
                return q, "따옴표 인용", ""
            return sent, "풀어 쓴 서술", ""
    return None, None, "판단에서 조항 언급을 다시 찾지 못함"


# ------------------------------------------------------------------ 점검·수정
log = []
C["_orig_text"] = C["clause_text"]
for i, r in C[C["clause_text"].fillna("") != ""].iterrows():
    key, ntt, ref, level = r["case_key"], int(r["nttId"]), s(r["clause_ref"]), s(r["clause_level"])
    n = art_no_of(ref)
    t0, a0, form0, src0 = s(r["clause_text"]), s(r["clause_text_article"]), s(r["clause_text_form"]), s(r["clause_text_source"])
    p_t, p_a = problems(t0, n), problems(a0, n)
    if form0 == "풀어 쓴 서술" and not p_t:
        p_t = []  # 풀어 쓴 서술은 아래에서 언급 문장만 남기는지 따로 본다
    new_t, new_a, new_form, new_src, action = t0, a0, form0, src0, "그대로"
    # '제N조(…)에 …', '제N조 제2항에서는 …' 꼴: 조문이 아니라 위원회가 조항을 두고 쓴 문장 → 풀어 쓴 서술로 본다(4-8 정의)
    lead = re.sub(r"^\s*[□○◦ᄋ·■◇◆⦁•\-]\s*", "", t0)
    lead_rule = False
    if form0 == "조문 그대로" and re.match(r"^(?:[^\n]{0,40}?약관\s*)?제\s?\d+\s?조(?:\s?[\(（][^)）]*[\)）])?\s?(?:제\s?\d+\s?항\s?)?(?:제\s?\d+\s?호\s?)?(?:에서는|에서|에는|에|은|는)\s", lead):
        form0 = "풀어 쓴 서술"
        new_form = "풀어 쓴 서술"
        lead_rule = True
        if "1" not in p_t:
            p_t = p_t + ["1"]
    if form0 != "풀어 쓴 서술" and not p_t and not p_a:
        continue
    found = relookup(key, ntt, ref, level) if (p_t or p_a or form0 == "풀어 쓴 서술") else None
    if found and (p_t or form0 == "풀어 쓴 서술"):
        new_t, new_a, new_src = found[0], found[1], found[2]
        new_form = "조문 그대로"
        action = f"{'붙임' if found[2] == '붙임' else '기초 사실·본문'}의 조문으로 교체"
    elif form0 == "풀어 쓴 서술":
        sent, why = paraphrase_sentence(t0, n)
        if sent is None:
            new_t, new_a, action = "", "", f"조항 문구 없음({why})"
        elif sent.startswith("QUOTE:"):
            new_t, new_form = sent[6:], "따옴표 인용"
            new_a = new_t if level == "조" else ""
            action = "닫는 따옴표 전에 잘린 인용 → 따옴표 인용"
        else:
            new_t = sent
            new_a = sent if level == "조" else ""
            action = "풀어 쓴 서술: 조항 언급 문장만 남김" if sent != t0.strip() else "그대로(풀어 쓴 서술)"
    elif p_t:
        ct = clean_verbatim(t0, n)
        if ct and ok_text(ct):
            new_t, action = ct, "위원회·당사자 문장/제목/생략 표시/다음 조 잘라 냄"
        else:
            # 첫 문장부터 '…라고 규정' 꼴이면 풀어 쓴 서술(4-8 정의)
            if REPORTING.search(t0[:300]) and not re.search(r"“[^”]{20,}”", t0):
                sent, why = paraphrase_sentence(t0, n)
                if sent:
                    new_t, new_form, new_a, action = sent, "풀어 쓴 서술", (sent if level == "조" else ""), "따옴표 없는 '…라고 규정' → 풀어 쓴 서술"
                else:
                    new_t, new_a, action = "", "", f"조항 문구 없음({why})"
            else:
                ft, fform, why = from_judgment(key, ntt, n)
                if ft:
                    new_t, new_form = ft, fform
                    new_a = ft if level == "조" else ""
                    action = f"판단의 조항 언급 문장으로 다시 → {fform}"
                else:
                    new_t, new_a, action = "", "", f"조항 문구 없음({why})"
    # 조 전체 문구(clause_text_article)도 같은 기준
    if new_t and new_form != "풀어 쓴 서술" and not action.endswith("교체"):
        if p_a or (new_a and problems(new_a)):
            ca = clean_verbatim(new_a, n) if new_a else ""
            new_a = ca if (ca and ok_text(ca)) else ""
            action += " / 조 전체 문구 " + ("잘라 냄" if new_a else "비움(깨끗한 조 전체 문구 없음)")
    if not new_t:
        new_a = ""
    if lead_rule and new_t and new_form == "풀어 쓴 서술" and not action.startswith("풀어 쓴 서술: 조항"):
        action = "'제N조(…)에 …' 꼴 위원회 문장 → 풀어 쓴 서술"
    if (new_t, new_a, new_form, new_src) == (t0, a0, s(r["clause_text_form"]), src0):
        if p_t or p_a:
            log.append(dict(case_key=key, 문제_유형=",".join(p_t) + ("" if not p_a else f" / 조전체:{','.join(p_a)}"),
                            고치기_전_앞80자=one_line(t0, 80), 고친_뒤_앞80자=one_line(new_t, 80),
                            처리=("그대로(풀어 쓴 서술: 조항 언급 문장 하나뿐)" if form0 == "풀어 쓴 서술" else "그대로(점검 결과 약관 조문 안의 말·번호)"), nttId=ntt))
        continue
    C.at[i, "clause_text"] = new_t
    C.at[i, "clause_text_article"] = new_a
    C.at[i, "clause_text_form"] = new_form if new_t else ""
    C.at[i, "clause_text_source"] = new_src if new_t else ""
    ptype = ",".join(p_t) if p_t else ("풀어 쓴 서술 다듬기" if form0 == "풀어 쓴 서술" else "")
    if p_a:
        ptype += f" / 조전체:{','.join(p_a)}"
    log.append(dict(case_key=key, 문제_유형=ptype, 고치기_전_앞80자=one_line(t0, 80), 고친_뒤_앞80자=one_line(new_t, 80),
                    처리=action, nttId=ntt))

# ------------------------------------------------------------------ 제외 사유 다시 매기기(조항 관련 사유만; 다른 사유는 그대로)
CLAUSE_REASONS = {"", "조항 문구 없음", "풀어 쓴 서술"}
before_reason = C["exclude_reason"].copy()
for i, r in C.iterrows():
    if r["exclude_reason"] not in CLAUSE_REASONS or not s(r["clause_ref"]):
        continue
    if not s(r["clause_text"]):
        C.at[i, "exclude_reason"] = "조항 문구 없음"
    elif s(r["clause_text_form"]) == "풀어 쓴 서술":
        C.at[i, "exclude_reason"] = "풀어 쓴 서술"
    else:
        C.at[i, "exclude_reason"] = ""
changed = C[before_reason != C["exclude_reason"]]
C = C.drop(columns="_orig_text")
C.to_csv(os.path.join(INTERIM, "cases.csv"), index=False, encoding="utf-8-sig")
L = pd.DataFrame(log)
L.rename(columns={"문제_유형": "문제 유형", "고치기_전_앞80자": "고치기 전 앞 80자", "고친_뒤_앞80자": "고친 뒤 앞 80자"})[
    ["case_key", "문제 유형", "고치기 전 앞 80자", "고친 뒤 앞 80자", "처리", "nttId"]].to_csv(
    os.path.join(DOCS, "조항문구_점검.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 난이도 입력 다시 만들기(diff_id·eval_pick 유지)
old = OLD_MAP.merge(OLD_DIFF, on="diff_id")
old_base = pd.read_csv(os.path.join(INTERIM, "cases_본실행.csv"))
# 같은 case_key가 두 행인 경우(제2009-29호): 본실행 때의 문구로 어느 nttId인지 맞춘다
ntt_of = {}
for _, o in old.iterrows():
    cand = old_base[(old_base["case_key"] == o["case_key"]) & (old_base["clause_text"].fillna("") == s(o["clause_text"]))]
    used = {v for v in ntt_of.values()}
    picks = [int(x) for x in cand["nttId"] if (o["case_key"], int(x)) not in used]
    ntt_of[o["diff_id"]] = (o["case_key"], picks[0] if picks else int(cand["nttId"].iloc[0]))
rows, kept_ids = [], set()
Ckey = {(k, int(n)): idx for idx, (k, n) in enumerate(zip(C["case_key"], C["nttId"]))}
for did, (k, n) in ntt_of.items():
    row = C.iloc[Ckey[(k, n)]]
    kept_ids.add((k, n))
    if s(row["clause_text"]):
        ep = int(old.loc[old["diff_id"] == did, "eval_pick"].iloc[0])
        rows.append(dict(diff_id=did, case_key=k, nttId=n, eval_pick=ep))
new_rows = C[(C["clause_text"].fillna("") != "") & ~C.apply(lambda x: (x["case_key"], int(x["nttId"])) in kept_ids, axis=1)]
nxt = 251
for _, row in new_rows.sort_values(["case_key", "nttId"]).iterrows():
    rows.append(dict(diff_id=f"D{nxt:03d}", case_key=row["case_key"], nttId=int(row["nttId"]), eval_pick=0))
    nxt += 1
M = pd.DataFrame(rows)
M = M.merge(C[["case_key", "nttId", "issue_type", "clause_level", "clause_text_form", "clause_text", "clause_text_article",
               "exclude_reason"]], on=["case_key", "nttId"], how="left").sort_values("diff_id").reset_index(drop=True)
DCOLS = ["diff_id", "issue_type", "clause_level", "clause_text_form", "clause_text", "clause_text_article", "eval_pick"]
M[DCOLS].to_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"), index=False, encoding="utf-8-sig")
M[["diff_id", "case_key"]].to_csv(os.path.join(INTERIM, "difficulty_id_map.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 대조표본: 다시 뽑지 않고 문구 열만 갱신
KB = os.path.join(DOCS, "대조표본_본실행.csv")
if not os.path.exists(KB):
    shutil.copyfile(os.path.join(DOCS, "대조표본.csv"), KB)
K = pd.read_csv(KB)
for j, kr in K.iterrows():
    row = C.iloc[Ckey[(kr["case_key"], int(kr["nttId"]))]]
    for col in ["clause_text", "clause_text_form", "clause_text_source"]:
        K.at[j, col] = row[col]
K.to_csv(os.path.join(DOCS, "대조표본.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 표준출력
print("== 점검 대상(clause_text 있는 행, 본실행):", int((old_base["clause_text"].fillna("") != "").sum()))
print("점검표 행:", len(L))
ptypes = L["문제_유형"].fillna("")
for t_ in ["1", "2", "3", "4"]:
    print(f"문제 유형 {t_} (clause_text):", int(ptypes.str.split(" / ").str[0].str.split(",").apply(lambda xs: t_ in xs).sum()),
          f" (조전체 문구):", int(ptypes.str.contains(f"조전체:[0-9,]*{t_}").sum()))
print("풀어 쓴 서술 다듬기만:", int((ptypes == "풀어 쓴 서술 다듬기").sum()))
act = L["처리"].str.replace(r"\(.*", "", regex=True).str.split(" / ").str[0]
print("처리별:", act.value_counts().to_dict())
print("조 전체 문구 처리:", L["처리"].str.extract(r"조 전체 문구 (\S+)")[0].value_counts().to_dict())
print("제외 사유가 바뀐 행:", len(changed))
print(pd.crosstab(before_reason[changed.index].replace("", "(분석 포함)"), changed["exclude_reason"].replace("", "(분석 포함)")).to_string())
inc_before = int((before_reason == "").sum())
inc_after = int((C["exclude_reason"] == "").sum())
print("분석 포함:", inc_before, "→", inc_after)
print("시기별 분석 포함:", C[C["exclude_reason"] == ""]["period"].value_counts().reindex(G["P"]).to_dict())
print("제외 사유:", C["exclude_reason"].replace("", "(분석 포함)").value_counts().to_dict())
print("clause_text_form:", C["clause_text_form"].fillna("").replace("", "(없음)").value_counts().to_dict())
ev = M[M["eval_pick"] == 1]
print("eval_pick 남은 행:", len(ev), " 그중 분석 포함:", int((ev["exclude_reason"].fillna("") == "").sum()))
gone_ev = set(old[old["eval_pick"] == 1]["diff_id"]) - set(M["diff_id"])
print("eval_pick 중 문구가 없어져 빠진 diff_id:", sorted(gone_ev))
print("eval_pick 중 분석에서 제외된 사건:", ev[ev["exclude_reason"].fillna("") != ""][["diff_id", "case_key", "exclude_reason"]].to_dict("records"))
kx = K.merge(C[["case_key", "nttId", "exclude_reason"]], on=["case_key", "nttId"])
print("대조표본 중 분석에서 제외된 사건:", kx[kx["exclude_reason"] != ""][["case_key", "exclude_reason"]].to_dict("records"))
print("난이도 입력 행:", len(M), " 빠진 diff_id 수:", len(set(old["diff_id"]) - set(M["diff_id"])), " 새 diff_id:",
      M[M["diff_id"] > "D250"]["diff_id"].tolist())
