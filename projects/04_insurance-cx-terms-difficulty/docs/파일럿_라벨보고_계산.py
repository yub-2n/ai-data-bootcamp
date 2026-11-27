"""case-parser 파일럿 모드 계산 스크립트 (2026-10-30)

사용:  python3 docs/파일럿_라벨보고_계산.py
입력:  data/interim/pilot_sample.csv, data/interim/decisions.csv,
       data/interim/fss_details_enriched.csv, data/interim/texts/*.txt
       (texts는 decisions.csv의 '오류'가 빈 행의 파일만 연다)
출력:  data/interim/pilot_labels.csv        사건별 자동 후보 라벨(결과 열 포함, 난이도 쪽에 넘기지 않음)
       data/interim/pilot_for_difficulty.csv 난이도 입력(결과·시기 관련 열 없음)
       표준출력: 보고서(docs/파일럿_라벨보고.md)에 옮긴 모든 숫자

원칙(PROJECT.md 4-1~4-7)
  - 분포만 계산한다. 난이도와 결과의 관계는 계산하지 않는다.
  - 규칙은 PROJECT.md 4-2(약관 표지가 붙은 제○조, 법령 제외, 처음 언급 조항) 그대로.
  - 자동 판정은 '후보'이며, 애매하면 needs_review = 1.
"""
import os
import re
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
TEXTS = os.path.join(INTERIM, "texts")

pilot = pd.read_csv(os.path.join(INTERIM, "pilot_sample.csv"))
dec = pd.read_csv(os.path.join(INTERIM, "decisions.csv"))
enr = pd.read_csv(os.path.join(INTERIM, "fss_details_enriched.csv"))


def s(x):
    return "" if pd.isna(x) else str(x)


# ------------------------------------------------------------------ 1. 조항 추출(4-2)
ART = re.compile(
    r"제\s?(\d+)\s?조(?:의\s?\d+)?"                       # 제N조(의M)
    r"\s*(?:[\(（\[【]\s*([^\)）\]】\n]{1,40})\s*[\)）\]】])?"  # (조 제목)
    r"\s*(?:(제\s?\d+\s?항)|([①-⑳󰊱󰊲󰊳󰊴]))?"             # 항
    r"\s*(?:(제\s?\d+\s?호))?"                            # 호
)
# 약관 표지(4-2 ②). '특약'은 결정문이 '특별약관'의 줄임말로 정의해 쓰는 경우가 있어 함께 인정(보고서에 따로 셈)
CLAUSE_MARK = re.compile(r"약관|특약")
LAW_IN_CLAUSE_WORD = re.compile(r"약관의\s?규제에\s?관한\s?법률|약관규제법")
# 법령 표지(4-2 ③): '…법' 뒤에 공백·괄호·'제'가 오는 경우, 법률·시행령·시행규칙, 동법·같은 법
LAW_MARK = re.compile(
    r"법률|시행령|시행규칙|동\s?법|같은\s?법|[가-힣]+법(?=[\s」｣』\)\]]|제)|요령|훈령|고시"
)
WINDOW = 60


def is_clause_ref(text, start):
    """제○조 앞 WINDOW 글자 안에서 가장 가까운 표지가 약관 표지면 약관 조항, 법령 표지면 법령."""
    w0 = max(0, start - WINDOW)
    w = text[w0:start]
    law_spans = [m.span() for m in LAW_MARK.finditer(w)] + [m.span() for m in LAW_IN_CLAUSE_WORD.finditer(w)]
    law_end = max([e for _, e in law_spans], default=-1)
    cl_end = -1
    via = ""
    for m in CLAUSE_MARK.finditer(w):
        inside_law = any(a <= m.start() < b for a, b in law_spans)
        if not inside_law and m.end() > cl_end:
            cl_end, via = m.end(), m.group(0)
    if cl_end > law_end and cl_end >= 0:
        return True, via
    return False, ""


