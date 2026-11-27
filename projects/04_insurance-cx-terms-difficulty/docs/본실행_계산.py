"""case-parser 본 모드 계산 스크립트 (2026-11-03)

사용:  python3 docs/본실행_계산.py
입력:  data/interim/decisions.csv, data/interim/texts/*.txt('오류'가 빈 행의 txt만 연다),
       data/interim/fss_details_enriched.csv, data/interim/pilot_sample.csv
출력:  data/interim/cases.csv                  사건별 라벨(PROJECT.md 5장 열 + partial, partial_hint,
                                               clause_text_form, clause_text_article, topic + 보조 열)
       data/interim/needs_review.csv           needs_review = 1인 사건의 항목별 이유와 근거 문장
       docs/대조표본.csv                        분석 포함 - 파일럿 27건 중 시기별 고르게 20건(시드 42)
       data/interim/cases_for_difficulty.csv   팀원B용(diff_id, issue_type, clause_level, clause_text_form,
                                               clause_text, clause_text_article, eval_pick만)
       data/interim/difficulty_id_map.csv      diff_id ↔ case_key(정유빈 보관)
       표준출력: docs/제외사유.md, docs/변환실패.md에 옮긴 모든 숫자

규칙: PROJECT.md 4-1~4-8, 4-8-1(2026-11-03 확정). 파일럿 코드(docs/파일럿_라벨보고_계산.py)의 조항 추출·
문구 확보 함수를 그대로 가져오고, 4-8에서 확정한 부분만 더했다.
- 난이도는 계산하지 않는다. 난이도와 결과의 관계도 계산하지 않는다.
- 애매하면 needs_review = 1. 근거 문장은 evidence_snippet(결과) 및 *_evidence 열에 남긴다.
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
TEXTS = os.path.join(INTERIM, "texts")
DOCS = os.path.join(ROOT, "docs")
SEED = 42
P = ["~2009", "2010-2016", "2017-2026"]

dec = pd.read_csv(os.path.join(INTERIM, "decisions.csv"))
enr = pd.read_csv(os.path.join(INTERIM, "fss_details_enriched.csv"))
pilot = pd.read_csv(os.path.join(INTERIM, "pilot_sample.csv"))


def s(x):
    return "" if pd.isna(x) else str(x)


def one_line(x, n=300):
    return re.sub(r"\s+", " ", s(x)).strip()[:n]


# =========================================================================== 0. case_key
def key_from_filename(fn):
    rest = re.sub(r"^\d+_\d+_", "", fn)
    m = re.search(r"(\d{2,4})\s*[-_]\s*(\d{1,3})", rest)
    if not m:
        return None
    y = m.group(1)
    if len(y) == 2:
        y = ("19" + y) if int(y) > 50 else ("20" + y)
    return f"{y}-{int(m.group(2))}"


def norm_key(k):
    if not k:
        return None
    y, n = k.split("-")
    return f"{y}-{int(n)}"


# 본문에서 잡은 조정번호가 다른 사건(인용한 선례·고시 번호)인 경우: 파일명·게시물 제목의 번호가 맞다.
# (64356: 파일명·제목 2002-38, 본문 추출 2000-48 / 64360: 파일명 2002-52, 본문 추출 1999-58(고시 번호)
#  / 64439: 파일명·제목·본문 2행 2005-38, 본문 추출 2003-32) — 원문 확인 후 파일명 번호를 쓴다.
def case_key_of(row):
    fk = key_from_filename(s(row["파일명"]))
    bk = norm_key(s(row["조정번호"])) if s(row["조정번호"]) else None
    if fk and bk and fk != bk:
        return fk, f"파일명({fk}) ≠ 본문 추출({bk}) → 파일명"
    if bk:
        return bk, ""
    if fk:
        return fk, "본문 없음 → 파일명"
    return f"nttId{row['nttId']}", "조정번호 없음 → nttId"


# =========================================================================== 1. pdf(제2022-5호) 정리
def clean_pdf_text(t):
    """쪽 번호 줄('- 3 -')과 쪽 아래 각주 블록, 본문 속 각주 번호(…보험1) 계약)를 지운다."""
    pages = re.split(r"(?m)^\s*-\s*\d+\s*-\s*$", t)
    out_pages, next_fn = [], 1
    for pg in pages:
        lines = pg.split("\n")
        cut = None
        for i, ln in enumerate(lines):
            m = re.match(r"^(\d{1,2})\)\s", ln)
            if m and int(m.group(1)) == next_fn:
                cut = i
                break
        if cut is not None:
            fn_block = lines[cut:]
            nums = [int(m.group(1)) for ln in fn_block for m in [re.match(r"^(\d{1,2})\)\s", ln)] if m]
            next_fn = max(nums) + 1
            lines = lines[:cut]
        out_pages.append("\n".join(lines))
    body = "\n".join(out_pages)
    # pdf 변환에서 항 기호(①…)가 사용자 정의 글자(\uf000)나 '□7'로 바뀐 것: '□7'도 같은 항 표지로 통일
    body = re.sub(r"(?m)^□(\d{1,2})\s", "\uf000 ", body)
    pos = 0
    for n in range(1, next_fn):
        m = re.compile(rf"(?<=[^\s\d]){n}\)").search(body, pos)
        if m:
            body = body[: m.start()] + body[m.end():]
            pos = m.start()
    return body, next_fn - 1


def split_pdf_sections(t):
    def between(a, b):
        ma = re.search(a, t)
        if not ma:
            return ""
        mb = re.search(b, t[ma.end():]) if b else None
        return t[ma.end(): ma.end() + mb.start()] if mb else t[ma.end():]
    return {
        "주문": between(r"(?m)^\s*주\s*문\s*$", r"(?m)^\s*신\s*청\s*취\s*지\s*$").strip(),
        "신청취지": between(r"(?m)^\s*신\s*청\s*취\s*지\s*$", r"(?m)^\s*이\s*유\s*$").strip(),
        "신청인_주장": between(r"(?m)^가\.\s*신청인의\s*주장", r"(?m)^나\.\s*피신청인의\s*주장").strip(),
        "피신청인_주장": between(r"(?m)^나\.\s*피신청인의\s*주장", r"(?m)^3\.\s*위원회\s*판단").strip(),
        "위원회_판단": between(r"(?m)^3\.\s*위원회\s*판단", r"(?m)^4\.\s*결론").strip(),
        "결론": between(r"(?m)^4\.\s*결론", r"(?m)^<\s*붙임\s*>").strip(),
        "붙임": between(r"(?m)^<\s*붙임\s*>", r"(?m)^<\s*별첨\s*>").strip(),
    }


# =========================================================================== 2. 조항 추출(4-2, 파일럿 함수 + 4-8 보완)
ART = re.compile(
    r"제\s?(\d+)\s?조(?:의\s?\d+)?"
    r"\s*(?:[\(（\[【]\s*([^\)）\]】\n]{1,40})\s*[\)）\]】])?"
    r"\s*(?:(제\s?\d+\s?항)|([①-⑳󰊱󰊲󰊳󰊴]))?"
    r"\s*(?:(제\s?\d+\s?호))?"
)
CLAUSE_MARK = re.compile(r"약관|특약")  # 4-8 ②: '특약' 포함
LAW_IN_CLAUSE_WORD = re.compile(r"약관의\s?규제에\s?관한\s?법률|약관규제법|약관의\s?규제\s?등에\s?관한\s?법률|약관의규제등에관한법률")
LAW_MARK = re.compile(r"법률|시행령|시행규칙|동\s?법|같은\s?법|[가-힣]+법(?=[\s」｣』\)\]]|제)|요령|훈령|고시|세칙|규정\s*제")
WINDOW = 60


def is_clause_ref(text, start):
    w0 = max(0, start - WINDOW)
    w = text[w0:start]
    law_spans = [m.span() for m in LAW_MARK.finditer(w)] + [m.span() for m in LAW_IN_CLAUSE_WORD.finditer(w)]
    law_end = max([e for _, e in law_spans], default=-1)
    cl_end, via = -1, ""
    for m in CLAUSE_MARK.finditer(w):
        inside_law = any(a <= m.start() < b for a, b in law_spans)
        if not inside_law and m.end() > cl_end:
            cl_end, via = m.end(), m.group(0)
    if cl_end > law_end and cl_end >= 0:
        return True, via
    return False, ""


CIRC = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
ALT = "󰊱󰊲󰊳󰊴"


def first_clause(text):
    law_n = 0
    for m in ART.finditer(text):
        ok, via = is_clause_ref(text, m.start())
        if not ok:
            law_n += 1
            continue
        n = m.group(1)
        title = (m.group(2) or "").strip()
        hang, ho = m.group(3) or m.group(4), m.group(5)
        ref, level = f"제{n}조", "조"
        if hang:
            if hang.startswith("제"):
                hnum = re.sub(r"\D", "", hang)
            elif hang in CIRC:
                hnum = str(CIRC.index(hang) + 1)
            else:
                hnum = str(ALT.index(hang) + 1)
            ref += f" 제{hnum}항"
            level = "항"
        if ho:
            ref += f" 제{re.sub(r'[^0-9]', '', ho)}호"
            level = "호"
        ctx0 = max(0, m.start() - 60)
        return dict(clause_ref=ref, art_no=int(n), clause_title=title, clause_level=level, mark_via=via,
                    mention=text[ctx0:m.end() + 60].replace("\n", " ")), law_n
    return None, law_n


def section(text, start_pats, end_pats):
    st = None
    for p in start_pats:
        m = re.search(p, text)
        if m:
            st = m.end()
            break
    if st is None:
        return ""
    en = len(text)
    for p in end_pats:
        m = re.search(p, text[st:])
        if m:
            en = min(en, st + m.start())
    return text[st:en]


def facts_section(text):
    return section(text, [r"1\.\s*기초\s*사실", r"가\.\s*사실관계", r"○\s*사실관계", r"가\.\s*다툼이\s*없는\s*사실"],
                   [r"\n\s*2\.\s*당사자\s*주장", r"\n\s*나\.\s*당사자", r"\n\s*○\s*당사자"])


LAW_HEAD = re.compile(
    r"^\s*(?:□|■|\[|<|·)?\s*(?:관련\s?법규|관계\s?법규|관련\s?법령|舊?[가-힣ㆍ·\s]{0,20}(?:법|법률|시행령|시행규칙)\s*(?:\(|\]|>|$|제\s?\d+\s?조))")


def strip_law_segments(att):
    """붙임에서 법령 부분(관련 법규, □ 상법, 의료법 제3조… 등)을 뺀다(4-2 ③). 약관 머리줄이 나오면 다시 넣는다."""
    out, in_law = [], False
    for ln in att.split("\n"):
        st = ln.strip()
        if LAW_HEAD.match(st) and "약관" not in st:
            in_law = True
            continue
        if in_law and (re.match(r"^\s*(?:□|<|\[|【)", st) and ("약관" in st or "붙임" in st)):
            in_law = False
        if re.match(r"^<\s*별첨\s*>", st):
            in_law = True
            continue
        if not in_law:
            out.append(ln)
    return "\n".join(out)


def article_block(src, art_no):
    pat = re.compile(rf"(?m)^\s*(?:[□○◦ᄋ·\-\*■◇◆▢]\s*)?제\s?{art_no}\s?조(?!\s*의)")
    m = pat.search(src)
    if not m:
        return ""
    rest = src[m.start():]
    nl = rest.find("\n")
    nl = len(rest) if nl < 0 else nl
    nxt = re.search(r"(?m)^\s*(?:[□○◦ᄋ·■◇◆▢]\s*)?(제\s?\d+\s?조(?:의\s?\d+)?\s*(?:[\(（【\[]|$)|\[|<|【|※|상법|형법|관련\s?법규|관계\s?법규|\s*□|[가-힣 ]*법\s*$|<\s*상법)",
                    rest[nl + 1:])
    blk = rest[: nl + 1 + nxt.start()] if nxt else rest
    keep = [ln for ln in blk.split("\n") if not (re.search(r"[^니]다\.\s*$", ln) and len(ln) > 30)]
    return "\n".join(keep).strip()


def article_title(src, art_no):
    m = re.search(rf"(?m)^\s*(?:□\s*)?제\s?{art_no}\s?조\s*[\(（\[【]\s*([^\)）\]】\n]{{1,40}})\s*[\)）\]】]", src)
    return m.group(1).strip() if m else ""


def cut_level(blk, level, ref):
    if level == "조" or not blk:
        return blk
    hm = re.search(r"제(\d+)항", ref)
    hom = re.search(r"제(\d+)호", ref)
    out = blk
    if hm:
        k = int(hm.group(1))
        sym = [CIRC[k - 1]] + ([ALT[k - 1]] if k <= 4 else [])
        pos = min([out.find(c) for c in sym if out.find(c) >= 0], default=-1)
        if pos >= 0:
            nxt_syms = [CIRC[k]] + ([ALT[k]] if k < 4 else [])
            nposs = [out.find(c, pos + 1) for c in nxt_syms if out.find(c, pos + 1) >= 0]
            out = out[pos: min(nposs)] if nposs else out[pos:]
        elif "" in out and k == 1:
            # pdf(제2022-5호): 항 기호가 사용자 정의 글자()로 변환됨. 첫 항만 안전하게 자를 수 있다.
            parts = re.split(r"|\n□\d", out)
            out = parts[1] if len(parts) > 1 else out
    if hom:
        k = int(hom.group(1))
        m = re.search(rf"(?m)^\s*{k}\.\s", out)
        if m:
            n2 = re.search(rf"(?m)^\s*{k + 1}\.\s", out[m.end():])
            out = out[m.start(): m.end() + n2.start()] if n2 else out[m.start():]
    return out.strip()


def quoted_text(sentence):
    qs = re.findall(r"[“\"]([^”\"]{20,})[”\"]", sentence)
    qs += [q for q in re.findall(r"『([^』]{20,})』", sentence)]
    qs += [q for q in re.findall(r"‘([^’]{20,})’", sentence) if re.search(r"(니다|한다|된다)\.?\s*$", q)]
    qs += [q for q in re.findall(r"「([^」]{20,})」", sentence) if re.search(r"(니다|한다|된다|있다|다)\.?\s*$", q)]
    if not qs:
        return ""
    # 문장 안에서 가장 먼저 나오는 인용
    return sorted(qs, key=lambda q: sentence.find(q))[0].strip()


# 약관 문체(…합니다/드립니다)로 끝나고 '…고 규정/정하고' 같은 전달 표현이 없으면 조문을 그대로 옮겨 적은 것으로 본다
VERBATIM_END = re.compile(r"(니다|니다\s*\.)\s*[\.。]?\s*$")
REPORTING = re.compile(r"(고|라고|다고|함을|도록|것으로)\s?(규정|정하|정한|명시|되어)|에 의하면|에 따르면|에서는|에는,")


SUMMARY = re.compile(r"에 의하면|규정하고 있|정하고 있|라고 규정|도록 정하")


def clause_text_for(att, text, judg, cl):
    """반환: (clause_text, clause_text_article, clause_text_source, text_form)"""
    n, level, ref = cl["art_no"], cl["clause_level"], cl["clause_ref"]
    for src, srcname in [(strip_law_segments(att), "붙임"), (facts_section(text), "본문 인용"), (judg, "본문 인용")]:
        if not src:
            continue
        blk = article_block(src, n)
        if blk:
            if not cl["clause_title"]:
                cl["clause_title"] = article_title(src, n)
            form = "풀어 쓴 서술" if SUMMARY.search(blk[:200]) else "조문 그대로"
            return cut_level(blk, level, ref), blk, srcname, form
    m = None
    for mm in ART.finditer(judg):
        if int(mm.group(1)) == n and is_clause_ref(judg, mm.start())[0]:
            m = mm
            break
    if m:
        st = judg.rfind("\n", 0, m.start()) + 1
        en_m = re.search(r"(규정하고 있음|규정하고 있으며|정하고 있고|정하고 있으며|규정되어 있음|있음\.|하고 있는 바,|\n□|\n◦|\n○)",
                         judg[m.end():])
        en = m.end() + en_m.end() if en_m else min(len(judg), m.end() + 400)
        sent = re.sub(r"[\s◦○□]+$", "", judg[st:en].strip())
        q = quoted_text(sent)
        if not q:
            seg = judg[m.start():en].strip()
            seg_lines = re.split(r"\n(?=\s*[□○◦ᄋ]\s)", judg[m.start():])
            seg2 = seg_lines[0].strip() if seg_lines else seg
            fs = re.search(r"니다\.?|[^니]다\.", seg2)  # 언급 뒤 첫 문장 끝
            if fs and fs.group(0).startswith("니다") and not REPORTING.search(seg2[: fs.start()]):
                return cut_level(seg2, level, ref), seg2, "본문 인용", "조문 그대로"
        if q:
            # 따옴표 인용은 언급된 단위(조/항/호)의 문구다. 조 전체 문구는 조 단위일 때만 같다.
            return q, (q if level == "조" else ""), "본문 인용", "따옴표 인용"
        return sent, (sent if level == "조" else ""), "본문 인용", "풀어 쓴 서술"
    return "", "", "", ""


# 4-8 ③: 판단이 조 번호 없이 별칭·별표로 가리키는 경우(사람 연결 대상) 찾기
ALIAS = re.compile(r"이 사건\s?(면책\s?사유|면책\s?조항|면책\s?약관|약관\s?조항|약관\s?규정|조항)(?!\s*제\s?\d)|별표\s?\d*|[가-힣]*분류표|면책\s?조항")


# =========================================================================== 3. 결과 판정(4-1, 4-8 판정표)
GRANT_LISTED = re.compile(r"지급하라|부활하라|환급하라|인정하고|취소하고|취소하라|지급하고")
GRANT_OTHER = re.compile(r"하라|인용한다|확인한다|책임이 있다|지급한다")
PARTIAL_EXPL = re.compile(r"일부\s?인용")
PARTIAL_PHRASE = re.compile(r"(?:하지|되지|아니하|않)[^\s,.]{0,3}\s?않?으나|아니하나|않으나|어려우나|이유가\s?없다고\s?할\s?것이나|이유\s?없다고\s?할\s?것이나")
C_GRANT = re.compile(r"지급하여야|지급함이\s?타당|지급할\s?책임이\s?있|지급책임이\s?(있|존재)|책임이\s?있다고\s?판단|책임은\s?있|책임이\s?있는\s?것으로|"
                     r"지급되어야|원상\s?회복|추가\s?지급|추가로\s?지급|정당하지\s?아니|부당하|부당함|인정함이\s?타당|무효라고|무효이며|무효이므로|"
                     r"보상함이\s?타당|배상할\s?책임이\s?있|취소하고|이유\s?있다|그\s?이유있|이유가\s?충분치\s?못|해지처리를\s?취소|지급하는\s?것이\s?타당|"
                     r"지급되어야\s?할|지급하여야\s?할")
C_DENY = re.compile(r"책임이\s?없|책임은\s?존재하지|존재하지\s?않|지급대상이\s?아니|이유가?\s?없(?:다|으므로|는|음)|"
                    r"(?:처리|조치|것|거절)[은는]\s?(?:타당|정당)|정당하다고|인정될\s?수\s?없|증거가\s?부족|이유가\s?불충분|"
                    r"받아들이기\s?어렵|보기\s?어렵다고\s?판단|보기\s?어렵다|보기\s?어려움|청구를\s?기각|볼\s?수\s?없다고\s?판단|"
                    r"지지\s?아니하|아니라고\s?판단")
# 인정 표현이 부정된 꼴('…책임이 있다고 보기 어려운')은 인정 표현에서 빼고 배척으로 센다
NEG_GRANT = re.compile(r"(?:책임|의무)이?\s?있다고\s?(?:보기|볼\s?수)\s?(?:어려|없)|(?:부당하다고|무효라고|정당하지\s?아니하다고)\s?(?:보기|볼\s?수)\s?(?:어려|없)")


def decide_order(ju):
    """주문(또는 1998년 조정결정사항·각하결정사항) 표현 판정. 반환: (type, cited, flags)"""
    j = re.sub(r"\s+", " ", ju)
    if re.search(r"각하", j):
        return "각하", None, []
    if re.search(r"취하", j):
        return "취하", None, []
    if re.search(r"불성립", j):
        return "조정 불성립", None, []
    has_deny = bool(re.search(r"기각한다|기각함", j))
    has_grant_l = bool(GRANT_LISTED.search(j))
    has_grant_o = bool(re.search(r"피신청인[은는에].*?(하라|확인한다|책임이 있다|지급한다)|인용한다|유효(임|함)을 확인한다|체결되었음을 확인한다", j))
    if has_deny and (has_grant_l or has_grant_o):
        return "이행 명령 + 일부 기각", 1, ["주문에 이행 명령과 기각이 함께 있음 — 일부 인용 여부 사람 확인"]
    if has_deny:
        return "기각", 0, []
    if has_grant_l:
        verbs = re.findall(GRANT_LISTED, j)
        return "이행 명령(" + "+".join(dict.fromkeys(verbs)) + ")", 1, []
    if has_grant_o:
        return "판정표에 없는 인용 표현", 1, ["주문 표현이 판정표 예시에 없음(고객 요구를 들어준 명령으로 보이나 사람 확인)"]
    return "기타", None, ["주문 표현 판정표에 없음"]


def decide_conclusion(gyeol):
    """주문이 없는 옛 결정: 결론 문장으로 판정(4-8). 인정 표현이 하나라도 있으면 1(일부 인용도 1),
    인정·배척이 함께 있으면 일부 인용 확인 표시. 반환: (type, cited, mixed, 근거 문장)"""
    g = re.sub(r"\s+", " ", gyeol)
    g = re.split(r"\(\s*별\s*지\s*\)", g)[0]
    if re.search(r"각하", g):
        m = re.search(r"[^.]*각하[^.]*", g)
        return "결론: 각하", None, False, m.group(0)
    negs = [m.span() for m in NEG_GRANT.finditer(g)]
    g2 = g
    for a, b in negs:
        g2 = g2[:a] + " " * (b - a) + g2[b:]
    gm = list(C_GRANT.finditer(g2))
    dm = list(C_DENY.finditer(g)) + [type("M", (), {"start": lambda self, a=a: a})() for a, _ in negs]
    def sent_at(pos):
        st = max(g.rfind(". ", 0, pos), -1) + 1
        en = g.find(". ", pos)
        return g[st: en + 1 if en >= 0 else len(g)].strip()
    if not gm and not dm:
        return "결론: 판정 불가", None, False, g[-250:]
    if gm:
        return "결론: 지급 인정" + (" (배척 표현도 있음)" if dm else ""), 1, bool(dm), sent_at(gm[-1].start())
    return "결론: 청구 배척", 0, False, sent_at(dm[-1].start())


def last_sentences(t, n=2):
    sents = [x.strip() for x in re.split(r"(?<=[다음함됨])\.\s*", re.sub(r"\s+", " ", t)) if x.strip()]
    return " ".join(sents[-n:])


# =========================================================================== 4. 부정 표현(4-4, 4-8, 4-8-1)
try:
    from kiwipiepy import Kiwi
    kiwi = Kiwi()
except Exception:  # pragma: no cover
    kiwi = None

KW = {
    "explained_duty": re.compile(r"설명\s?의무|명시[·ㆍ]?\s?설명|설명하지\s?않|설명을\s?하지"),
    "ambiguity": re.compile(r"모호|불명확|불분명|명백하지\s?(아니|않)|다의적|작성자\s?불이익|고객에게\s?유리하게"),
}
NEG = {"없", "아니", "않", "못"}
# 4-8 제외 맥락
EXC_CLAIM = re.compile(r"주장하|다투고|다툰다|주장한다|주장함|주장이다|다고\s?하고\s?있|라고\s?하고\s?있|진술하|진술한")
EXC_LAW = re.compile(r"판시|선고|[가-힣]+법\s?제\s?\d+\s?조|법률\s?제\s?\d+\s?조|대법원|판례|판결")
# 소제목·쟁점 문장(4-8 '소제목 줄', 파일럿 보고 7장 3번 '소제목·쟁점 문장'): 결론 문장이 아니다
EXC_HEAD = re.compile(r"^\s*(?:\(?\d{1,2}\)|[가-하]\.|\([가-하]\)|[①-⑳]|[ⅰ-ⅹ]+\)|\d\.)\s")
EXC_ISSUE = re.compile(r"쟁점은|쟁점이|여부라\s?할|여부이다|여부에\s?(대하여|관하여)\s?(살펴|본다)|여부를\s?살펴|여부\s*$")
# 양보·가정 절('…설명하지 않았다고 하여', '…대상이라고 하더라도') 안의 키워드는 위원회 결론이 아니다
CONCESSIVE = re.compile(r"^[^,.]{0,30}?(?:다고|라고|이라고)?\s?(?:하여도|하더라도|더라도|하여|해서)\b|^[^,.]{0,25}?(?:다고|라고)\s?하여|"
                        r"^[^,.]{0,25}?(?:였|했|하|이)?(?:다면|라면)\b|^[^,.]{0,14}?(?:는|은)\s한\s|"
                        r"^[^,.]{0,20}?(?:될|한|하는|된|할)\s?경우")
TERMS_SUBJ = re.compile(r"약관|조항|문언|규정|특약|특별약관|용어|정의|의미|뜻|해석")
CASE_REF = re.compile(r"이 사건|본건|본 건|이건|이 건|동 건|당해|피신청인|신청인|피보험자")
APPLY_NEXT = re.compile(r"(이 사건|본\s?건|이\s?건|동\s?건|동|위|당해)\s?(보험)?\s?(약관|조항|특약|특별약관|규정|사고|보험계약|계약|수술|질병|장해)")
CASE_REF2 = re.compile(r"이 사건|본\s?건|이\s?건|동\s?건")
NONTERMS_DOC = re.compile(r"청약서|증권|안내장|상품설명서|설명서|가입설계서|질문표|질문사항")


def sentences(t):
    out = []
    for line in t.split("\n"):
        out += [x.strip() for x in re.split(r"(?<=[다음함됨임])\.\s+", line) if x.strip()]
    return out


def after_morphs(sent, end):
    tail = sent[end:end + 60]
    if kiwi is None:
        return [], tail
    return [t.form for t in kiwi.tokenize(tail)[:15]], tail


def inside_quote(sent, pos):
    opens = len(re.findall(r"[“\"「『‘]", sent[:pos]))
    closes = len(re.findall(r"[”\"」』’]", sent[:pos]))
    return opens > closes


def judge_kw(var, sent, nxt, m):
    """반환: (값 0/1/2/None, 이유). 0 = 판정에 쓰지 않음(제외 맥락 등)."""
    st = sent.strip()
    if (re.match(r"^\s*[가-하]\.\s", st) or EXC_HEAD.match(st)) and len(st) < 45:
        return 0, "소제목 줄(제외 맥락)"
    if EXC_ISSUE.search(st):
        return 0, "쟁점·소제목 문장(결론 아님, 제외 맥락)"
    if EXC_CLAIM.search(sent):
        return 0, "당사자·설계사 주장 문장(제외 맥락)"
    if inside_quote(sent, m.start()) or re.search(r"니다[.\s]*$", st):
        return 0, "따옴표 안 인용·약관 문체 문장(위원회 결론 아님)"
    forms, tail = after_morphs(sent, m.end())
    if CONCESSIVE.search(sent[m.end():m.end() + 45]):
        return 0, "양보·가정 절 안의 키워드(…다고 하여/하더라도) — 위원회 결론 아님"
    fs = set(forms)
    neg = any(f.startswith(("없", "아니", "않", "못", "어렵", "어려")) for f in fs)  # kiwi는 '아니하'를 한 형태소로 냄
    # 4-8-1: 원칙 문장·법령 조문·판례 인용은 0. 단, 같은 문장이나 다음 문장에서 이 사건에 적용하면 판정에 쓴다.
    law_cite = bool(EXC_LAW.search(sent))
    principle = law_cite or not CASE_REF.search(sent)
    applied = (CASE_REF2.search(sent) if law_cite else False) or APPLY_NEXT.search(nxt or "")
    if principle and not applied:
        return 0, ("법령·판례 인용" if law_cite else "원칙") + " 문장, 같은·다음 문장에서 이 사건에 적용하지 않음(제외 맥락)"
    if var == "explained_duty" and principle:
        return None, "설명의무 원칙·법령 문장을 다음 문장에서 이 사건에 적용 — 위반 인정/불인정 방향은 사람 확인"
    if var == "explained_duty":
        violate = bool(re.search(r"위반|불이행", tail))
        fulfill = bool(re.search(r"이행|다하|설명하였|설명하였다", tail))
        kwd = m.group(0)
        if kwd.startswith("설명하지") or kwd.startswith("설명을"):
            return (1, "키워드 자체가 부정형(설명하지 않/설명을 하지)") if not neg or "않" in kwd else (None, "부정형 키워드 + 뒤 부정")
        if violate and not neg:
            return 1, "뒤에 '위반/불이행', 부정 형태소 없음"
        if violate and neg:
            return 2, "뒤에 '위반' + 부정 형태소"
        if fulfill and neg:
            return 1, "뒤에 '이행/다하' + 부정 형태소"
        if fulfill and not neg:
            return 2, "뒤에 '이행/다하', 부정 형태소 없음"
        return 0, "위반·이행 판단 없음(대상 여부 등, 4-8-1에 따라 0)"
    # ambiguity
    own = re.sub(r"“[^”]*”|\"[^\"]*\"", "", LAW_IN_CLAUSE_WORD.sub("", sent))  # 법령 이름·따옴표 인용을 뺀 위원회 문장
    if NONTERMS_DOC.search(own) and "약관" not in own:
        return 0, "약관이 아닌 문서(청약서·증권·안내장 등)의 불명확(4-8-1에 따라 0)"
    if not TERMS_SUBJ.search(sent[max(0, m.start() - 80): m.end() + 10]):
        return 0, "불명확의 대상이 약관이 아님(사실관계·인과관계 등, 4-8-1에 따라 0)"
    kwd = m.group(0)
    if re.match(r"명백하지|다의적|작성자|고객에게", kwd):
        return 1, "키워드 자체가 모호함 인정형" + ("(원칙 문장, 다음 문장에서 이 사건 조항에 적용)" if principle else "")
    if neg:
        return 2, "뒤에 부정 형태소(없/아니/않/못/어렵)"
    return 1, "뒤에 부정 형태소 없음"


def soguel_part(judg):
    m = None
    for mm in re.finditer(r"(?m)^\s*(?:[가-하라마바사]\.|\(\d\)|\d\.)?\s*(소\s?결|결\s?론)\s*$", judg):
        m = mm
    return judg[m.start():] if m else ""


def neg_label(case_text, judg, concl):
    """사건 단위 explained_duty, ambiguity. 반환 dict(var → (값, needs_review, evidence, rows))"""
    res = {}
    full = judg + "\n" + concl
    sl = sentences(full)
    sog = soguel_part(judg) + "\n" + concl
    sog_set = set(sentences(sog)) if sog.strip() else set()
    for var, rx in KW.items():
        rows = []
        for i, sent in enumerate(sl):
            nxt = sl[i + 1] if i + 1 < len(sl) else ""
            for m in rx.finditer(sent):
                v, why = judge_kw(var, sent, nxt, m)
                a = max(0, m.start() - 80)
                rows.append(dict(val=v, why=why, in_sog=sent in sog_set,
                                 excerpt=sent[a:m.end() + 100].replace("\n", " ")))
        dec_rows = [r for r in rows if r["val"] in (1, 2)]
        sog_rows = [r for r in dec_rows if r["in_sog"]]
        use = sog_rows if sog_rows else dec_rows
        none_rows = [r for r in rows if r["val"] is None]
        if any(r["val"] == 1 for r in use):
            val = 1
            ev = next(r for r in use if r["val"] == 1)
        elif any(r["val"] == 2 for r in use):
            val = 2
            ev = next(r for r in use if r["val"] == 2)
        else:
            val, ev = 0, None
        nr = bool(none_rows) and val != 1
        if sog_rows and any(r["val"] != sog_rows[0]["val"] for r in dec_rows):
            note = "소결과 앞 문단 판정이 달라 소결을 따름"
        else:
            note = ""
        evid = ""
        if ev:
            evid = ev["excerpt"]
        elif none_rows:
            evid = none_rows[0]["excerpt"]
        res[var] = dict(val=val, nr=nr, evidence=evid, n_rows=len(rows), note=note,
                        none_reason=(none_rows[0]["why"] if none_rows else ""))
    return res


# =========================================================================== 5. 자동차보험(4-6-2)
AUTO_TERMS = re.compile(r"자동차보험|자동차종합보험|대인배상|대물배상|자기신체사고|무보험자동차|무보험차|자동차손해배상|자배법|자기차량손해|자동차취급업자|지불보증")
PROD_LINE = re.compile(r"[^\n]*(?:보험종목|보험상품명|보험\s?종\s?목)[^\n]*(?:\n[^\n]{0,60}){0,2}|[^\n]{0,60}(?:보험(?:계약)?(?:을|에)\s?(?:체결|가입))[^\n]{0,30}")
AUTO_PROD = re.compile(r"(?:개인용|업무용|영업용|이륜)?\s?(?:[◎○◯*☐\s]*)자동차\s?(?:종합)?\s?보험|자동차취급업자|취급업자\s?(?:종합)?보험|대리운전업자\s?특별약관")
# 본문을 읽고 판정한 건(근거 문장은 아래 문자열이 실제 본문에 있는지 코드로 확인한다).
# 값: (is_auto, needs_review, 근거 문자열, 메모)
AUTO_MANUAL = {
    "2000-9": (1, 0, "개인용자동차보험계약이 체결되어 있음", "기초 사실: 개인용자동차보험(대인배상 등)"),
    "2003-5": (1, 0, "보험종목 : 업무용자동차보험", ""),
    "2003-10": (1, 0, "보험종목 : ◎◎자동차보험", ""),
    "2010-56": (1, 0, "대인배상Ⅰ", "기초 사실 표: ☐☐ 자동차보험, 대인배상Ⅰ·Ⅱ"),
    "2010-67": (1, 0, "업무용 자동차보험", ""),
    "2010-70": (1, 0, "개인용 자동차보험", ""),
    "2012-18": (1, 0, "자동차보험 자기신체사고 담보대상에 해당하는지 여부", "안건명·판단: 자동차보험 자기신체사고 담보"),
    "2016-7": (1, 0, "자동차보험", "기초 사실 표: ** 자동차보험, 자동차상해 특별약관"),
    "2017-5": (1, 0, "자동차종합보험계약을 체결하였다", ""),
    "2017-6": (1, 0, "업무용자동차 보험을 체결하였다", ""),
    "2017-7": (1, 0, "자동차보험(이하 ‘이 사건 보험계약’이라 한다)을 체결하였으며", "개인용 자동차보험"),
    "2017-15": (1, 0, "자기차량손해담보", "쟁점 담보가 자동차보험 자기차량손해"),
    "2018-1": (1, 0, "영업용자동차보험계약", ""),
    "2007-97": (1, 1, "보험종목 : 자동차취급업자 종합보험", "자동차취급업자종합보험(대리운전) — 4-6-2 예시 종목에 직접 없음, 사람 확인"),
    "2012-15": (1, 1, "대리운전업자특별약관", "취급업자보험 대리운전업자특약(대인배상2·대물·자기신체·자기차량) — 사람 확인"),
    "2015-15": (1, 1, "자동차취급업자종합보험 가입", "자동차취급업자종합보험(대리운전) — 사람 확인"),
    "2002-12": (1, 1, "치료비를 지불보증함이 타당함", "보험 종목 기재 없음. 쟁점이 차량 충돌 과실·치료비 지불보증(자동차보험 대인배상 성격) — 사람 확인"),
    "2002-51": (1, 1, "#1차량 운전자의 일방과실에 기인한 사고이므로 보상책임이 없음", "보험 종목 기재 없음. 쟁점이 차량 충돌 과실(자동차보험 대인배상 성격) — 사람 확인"),
    # 포함(is_auto = 0): 교통사고라도 상해·생명·운전자·실손·배상책임 보험
    "2000-38": (0, 0, "교통안전보험", "4-8-1 사람 판정: 생명보험사 교통안전보험"),
    "2022-5": (0, 0, "단체상해보험", "4-8-1 사람 판정: 단체상해보험 형사합의금 특약(운전자보험 성격)"),
    "2026-3": (0, 0, "보험계약을 체결하였다", "운전자보험 성격 형사합의금 특약(4-6-2 포함 예)"),
    "2026-4": (0, 0, "보험계약을 체결하였다", "운전자보험 성격 형사합의금 특약(4-6-2 포함 예)"),
    "2026-5": (0, 0, "보험계약을 체결하였다", "운전자보험 성격 형사합의금 특약(4-6-2 포함 예)"),
    "2020-9": (0, 0, "실손", "실손의료보험의 보상 범위(4-6-2 포함 예)"),
    "1998-38": (0, 0, "안전보험", "생명보험사 안전보험의 무보험차량 사망보험금(상해·생명보험)"),
    "2009-6": (0, 0, "보험종목 : 「무배당 OO라이프원더풀보험」", "운전중 비용손해(형사합의지원금) 특약 — 운전자보험 성격"),
    "2010-13": (0, 0, "형사합의금지원(타인사망) 담보", "운전자보험 성격"),
    "2003-12": (0, 0, "운전자보험", ""),
    "2003-18": (0, 0, "장기상해운전자보험", ""),
    "2017-4": (0, 0, "형사합의지원금 담보 특별약관", "운전자보험 성격"),
    "2017-11": (0, 0, "차량정비업자배상책임 특별약관", "배상책임보험(자동차보험 아님)"),
    "2006-85": (0, 0, "영업배상책임보험", ""),
    "2002-7": (0, 0, "피보험시설 구내의 인접도로", "시설 배상책임 특약(자동차보험 아님)"),
    "2010-69": (0, 0, "질병입원의료비", "질병보험의 입원의료비"),
}


def auto_check(key, text, cand):
    if key in AUTO_MANUAL:
        v, nr, ev, memo = AUTO_MANUAL[key]
        flat = re.sub(r"\s+", "", text)
        if re.sub(r"\s+", "", ev) not in flat:
            return v, 1, f"(근거 문자열 확인 실패) {ev}", "근거 문자열이 본문에 없음 — 사람 확인"
        i = flat.find(re.sub(r"\s+", "", ev))
        return v, nr, ev, memo or "본문 확인"
    hits = AUTO_TERMS.findall(text)
    fac = facts_section(text) or text[:3000]
    prods = [one_line(p, 120) for p in PROD_LINE.findall(fac)]
    prod_auto = [p for p in prods if AUTO_PROD.search(p) and "운전자" not in p]
    if prod_auto:
        return 1, 1, prod_auto[0], "기초 사실의 보험 종목에 자동차보험 표지 — 사람 확인(수동 표에 없는 건)"
    if cand:
        return 0, 1, (prods[0] if prods else ""), "제목 후보(auto_candidate)인데 본문 보험 종목이 자동차보험 아님 — 사람 확인"
    if hits:
        return 0, 0, (prods[0] if prods else ""), "보험 종목이 자동차보험 아님(본문에 자동차 관련어는 법령·비교 서술 등으로 등장)"
    return 0, 0, (prods[0] if prods else ""), "본문에 자동차보험 담보 표지 없음"


# =========================================================================== 6. 쟁점 유형·주제(4-8)
def issue_from(textv):
    t = re.sub(r"\s+", "", textv or "")
    if re.search(r"보상하지(아니하|않)|지급하지(아니하|않)|면책", t):
        return "면책"
    if re.search(r"알릴의무|고지|설명의무", t):
        return "고지·설명"
    return None


TOPICS = [("계약 전 알릴 의무", r"알릴|고지"), ("면책", r"보상하지|지급하지|면책"), ("계약 해지·부활", r"해지|부활|효력"),
          ("보험기간·갱신", r"보험기간|갱신"), ("장해", r"장해"), ("수술·입원 정의", r"수술|입원"),
          ("질병 정의", r"암|질환|진단"), ("재해·상해 정의", r"재해|상해|사고"), ("보험금 지급사유", r"지급사유|보상하는")]


def topic_of(title, agenda):
    base = title if title else agenda
    t = re.sub(r"[\s\(\)（）\[\]【】<>]", "", base or "")
    for name, rx in TOPICS:
        if re.search(rx, t):
            return name, ("조 제목" if title else "안건명")
    return "기타", ("조 제목" if title else "안건명")


# =========================================================================== 7. 실행
enr_by = enr.set_index("nttId")
pilot_ntt = set(pilot["nttId"])
PILOT_HUMAN = {"2006-3": (0, 1), "2017-18": (0, 0), "2021-16": (1, 0), "2017-2": (0, 1), "2026-9": (0, 0)}  # 4-8-1

rows, review = [], []


def add_rev(key, item, why, ev=""):
    review.append(dict(case_key=key, 항목=item, 이유=why, 근거_문장=one_line(ev, 400)))


for _, r in dec.iterrows():
    key, key_note = case_key_of(r)
    ntt = int(r["nttId"])
    e = enr_by.loc[ntt] if ntt in enr_by.index else None
    err = s(r["오류"])
    title = s(e["title"]) if e is not None else ""
    base = dict(case_key=key, nttId=ntt, title=title, case_key_note=key_note, pilot=int(ntt in pilot_ntt),
                site_auto=int(e["site_auto"]) if e is not None else 0,
                auto_candidate=int(e["auto_candidate"]) if e is not None else 0, reg_date=s(e["reg_date"]) if e is not None else "")
    # 결정일·연도(4-6-1): 조정일자(hwp) → 조정번호 연도 → 등록일 연도(needs_review)
    nr_items = []
    if s(r["조정일자"]):
        dd, yr, basis = s(r["조정일자"]), int(s(r["조정일자"])[:4]), "조정일자(hwp)"
    elif re.match(r"^\d{4}-\d+$", key):
        dd, yr, basis = "", int(key[:4]), "조정번호 연도"
    elif e is not None and pd.notna(e["year"]):
        dd, yr, basis = "", int(e["year"]), "fss_details year"
    else:
        dd, yr, basis = "", int(s(e["reg_date"])[:4]) if e is not None else None, "등록일 연도"
        nr_items.append(("결정일", "결정일·조정번호 연도 없음 → 등록일 연도", ""))
    period = "~2009" if yr <= 2009 else ("2010-2016" if yr <= 2016 else "2017-2026")
    base.update(decision_date=dd, decision_year=yr, date_basis=basis, period=period)
    if err:
        reason = "지원하지 않는 형식" if "지원하지 않는 형식" in err else ("배포용 문서" if "배포용" in err else "변환 실패")
        base.update(converted=0, exclude_reason=reason, needs_review=0, is_auto="",
                    evidence_snippet="", auto_evidence="본문 없음(판정하지 않음)")
        rows.append(base)
        continue
    txt_path = os.path.join(TEXTS, os.path.splitext(s(r["파일명"]))[0] + ".txt")
    text = open(txt_path, encoding="utf-8").read()
    fields = {c: s(r[c]) for c in ["주문", "신청취지", "당사자_주장", "신청인_주장", "피신청인_주장", "위원회_판단", "결론", "붙임"]}
    pdf_note = ""
    if s(r["형식"]) == "pdf":
        text, nfn = clean_pdf_text(text)
        fields.update(split_pdf_sections(text))
        pdf_note = f"pdf: 쪽 번호 줄·각주 {nfn}개 지우고 구역 다시 나눔"
    judg, concl = fields["위원회_판단"], fields["결론"]
    judg_note = s(r["위원회_판단_추출"])
    if not judg.strip():
        judg = section(text, [r"쟁점사항에\s*대한\s*검토", r"위원회\s*판단", r"판\s*단"], [r"\n\s*\d\.\s*결\s*론"]) or text[int(len(text) * 0.5):]
        judg_note = "추정(위원회_판단 없음 → '쟁점사항에 대한 검토' 이후)"
    if judg_note.startswith("추정"):
        nr_items.append(("판단 범위", f"위원회_판단 범위 추정({judg_note}) — 사람 확인", judg[:200]))
    # ---------- 결과
    ju = fields["주문"].strip()
    order_src = "주문"
    if not ju:
        m = re.search(r"\n\s*\d\.\s*((?:조\s*정|각\s*하)\s*결\s*정\s*사\s*항)\s*\n(.*?)\n\s*\d\.\s", text, re.S)
        if m:
            ju, order_src = m.group(2).strip(), m.group(1).replace(" ", "") + "(1998년 결정의 주문 항목)"
    flags, partial, partial_hint = [], 0, 0
    if ju:
        otype, cited, ofl = decide_order(ju)
        flags += ofl
        ev = f"[{order_src}] " + one_line(ju, 250)
        outcome_raw = one_line(ju, 300)
    else:
        src_txt = concl
        cl_src = "결론"
        if not src_txt.strip():
            m = re.search(r"\[(인용|기각|각하)결정\s*이유\]", text)
            src_txt = (f"[{m.group(1)}결정 이유] " if m else "") + last_sentences(judg, 2)
            cl_src = "판단 마지막 문장(결론 항목 없음)"
        otype, cited, mixed, csent = decide_conclusion(src_txt)
        if src_txt.startswith("[인용결정"):
            otype, cited, mixed, csent = "결론: 인용결정 이유('[인용결정 이유]' 머리말)", 1, False, src_txt[:200]
        ju_m = re.search(r"[^.。\n]*주문과\s?같이[^.。\n]*", text)
        ev = f"[{cl_src}, 주문 없음] " + one_line(csent, 250) + (f" / [이에 주문과 같이] {one_line(ju_m.group(0), 120)}" if ju_m else "")
        outcome_raw = one_line(csent, 300)
        flags.append(f"주문 없음 → {cl_src}으로 판정")
        if mixed:
            flags.append("결론에 인정·배척 표현이 함께 있음 — 일부 인용 여부 사람 확인")
    if otype in ("각하", "취하", "조정 불성립", "결론: 각하"):
        cited = None
        reason_merit = "각하" if "각하" in otype else otype
        if order_src.startswith("각하결정사항") or (not fields["주문"].strip() and re.search(r"이유가?\s?없|이유\s?없어|불충분|충분치\s?못|증거가\s?부족", concl + judg[-600:])):
            nr_items.append(("cited", "옛 결정의 '각하'가 이유 판단 뒤 청구 배척 뜻으로 쓰임(본안 판단일 수 있음). 4-8 판정표대로 제외했으나 사람 확인",
                             ev))
    else:
        reason_merit = ""
    gy = fields["결론"] + " " + fields["주문"]
    if cited == 1:
        if PARTIAL_EXPL.search(gy):
            partial = 1
        elif PARTIAL_PHRASE.search(fields["결론"]):
            mm = PARTIAL_PHRASE.search(fields["결론"])
            nr_items.append(("일부인용", "주문은 이행 명령인데 결론에 일부 배척 표현 — 신청취지와 대조(4-8 (나))",
                             fields["결론"][max(0, mm.start() - 120): mm.end() + 80]))
        chwi = fields["신청취지"]
        if fields["주문"].strip() and chwi.strip() and not re.search(r"주문과\s?같", chwi):
            if re.sub(r"\W", "", chwi)[:80] != re.sub(r"\W", "", fields["주문"])[:80]:
                partial_hint = 1
    for f in flags:
        if f.startswith("주문 없음"):
            nr_items.append(("cited", f, ev))
        elif "일부 인용" in f:
            nr_items.append(("일부인용", f, ev))
        else:
            nr_items.append(("cited", f, ev))
    if cited is None and not reason_merit:
        nr_items.append(("cited", f"결과 판정 불가({otype})", ev))
    # ---------- 조항(판단 기반, 4-8)
    att = fields["붙임"]
    clJ, lawJ = first_clause(judg)
    ct = cta = cts = form = ""
    if clJ:
        ct, cta, cts, form = clause_text_for(att, text, judg, clJ)
    arg = fields["당사자_주장"] or (fields["신청인_주장"] + "\n" + fields["피신청인_주장"])
    clA, lawA = first_clause(arg)
    ctA = ctaA = ctsA = formA = ""
    if clA:
        ctA, ctaA, ctsA, formA = clause_text_for(att, text, judg, clA)
    alias_hit = ""
    if not clJ:
        am = ALIAS.search(judg)
        if am and (re.search(r"제\s?\d+\s?조", att) or re.search(r"제\s?\d+\s?조", facts_section(text)) or re.search(r"별표|분류표", att + judg)):
            alias_hit = judg[max(0, am.start() - 80): am.end() + 80]
            nr_items.append(("수동 연결", f"판단이 조 번호 없이 별칭·별표('{am.group(0)}')로 조항을 가리킴. 붙임·기초 사실의 조문과 사람이 연결(4-8 ③)",
                             alias_hit))
    # ---------- 자동차
    is_auto, auto_nr, auto_ev, auto_memo = auto_check(key, text, base["auto_candidate"] == 1)
    if auto_nr:
        nr_items.append(("is_auto", auto_memo, auto_ev))
    # ---------- 부정 표현
    neg = neg_label(text, judg, concl)
    ed, am_ = neg["explained_duty"]["val"], neg["ambiguity"]["val"]
    ed_ev, am_ev = neg["explained_duty"]["evidence"], neg["ambiguity"]["evidence"]
    neg_src = "자동(4-8 규칙)"
    if key in PILOT_HUMAN:
        ed_auto, am_auto = ed, am_
        ed, am_ = PILOT_HUMAN[key]
        neg_src = f"4-8-1 사람 판정(자동 결과 ed={ed_auto}, amb={am_auto})"
    else:
        if neg["explained_duty"]["nr"]:
            nr_items.append(("explained_duty", f"판정 불가 문장 있음({neg['explained_duty']['none_reason']})", ed_ev))
        if neg["ambiguity"]["nr"]:
            nr_items.append(("ambiguity", f"판정 불가 문장 있음({neg['ambiguity']['none_reason']})", am_ev))
    # ---------- 쟁점 유형·주제
    ctitle = clJ["clause_title"] if clJ else ""
    it = issue_from(s(r["안건명"]))
    it_src = "안건명"
    if not it:
        it = issue_from(ctitle)
        it_src = "조 제목"
    if not it:
        it, it_src = "보상범위·정의", "기본값"
    topic, topic_src = topic_of(re.sub(r"\s+", "", ctitle), s(r["안건명"]))
    # ---------- 제외 사유(우선순위: 형식 → 중복 → 자동차 → 본안 아님 → 조항)
    if is_auto == 1:
        exr = "자동차보험"
    elif reason_merit:
        exr = f"본안 아님({reason_merit})"
    elif not clJ:
        exr = "조항 미추출"
    elif not ct:
        exr = "조항 문구 없음"
    elif form == "풀어 쓴 서술":
        exr = "풀어 쓴 서술"
    else:
        exr = ""
    if not clA:
        exrA = "조항 미추출"
    elif not ctA:
        exrA = "조항 문구 없음"
    elif formA == "풀어 쓴 서술":
        exrA = "풀어 쓴 서술"
    else:
        exrA = ""
    base.update(
        converted=1, is_auto=is_auto, outcome_raw=outcome_raw, outcome_type=otype, outcome_src=order_src if fields["주문"].strip() or order_src != "주문" else "결론",
        cited=cited, partial=partial if cited == 1 else (0 if cited == 0 else ""), partial_hint=partial_hint,
        clause_ref=clJ["clause_ref"] if clJ else "", clause_title=ctitle, clause_level=clJ["clause_level"] if clJ else "",
        clause_source="판단" if clJ else "", clause_text_source=cts, clause_text_form=form, clause_text=ct,
        clause_text_article=cta, clause_mark_via=clJ["mark_via"] if clJ else "",
        clause_evidence=one_line(clJ["mention"], 200) if clJ else (one_line(alias_hit, 200) if alias_hit else ""),
        arg_clause_ref=clA["clause_ref"] if clA else "", arg_clause_title=clA["clause_title"] if clA else "",
        arg_clause_level=clA["clause_level"] if clA else "", arg_clause_text_source=ctsA, arg_clause_text_form=formA,
        arg_clause_text=ctA, arg_clause_text_article=ctaA, arg_exclude_reason=exrA,
        issue_type=it, issue_type_source=it_src, topic=topic, topic_source=topic_src,
        explained_duty=ed, ambiguity=am_, neg_source=neg_src, explained_duty_evidence=one_line(ed_ev, 300),
        ambiguity_evidence=one_line(am_ev, 300), auto_evidence=one_line(auto_ev, 200), auto_memo=auto_memo,
        exclude_reason=exr, evidence_snippet=ev, judgment_extraction=judg_note, pdf_note=pdf_note,
        law_refs_skipped_judgment=lawJ,
    )
    for it_, why, evv in nr_items:
        add_rev(key, it_, why, evv)
    base["needs_review"] = int(bool(nr_items))
    base["review_items"] = "; ".join(dict.fromkeys(i for i, _, _ in nr_items))
    rows.append(base)

C = pd.DataFrame(rows)

# ---------- 중복(4-6): 같은 case_key는 하나만. 조정일자가 있는 행 → 먼저 등록된 행을 남긴다.
# 변환 안 된 행(배포용·tif)은 자기 제외 사유를 그대로 두고, 같은 번호의 변환된 행이 있으면 dup_of_nttId만 적는다.
C["_has_date"] = (C["decision_date"].fillna("") != "").astype(int)
C = C.sort_values(["case_key", "converted", "_has_date", "reg_date"], ascending=[True, False, False, True])
dup = C.duplicated("case_key", keep="first")
for i in C[dup].index:
    keep = C[(C["case_key"] == C.at[i, "case_key"]) & ~dup].iloc[0]
    C.at[i, "dup_of_nttId"] = keep["nttId"]
    if C.at[i, "converted"] == 1:
        C.at[i, "exclude_reason"] = "중복"
C = C.drop(columns="_has_date")

# ---------- 게시물 단위로 decisions.csv에 없는 83건(결정례 아님 2, 사이트 분류 자동차보험 81)
extra = []
for _, e in enr[~enr["nttId"].isin(dec["nttId"])].iterrows():
    if int(e.get("is_casebook", 0) or 0) == 1 or "사례집" in s(e["title"]):
        exr, ev = "결정례 아님", "제목에 '사례집'(4-6-1)"
    elif int(e["site_auto"]) == 1:
        exr, ev = "자동차보험", "사이트 분류 '자동차보험' — 첨부를 받지 않아 본문 판정 못 함(미확인)"
    else:
        exr, ev = "미수집", "decisions.csv에 없음"
    yr = int(e["year"]) if pd.notna(e["year"]) else int(s(e["reg_date"])[:4])
    m = re.search(r"(\d{4})-(\d+)", s(e["decision_no"]))
    extra.append(dict(case_key=f"nttId{int(e['nttId'])}", nttId=int(e["nttId"]), title=s(e["title"]), converted=0,
                      decision_date="", decision_year=yr, date_basis=f"fss_details {s(e['year_source'])}",
                      period="~2009" if yr <= 2009 else ("2010-2016" if yr <= 2016 else "2017-2026"),
                      site_auto=int(e["site_auto"]), auto_candidate=int(e["auto_candidate"]), pilot=0,
                      is_auto=(1 if exr == "자동차보험" else ""), exclude_reason=exr, needs_review=0,
                      auto_evidence=ev, evidence_snippet="", reg_date=s(e["reg_date"]),
                      post_level_only=1))
C = pd.concat([C, pd.DataFrame(extra)], ignore_index=True)
C["post_level_only"] = C["post_level_only"].fillna(0).astype(int)
C["exclude_reason"] = C["exclude_reason"].fillna("")

# ---------- 개인정보 점검(저장 열): 마스킹되지 않은 '역할어 + 한글 이름' 후보를 찾는다(저장 전 보고용)
ROLE = r"(?:신청인|피신청인|피보험자|계약자|보험계약자|수익자|망인|설계사|모집인|배우자|처|남편|아들|딸|부친|모친)"
NAME_RX = re.compile(ROLE + r"\s*[:：]?\s*([김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구민진나지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모탁국어은편용][가-힣]{1,2})(?=\s*[\(,은는이가의에씨님]|\s)")
COMMON = set("이 사건 이건 이유 이를 이에 이후 이상 이하 이미 이러 이와 이번 이용 이행 이전 이는 정상 정도 정하 정한 정함 주장 주계약 주피 주된 주로 주식 전부 전액 전혀 전체 전에 전후 신청 신고 신체 신의 고지 고의 고객 고려 보험 보상 보장 보고 보아 부담 부분 부활 부당 부지 사망 사고 사실 사유 사건 사이 상대 상해 상속 성립 성인 소유 소송 소멸 손해 수술 수익 수령 원인 원상 원고 유지 유효 유족 인정 인과 인하 일부 일반 일방 임의 장해 장기 재해 지급 지정 진단 차량 차주 차액 채무 최초 최근 측에 하여 하지 한도 한편 해당 해지 현재 현장 황 기간 기재 기존 기초 명시 명의 모집 문의 민법 박탈 반환 방문 배상 백혈 변경 서면 서류 석방 선택 설명 성명 소득 송금 심사 안내 양측 엄격 연금 연락 오해 옥외 왕복 용도 우선 운전 위반 위험 육체 은행 의사 의료 이송 인수 입원 입증 자료 작성 전달 조사 조치 주소 주의 중대 증권 지위 진술 질병 채권 청구 추가 치료 통원 통지 판단 편의 표시 하차 합의 허위 현금 홍보 확인 회사 동의 동생 남편 공제 구상 권리 금액 금원 나머 노동 도로 마련 명백 반면 방법 법률 변제 성질 손실 시점 신뢰 심신 안전 양도 어려 여부 연대 염려 오인 오직 우려 원칙 위로 유리 의무 인식 장소 정당 제출 제한 조건 조정 주택 지체 진행 차이 책임 처리 최고 탁송 판정 평균 피해 한정 함께 해석 허용 현저 홍콩 효력 공동 과실 구체 국내 금지 기록 김씨 내용 노력 단순".split())
priv = []
for col in ["evidence_snippet", "clause_text", "clause_text_article", "explained_duty_evidence", "ambiguity_evidence",
            "auto_evidence", "clause_evidence", "outcome_raw", "arg_clause_text"]:
    if col not in C.columns:
        continue
    for i, v in C[col].fillna("").items():
        for m in NAME_RX.finditer(str(v)):
            nm = m.group(1)
            if nm[:2] in COMMON or nm in COMMON or nm[:1] + nm[1:2] in COMMON:
                continue
            priv.append(dict(row=i, case_key=C.at[i, "case_key"], col=col, cand=m.group(0)))

# ---------- 출력 열
MAIN = ["case_key", "nttId", "decision_date", "period", "title", "is_auto", "outcome_raw", "cited",
        "clause_ref", "clause_title", "clause_level", "clause_source", "clause_text_source", "clause_text",
        "issue_type", "explained_duty", "ambiguity", "exclude_reason", "needs_review", "evidence_snippet"]
ADD = ["partial", "partial_hint", "clause_text_form", "clause_text_article", "topic"]
AUX = ["decision_year", "date_basis", "pilot", "converted", "post_level_only", "case_key_note", "dup_of_nttId",
       "site_auto", "auto_candidate", "auto_evidence", "auto_memo", "outcome_type", "outcome_src",
       "clause_mark_via", "clause_evidence", "issue_type_source", "topic_source",
       "neg_source", "explained_duty_evidence", "ambiguity_evidence",
       "arg_clause_ref", "arg_clause_title", "arg_clause_level", "arg_clause_text_source", "arg_clause_text_form",
       "arg_clause_text", "arg_clause_text_article", "arg_exclude_reason",
       "judgment_extraction", "pdf_note", "review_items"]
for c in MAIN + ADD + AUX:
    if c not in C.columns:
        C[c] = ""
C["needs_review"] = C["needs_review"].fillna(0).astype(int)
C = C.sort_values(["decision_year", "case_key"]).reset_index(drop=True)
C[MAIN + ADD + AUX].to_csv(os.path.join(INTERIM, "cases.csv"), index=False, encoding="utf-8-sig")

# ---------- needs_review.csv
ORDER = {"cited": 0, "일부인용": 1, "수동 연결": 2, "조항": 2, "is_auto": 3, "판단 범위": 4, "결정일": 5,
         "explained_duty": 6, "ambiguity": 7}
R = pd.DataFrame(review)
R = R[R["case_key"].isin(C.loc[C["needs_review"] == 1, "case_key"])]
R["_o"] = R["항목"].map(ORDER).fillna(9)
R = R.sort_values(["_o", "case_key"]).drop(columns="_o")
R.to_csv(os.path.join(INTERIM, "needs_review.csv"), index=False, encoding="utf-8-sig")

# ---------- 대조표본(20) · 평가 시트 표본(25)
INC = C[(C["exclude_reason"] == "")].copy()


def even_sample(pool, n, seed, exclude_keys):
    pool = pool[~pool["case_key"].isin(exclude_keys)]
    sizes = pool["period"].value_counts().reindex(P).fillna(0).astype(int)
    base_n = n // len(P)
    alloc = {p: min(base_n, sizes[p]) for p in P}
    rest = n - sum(alloc.values())
    for p in sizes.sort_values(ascending=False).index:  # 남는 몫은 후보가 많은 구간부터 1건씩
        if rest <= 0:
            break
        if sizes[p] > alloc[p]:
            alloc[p] += 1
            rest -= 1
    picks = [pool[pool["period"] == p].sample(n=alloc[p], random_state=seed) for p in P]
    return pd.concat(picks), alloc


pilot_keys = set(C.loc[C["pilot"] == 1, "case_key"])
CHK, chk_alloc = even_sample(INC, 20, SEED, pilot_keys)
chk_cols = ["case_key", "nttId", "period", "decision_date", "title", "text_file", "outcome_src", "outcome_raw", "evidence_snippet",
            "cited", "partial", "partial_hint", "clause_ref", "clause_title", "clause_level", "clause_text_source",
            "clause_text_form", "clause_evidence", "clause_text", "issue_type", "issue_type_source",
            "explained_duty", "explained_duty_evidence", "ambiguity", "ambiguity_evidence", "is_auto", "auto_evidence",
            "needs_review", "review_items",
            "사람_cited", "사람_issue_type", "사람_explained_duty", "사람_ambiguity", "사람_메모"]
fn_map = dict(zip(dec["nttId"].astype(str) + "|" + dec.apply(lambda x: case_key_of(x)[0], axis=1),
                  "data/interim/texts/" + dec["파일명"].map(lambda f: os.path.splitext(f)[0] + ".txt")))
CHK["text_file"] = (CHK["nttId"].astype(int).astype(str) + "|" + CHK["case_key"]).map(fn_map)
for c in chk_cols:
    if c not in CHK.columns:
        CHK[c] = ""
CHK[chk_cols].to_csv(os.path.join(DOCS, "대조표본.csv"), index=False, encoding="utf-8-sig")
EVAL, eval_alloc = even_sample(INC, 25, SEED, pilot_keys | set(CHK["case_key"]))

# ---------- 난이도 입력(가림)
D = C[C["clause_text"].fillna("") != ""].copy()
D = D.sample(frac=1, random_state=SEED).reset_index(drop=True)
D["diff_id"] = [f"D{i + 1:03d}" for i in range(len(D))]
D["eval_pick"] = D["case_key"].isin(EVAL["case_key"]).astype(int)
DCOLS = ["diff_id", "issue_type", "clause_level", "clause_text_form", "clause_text", "clause_text_article", "eval_pick"]
D[DCOLS].to_csv(os.path.join(INTERIM, "cases_for_difficulty.csv"), index=False, encoding="utf-8-sig")
D[["diff_id", "case_key"]].to_csv(os.path.join(INTERIM, "difficulty_id_map.csv"), index=False, encoding="utf-8-sig")

# =========================================================================== 표준출력
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 120)
N = len(C)
print("== 0. 행 수", N, "(decisions.csv", len(dec), "+ 게시물만", len(extra), ")  게시물 수", C["nttId"].nunique())
print("case_key 정정:", C.loc[C["case_key_note"].fillna("").str.contains("≠"), ["nttId", "case_key", "case_key_note"]].to_string(index=False))
print("\n== 1. 제외 사유")
er = C["exclude_reason"].replace("", "(분석 포함)").value_counts()
print(er.to_string())
print("합계 확인:", N, "=", int((C["exclude_reason"] == "").sum()), "+", int((C["exclude_reason"] != "").sum()))
inc = C[C["exclude_reason"] == ""]
print("\n== 2. 분석 포함", len(inc))
print("cited:", inc["cited"].value_counts(dropna=False).to_dict(), " partial=1:", int((inc["partial"] == 1).sum()),
      " partial_hint=1:", int((inc["partial_hint"] == 1).sum()))
print("시기별:", inc["period"].value_counts().reindex(P).to_dict())
print("구간 합치기(30건 미만):", {p: bool(inc["period"].value_counts().get(p, 0) < 30) for p in P})
print("시기 × cited 건수(분포):")
print(pd.crosstab(inc["period"], inc["cited"].astype(str), margins=True).to_string())
print("\n== 3. needs_review")
print("사건 수(전체 행 기준):", int(C["needs_review"].sum()), "/ 분석 포함 중:", int(inc["needs_review"].sum()))
print("항목별 사건 수:", R.groupby("항목")["case_key"].nunique().to_dict())
print("항목별 사건 수(분석 포함만):", R[R["case_key"].isin(inc["case_key"])].groupby("항목")["case_key"].nunique().to_dict())
print("\n== 4. 기준값 11 비교표(인용률·시기 분포, 난이도 미사용)")
T = C[C["converted"] == 1].copy()
T["grp"] = T["exclude_reason"].replace("", "분석 포함")
T["c1"] = (T["cited"] == 1).astype(float)
T.loc[T["cited"].isna() | (T["cited"] == ""), "c1"] = np.nan
g = T.groupby("grp").agg(n=("case_key", "size"), cited_known=("c1", "count"), cited1=("c1", "sum"))
g["cite_rate"] = (g["cited1"] / g["cited_known"]).round(3)
pdist = pd.crosstab(T["grp"], T["period"]).reindex(columns=P).fillna(0).astype(int)
print(g.join(pdist).to_string())
noext = T[T["exclude_reason"].isin(["조항 미추출", "조항 문구 없음", "풀어 쓴 서술"])]
r_inc = g.loc["분석 포함", "cite_rate"]
r_noext = noext["c1"].mean()
print(f"조항 관련 제외 전체(미추출+문구 없음+풀어 쓴 서술) n={len(noext)}, 인용률={r_noext:.3f}; 분석 포함 인용률={r_inc:.3f}; 차이={abs(r_inc - r_noext) * 100:.1f}%p")
r_ne = T[T["exclude_reason"] == "조항 미추출"]["c1"].mean()
print(f"조항 미추출만: 인용률={r_ne:.3f}; 차이={abs(r_inc - r_ne) * 100:.1f}%p (기준값 11: 10%p 이상이면 한계)")
print("\n== 5. 조항·문구")
print("clause_level(분석 포함):", inc["clause_level"].value_counts().to_dict())
print("clause_text_source(분석 포함):", inc["clause_text_source"].value_counts().to_dict())
print("clause_text_form(판단 조항 있음 전체):", T["clause_text_form"].replace("", "(없음)").value_counts().to_dict())
print("'특약' 표지로 인정(분석 포함):", int((inc["clause_mark_via"] == "특약").sum()))
lv = inc[inc["clause_level"].isin(["항", "호"])]
print("항·호 단위 중 clause_text_article 확보:", int((lv["clause_text_article"].fillna("") != "").sum()), "/", len(lv))
print("주장 위치 버전: 조항 추출", int((T["arg_clause_ref"].fillna("") != "").sum()), "/", len(T),
      " 주장 기준 포함 가능(제외 사유 없음·자동차·본안 아님 제외 전):", int((T["arg_exclude_reason"].fillna("x") == "").sum()))
print("\n== 6. 쟁점 유형·주제(분석 포함)")
print(inc["issue_type"].value_counts().to_dict(), inc["issue_type_source"].value_counts().to_dict())
tp = inc["topic"].value_counts()
print(tp.to_dict(), "기타 비율", round(tp.get("기타", 0) / len(inc), 3))
print("\n== 7. 부정 표현(분석 포함)")
print("explained_duty:", inc["explained_duty"].value_counts().to_dict(), "ambiguity:", inc["ambiguity"].value_counts().to_dict())
pil = C[C["case_key"].isin(PILOT_HUMAN)][["case_key", "explained_duty", "ambiguity", "neg_source"]]
print("4-8-1 파일럿 5건(사람 값 / 자동 결과):"); print(pil.to_string(index=False))
print("\n== 8. 자동차보험")
print("is_auto=1(본문 판정):", int(((C["is_auto"] == 1) & (C["post_level_only"] == 0)).sum()), " 사이트 분류(본문 없음):",
      int(((C["exclude_reason"] == "자동차보험") & (C["post_level_only"] == 1)).sum()))
for k, (v, nr, ev, memo) in AUTO_MANUAL.items():
    row = C[C["case_key"] == k]
    if row.empty:
        print("  수동 표 키 없음:", k)
    elif "확인 실패" in s(row.iloc[0]["auto_evidence"]):
        print("  근거 확인 실패:", k)
print("\n== 9. 시기 판정 근거", C[C["converted"] == 1]["date_basis"].value_counts().to_dict())
print("\n== 10. 대조표본 배분", chk_alloc, " 평가 표본 배분", eval_alloc)
print("대조표본 ∩ 파일럿:", len(set(CHK["case_key"]) & pilot_keys), " 평가 ∩ (파일럿 ∪ 대조):",
      len(set(EVAL["case_key"]) & (pilot_keys | set(CHK["case_key"]))))
print("cases_for_difficulty 행:", len(D), " eval_pick=1:", int(D["eval_pick"].sum()),
      " 분석 포함 중:", int((D["exclude_reason"] == "").sum()), " 제외 사유별:", D.loc[D["exclude_reason"] != "", "exclude_reason"].value_counts().to_dict())
print("\n== 11. 개인정보 후보", len(priv))
for p_ in priv[:40]:
    print("  ", p_)
print("\n== 12. 변환 실패(오류 행)")
F = C[(C["converted"] == 0) & (C["post_level_only"] == 0)]
print(F.groupby(["exclude_reason", "period"]).size().to_string())


# =========================================================================== 13. docs/제외사유.md, docs/변환실패.md
def md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r_ in df.iterrows():
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else str(v) for v in r_.values) + " |")
    return "\n".join(out)


C["grp"] = C["exclude_reason"].replace("", "분석 포함")
flow = C.groupby("grp").agg(건수=("case_key", "size")).reset_index().rename(columns={"grp": "구분"})
flow["비율"] = (flow["건수"] / N).round(3)
byp = pd.crosstab(C["grp"], C["period"]).reindex(columns=P).fillna(0).astype(int).reset_index().rename(columns={"grp": "구분"})
flow = flow.merge(byp, on="구분").sort_values("건수", ascending=False)
G = T.copy()
G["grp"] = G["exclude_reason"].replace("", "분석 포함")
cmp_rows = []
for name, sub in [("분석 포함", G[G["grp"] == "분석 포함"])] + [(k, v) for k, v in G[G["grp"] != "분석 포함"].groupby("grp")] + \
        [("(합) 조항 관련 제외: 조항 미추출 + 조항 문구 없음 + 풀어 쓴 서술", noext)]:
    known = sub["c1"].dropna()
    rate = known.mean() if len(known) else np.nan
    cmp_rows.append({"구분": name, "건수": len(sub), "결과 판정된 건": len(known), "인용·일부 인용": int(known.sum()),
                     "인용률": round(rate, 3) if len(known) else "",
                     "분석 포함과 차이(%p)": "" if name == "분석 포함" or not len(known) else round(abs(rate - r_inc) * 100, 1),
                     **{p_: int((sub["period"] == p_).sum()) for p_ in P}})
CMP = pd.DataFrame(cmp_rows)
pd.DataFrame(cmp_rows).to_csv(os.path.join(DOCS, "제외사유_비교표.csv"), index=False, encoding="utf-8-sig")
r_para = G[G["grp"] == "풀어 쓴 서술"]["c1"].mean()
_ml = C[C["case_key"].isin(R.loc[R["항목"] == "수동 연결", "case_key"])]["exclude_reason"].value_counts()
md = f"""# 제외 사유 (case-parser 본 모드, 2026-11-03)