def first_clause(text):
    """처음 언급된 약관 조항(4-2 ④). 반환: dict 또는 None, 그리고 법령 조문 건수."""
    law_n = 0
    for m in ART.finditer(text):
        ok, via = is_clause_ref(text, m.start())
        if not ok:
            law_n += 1
            continue
        n = m.group(1)
        title = (m.group(2) or "").strip()
        hang = m.group(3) or m.group(4)
        ho = m.group(5)
        ref = f"제{n}조"
        level = "조"
        if hang:
            hnum = re.sub(r"\D", "", hang) if hang.startswith("제") else str("①②③④⑤⑥⑦⑧⑨⑩".find(hang) + 1 if hang in "①②③④⑤⑥⑦⑧⑨⑩" else "󰊱󰊲󰊳󰊴".find(hang) + 1)
            ref += f" 제{hnum}항"
            level = "항"
        if ho:
            ref += f" 제{re.sub(r'[^0-9]', '', ho)}호"
            level = "호"
        ctx0 = max(0, m.start() - 40)
        return dict(clause_ref=ref, art_no=int(n), clause_title=title, clause_level=level,
                    mark_via=via, mention=text[ctx0:m.end() + 40].replace("\n", " ")), law_n
    return None, law_n


# ------------------------------------------------------------------ 2. 결과 판정 후보(4-1)
def outcome(row):
    ju = s(row["주문"]).strip()
    gyeol = s(row["결론"])
    chwi = s(row["신청취지"])
    flags = []
    if ju:
        src = "주문"
        if re.search(r"각하", ju):
            typ, cited = "각하", None
        elif re.search(r"취하", ju):
            typ, cited = "취하", None
        elif re.search(r"기각한다", ju):
            typ, cited = "기각(신청인의 청구를 기각한다)", 0
        elif re.search(r"지급하라|환급하라|부활하라|취소하고|인정하고|이행하라", ju):
            verb = re.findall(r"(지급하라|환급하라|부활하라|취소하고|인정하고)", ju)
            typ, cited = "이행 명령(" + "+".join(dict.fromkeys(verb)) + ")", 1
        else:
            typ, cited = "기타", None
            flags.append("주문 표현 판정표에 없음")
    else:
        src = "결론(주문 없음)"
        flags.append("주문 없음 → 결론으로 판정")
        if re.search(r"지급하여야|지급할 책임이 있|부당하", gyeol):
            typ, cited = "주문 없음·결론 지급 인정", 1
        elif re.search(r"보기 어렵|이유 없|타당하지 않|볼 수 없", gyeol):
            typ, cited = "주문 없음·결론 청구 배척", 0
        else:
            typ, cited = "주문 없음·판정 불가", None
    partial = ""
    if re.search(r"일부\s?인용", gyeol + ju):
        partial = "결론에 '일부인용' 명시"
    elif cited == 1 and re.search(r"않으나|이유가 없다고 할 것이나|어려우나|별론", gyeol):
        partial = "결론에 일부 배척 표현(않으나/어려우나 등) — 일부 인용 여부 확인 필요"
        flags.append(partial)
    if cited == 1 and ju and not re.search(r"주문과\s?같", chwi):
        flags.append("신청취지 ≠ '주문과 같음' — 신청취지와 주문 범위 대조 필요")
    if partial.startswith("결론에 '일부인용'"):
        cited_label = "일부 인용"
    elif cited == 1:
        cited_label = "인용"
    elif cited == 0:
        cited_label = "기각"
    else:
        cited_label = "미확인"
    return dict(outcome_src=src, outcome_type=typ, cited=cited, outcome_label=cited_label,
                partial_note=partial, outcome_flags="; ".join(flags),
                outcome_raw=(ju if ju else gyeol)[:200].replace("\n", " "))


# ------------------------------------------------------------------ 3. 본문 구역 나누기(텍스트 파일)
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
    return section(text, [r"1\.\s*기초\s*사실", r"가\.\s*사실관계", r"○\s*사실관계"],
                   [r"\n\s*2\.\s*당사자\s*주장", r"\n\s*나\.\s*당사자", r"\n\s*○\s*당사자"])