- 숫자 출처: `docs/본실행_계산.py` → `docs/본실행_계산_결과.txt`, `data/interim/cases.csv`, 비교표 `docs/제외사유_비교표.csv`.
- 단위: 결정문 1건(조정번호). 게시물 445건 = `decisions.csv` 첨부 366행(게시물 362건, 한 게시물에 결정문 3개인 게시물 2건) + 첨부를 받지 않은 게시물 83건(결정례 아님 2, 사이트 분류 자동차보험 81). 그래서 `cases.csv`는 {N}행이다.
- 제외 판정 순서: 결정례 아님 → 지원하지 않는 형식 → 배포용 문서 → 중복 → 자동차보험 → 본안 아님(각하) → 조항 미추출 → 조항 문구 없음 → 풀어 쓴 서술(4-8 조항 추출 보완 ①). 한 사건에는 앞의 사유 하나만 적었다.
- 난이도는 쓰지 않았다(기준값 11 점검은 인용률과 시기 분포만).

## 1. 전체 = 분석 포함 + 제외 (합계 확인: {N} = {int((C['exclude_reason'] == '').sum())} + {int((C['exclude_reason'] != '').sum())})

{md_table(flow)}

## 2. 기준값 11 — 분석 포함 vs 제외(사유별) 인용률·시기 분포