# ------------------------------------------------------------------ 4. 조항 문구 확보(4-2 ⑤)
def article_block(src, art_no):
    """src 안에서 줄 머리 '제N조' 또는 'N. (' 형태로 시작하는 조문 블록."""
    pat = re.compile(rf"(?m)^\s*(?:□\s*)?제\s?{art_no}\s?조")
    m = pat.search(src)
    if not m:
        return ""
    rest = src[m.start():]
    nl = rest.find("\n")
    nl = len(rest) if nl < 0 else nl
    nxt = re.search(r"(?m)^\s*(?:□\s*)?(제\s?\d+\s?조|\[|<|【|※|상법|형법|\s*□|[가-힣 ]*법\s*$|<\s*상법)", rest[nl + 1:])
    blk = rest[: nl + 1 + nxt.start()] if nxt else rest
    # 변환 때 본문에 끼어든 각주·편집자 설명 줄(약관 문체 '…니다.'가 아닌 '…다.'로 끝나는 서술문)은 뺀다
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
        circ = "①②③④⑤⑥⑦⑧⑨⑩"
        alt = "󰊱󰊲󰊳󰊴"
        sym = [circ[k - 1]] + ([alt[k - 1]] if k <= 4 else [])
        pos = min([out.find(c) for c in sym if out.find(c) >= 0], default=-1)
        if pos >= 0:
            nxt_syms = [circ[k]] + ([alt[k]] if k < 4 else [])
            nposs = [out.find(c, pos + 1) for c in nxt_syms if out.find(c, pos + 1) >= 0]
            out = out[pos: min(nposs)] if nposs else out[pos:]
        # 기호가 없으면(①이 생략된 단일 항) 그대로 둔다
    if hom:
        k = int(hom.group(1))
        m = re.search(rf"(?m)^\s*{k}\.\s", out)
        if m:
            n2 = re.search(rf"(?m)^\s*{k + 1}\.\s", out[m.end():])
            out = out[m.start(): m.end() + n2.start()] if n2 else out[m.start():]
    return out.strip()


def quoted_text(sentence):
    """처음 나오는 20자 이상 따옴표 인용 하나(처음 언급 원칙과 같은 방식)."""
    qs = re.findall(r"[“\"]([^”\"]{20,})[”\"]", sentence)
    return qs[0].strip() if qs else ""


SUMMARY = re.compile(r"에 의하면|규정하고 있|정하고 있|라고 규정|도록 정하")


def clause_text_for(row, text, judg, cl):
    """반환: (clause_text, clause_text_source, text_form)
    text_form: '조문 그대로' | '따옴표 인용' | '풀어 쓴 서술'(위원회가 요약해 옮긴 문장)"""
    n, level, ref = cl["art_no"], cl["clause_level"], cl["clause_ref"]
    att = s(row["붙임"])
    for src, srcname in [(att, "붙임"), (facts_section(text), "본문 인용"), (judg, "본문 인용")]:
        if not src:
            continue
        blk = article_block(src, n)
        if blk:
            if not cl["clause_title"]:
                cl["clause_title"] = article_title(src, n)
            form = "풀어 쓴 서술" if SUMMARY.search(blk[:200]) else "조문 그대로"
            return cut_level(blk, level, ref), srcname, form
    # 판단 안의 언급 문장(옛 결정의 '(1) 관련 약관 규정' 등)
    m = None
    for mm in ART.finditer(judg):
        if int(mm.group(1)) == n and is_clause_ref(judg, mm.start())[0]:
            m = mm
            break
    if m:
        st = judg.rfind("\n", 0, m.start()) + 1
        en_m = re.search(r"(규정하고 있음|규정하고 있으며|정하고 있고|정하고 있으며|규정되어 있음|있음\.|하고 있는 바,|\n□|\n◦|\n○)", judg[m.end():])
        en = m.end() + en_m.end() if en_m else min(len(judg), m.end() + 400)
        sent = re.sub(r"[\s◦○□]+$", "", judg[st:en].strip())
        q = quoted_text(sent)
        if q:
            return q, "본문 인용", "따옴표 인용"
        return sent, "본문 인용", "풀어 쓴 서술"
    return "", "", ""


# ------------------------------------------------------------------ 5. 부정 표현 후보(4-4)
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


def sentences(t):
    """줄 단위로 먼저 나누고, 한 줄 안에서는 '…다. / …음. / …함.' 뒤에서 나눈다."""
    out = []
    for line in t.split("\n"):
        out += [x.strip() for x in re.split(r"(?<=[다음함됨임])\.\s+", line) if x.strip()]
    return out


def after_morphs(sent, end):
    tail = sent[end:end + 60]
    if kiwi is None:
        return [], tail
    toks = kiwi.tokenize(tail)
    return [t.form for t in toks[:15]], tail


def judge_kw(var, sent, m):
    forms, tail = after_morphs(sent, m.end())
    fs = set(forms)
    neg = bool(fs & NEG) or "어렵" in fs
    principle = bool(re.search(r"경우에는|하여야 한다|해석하여야|해석해야|판시", sent))
    if var == "explained_duty":
        violate = bool(re.search(r"위반|불이행", tail))
        fulfill = "이행" in tail or "다하" in tail or "설명하였" in tail
        if m.group(0).startswith("설명하지") or m.group(0).startswith("설명을"):
            val, why = (1, "키워드 자체가 부정형(설명하지 않/설명을 하지)")
        elif violate and not neg:
            val, why = 1, "뒤에 '위반/불이행', 부정 형태소 없음"
        elif violate and neg:
            val, why = 2, "뒤에 '위반' + 부정 형태소"
        elif fulfill and neg:
            val, why = 1, "뒤에 '이행/다하' + 부정 형태소(이행하지 않음)"
        elif fulfill and not neg:
            val, why = 2, "뒤에 '이행/다하', 부정 형태소 없음"
        else:
            val, why = None, "위반·이행 표현 없음(대상 여부 등)"
    else:
        kwd = m.group(0)
        if re.match(r"명백하지|다의적|작성자|고객에게", kwd):
            if principle:
                val, why = None, "법리(원칙) 서술 문장 — 사건 판단인지 사람 확인"
            else:
                val, why = 1, "키워드 자체가 모호함 인정형"
        elif neg:
            val, why = 2, "뒤에 부정 형태소(없/아니/않/못/어렵)"
        else:
            val, why = 1, "뒤에 부정 형태소 없음"
    return val, why, forms


def kw_rows(case_key, judg_concl):
    rows = []
    for var, rx in KW.items():
        for sid, sent in enumerate(sentences(judg_concl)):
            for m in rx.finditer(sent):
                val, why, forms = judge_kw(var, sent, m)
                a = max(0, m.start() - 80)
                rows.append(dict(case_key=case_key, var=var, sent_id=sid, keyword=m.group(0),
                                 excerpt=sent[a:m.end() + 90].replace("\n", " "),
                                 auto=val, why=why, morphs=" ".join(forms[:8])))
    return rows


def case_value(rows, var):
    vals = [r["auto"] for r in rows if r["var"] == var]
    if not vals:
        return 0, 0
    known = {v for v in vals if v is not None}
    if len(known) == 1 and None not in vals:
        return known.pop(), 0
    if len(known) == 1:
        return known.pop(), 1
    return None, 1


# ------------------------------------------------------------------ 6. 자동차보험 판정 후보(4-6-2)
AUTO_TERMS = re.compile(r"자동차보험|대인배상|대물배상|자기신체사고|무보험자동차|무보험차량|자동차손해배상|자배법|자기차량손해")
PRODUCT_LINE = re.compile(r"(보험종목\s*:\s*[^\n]+|[^\n]{0,30}보험(?:계약)?에 가입[^\n]{0,20}|[^\n]{0,40}보험(?:계약)?을 체결[^\n]{0,10})")


def auto_check(text, cand):
    facts = facts_section(text)
    prod = PRODUCT_LINE.findall(facts)
    hits = AUTO_TERMS.findall(text)
    prod_auto = any(re.search(r"자동차보험|자동차종합보험", p) for p in prod)
    if prod_auto:
        return 1, 1, "기초 사실의 보험 종목이 자동차보험", prod, hits
    if hits or cand:
        return 0, 1, "보험 종목은 자동차보험 아님, 본문에 자동차보험 담보 용어 있음 — 사람 확인", prod, hits
    return 0, 0, "보험 종목·쟁점 담보에 자동차보험 표지 없음", prod, hits


# ------------------------------------------------------------------ 7. 쟁점 유형 후보(4-5)
def issue_from(textv):
    if re.search(r"보상하지\s?(아니하|않)|지급하지\s?아니하|면책", textv):
        return "면책"
    if re.search(r"알릴\s?의무|고지|설명\s?의무", textv):
        return "고지·설명"
    return "보상 범위·정의"


# ------------------------------------------------------------------ 실행
m = pilot[["nttId", "period", "title", "auto_candidate", "site_auto", "year", "year_source", "reg_date"]].merge(
    dec, on="nttId", how="left")