본문이 있는(변환된) 행만 대상이다. 인용률 = 인용·일부 인용 / 결과 판정된 건. 각하는 본안 판단이 아니어서 결과 판정을 하지 않았다.

{md_table(CMP)}

- **기준값 11 판정(분석 포함 vs 조항 미추출)**: 차이 {abs(r_inc - r_ne) * 100:.1f}%p → 10%p 미만.
- 참고: 조항 관련 제외를 모두 합하면 차이 {abs(r_inc - r_noext) * 100:.1f}%p(10%p 미만). **풀어 쓴 서술만 따로 보면 {abs(r_inc - r_para) * 100:.1f}%p**로 10%p를 넘는다. 풀어 쓴 서술 제외는 4-8에서 새로 생긴 사유라 기준값 11 문구(조항 미추출)에 직접 들어 있지 않다. 한계에 적을지는 팀 판단(미확인).

## 3. 사유별 설명

- **자동차보험**: 본문 판정 {int(((C['exclude_reason'] == '자동차보험') & (C['post_level_only'] == 0)).sum())}건(기초 사실의 보험 종목·쟁점 담보, 근거 문장은 `cases.csv`의 `auto_evidence`) + 사이트 분류 '자동차보험' {int(((C['exclude_reason'] == '자동차보험') & (C['post_level_only'] == 1)).sum())}건. 사이트 분류 81건은 첨부를 받지 않아 본문으로 판정하지 못했다(4-6-2의 '본문 기준'을 적용 못 함, 미확인). 본문 판정 중 자동차취급업자(대리운전) 3건, 보험 종목 기재가 없는 차량 충돌 과실 2건은 `needs_review`(is_auto).
- **배포용 문서**: 19건(모두 2010-2016). 보호를 풀지 않았다. 안내문 txt는 열지 않았다. 이 중 제2012-14호(64673)는 같은 번호의 변환된 결정문(64681)이 따로 있어 그 행이 분석에 들어간다(`dup_of_nttId`).
- **본안 아님(각하)**: 15건. 제2010-41호(소송 제기로 조정 중지), 제2003-46호(사실관계 확정 곤란, 세칙 제25조)는 절차상 각하다. 나머지 13건(1998년 '각하결정사항' 12건 + 제2001-31호)은 위원회가 청구 이유를 판단한 뒤 '이유 없어 각하'라고 쓴 것으로, 지금 말로는 기각에 가깝다. 4-8 판정표('각하 → 제외')대로 제외하고 `needs_review`(cited)로 올렸다. → 규칙 변경 제안 1.
- **조항 미추출**: 판단 부분에 약관 표지가 붙은 `제○조`가 없음. 판단이 별표·분류표·'이 사건 면책사유' 같은 별칭으로 조항을 가리키는 4-8 ③ **사람 연결 대상**은 {_ml.sum()}건이다(조항 미추출 {_ml.get('조항 미추출', 0)}건, 본안 아님(각하) {_ml.get('본안 아님(각하)', 0)}건; `needs_review.csv` 항목 '수동 연결'). 사람이 연결하면 조항 미추출 쪽은 분석 포함으로 바뀔 수 있다.
- **풀어 쓴 서술**: 판단 조항은 찾았지만 문구가 위원회가 풀어 쓴 문장뿐(4-8 ①). 문구는 `clause_text`에 남겼다(선택 민감도 '풀어 쓴 서술 포함'용).
- **중복**: 제2009-29호가 두 게시물(64488, 64502)에 올라 있다. 조정일자가 있는 64488을 남겼다.
- **결정례 아님**: 사례집 게시물 2건(64709, 64766).
- **지원하지 않는 형식**: tif 2건(64666, 64667). OCR은 쓰지 않았다. pdf 1건(제2022-5호)은 4-6-1 변경대로 포함했다(쪽 번호·각주를 지우고 추출).