labels, kwall, autorows = [], [], []
for _, r in m.iterrows():
    key = s(r["조정번호"])
    if not key:  # 변환 못 한 첨부: 파일명의 조정번호(예: 제2022-5호)를 쓰고, 없으면 nttId
        fm = re.search(r"(\d{4})-(\d+)", s(r["파일명"]))
        key = f"{fm.group(1)}-{fm.group(2)}" if fm else f"nttId{r['nttId']}"
    err = s(r["오류"])
    base = dict(case_key=key, nttId=r["nttId"], period=r["period"], title=r["title"],
                auto_candidate=r["auto_candidate"])
    if err:
        reason = "지원하지 않는 형식" if "지원하지 않는 형식" in err else ("배포용 문서" if "배포용" in err else "변환 실패")
        base.update(converted=0, exclude_reason=reason, needs_review=0, decision_date="",
                    date_basis=r["year_source"], is_auto="", auto_note="본문 없음 — 판정 불가(미확인)")
        labels.append(base)
        autorows.append(dict(case_key=key, title=r["title"], product="(본문 없음)", hits="", auto="미확인",
                             why="pdf 첨부라 본문을 읽지 않음(지원하지 않는 형식)"))
        continue
    txt_path = os.path.join(TEXTS, os.path.splitext(r["파일명"])[0] + ".txt")
    text = open(txt_path, encoding="utf-8").read()
    judg = s(r["위원회_판단"])
    concl = s(r["결론"])
    arg = s(r["당사자_주장"]) or (s(r["신청인_주장"]) + "\n" + s(r["피신청인_주장"]))
    nr = []
    # 결정일
    if s(r["조정일자"]):
        dd, basis = s(r["조정일자"]), "조정일자(hwp)"
    elif pd.notna(r["year"]) and r["year_source"] == "조정번호":
        dd, basis = "", "조정번호 연도"
    else:
        dd, basis = "", "등록일 연도"
        nr.append("결정일·조정번호 연도 없음")
    oc = outcome(r)
    if oc["outcome_flags"]:
        nr.append(oc["outcome_flags"])
    clJ, lawJ = first_clause(judg)
    clA, lawA = first_clause(arg)
    ct, cts, form = ("", "", "")
    if clJ:
        ct, cts, form = clause_text_for(r, text, judg, clJ)
        if form == "풀어 쓴 서술":
            nr.append("조항 문구가 풀어 쓴 서술")
    ctA, ctsA, formA = clause_text_for(r, text, judg, clA) if clA else ("", "", "")
    if s(r["위원회_판단_추출"]).startswith("추정"):
        nr.append("위원회_판단 범위 추정 — 사람 확인")
    rows = kw_rows(key, judg + "\n" + concl)
    kwall += rows
    ed, ed_nr = case_value(rows, "explained_duty")
    am, am_nr = case_value(rows, "ambiguity")
    if ed_nr:
        nr.append("explained_duty 애매")
    if am_nr:
        nr.append("ambiguity 애매")
    isauto, auto_nr, auto_why, prod, hits = auto_check(text, r["auto_candidate"] == 1)
    if auto_nr:
        nr.append("is_auto 사람 확인")
        autorows.append(dict(case_key=key, title=r["title"], product=" / ".join(prod)[:160],
                             hits=", ".join(dict.fromkeys(hits)), auto=isauto, why=auto_why))
    # 쟁점 유형 후보 A: 조 제목(없으면 조항 언급 앞뒤 글자), 후보 B: 안건명
    issue_clause = issue_from(clJ["clause_title"] or clJ["mention"]) if clJ else ""
    issue_title = issue_from(s(r["안건명"]))
    if not clJ:
        exr = "조항 미추출"
    elif not ct:
        exr = "조항 문구 없음"
    else:
        exr = ""
    base.update(
        converted=1, decision_date=dd, date_basis=basis, is_auto=isauto,
        outcome_src=oc["outcome_src"], outcome_type=oc["outcome_type"], outcome_raw=oc["outcome_raw"],
        cited=oc["cited"], outcome_label=oc["outcome_label"], partial_note=oc["partial_note"],
        clause_ref=clJ["clause_ref"] if clJ else "", clause_title=clJ["clause_title"] if clJ else "",
        clause_level=clJ["clause_level"] if clJ else "", clause_mark_via=clJ["mark_via"] if clJ else "",
        clause_source="판단" if clJ else "", clause_text_source=cts, clause_text_form=form, clause_text=ct,
        law_refs_in_judgment=lawJ,
        arg_clause_ref=clA["clause_ref"] if clA else "", arg_clause_level=clA["clause_level"] if clA else "",
        arg_clause_text_ok=int(bool(ctA)), law_refs_in_args=lawA,
        issue_type_by_clause=issue_clause, issue_type_by_title=issue_title,
        issue_type=issue_clause or issue_title,
        explained_duty=ed, ambiguity=am, exclude_reason=exr,
        needs_review=int(bool(nr)), review_notes="; ".join(nr),
        judgment_extraction=s(r["위원회_판단_추출"]),
    )
    labels.append(base)

L = pd.DataFrame(labels)
K = pd.DataFrame(kwall)
A = pd.DataFrame(autorows)

# ------------------------------------------------------------------ 출력 파일
lab_cols = ["case_key", "nttId", "period", "decision_date", "date_basis", "title", "auto_candidate", "is_auto",
            "converted", "outcome_src", "outcome_type", "outcome_raw", "cited", "outcome_label", "partial_note",
            "clause_ref", "clause_title", "clause_level", "clause_mark_via", "clause_source", "clause_text_source",
            "clause_text_form", "clause_text", "law_refs_in_judgment", "arg_clause_ref", "arg_clause_level",
            "arg_clause_text_ok", "law_refs_in_args", "issue_type_by_clause", "issue_type_by_title", "issue_type",
            "explained_duty", "ambiguity", "exclude_reason", "needs_review", "review_notes", "judgment_extraction"]
L.reindex(columns=lab_cols).to_csv(os.path.join(INTERIM, "pilot_labels.csv"), index=False, encoding="utf-8-sig")

# 시기(period)·결과 관련 열은 넣지 않는다(case-parser 역할 정의 7번, PROJECT.md 4-7 가림 규칙)
diff_cols = ["case_key", "issue_type", "clause_ref", "clause_title", "clause_level", "clause_source",
             "clause_text_source", "clause_text_form", "clause_text"]
D = L[(L["converted"] == 1) & (L["clause_text"].fillna("") != "")][diff_cols].copy()
D.to_csv(os.path.join(INTERIM, "pilot_for_difficulty.csv"), index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------ 표준출력(보고서용 숫자)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 80)
P = ["~2009", "2010-2016", "2017-2026"]
print("== 0. 대상", len(L), "건, 구간별", L["period"].value_counts().reindex(P).to_dict())

print("\n== 1. 변환 성공률(구간별)")
cv = L.groupby("period")["converted"].agg(["sum", "count"]).reindex(P)
cv["rate"] = (cv["sum"] / cv["count"]).round(3)
print(cv.to_string())
print("전체", int(L["converted"].sum()), "/", len(L), round(L["converted"].mean(), 3))

C = L[L["converted"] == 1]
print("\n== 2. 주문 표현 유형별 건수(후보)")
print(C["outcome_type"].value_counts().to_string())
print("\n결과 후보 라벨(구간별, 분포만)")
ct = pd.crosstab(L["period"], L["outcome_label"].fillna("제외(변환 안 됨)"), margins=True).reindex(P + ["All"])
print(ct.to_string())
print("\n결과 후보 비율(구간 내, 변환된 건 기준)")
print((pd.crosstab(C["period"], C["outcome_label"], normalize="index").round(3)).reindex(P).to_string())

print("\n== 3. 조항 추출 비율(변환 성공 건 기준)")
nC = len(C)
jx = (C["clause_ref"] != "").sum()
jt = (C["clause_text"].fillna("") != "").sum()
ax = (C["arg_clause_ref"] != "").sum()
at = (C["arg_clause_text_ok"] == 1).sum()
print(f"판단: 조항 추출 {jx}/{nC} = {jx/nC:.3f}, 추출+문구 확보 {jt}/{nC} = {jt/nC:.3f}")
print(f"주장: 조항 추출 {ax}/{nC} = {ax/nC:.3f}, 추출+문구 확보 {at}/{nC} = {at/nC:.3f}")
by = C.assign(j=(C["clause_ref"] != ""), jt=(C["clause_text"].fillna("") != ""), a=(C["arg_clause_ref"] != ""),
              at=(C["arg_clause_text_ok"] == 1)).groupby("period")[["j", "jt", "a", "at"]].agg(["sum", "count"])