## 4. 구간 합치기(기준값 5)

분석 사건 수: {", ".join(f"{p_} {int((inc['period'] == p_).sum())}건" for p_ in P)}. 30건 미만 구간 없음 → **합치지 않음**.
"""
open(os.path.join(DOCS, "제외사유.md"), "w", encoding="utf-8").write(md)

F = C[(C["converted"] == 0) & (C["post_level_only"] == 0)].merge(dec[["nttId", "파일명", "오류"]], on="nttId", how="left")
F["파일 형식"] = F["파일명"].str.extract(r"(\.\w+)$")[0]
fl = F[["nttId", "case_key", "파일명", "파일 형식", "오류", "period", "exclude_reason", "dup_of_nttId"]].sort_values(["exclude_reason", "nttId"])
summ = fl.groupby(["오류", "period"]).size().reset_index(name="건수")
md2 = f"""# 변환 실패 목록 (2026-11-03 갱신, pdf 포함 후)

- 기준: `data/interim/decisions.csv`의 `오류`가 비어 있지 않은 행. 숫자 출처: `docs/본실행_계산.py`(12장).
- 2026-11-03 변경(4-6-1): 글자를 뽑을 수 있는 pdf(제2022-5호, nttId 64819)는 변환해 **포함**했다. 그래서 실패는 22건 → **{len(fl)}건**이다.
- 배포용 문서의 안내문 txt 19개는 `texts/`에 남아 있지만 읽지 않았다(지우지 않음). 보호는 풀지 않았다.

## 요약
{md_table(summ)}

## 목록
{md_table(fl.fillna(""))}

## 참고
- 64673(제2012-14호, 배포용)은 같은 번호의 다른 게시물 64681이 변환돼 분석에 들어간다(`dup_of_nttId`).
- 64667 파일명에 "96.7.25"가 있어 1996년 결정일 수 있다(미확인). 구간은 ~2009로 같다. 조정번호가 없어 `case_key`는 `nttId64667`.
"""
open(os.path.join(DOCS, "변환실패.md"), "w", encoding="utf-8").write(md2)
print("\n== 13. docs/제외사유.md, docs/변환실패.md 작성. 변환 실패", len(fl), "건; 풀어 쓴 서술 인용률", round(r_para, 3))