print(by.reindex(P).to_string())
print("'특약' 표지로만 인정된 판단 조항:", int((C["clause_mark_via"] == "특약").sum()))
print("판단에서 걸러낸 법령 조문 언급 수(첫 약관 조항 이전까지):", int(C["law_refs_in_judgment"].sum()),
      "/ 주장:", int(C["law_refs_in_args"].sum()))
print("문구 출처:", C["clause_text_source"].value_counts().to_dict(), "형태:", C["clause_text_form"].value_counts().to_dict())
print("조항 단위:", C["clause_level"].value_counts().to_dict())

print("\n== 4. 추정 분석 사건 수(기준값 8)")
E = enr.copy()
n_post = len(E)
casebook = int(E["is_casebook"].fillna(0).astype(int).sum())
site_auto = int(E["site_auto"].fillna(0).astype(int).sum())
ins_ratio_list = (n_post - casebook - site_auto) / n_post
pilot_nonauto = (C["is_auto"] == 0).sum() / len(C)
ins_ratio = ins_ratio_list * pilot_nonauto
merit = C["cited"].notna().sum() / len(C)
conv = L["converted"].mean()
dconv = dec["오류"].isna().sum() / len(dec)
for nm, ext in [("판단", jt / nC), ("주장", at / nC)]:
    est = n_post * ins_ratio * merit * conv * ext
    print(f"{nm}: 445(실제 {n_post}) x 보험비율 {ins_ratio:.3f}(목록 비사례집·비사이트자동차 {ins_ratio_list:.3f} x 파일럿 본문 비자동차 {pilot_nonauto:.3f})"
          f" x 본안 {merit:.3f} x 변환 {conv:.3f} x 추출·문구 {ext:.3f} = {est:.1f}")
    est2 = n_post * ins_ratio * merit * dconv * ext
    print(f"   (참고: 변환 성공률을 전체 변환 결과 {dconv:.3f}로 바꾸면 {est2:.1f})")
print(f"목록 수 {n_post}, 사례집 {casebook}, 사이트 자동차 {site_auto}, decisions.csv 행 {len(dec)}, 오류 없음 {dec['오류'].isna().sum()}")
ok_arg = at / nC >= 0.60
est_arg = n_post * ins_ratio * merit * conv * (at / nC)
print("기준값 8 판정: 주장 60% 이상?", ok_arg, "/ 주장 추정 100건 이상?", est_arg >= 100,
      "→", "주장 기반" if (ok_arg and est_arg >= 100) else "판단 기반")

print("\n== 5. 제외 사유별 건수(4-2 기준, 판단 위치)")
L2 = L.copy()
L2["exclude_reason"] = L2["exclude_reason"].fillna("")
print(L2["exclude_reason"].replace("", "(포함)").value_counts().to_string())
print("합계 확인:", len(L2), "=", (L2["exclude_reason"] == "").sum(), "+", (L2["exclude_reason"] != "").sum())
print("needs_review:", int(L2["needs_review"].fillna(0).sum()))

print("\n== 6. 쟁점 유형 후보")
print(pd.crosstab(C["issue_type_by_clause"].replace("", "(조항 없음)"), C["issue_type_by_title"]).to_string())
print("최종 후보(조항 우선, 없으면 안건명):", C["issue_type"].value_counts().to_dict())

print("\n== 7. 조 제목 목록(판단 첫 조항)")
print(C[C["clause_ref"] != ""][["case_key", "clause_ref", "clause_title", "clause_level", "clause_text_form"]].to_string(index=False))

print("\n== 8. 부정 표현 후보 문장 수", len(K))
if len(K):
    print(K.groupby(["var", "auto"], dropna=False).size().to_string())
    print(C[["case_key", "explained_duty", "ambiguity"]].to_string(index=False))

print("\n== 9. 자동차 판정 표 행 수", len(A))
print(A.to_string(index=False))

print("\n== 10. pilot_for_difficulty.csv 열 검사")
cols = list(pd.read_csv(os.path.join(INTERIM, "pilot_for_difficulty.csv")).columns)
banned = [c for c in cols if re.search(r"cited|outcome|exclude|evidence|주문|결론|decision|period|year|needs_review|partial|review", c)]
print("열:", cols, "행:", len(D))
print("결과 관련 열:", banned if banned else "없음")

# 보고서 표 작성용 상세(사람 판정 표 1)
K.to_csv(sys.stdout if "--kw" in sys.argv else os.devnull, index=False)
