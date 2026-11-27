# -*- coding: utf-8 -*-
"""
difficulty_profile.py — 난이도 프로필 (제안 A 심화판, 탐색적 보조 분석)

지시: docs/지시/난이도프로필_실행.md
- 주 결과(05·07·통계요약)는 읽지도 바꾸지도 않는다.
- 새 지표·차원 점수를 cited와 검정하거나 회귀에 넣지 않는다.
  (인용률은 10_조항주제.csv, 02_기술통계.csv 값을 옆에 붙여 보여주기만 한다)
- 기존 4개 지표는 difficulty_colab.py(indicators, compute, 고정 설정)를 import해서 쓴다.
- 새 지표 5개(☆)는 "탐색적, 결과를 본 뒤 추가"한 지표다(수정 1: 5개로 확정).
- 수정 1: docs/보고/고쳐쓰기_뜻확인.csv는 사람이 답을 적는 파일이라 다시 쓰지 않고 읽기만 한다.
- 처음부터 다시 돌리면 같은 결과(시드 42).

실행: py -3.10 outputs/stats/difficulty_profile.py
"""
import collections
import glob
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import difficulty_colab as dc  # noqa: E402

dc.BASE = BASE
OUT = HERE
FIG = os.path.join(OUT, "figs")
REPORT_DIR = os.path.join(BASE, "docs", "보고")
ENC = "utf-8-sig"
SEED = 42
N_BOOT = 1000
HIGH = 90.0
DUP_KEY, DUP_CHOSEN, DUP_DROPPED = "2009-29", "D204", "D246"   # 통계 단계 확정


def p(*a):
    return os.path.join(BASE, *a)


# =====================================================================
# 1. 지표 정의 (지시 1장 고정)
# =====================================================================
IND = ["term_ratio", "noun_chain_max", "words_per_sentence", "ec_per_sentence", "etm_per_sentence",
       "exception_count", "cond_per_sentence", "neg_count", "ref_count", "ref_chain"]
NEW_IND = ["noun_chain_max", "ec_per_sentence", "etm_per_sentence", "cond_per_sentence", "neg_count"]
OLD_IND = ["term_ratio", "words_per_sentence", "exception_count", "ref_count", "ref_chain"]
DIMS = collections.OrderedDict([
    ("vocab", ["term_ratio", "noun_chain_max"]),
    ("sentence", ["words_per_sentence", "ec_per_sentence", "etm_per_sentence"]),
    ("logic", ["exception_count", "cond_per_sentence", "neg_count"]),
    ("ref", ["ref_count", "ref_chain"]),
])
DIM_KO = {"vocab": "어휘", "sentence": "문장 구조", "logic": "논리 구조", "ref": "참조 구조"}
# 문장 단위 핫스팟(지시 4-2): ref_chain은 쓰지 않는다
SENT_DIMS = collections.OrderedDict([
    ("vocab", ["term_ratio", "noun_chain_max"]),
    ("sentence", ["words_per_sentence", "ec_per_sentence", "etm_per_sentence"]),
    ("logic", ["exception_count", "cond_per_sentence", "neg_count"]),
    ("ref", ["ref_count"]),
])
CHAIN_TAGS = {"NNG", "NNP", "XSN"}
COND_EC = {"면", "으면", "거든"}
NEG = {("않", "VX"), ("아니", "VCN"), ("못", "MAG"), ("없", "VA")}

TERMS = pd.read_csv(p("outputs", "stats", "term_dict.csv"), encoding=ENC)["term"].tolist()
KIWI = dc.kiwi(TERMS)                        # difficulty_colab과 같은 Kiwi 객체
CAPTURED = {k: collections.Counter() for k in NEW_IND}


def base_tag(tag):
    return str(tag).split("-")[0]


def new_indicators(text, record=None):
    """새 지표(☆ 5개). record가 주어지면 잡힌 형태를 센다."""
    t = dc.norm(text)
    sents = KIWI.split_into_sents(t) or []
    n_s = len(sents) if sents else 1
    bounds = [s.start for s in sents][1:]
    toks = KIWI.tokenize(t)
    ec = etm = cond = neg = 0
    best, best_form, cur, cur_form, prev_sent = 0, "", 0, [], 0
    for x in toks:
        tg = base_tag(x.tag)
        sent_id = sum(1 for b in bounds if x.start >= b)
        if sent_id != prev_sent:
            cur, cur_form, prev_sent = 0, [], sent_id
        if tg in CHAIN_TAGS:
            cur += 1
            cur_form.append(x.form)
            if cur > best:
                best, best_form = cur, "+".join(cur_form)
        else:
            cur, cur_form = 0, []
        if tg == "EC":
            ec += 1
            if record is not None:
                CAPTURED["ec_per_sentence"][f"{x.form}/EC"] += 1
            if x.form in COND_EC:
                cond += 1
                if record is not None:
                    CAPTURED["cond_per_sentence"][f"{x.form}/EC"] += 1
        if tg == "ETM":
            etm += 1
            if record is not None:
                CAPTURED["etm_per_sentence"][f"{x.form}/ETM"] += 1
        if x.form == "경우" and tg == "NNG":
            cond += 1
            if record is not None:
                CAPTURED["cond_per_sentence"]["경우/NNG"] += 1
        if (x.form, tg) in NEG:
            neg += 1
            if record is not None:
                CAPTURED["neg_count"][f"{x.form}/{tg}"] += 1
    if record is not None and best > 0:
        CAPTURED["noun_chain_max"][best_form] += 1
    return {"noun_chain_max": best, "ec_per_sentence": ec / n_s, "etm_per_sentence": etm / n_s,
            "cond_per_sentence": cond / n_s, "neg_count": neg}


def old_indicators(text):
    """기존 지표(★): difficulty_colab.indicators 그대로."""
    r = dc.indicators(text, TERMS)
    return {"term_ratio": r["term_ratio"], "words_per_sentence": r["words_per_sentence"],
            "exception_count": r[f"exception_count_{dc.EXC_MAIN}"], "ref_count": r[f"ref_count_{dc.REF_MAIN}"],
            "ref_chain": r["ref_count_chain"], "n_sents": r["n_sents"]}


def indicators10(text, record=None):
    d = old_indicators(text)
    d.update(new_indicators(text, record))
    return d


# =====================================================================
# 2. 표준약관 추출
# =====================================================================
# (종류, 세부, 시작 쪽, 끝 쪽) — PDF 쪽 번호. 목차(1쪽)와 TERM_SOURCES로 정함
SEGMENTS = [
    ("생명보험", "생명보험", 1, 25),                       # 본문 1~25, <부표> 26~55 제외
    ("질병·상해보험", "질병·상해보험(손해보험 회사용)", 144, 175),   # <부표 9> 176~203 제외
    ("실손의료보험", "기본형", 204, 249),                  # <붙임1> 용어의 정의 250~252, <붙임2> 253 제외
    ("실손의료보험", "특별약관1(중증 비급여)", 254, 283),
    ("실손의료보험", "특별약관2(비중증 비급여)", 284, 313),
]
STD_TYPES = ["생명보험", "질병·상해보험", "실손의료보험"]
DROP_LOG = collections.Counter()


def _inside(o, b):
    cx, cy = (o["x0"] + o["x1"]) / 2, (o["top"] + o["bottom"]) / 2
    return b[0] <= cx <= b[2] and b[1] <= cy <= b[3]


def page_text(pg):
    """표 셀을 뺀 쪽 본문. 실손의 '보장종목 | 보상하는(하지 않는) 사항' 배치 표는
    본문이 표 안에 들어 있어 오른쪽 열 글자만 본문으로 남긴다(머리 행·보장종목 열은 뺌).
    그 밖의 표(2행 이상)는 표 셀이라 모두 뺀다. 1행짜리 표는 강조 상자라 본문으로 둔다."""
    ts = pg.find_tables()
    layouts, drops = [], []
    for t in ts:
        ex = t.extract()
        h = [(c or "") for c in ex[0]] if ex else []
        if (len(h) >= 2 and "보장종목" in h[0].replace(" ", "")
                and re.match(r"보상하(는|지않는)사항", h[1].replace(" ", ""))):
            c1 = [c for c in t.rows[0].cells[1:] if c][0]
            layouts.append((t.bbox, c1[0], t.rows[0].bbox))
    for t in ts:
        if any(t.bbox == L[0] for L in layouts):
            continue
        if len(t.rows) >= 2:
            drops.append(t.bbox)
    DROP_LOG["표(2행 이상) 뺌"] += len(drops)
    DROP_LOG["보장종목 배치 표(본문 열만 사용)"] += len(layouts)

    def keep(o):
        if o.get("object_type") != "char":
            return True
        for b in drops:
            if _inside(o, b):
                return False
        for tb, bx, hb in layouts:
            if _inside(o, hb):
                return False
            if _inside(o, tb) and (o["x0"] + o["x1"]) / 2 < bx:
                return False
        return True
    return pg.filter(keep).extract_text() or ""


LIST_START = re.compile(r"^(\d+\.|[가-하]\.|[①-⑳]|\d+\)|[가-하]\)|\(\d+\)|※|【|주\)|-\s)")
ATTACH_TAGS = ("J", "E", "XS", "VCP", "SF", "SP", "SSC", "SSO", "SE", "SO")


def join_lines(lines):
    """PDF 줄바꿈을 잇는다. 한글 약관은 낱말 중간에서 줄이 바뀌므로,
    이은 자리가 형태소 안이거나 다음 형태소가 조사·어미·접사·문장부호면 붙이고, 아니면 띄운다."""
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if not out:
            out = ln
            continue
        if LIST_START.match(ln) or re.search(r"[.:;]$", out):
            out += " " + ln
            continue
        left = out.split(" ")[-1]
        right = ln.split(" ")[0]
        joined = left + right
        cut = len(left)
        toks = KIWI.tokenize(joined)
        space = True
        for x in toks:
            if x.start < cut < x.start + x.len:
                space = False
                break
            if x.start == cut:
                space = not base_tag(x.tag).startswith(ATTACH_TAGS)
                break
        out += (" " if space else "") + ln
    return out


AMEND = re.compile(r"<\s*(개\s*정|신\s*설|삭\s*제|본\s*조\s*신\s*설)[^>]*>")


def extract_standard():
    import pdfplumber
    pdfs = sorted(glob.glob(p(dc.PDF_GLOB)))
    if len(pdfs) != 1:
        sys.exit(f"표준약관 PDF가 1개가 아닙니다: {pdfs}")
    arts = []
    with pdfplumber.open(pdfs[0]) as pdf:
        for std_type, sub, a, b in SEGMENTS:
            lines = []
            for i in range(a, b + 1):
                txt = page_text(pdf.pages[i - 1])
                for ln in txt.split("\n"):
                    s = ln.strip()
                    if re.fullmatch(r"-\s*\d+\s*-", s) or s.startswith("□") or re.match(r"^<[^>]*보험>", s):
                        continue
                    if re.match(r"^제\s*\d+\s*관", s):
                        lines.append("@@관")
                        continue
                    lines.append(s)
            text = "\n".join(lines)
            text = AMEND.sub("", text)
            # 조 머리 찾기: 줄 머리 + 번호가 앞 조 다음(같은 번호는 '의N'만)
            heads, last = [], 0
            for m in re.finditer(r"(?m)^\s*제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*([\(\[])", text):
                n, sub_n = int(m.group(1)), m.group(2)
                if not (n == last + 1 or (n == last and sub_n)):
                    continue
                # 제목 괄호 끝 찾기(괄호 안 괄호 허용, 줄바꿈 허용)
                close = ")" if m.group(3) == "(" else "]"
                depth, k = 0, m.end() - 1
                while k < len(text) and k < m.end() + 120:
                    ch = text[k]
                    if ch in "([":
                        depth += 1
                    elif ch in ")]":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                if depth != 0 or text[k] != close:
                    continue
                after = text[k + 1:k + 4]
                if re.match(r"[를을에와과의및,]|\s*제\s*\d", after):
                    continue
                heads.append((m.start(), k + 1, m.group(1) + (f"의{sub_n}" if sub_n else ""),
                              re.sub(r"\s+", "", text[m.end():k])))
                last = n
            for j, (st0, en0, no, title) in enumerate(heads):
                end = heads[j + 1][0] if j + 1 < len(heads) else len(text)
                body = text[en0:end]
                body = body.split("@@관")[0]           # 다음 관 제목 앞에서 끊음
                arts.append({"std_type": std_type, "std_sub": sub, "art_no": no,
                             "art_title": title, "body_lines": body.strip("\n").split("\n")})
    return pd.DataFrame(arts)


def split_hang(lines):
    """항(①②…) 단위. 원문자가 없으면 조 전체가 항 하나."""
    groups, cur = [], []
    for ln in lines:
        if re.match(r"^[①-⑳]", ln.strip()) and cur:
            groups.append(cur)
            cur = []
        cur.append(ln)
    if cur:
        groups.append(cur)
    return groups


def build_units(arts):
    units = []
    excluded = []
    for _, a in arts.iterrows():
        if "용어" in a.art_title and "정의" in a.art_title:
            excluded.append(f"{a.std_type}/{a.std_sub} 제{a.art_no}조({a.art_title})")
            continue
        art_text = join_lines(a.body_lines)
        if not dc.norm(art_text):
            continue
        uid = f"{a.std_sub}|{a.art_no}"
        units.append({"std_type": a.std_type, "unit": "조", "uid": uid, "text": art_text})
        for hi, g in enumerate(split_hang(a.body_lines), 1):
            ht = join_lines(g)
            if not dc.norm(ht):
                continue
            units.append({"std_type": a.std_type, "unit": "항", "uid": f"{uid}|{hi}", "text": ht})
            for si, s in enumerate(KIWI.split_into_sents(dc.norm(ht)), 1):
                if s.text.strip():
                    units.append({"std_type": a.std_type, "unit": "문장", "uid": f"{uid}|{hi}|{si}", "text": s.text})
    return pd.DataFrame(units), excluded


# =====================================================================
# 백분위·차원 점수
# =====================================================================
def pct_of(dist, x):
    """0~100, 같은 값은 중간 순위(percentileofscore kind='mean')."""
    if pd.isna(x):
        return np.nan
    return float(stats.percentileofscore(dist, x, kind="mean"))


def add_pct(df, bench, cols, prefix="pct_"):
    for c in cols:
        d = bench[c].astype(float).values
        df[prefix + c] = [pct_of(d, v) for v in df[c]]
    return df


def dim_scores(df, dims, prefix="pct_", suffix=""):
    for k, cols in dims.items():
        df[f"dim_{k}{suffix}"] = df[[prefix + c for c in cols]].mean(axis=1)
    return df


def top_dim(row, suffix=""):
    vals = [(row[f"dim_{k}{suffix}"], k) for k in DIMS]
    best = max(v for v, _ in vals)
    if not best >= HIGH:
        return "없음"
    return [DIM_KO[k] for v, k in vals if v == best][0]


def top_dim_rel(row):
    """수정 1-4: 90 기준과 상관없이 가장 높은 차원(같으면 DIMS 순서). 표시용(그림 A4 점 색), 검정 없음."""
    vals = [(row[f"dim_{k}"], k) for k in DIMS]
    best = max(v for v, _ in vals)
    return [DIM_KO[k] for v, k in vals if v == best][0]


# =====================================================================
# 가림 규칙(지시 4-4): 개인 정보처럼 보이는 말
# =====================================================================
MASK_PATS = [
    r"\d{6}\s*-\s*[1-4]\d{6}",                       # 주민등록번호
    r"0\d{1,2}-\d{3,4}-\d{4}",                        # 전화번호
    r"[\w.]+@[\w.]+",                                 # 전자우편
    r"(?<![가-힣])(신청인|피신청인|청구인|망인|환자)(?![가-힣])",   # 사건 당사자 지칭
    r"[가-힣][○○ㅇ*Ｏ]{1,2}(?=\s|씨|님|$)",          # 이미 가린 이름
]
MASK_COUNT = collections.Counter()


def mask(text, where):
    t = str(text)
    for pat in MASK_PATS:
        t, n = re.subn(pat, "[가림]", t)
        MASK_COUNT[where] += n
    return t


# =====================================================================
# 6. 고쳐 쓰기 (모델: Claude Opus 5.5, claude-opus-5-5) — 지시 6-2 규칙대로 사람이 아니라 모델이 씀
#     사람이 '예'라고 하기 전에는 "검토 전 시연"
# =====================================================================
REWRITE_MODEL = "Claude Opus 5.5 (claude-opus-5-5)"
REWRITE_PROMPT = ("아래 보험 약관 조항(hotspot 문장 포함 원문 전체)을 쉬운 우리말로 고쳐 써라. "
                  "보장·면책 조건, 예외, 숫자, 기간, 대상은 하나도 빼거나 더하지 않는다. "
                  "긴 문장은 나누고, 겹친 예외는 목록으로 풀고, 전문용어는 처음 나올 때 괄호로 풀이한다. "
                  "법적 효과가 달라질 수 있는 말은 원문 표현을 유지한다.")
# 고친 문장 고정본(규칙으로 뽑힌 6개). 줄바꿈은 목록을 보이기 위한 것이고 지표 계산 때 공백으로 바뀐다.
REWRITES = {
    "D112": """제9조(보험금의 지급사유)
회사는 피보험자(보험 사고의 대상이 되는 사람)에게 아래 사유 중 어느 하나가 생긴 경우에는 보험수익자(보험금을 받는 사람)에게 약정한 보험금을 지급합니다.
보험금은 [별표 1] "보험금 지급기준표"를 봅니다. 아래에서 말하는 장해분류표는 [별표 4]입니다.
아래 사유는 모두 보험기간 중에 생긴 것이어야 합니다.
1. 유족급여금: 농업작업안전재해 또는 농업작업안전질병으로 사망한 경우. 다만, 농업작업안전질병 중 '유해생물방제제(농약)의 독성효과(T60)'로 인한 사망은 제외합니다.
2. 장례비: 농업작업안전재해 또는 농업작업안전질병으로 사망한 경우. 다만, 농업작업안전질병 중 '유해생물방제제(농약)의 독성효과(T60)'로 인한 사망은 제외합니다.
3. 고도장해급여금: 동일한 농업작업안전재해 또는 동일한 농업작업안전질병으로 장해분류표상 여러 신체부위의 장해지급률(장해 정도에 따라 정한 비율)을 더하여 80% 이상인 장해상태가 되었을 때. 최초 1회에 한합니다. 다만, 부부형은 주피보험자, 종피보험자 각각 최초 1회에 한합니다.
4. 재해장해급여금: 농업작업안전재해로 장해분류표에서 정한 장해지급률 중 3% 이상 80% 미만에 해당하는 장해상태가 되었을 때.
5. 간병(재해장해)급여금: 동일한 농업작업안전재해로 장해분류표상 여러 신체부위의 장해지급률을 더하여 50% 이상인 장해상태가 되었을 때. 최초 1회에 한합니다. 다만, 부부형은 주피보험자, 종피보험자 각각 최초 1회에 한합니다.
6. 간병(질병장해)급여금: 동일한 농업작업안전질병으로 장해분류표상 여러 신체부위의 장해지급률을 더하여 80% 이상인 장해상태가 되었을 때. 최초 1회에 한합니다. 다만, 부부형은 주피보험자, 종피보험자 각각 최초 1회에 한합니다.
7. 재활(고도장해)급여금: 동일한 농업작업안전재해 또는 동일한 농업작업안전질병으로 장해분류표상 여러 신체부위의 장해지급률을 더하여 80% 이상인 장해상태가 되었을 때. 최초 1회에 한합니다. 다만, 부부형은 주피보험자, 종피보험자 각각 최초 1회에 한합니다.
8. 재활(재해장해)급여금: 농업작업안전재해로 장해분류표에서 정한 장해지급률 중 3% 이상 80% 미만에 해당하는 장해상태가 되었을 때.
9. 휴업(입원)급여금: 농업작업안전재해 또는 농업작업안전질병으로 4일 이상 입원하였을 때.
10. 특정질병수술급여금: 특정질병으로 수술을 받았을 때.
11. 특정감염병진단급여금: 특정감염병으로 진단 확정되었을 때.
12. 상해·질병치료급여금: 농업작업안전재해 또는 농업작업안전질병으로 치료를 받았을 때. 다만, 상해·질병치료급여금은 기본형 가입자에 한하여 보장합니다.""",
    "D210": """회사는 피보험자가 이 특별약관의 보험기간 중에 자동차를 운전하던 중 발생한 급격하고도 우연한 자동차사고로 타인에게 아래 1~3 중 어느 하나에 해당하는 상해를 입힌 경우에 보험금을 지급합니다.
- 여기서 자동차에서 이륜자동차는 제외합니다.
- 타인에서 피보험자의 부모, 배우자, 자녀는 제외합니다. 이하 이 타인을 「피해자」라 합니다.
지급하는 금액은 매 사고마다 피해자 각각에 대하여 피보험자가 형사합의금으로 지급한 금액(이하 『형사합의금』이라 합니다)입니다. 회사는 이 금액을 피보험자에게 교통사고처리보장V보험금으로 지급합니다.
1. 피해자를 사망하게 한 경우
2. "중대한법규위반 교통사고"로 피해자가 42일 이상 치료를 요한다는 진단을 받은 경우
- 42일은 피해자 1인을 기준으로 합니다. 다수 피해자는 진단일을 합하여 계산하지 않습니다.
- 다만, 피해자 1인에 대하여 하나의 사고로 최초 진단 이후에 추가진단이 있을 경우에는 진단일을 합하여 적용합니다.
3. "일반교통사고"로 피해자에게 중상해를 입혀 형법 제258조 제1항 또는 제2항, 형법 제268조 또는 교통사고처리특별법 제3조에 따라 검찰에 의해 공소제기(이하 "기소"라 합니다)되거나, 자동차손해배상보장법 시행령 제3조(【별표7】(자동차사고 부상 등급표) 참조)에서 정한 상해급수 1급, 2급 또는 3급에 해당하는 부상을 입힌 경우""",
    "D201": """제2조(보험금의 종류 및 지급사유)
회사는 아래 두 조건이 모두 생기면 보험수익자(보험금을 받는 자)에게 질병 고도장애(1,2급) 생활자금을 지급합니다.
조건 1. 피보험자(보험대상자)가 보험기간 중 진단확정된 질병으로 장애가 발생할 것.
- 장애의 종류: '장애인 복지법 시행령' 제2조 및 '장애인 복지법 시행규칙' 제2조([별표16] 참조)의 지체장애, 뇌병변장애, 시각장애, 청각장애, 언어장애, 지적장애, 신장장애, 심장장애, 간 장애, 안면장애, 장루·요루장애, 호흡기장애 중 하나 이상.
- 단, 자폐장애, 정신장애, 간질장애는 제외합니다.
조건 2. 1급 또는 2급 장애인(지체장애인, 뇌병변장애인, 시각장애인, 청각장애인, 언어장애인, 지적장애인, 신장장애인, 심장장애인, 간 장애인, 안면장애인, 장루·요루장애인, 호흡기장애인)이 될 것.
지급 방법은 다음과 같습니다.
- 최초 1회에 한하여 10년간 매년 지급합니다.
- 지급 금액은 보험증권(보험가입증서)에 기재된 이 특별약관의 보험가입금액입니다.
- 지급일은 보험금 지급사유 발생 해당일입니다. 단, 해당년도에 보험금 지급사유 발생일이 없는 경우에는 보험금 지급사유 발생일이 속한 달의 말일로 합니다.""",
    "D013": """② 제1항에도 불구하고, 사이버몰을 이용하여 계약을 체결한 때에는 청약서 부본을 드리지 아니할 수 있습니다.
사이버몰은 전자거래기본법 제2조 제5호에 의해 컴퓨터를 이용하여 보험거래를 할 수 있도록 설정된 가상의 영업장을 말합니다.
또한 전화를 이용하여 계약을 체결하는 경우에 회사는 다음과 같이 합니다.
1. 계약자의 동의를 얻습니다.
2. 보험계약 체결을 위하여 필요한 사항을 질문 또는 설명합니다. 필요한 사항에는 청약내용, 보험료납입, 보험기간, 계약전 알릴의무, 약관의 중요한 내용 등이 있습니다.
3. 그에 대한 계약자의 답변, 확인내용을 음성 녹음합니다.
이렇게 음성 녹음함으로써 약관의 중요한 내용을 설명한 것으로 봅니다.""",
    "D261": """[별표4] '중대한 질병'의 정의
I. 중대한 암(Critical Cancer)
① '중대한 암'이란 악성종양세포가 존재하고, 그 세포가 주위 조직으로 침윤파괴적 증식(주위 조직을 파고들어 파괴하며 늘어남)을 하는 것으로 특징 지을 수 있는 악성종양을 말합니다.
다음 각호에 해당하는 경우는 보장에서 제외합니다.
1. 다음의 가.~바.에 해당하는 악성종양
가. 악성흑색종(melanoma) 중에서 침범정도가 낮은 경우. 침범정도가 낮은 경우란 Breslow 분류법상 그 깊이가 1.5mm 이하인 경우를 말합니다.
나. 초기전립샘암. 본 상품의 '초기 전립샘암'이란 modified Jewett 병기분류상 stage B0 이하 또는 1992년 TNM병기상 T1c 이하인 모든 전립샘암을 말합니다.
다. 초기갑상샘암. '초기갑상샘암'이란 유두암(papillary cancer) 또는 여포암(follicular cancer)으로서 암 종괴(덩어리)의 크기가 2.0cm 미만이고 림프절 전이나 원격전이가 없는 모든 갑상샘암을 말합니다.
라. 인간면역바이러스(HIV) 감염과 관련된 악성 종양. 단, 의료법에서 정한 의료인의 진료상 또는 치료중 혈액에 의한 HIV 감염과 관련된 악성종양은 해당진료기록을 통해 객관적으로 확인되는 경우는 제외합니다.
마. 악성흑색종(melanoma) 이외의 모든 피부암(C44)
바. 「중대한 질병 및 수술 보장개시일」 이전에 발생한 암이 「중대한 질병 및 수술 보장개시일」 이후에 재발되거나 전이된 경우
2. 병리학적으로 전암병소(premalignant condition or condition with malignant potential), 상피내암(carcinoma in-situ), 경계성종양(borderline malignancy) 등 '중대한 암'에 해당하지 않는 질병
3. 신체부위에 관계없이 병리학적으로 현재 양성종양인 경우
② 암의 진단확정은 해부병리 전문의사 또는 임상병리 전문의사 자격증을 가진 자에 의하여 내려져야 합니다.
이 진단은 다음 검사 중 어느 하나에 대한 현미경 소견을 기초로 하여야 합니다.
- 조직(fixed tissue)검사
- 미세침흡인검사(fine needle aspiration biopsy)
- 혈액(hemic system)검사
③ 위의 병리학적 진단이 가능하지 않을 때에만 암에 대한 임상학적 진단이 그 암의 증거로 인정됩니다.
이 경우에는 피보험자가 암으로 진단 또는 치료를 받고 있음을 증명할 만한, 의사가 작성한 문서화된 기록 또는 증거가 있어야 합니다.""",
    "D030": """제12조(보험료의 납입연체시 납입최고(독촉)와 계약의 해지)
① 계약자가 제2회 이후의 보험료를 납입기일까지 납입하지 아니하는 때에는 다음과 같이 합니다.
1. 납입기일 다음날부터 납입기일이 속하는 달의 다음달 말일까지를 납입최고(독촉)기간으로 합니다.
2. 회사는 제3항에서 정한 바에 따라 최고(납입을 독촉)합니다.
3. 납입최고(독촉)기간 안에 보험료가 납입되지 아니하는 경우, 회사는 납입최고(독촉)기간이 끝나는 날의 다음날 계약을 해지합니다.
4. 납입최고(독촉)기간 안에 발생한 사고에 대하여 회사는 약정한 보험금을 지급합니다.
② 제1항에 불구하고, 회사의 책임 있는 사유로 인하여 계약자가 보험료를 납입하지 못한 경우에는 납입기일부터 3개월이 되는 날까지를 납입최고(독촉)기간으로 하여 제1항을 적용합니다.
회사의 책임 있는 사유에는 회사의 방문수금 불이행, 은행 납입통지서의 미교부, 자동이체 미신청 등이 있습니다.
다만, 회사가 다시 보험료를 수금 또는 자동이체하기로 하거나 은행납입통지서를 교부하기로 한 경우에는, 그 수금(자동이체) 또는 재교부일부터 15일이 되는 날을 새로운 납입기일로 하여 제1항의 납입최고(독촉)기간을 적용합니다.
③ 제2회 이후의 보험료가 납입기일까지 납입되지 아니하여 보험료 납입이 연체중인 경우, 회사는 납입최고(독촉)기간이 끝나기 15일 이전까지 서면 또는 전화(음성녹음)로 다음 내용을 알려 드립니다.
- 알리는 대상: 계약자(타인을 위한 보험의 경우 특정된 보험금을 받을 수익자(보험수익자 포함))
- 알리는 내용 1: 납입최고(독촉)기간 안에 연체된 보험료를 납입하여야 한다는 내용
- 알리는 내용 2: 납입최고(독촉)기간이 끝나는 날까지 보험료가 납입되지 않은 경우
④ 제1항에 따라 계약이 해지된 경우에는 해약환급금(계약이 해지될 때 회사가 계약자에게 돌려주는 금액)을 지급합니다.""",
}
# 고친 사람(모델) 메모: 사람 확인 때 특히 볼 곳
REWRITE_MEMO = {
    "D112": "(시연자 메모) 매 호의 '보험기간 중'을 앞으로 한 번 모음. 1·2호는 원문처럼 반복.",
    "D210": "(시연자 메모) 3호는 '중상해를 입혀'가 뒤 조건(상해급수 1~3급)에도 걸리는지 원문이 모호해 원문 문장 그대로 둠.",
    "D201": "(시연자 메모) '발생하고 … 되었을 때'를 '두 조건이 모두'로 풀었음.",
    "D013": "(시연자 메모) 원문 '제1항의 제1항에도'를 '제1항에도'로 줄였음(원문 오기로 보임). '제1항에도 불구하고'는 원문처럼 첫 문장에만 붙임.",
    "D261": "(시연자 메모) 라.의 '단, … 제외'(제외의 제외)는 원문 표현 유지.",
    "D030": "(시연자 메모) 원문 '지동이체'를 '자동이체'로 고침(오기로 보임). ③ 알리는 내용 2는 원문에 결과가 적혀 있지 않아 더하지 않음.",
}


# =====================================================================
# 실행
# =====================================================================
def main():
    os.makedirs(FIG, exist_ok=True)
    log = {}

    # ---------------- 2. 표준약관 ----------------
    arts = extract_standard()
    units, excluded_defs = build_units(arts)
    ind_std = pd.DataFrame([indicators10(t, record=("std" if u == "조" else None))
                            for t, u in zip(units["text"], units["unit"])])
    units = pd.concat([units.reset_index(drop=True), ind_std], axis=1)
    assert not units[(units.unit == "조")]["uid"].str.contains("용어").any()
    log["arts"] = arts
    log["excluded_defs"] = excluded_defs

    rows11 = []
    for st in STD_TYPES + ["전체"]:
        for u in ["조", "항", "문장"]:
            s = units[(units.unit == u) & ((units.std_type == st) if st != "전체" else True)]
            r = {"std_type": st, "unit": u, "n_units": len(s), "usable_n50": int(len(s) >= 50),
                 "used_as_benchmark": int(st == "전체")}
            for c in IND:
                r[f"{c}_median"] = round(float(s[c].median()), 4)
                r[f"{c}_p90"] = round(float(np.percentile(s[c].astype(float), 90)), 4)
            rows11.append(r)
    df11 = pd.DataFrame(rows11)
    df11.to_csv(os.path.join(OUT, "11_표준약관기준.csv"), index=False, encoding=ENC)
    B_ART = units[units.unit == "조"]
    B_HANG = units[units.unit == "항"]
    B_SENT = units[units.unit == "문장"]
    for nm, b in (("조", B_ART), ("항", B_HANG), ("문장", B_SENT)):
        if len(b) < 50:
            sys.exit(f"표준약관 전체 {nm} 단위가 50 미만입니다. 멈춥니다.")

    # ---------------- 3. 결정례 조항 ----------------
    cases = pd.read_csv(p("data", "interim", "cases.csv"), encoding=ENC, dtype={"case_key": str})
    idmap = pd.read_csv(p("data", "interim", "difficulty_id_map.csv"), encoding=ENC, dtype=str)
    diff = pd.read_csv(p("data", "processed", "difficulty.csv"), encoding=ENC)
    assert len(diff) == 261 and len(idmap) == 261
    cols = ["case_key", "exclude_reason", "topic", "issue_type", "period", "clause_level",
            "clause_text", "clause_text_article"]
    cc = cases[cases["clause_text"].fillna("").str.strip() != ""][cols]
    rows = []
    for _, m in idmap.iterrows():
        cand = cc[cc.case_key == m.case_key]
        if m.case_key == DUP_KEY:
            cand = cand[cand.exclude_reason.isna()] if m.diff_id == DUP_CHOSEN else cand[cand.exclude_reason.notna()]
        assert len(cand) == 1, (m.diff_id, m.case_key, len(cand))
        r = cand.iloc[0].to_dict()
        r["diff_id"] = m.diff_id
        r["in_analysis"] = int(pd.isna(r["exclude_reason"]) and m.diff_id != DUP_DROPPED)
        rows.append(r)
    prof = pd.DataFrame(rows)
    prof = prof.merge(diff, on="diff_id", how="left", suffixes=("", "_diff"), validate="one_to_one")
    assert int(prof.in_analysis.sum()) == 157

    # 기존 4개 지표 다시 계산해 difficulty.csv와 대조(차이는 보고, 값은 difficulty.csv)
    re_old = pd.DataFrame([old_indicators(t) for t in prof["clause_text"]])
    chk = {}
    for mine, theirs in (("term_ratio", "term_ratio"), ("words_per_sentence", "words_per_sentence"),
                         ("exception_count", "exception_count"), ("ref_count", "ref_count"),
                         ("ref_chain", "ref_count_chain")):
        diffv = (re_old[mine].astype(float) - prof[theirs].astype(float)).abs()
        chk[mine] = int((diffv > 1e-9).sum())
    log["recompute_mismatch"] = chk

    # 원래 단위(clause_text) 지표: 기존 = difficulty.csv, 새 = 계산
    orig = pd.DataFrame({"term_ratio": prof["term_ratio"], "words_per_sentence": prof["words_per_sentence"],
                         "exception_count": prof["exception_count"], "ref_count": prof["ref_count"],
                         "ref_chain": prof["ref_count_chain"]})
    new_o = pd.DataFrame([new_indicators(t) for t in prof["clause_text"]])
    orig = pd.concat([orig, new_o], axis=1)[IND]

    # 조 단위(clause_text_article)
    art_txt = prof["clause_text_article"].fillna("")
    empty = art_txt.str.strip() == ""
    same = [dc.norm(a) == dc.norm(b) for a, b in zip(art_txt, prof["clause_text"])]
    prof["bench_note"] = np.where(empty, "clause_text_article 비어 clause_text 사용",
                                  np.where(same, "조 전체 = 원래 문구", ""))
    art_txt = art_txt.where(~empty, prof["clause_text"])
    rec_mask = prof["in_analysis"] == 1
    art_rows = []
    for t, rec, use_orig, (_, o) in zip(art_txt, rec_mask, (empty | pd.Series(same)), orig.iterrows()):
        if use_orig:          # 문구가 clause_text와 같으면 기존 4개는 difficulty.csv 값
            d = dict(o)
            d.update(new_indicators(t, record=("dec" if rec else None)))
        else:
            d = indicators10(t, record=("dec" if rec else None))
        art_rows.append({c: d[c] for c in IND})
    art = pd.DataFrame(art_rows)
    log["n_art_own"] = int((~(empty | pd.Series(same))).sum())

    df12 = prof[["diff_id", "case_key", "in_analysis", "topic", "issue_type", "period", "clause_level",
                 "bench_note"]].copy()
    df12 = pd.concat([df12, art], axis=1)
    df12 = add_pct(df12, B_ART, IND)
    df12 = dim_scores(df12, DIMS)
    for k in DIMS:
        df12[f"high_{k}"] = (df12[f"dim_{k}"] >= HIGH).astype(int)
    df12["top_dim"] = df12.apply(top_dim, axis=1)
    # 보조: 원래 단위(조 → 조 분포, 항·호 → 항 분포)
    o2 = orig.copy()
    for c in IND:
        o2["po_" + c] = np.nan
    for i, lev in enumerate(prof["clause_level"]):
        b = B_ART if lev == "조" else (B_HANG if lev in ("항", "호") else None)
        if b is None:
            continue
        for c in IND:
            o2.loc[i, "po_" + c] = pct_of(b[c].astype(float).values, orig.loc[i, c])
    for k, cs in DIMS.items():
        df12[f"dim_{k}_orig"] = o2[["po_" + c for c in cs]].mean(axis=1)
    df12["top_dim_rel"] = df12.apply(top_dim_rel, axis=1)   # 수정 1-4: 맨 뒤 열로 추가(기존 열 순서 유지)
    df12 = df12.sort_values("diff_id").reset_index(drop=True)
    num = df12.select_dtypes("number").columns
    df12[num] = df12[num].round(4)
    df12.to_csv(os.path.join(OUT, "12_조항프로필.csv"), index=False, encoding=ENC)
    orig_by_id = pd.concat([prof[["diff_id", "clause_level", "clause_text"]], orig], axis=1).set_index("diff_id")

    A = df12[df12.in_analysis == 1].copy()

    # ---------------- 4. 문장 핫스팟 ----------------
    rows14 = []
    for _, r in A.iterrows():
        txt = dc.norm(prof.loc[prof.diff_id == r.diff_id, "clause_text"].iloc[0])
        sents = [s.text for s in KIWI.split_into_sents(txt) if s.text.strip()] or [txt]
        best = None
        for si, s in enumerate(sents, 1):
            d = indicators10(s)
            pc = {c: pct_of(B_SENT[c].astype(float).values, d[c]) for c in IND}
            ds = {k: float(np.mean([pc[c] for c in cs])) for k, cs in SENT_DIMS.items()}
            score = float(np.mean(list(ds.values())))
            if best is None or score > best[0]:
                best = (score, si, s, ds)
        score, si, s, ds = best
        hd = max(SENT_DIMS, key=lambda k: (ds[k], -list(SENT_DIMS).index(k)))
        rows14.append({"diff_id": r.diff_id, "case_key": r.case_key, "topic": r.topic, "n_sents": len(sents),
                       "sent_no": si, "hotspot_text": mask(s, "hotspot"), "hotspot_dim": DIM_KO[hd],
                       **{f"dim_{k}": round(ds[k], 4) for k in SENT_DIMS}})
    df14 = pd.DataFrame(rows14).sort_values("diff_id").reset_index(drop=True)
    df14.to_csv(os.path.join(OUT, "14_문장핫스팟.csv"), index=False, encoding=ENC)

    # ---------------- 5. 요약 ----------------
    t10 = pd.read_csv(os.path.join(OUT, "10_조항주제.csv"), encoding=ENC)
    t02 = pd.read_csv(os.path.join(OUT, "02_기술통계.csv"), encoding=ENC)
    order_td = [DIM_KO[k] for k in DIMS] + ["없음"]

    def mode_td(s):
        vc = s.value_counts()
        mx = vc.max()
        return [x for x in order_td if vc.get(x, 0) == mx][0]

    def group_row(s):
        r = {"n": len(s)}
        if len(s) < 5:
            return r
        for k in DIMS:
            r[f"dim_{k}_median"] = round(float(s[f"dim_{k}"].median()), 2)
        for k in DIMS:
            r[f"high_{k}_rate"] = round(float(s[f"high_{k}"].mean()), 4)
        r["top_dim_mode"] = mode_td(s["top_dim"])
        return r

    rows13 = []
    for tp, s in A.groupby("topic"):
        r = {"topic": tp, **group_row(s)}
        cr = t10.loc[t10.topic == tp, "cited_rate"]
        r["cited_rate"] = float(cr.iloc[0]) if len(cr) and len(s) >= 5 else np.nan
        rows13.append(r)
    colorder = ["topic", "n", "cited_rate"] + [f"dim_{k}_median" for k in DIMS] + \
               [f"high_{k}_rate" for k in DIMS] + ["top_dim_mode"]
    df13 = pd.DataFrame(rows13).reindex(columns=colorder).sort_values(["n", "topic"], ascending=[False, True]).reset_index(drop=True)
    df13.to_csv(os.path.join(OUT, "13_주제별프로필.csv"), index=False, encoding=ENC)

    rows13b = []
    for var, col02 in (("issue_type", "period"), ("period", "issue_type")):
        for g, s in A.groupby(var):
            r = {"group_var": var, "group": g, **group_row(s)}
            q = t02[(t02[var] == g) & (t02[col02] == "전체")]["cited_rate"]
            r["cited_rate"] = float(q.iloc[0]) if len(q) and len(s) >= 5 else np.nan
            rows13b.append(r)
    df13b = pd.DataFrame(rows13b).reindex(columns=["group_var", "group"] + colorder[1:])
    df13b.to_csv(os.path.join(OUT, "13b_유형시기별프로필.csv"), index=False, encoding=ENC)

    # 차원 간 스피어만(157, 조 단위)
    dimc = [f"dim_{k}" for k in DIMS]
    sp = pd.DataFrame(index=dimc, columns=dimc, dtype=float)
    for a in dimc:
        for b in dimc:
            sp.loc[a, b] = stats.spearmanr(A[a], A[b]).statistic
    log["dim_corr"] = sp.round(3)

    # 사람 평가 타당성(탐색적)
    ev = pd.read_csv(p("data", "processed", "평가점수.csv"), encoding=ENC)
    emap = pd.read_csv(p("outputs", "stats", "eval_map.csv"), encoding=ENC)
    raters = [c for c in ev.columns if c != "eval_id"]
    log["raters"] = raters
    ev["rater_mean"] = ev[raters].mean(axis=1)
    ev = ev.merge(emap, on="eval_id", how="inner", validate="one_to_one")
    ev = ev.merge(df12, on="diff_id", how="left", validate="one_to_one")
    ev = ev.merge(orig_by_id[IND].add_prefix("orig_"), left_on="diff_id", right_index=True, how="left")
    n = len(ev)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, n, size=(N_BOOT, n))
    # 수정 1-6: 조 단위 = 기본(앞 14행), 원래 단위 = 부록(뒤 14행).
    # 부트스트랩 표본(idx)은 모든 측정이 같이 쓰므로 순서를 바꿔도 값은 같다.
    measures = [(f"dim_{k}(조 단위)", f"dim_{k}") for k in DIMS] + \
               [(f"{c}(조 단위)", c) for c in IND] + \
               [(f"dim_{k}_orig(원래 단위)", f"dim_{k}_orig") for k in DIMS] + \
               [(f"{c}(원래 단위)", f"orig_{c}") for c in IND]
    rows15 = []
    y = ev["rater_mean"].values.astype(float)
    for lab, col in measures:
        x = ev[col].values.astype(float)
        ok = ~np.isnan(x)
        rho = stats.spearmanr(x[ok], y[ok]).statistic if ok.sum() > 2 else np.nan
        boots = []
        for b in range(N_BOOT):
            ii = idx[b]
            xb, yb = x[ii], y[ii]
            okb = ~np.isnan(xb)
            if okb.sum() > 2 and np.unique(xb[okb]).size > 1 and np.unique(yb[okb]).size > 1:
                boots.append(stats.spearmanr(xb[okb], yb[okb]).statistic)
        lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan))
        rows15.append({"measure": lab, "role": "기본(조 단위)" if "(조 단위)" in lab else "부록(원래 단위)",
                       "spearman": round(float(rho), 4), "ci_low": round(float(lo), 4),
                       "ci_high": round(float(hi), 4), "n": int(ok.sum()),
                       "note": "탐색적. 평가 점수 = 두 평가자 평균. 기본 14개·부록 14개를 함께 봐서 다중 비교 보정 없음"})
    rows15.append({"measure": "참고: 두 평가자 가중 카파(quadratic)", "role": "참고", "spearman": 0.059, "ci_low": -0.209,
                   "ci_high": 0.328, "n": n, "note": "평가일치도.md 값. 일치도 낮음(0.4 미만) → 위 상관은 해석 제한"})
    df15 = pd.DataFrame(rows15)
    df15.to_csv(os.path.join(OUT, "15_평가타당성.csv"), index=False, encoding=ENC)

    # ---------------- 6. 고쳐 쓰기 ----------------
    elig = df13[(df13.n >= 10) & df13.cited_rate.notna()].copy()
    elig["score"] = (elig["n"] * elig["cited_rate"]).round(6)
    top_topics = elig.sort_values(["score", "topic"], ascending=[False, True])["topic"].head(2).tolist()
    A["dim_mean"] = A[dimc].mean(axis=1)
    picks = []
    for tp in top_topics:
        s = A[A.topic == tp].sort_values(["dim_mean", "diff_id"], ascending=[False, True]).head(3)
        picks += s["diff_id"].tolist()
    log["top_topics"] = top_topics
    log["elig"] = elig
    log["picks"] = picks
    missing = [d for d in picks if d not in REWRITES]
    rows16, sheet = [], []
    if missing:
        print("고쳐 쓴 문장이 없는 조항:", missing)
        for d in missing:
            r = orig_by_id.loc[d]
            print(f"--- {d} ({r.clause_level}) ---\n{dc.norm(r.clause_text)}\n")
    else:
        for i, d in enumerate(picks, 1):
            r = orig_by_id.loc[d]
            bench = B_ART if r.clause_level == "조" else B_HANG
            before = {c: float(r[c]) for c in IND}
            after = indicators10(REWRITES[d])
            row = {"rewrite_id": f"R{i}", "diff_id": d, "topic": A.loc[A.diff_id == d, "topic"].iloc[0],
                   "clause_level": r.clause_level, "bench_unit": "조" if r.clause_level == "조" else "항"}
            for tag, vals in (("before", before), ("after", after)):
                pc = {c: pct_of(bench[c].astype(float).values, vals[c]) for c in IND}
                for k, cs in DIMS.items():
                    row[f"dim_{k}_{tag}"] = round(float(np.mean([pc[c] for c in cs])), 4)
            for c in IND:
                row[f"{c}_before"] = round(before[c], 4)
                row[f"{c}_after"] = round(float(after[c]), 4)
            rows16.append(row)
            sheet.append({"rewrite_id": f"R{i}", "diff_id": d, "원문": mask(dc.norm(r.clause_text), "rewrite"),
                          "고친 문장": mask(REWRITES[d], "rewrite"), "질문": "뜻이 같은가?",
                          "답(예/아니오/일부 다름)": "", "메모": REWRITE_MEMO.get(d, "")})
        # 수정 1-5: 뜻확인 시트는 사람이 답을 적은 파일이다. 있으면 절대 다시 쓰지 않고 읽기만 한다.
        sheet_path = os.path.join(REPORT_DIR, "고쳐쓰기_뜻확인.csv")
        if os.path.exists(sheet_path):
            ans = pd.read_csv(sheet_path, encoding=ENC, dtype=str, keep_default_na=False)
            acol = "답(예/아니오/일부 다름)"
            ans_map = dict(zip(ans["rewrite_id"], ans[acol].str.strip()))
            # 시트의 원문·고친 문장이 지금 코드와 같은지 대조(다르면 보고)
            cur = pd.DataFrame(sheet).set_index("rewrite_id")
            log["sheet_text_mismatch"] = [rid for rid in cur.index
                                          if rid not in set(ans.rewrite_id)
                                          or ans.set_index("rewrite_id").loc[rid, "원문"] != cur.loc[rid, "원문"]
                                          or ans.set_index("rewrite_id").loc[rid, "고친 문장"] != cur.loc[rid, "고친 문장"]]
        else:
            ans_map = {}
            os.makedirs(REPORT_DIR, exist_ok=True)
            pd.DataFrame(sheet).to_csv(sheet_path, index=False, encoding=ENC)
            log["sheet_text_mismatch"] = []
        for row in rows16:
            a = ans_map.get(row["rewrite_id"], "")
            row["human_answer"] = a if a else "(빈 칸)"
            row["status"] = "사람 확인 완료" if a == "예" else "검토 전 시연"
        log["answers"] = {r["rewrite_id"]: r["human_answer"] for r in rows16}
        pd.DataFrame(rows16).to_csv(os.path.join(OUT, "16_고쳐쓰기.csv"), index=False, encoding=ENC)
    df16 = pd.DataFrame(rows16)

    # ---------------- 7. 그림 ----------------
    figs = make_figs(df13, A, df16, df11, df12)

    # ---------------- 요약 md ----------------
    write_summary(log, units, df11, df12, A, df13, df13b, df14, df15, df16, figs)
    print("완료")


def make_figs(df13, A, df16, df11, df12=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False
    figs = {}
    t = df13[df13.n >= 5].copy()
    dmc = [f"dim_{k}_median" for k in DIMS]
    # A1
    M = t[dmc].values.astype(float)
    fig, ax = plt.subplots(figsize=(7, 0.6 * len(t) + 1.8))
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(4), [DIM_KO[k] for k in DIMS])
    ax.set_yticks(range(len(t)), [f"{a} ({b}건)" for a, b in zip(t.topic, t.n)])
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=10,
                    color="white" if v >= 60 else "black", fontweight="bold" if v >= HIGH else "normal")
            if v >= HIGH:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="red", lw=2.5))
    hi_i, hi_j = np.unravel_index(np.nanargmax(M), M.shape)
    title = f"주제별 난이도 차원(표준약관 조 대비 백분위 중앙값):" + chr(10) + f"가장 높은 칸은 {t.topic.iloc[hi_i]}의 {DIM_KO[list(DIMS)[hi_j]]} {M[hi_i, hi_j]:.0f}"
    if df12 is not None:   # 2026-11-05 추가: 가장 높은 칸 주제의 시기 구성(시기 차이 주의)
        _a = df12[(df12.in_analysis == 1) & (df12.topic == t.topic.iloc[hi_i])]
        _old = int((_a.period == "~2009").sum())
        title += chr(10) + f"(이 주제 {len(_a)}건 중 {_old}건이 2009년 이전 결정이라 현행 약관과의 차이는 시기 차이일 수 있다)"
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_A1_주제별차원.png"), dpi=200)
    plt.close(fig)
    figs["A1"] = (title.replace(chr(10), " "), "칸 숫자 = 그 주제 조항들의 차원 점수(표준약관 조 단위 백분위) 중앙값, 빨간 테두리 = 90 이상. 5건 미만 주제는 뺌.")
    # A2
    fig, ax = plt.subplots(figsize=(7, 4.2))
    data = [A[f"dim_{k}"].values for k in DIMS]
    ax.boxplot(data, tick_labels=[DIM_KO[k] for k in DIMS], showfliers=True)
    ax.axhline(HIGH, color="red", ls="--", lw=1.2)
    ax.text(0.55, HIGH + 1.5, "표준약관 상위 10% 기준선(90)", color="red", ha="left", va="bottom", fontsize=8,
            bbox=dict(facecolor="white", edgecolor="none", pad=1))
    rates = {k: float((A[f"dim_{k}"] >= HIGH).mean()) for k in DIMS}
    kmax = max(DIMS, key=lambda k: rates[k])
    title = f"결정례 조항(157건) 차원 점수: 90 이상 비율이 가장 큰 차원은 {DIM_KO[kmax]}({rates[kmax] * 100:.1f}%)"
    ax.set_title(title, fontsize=10)
    ax.set_ylabel("표준약관 조 단위 대비 백분위")
    ax.set_ylim(0, 105)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_A2_표준약관대비.png"), dpi=200)
    plt.close(fig)
    figs["A2"] = (title, "상자 = 157건 조 단위 차원 점수 분포, 빨간 점선 = 표준약관 조 분포의 90 백분위.")
    # A3
    if len(df16):
        n_ok = int((df16.status == "사람 확인 완료").sum())
        st_lab = "사람 뜻 확인 완료" if n_ok == len(df16) else ("검토 전" if n_ok == 0 else f"사람 확인 {n_ok}/{len(df16)}")
        fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharey=True)
        x = np.arange(4)
        for ax, (_, r) in zip(axes.ravel(), df16.iterrows()):
            b = [r[f"dim_{k}_before"] for k in DIMS]
            a = [r[f"dim_{k}_after"] for k in DIMS]
            ax.bar(x - 0.2, b, 0.4, label="고치기 전", color="#888888")
            ax.bar(x + 0.2, a, 0.4, label=f"고친 뒤({r.status})", color="#2b7bba")
            ax.axhline(HIGH, color="red", ls="--", lw=1)
            ax.set_xticks(x, [DIM_KO[k] for k in DIMS], fontsize=8)
            ax.set_title(f"{r.rewrite_id} {r.diff_id} ({r.topic}) - {r.status}", fontsize=9)
            ax.set_ylim(0, 105)
        axes[0, 0].legend(fontsize=7)
        mb = df16[[f"dim_{k}_before" for k in DIMS]].values.mean()
        ma = df16[[f"dim_{k}_after" for k in DIMS]].values.mean()
        title = f"고쳐 쓰기 시연 6개({st_lab}, 법률 검토 아님): 차원 점수 평균 {mb:.0f} → {ma:.0f}"
        fig.suptitle(title, fontsize=11)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, "fig_A3_고쳐쓰기전후.png"), dpi=200)
        plt.close(fig)
        figs["A3"] = (title, "회색 = 원문, 파랑 = 고친 문장(칸 제목에 사람 뜻 확인 상태). 기준 분포는 원래 단위(조 → 조, 항·호 → 항).")
    # A4
    t4 = df13[df13.n >= 5].copy()
    # 수정 1-4: 점 색 = 주제별 top_dim_rel(90 기준과 상관없이 가장 높은 차원)의 최빈값. 표시용, 검정 없음.
    order_rel = [DIM_KO[k] for k in DIMS]

    def mode_rel(s):
        vc = s.value_counts()
        return [x for x in order_rel if vc.get(x, 0) == vc.max()][0]
    rel = A.groupby("topic")["top_dim_rel"].apply(mode_rel)
    t4["top_dim_rel_mode"] = t4.topic.map(rel)
    colors = {"어휘": "#1b9e77", "문장 구조": "#d95f02", "논리 구조": "#7570b3", "참조 구조": "#e7298a", "없음": "#999999"}
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for td in order_rel:
        s = t4[t4.top_dim_rel_mode == td]
        if len(s):
            ax.scatter(s.n, s.cited_rate, s=s.n * 8, c=colors[td], alpha=0.7,
                       label=f"가장 높은 차원(최빈): {td}", edgecolor="k")
    xmax = float(t4.n.max())
    for _, r in t4.iterrows():
        right = r.n > 0.8 * xmax
        ax.annotate(r.topic, (r.n, r.cited_rate), fontsize=8, xytext=(-22 if right else 6, 12 if right else 6),
                    textcoords="offset points", ha="right" if right else "left")
    ylo, yhi = float(t4.cited_rate.min()), float(t4.cited_rate.max())
    pad = (yhi - ylo) * 0.12
    ax.set_ylim(ylo - pad, yhi + pad)
    ax.set_xlim(0, xmax * 1.08)
    ax.set_xlabel("건수(분석 포함 157건 중)")
    ax.set_ylabel("인용률(10_조항주제.csv 값)")
    big = t4.sort_values("n", ascending=False).iloc[0]
    title = f"주제별 건수와 인용률: {big.topic}가 {int(big.n)}건으로 가장 많다" + chr(10) + \
        "(점 색 = 90 기준과 상관없이 가장 높은 차원의 최빈값, 표시용)"
    ax.set_title(title, fontsize=10)
    lg = ax.legend(fontsize=7, loc="lower right")
    for h in lg.legend_handles:
        h.set_sizes([40])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_A4_우선순위.png"), dpi=200)
    plt.close(fig)
    figs["A4"] = (title.replace(chr(10), " "), "x = 건수, y = 인용률(기존 10번 표 값을 옮김, 검정 안 함), 점 크기 = 건수, 점 색 = 12번 top_dim_rel의 주제별 최빈값(표시용, 검정 없음). 5건 미만 주제는 뺌.")
    return figs


def md(df, cols=None):
    """수정 1-7: 빈 값(nan)은 '–'로 보인다."""
    d = (df if cols is None else df[cols]).reset_index(drop=True)
    d = d.astype(object).where(d.notna(), "–")
    return dc.md_table(d)


def write_summary(log, units, df11, df12, A, df13, df13b, df14, df15, df16, figs):
    L = []
    w = L.append
    w("# 난이도 프로필 요약 (탐색적 보조 분석)\n")
    w("**성격**: 탐색적 기술 분석. 주 결과(05 난이도 오즈비 0.770 [0.524, 1.130], \"연관이 뚜렷하지 않다\")는 바꾸지 않는다. "
      "새 지표·차원 점수는 `cited`와 검정하거나 회귀에 넣지 않았다. 인용률은 기존 표(10번·02번) 값을 옆에 붙였을 뿐이다. "
      "새 지표 5개(☆ noun_chain_max, ec_per_sentence, etm_per_sentence, cond_per_sentence, neg_count)는 "
      "**탐색적, 결과를 본 뒤 추가**한 지표다. ref_chain은 기존 지표(★)라 difficulty.csv의 ref_count_chain을 그대로 썼다.\n")
    w("## 표준약관 기준\n")
    w("- 기준 분포 = 표준약관 3종 합친 '전체' 분포(종류별 분포는 11번 표에 참고로 적음). 같은 값은 중간 순위 백분위.\n")
    w(md(df11[["std_type", "unit", "n_units", "usable_n50"]]) + "\n")
    w("\n표준약관 '전체' 기준표(중앙값 / 90 백분위 원값):\n")
    rows = []
    for c in IND:
        r = {"지표": c}
        for u in ["조", "항", "문장"]:
            s = df11[(df11.std_type == "전체") & (df11.unit == u)].iloc[0]
            r[f"{u} 중앙값"] = s[f"{c}_median"]
            r[f"{u} p90"] = s[f"{c}_p90"]
        rows.append(r)
    w(md(pd.DataFrame(rows)) + "\n")
    s = df11[(df11.std_type == "전체") & (df11.unit == "문장")].iloc[0]
    w(f"\n읽는 법: 표준약관 문장 상위 10% = 문장당 {s['words_per_sentence_p90']:.0f}어절 이상, "
      f"문장당 조건 표현 {s['cond_per_sentence_p90']:.0f}개 이상, 연결어미 {s['ec_per_sentence_p90']:.0f}개 이상.\n")
    w("\n## 주제별 프로필 (157건, 조 단위)\n")
    w("- 빈 칸(–) = 5건 미만 주제라 건수만 적음.\n\n")
    w(md(df13) + "\n")
    n_none = int((A.top_dim == "없음").sum())
    w(f"\n- **결과: 157건 중 {n_none}건({n_none / len(A) * 100:.1f}%)은 차원 점수가 모두 90 미만이라 top_dim이 '없음'이다.**\n")
    rel = A.top_dim_rel.value_counts()
    w("- 90 기준과 상관없이 가장 높은 차원(12번 `top_dim_rel`, 표시용·검정 없음): "
      + ", ".join(f"{k} {int(rel.get(k, 0))}" for k in [DIM_KO[x] for x in DIMS]) + ". 그림 A4 점 색에만 썼다.\n")
    w("\n## 쟁점 유형별·시기별\n")
    w(md(df13b) + "\n")
    w("\n## 차원 간 스피어만 상관 (157건, 조 단위)\n")
    w(dc.md_table(log["dim_corr"].reset_index()) + "\n")
    w("\n## 사람 평가와의 관계 (탐색적, 24개)\n")
    w(f"- 평가자 열: {', '.join(log['raters'])} (utf-8-sig로 정상 읽힘). 평가 점수 = 두 평가자 평균. 부트스트랩 1,000회, 시드 42.\n")
    w("- **두 평가자 가중 카파 0.059**(평가일치도.md) → 평균 점수 자체의 신뢰도가 낮아 아래 상관은 해석이 제한된다.\n")
    w("- **다중 비교 한계**: 기본 14개(차원 4 + 지표 10)와 부록 14개, 모두 28개 측정을 한꺼번에 봤고 보정하지 않았다. "
      "95% CI가 0을 넘지 않는 측정이 있어도 우연일 수 있다.\n")
    b15 = df15[df15.role == "기본(조 단위)"]
    a15 = df15[df15.role == "부록(원래 단위)"]
    ok = b15[(b15.ci_low > 0) | (b15.ci_high < 0)]
    w("- 기본(조 단위)에서 95% CI가 0을 넘지 않는 측정: "
      + (", ".join(f"{r.measure} {r.spearman:.3f} [{r.ci_low:.3f}, {r.ci_high:.3f}]" for r in ok.itertuples()) or "없음")
      + ".\n\n")
    w("### 기본: 조 단위 (12번 주 열)\n\n")
    w(md(pd.concat([b15, df15[df15.role == "참고"]]), ["measure", "spearman", "ci_low", "ci_high", "n"]) + "\n")
    w("\n### 부록: 원래 단위 (평가자가 본 `clause_text`)\n\n")
    w(md(a15, ["measure", "spearman", "ci_low", "ci_high", "n"]) + "\n")
    w("\n## 문장 핫스팟\n")
    w(f"- 157건 각각 가장 어려운 문장 1개(14번 표). hotspot_dim 분포: "
      + ", ".join(f"{k} {v}" for k, v in df14.hotspot_dim.value_counts().items()) + "\n")
    w(f"- 가림 처리: hotspot {MASK_COUNT['hotspot']}건, 고쳐 쓰기 원문·고친 문장 {MASK_COUNT['rewrite']}건. "
      "약관 문구 속 질병명(예: 악성신생물)은 일반 약관 용어라 가리지 않는다(수정 1-2에서 인정).\n")
    w("\n## 고쳐 쓰기 시연 (가독성 시연, 법률 검토 아님)\n")
    w(f"- 대상 주제(건수 10 이상 중 건수 × 인용률 상위 2): {', '.join(log['top_topics'])}\n")
    w(f"- 대상 조항: {', '.join(log['picks'])}\n")
    w(f"- 모델: {REWRITE_MODEL}. 지시 문구: \"{REWRITE_PROMPT}\"\n")
    w("- **법률 자문이 아니라 가독성 시연이다. 사람이 뜻이 같다고 확인('예')하기 전에는 검토 전 시연으로만 쓴다.**\n")
    if len(df16):
        n_ok = int((df16.status == "사람 확인 완료").sum())
        w(f"- 사람 뜻 확인(`docs/보고/고쳐쓰기_뜻확인.csv` 답 칸): '예' {n_ok}개 / 6개. "
          "'예'인 것만 '사람 확인 완료', 나머지는 '검토 전 시연'이다(`16_고쳐쓰기.csv`의 human_answer·status 열).\n")
        w("- 원문 오기를 고쳐 쓴 곳(사람 확인 대상): R4(D013) 원문 '제1항의 제1항에도' → '제1항에도', "
          "R6(D030) 원문 '지동이체' → '자동이체'. R6 ③의 '알리는 내용 2'는 원문에 결과가 적혀 있지 않아 더하지 않았다.\n\n")
        w(md(df16, ["rewrite_id", "diff_id", "topic", "clause_level"] +
             [f"dim_{k}_{t}" for k in DIMS for t in ("before", "after")] + ["human_answer", "status"]) + "\n")
    w("\n## 그림\n")
    for k, (title, desc) in figs.items():
        w(f"- `figs/fig_{k}_*.png` — {title}. {desc}\n")
    w("\n## 한계\n")
    w("1. 표준약관은 현행본(2026. 9. 10. 시행), 결정례 약관은 1998~2026년 결정의 것이다(분석 포함 기준). 옛 약관이 높게 나오는 것은 시기 차이일 수 있다.\n")
    w("2. 전문용어 사전이 표준약관 '용어의 정의'에서 나와, 어휘 차원(term_ratio)은 표준약관에 유리하다(용어 정의 조는 기준에서 뺐음).\n")
    w("3. 새 지표 5개(☆)는 결과를 본 뒤 추가한 탐색적 지표다.\n")
    w("4. 인용과의 관계는 검정하지 않았다(인용률은 기존 표 값을 붙임).\n")
    w("5. 사람 평가는 24개, 두 평가자 일치도가 낮다(가중 카파 0.059). 측정 28개(기본 14·부록 14)를 보정 없이 봤다.\n")
    w("6. 고쳐 쓰기는 법률 검토가 아니라 가독성 시연이다. 사람 뜻 확인은 '뜻이 같은가'만 본 것이고, "
      "답이 '예'가 아닌 것은 검토 전 시연으로 남는다.\n")
    w("7. 표준약관 추출 규칙 두 가지(수정 1-3에서 인정)로 어절 수에 오차가 남을 수 있다.\n"
      "   - 표: 2행 이상 표는 표 셀로 보고 뺐다. 다만 실손 '보장종목 | 보상하는(하지 않는) 사항' 배치 표는 본문이 표 안에 있어 "
      "오른쪽 열 글자만 본문으로 남겼다(머리 행·보장종목 열은 뺌). 1행짜리 표는 강조 상자라 본문으로 두었다.\n"
      "   - 줄바꿈 잇기: 다음 줄이 목록 머리(1. 가. ① 1) (1) ※ 【 주) -)로 시작하거나 앞 줄이 . : ; 로 끝나면 띄운다. "
      "그 밖에는 앞 줄 끝 어절과 다음 줄 첫 어절을 붙여 Kiwi로 나눠 보고, 이은 자리가 형태소 안이거나 "
      "다음 형태소가 조사·어미·접사·VCP·문장부호(J, E, XS, VCP, SF, SP, SSC, SSO, SE, SO)면 붙이고, 아니면 띄운다.\n")
    w("8. 조건 표현(cond_per_sentence)은 사실상 '경우' 수다(잡힌 형태 대부분이 '경우/NNG', '거든'은 0건). 정의는 바꾸지 않았다.\n")
    w("9. 참조 수(ref_count)와 참조 묶음 수(ref_chain)는 거의 같은 값이라, 참조 구조 차원은 사실상 지표 하나다. 정의는 바꾸지 않았다.\n")
    with open(os.path.join(OUT, "난이도프로필_요약.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(x.rstrip("\n") + "\n" for x in L))

    # 보고용 보조 정보(콘솔)
    print("units:", units.groupby(["std_type", "unit"]).size().to_dict())
    print("excluded defs:", log["excluded_defs"])
    print("recompute mismatch:", log["recompute_mismatch"], "own article rows:", log["n_art_own"])
    print("drop log:", dict(DROP_LOG))
    for k in NEW_IND:
        print(k, CAPTURED[k].most_common(20))
    print("mask:", dict(MASK_COUNT))
    print("answers:", log.get("answers"), "sheet text mismatch:", log.get("sheet_text_mismatch"))
    print("arts per segment:", log["arts"].groupby("std_sub").size().to_dict())
    print(log["elig"].to_string())


if __name__ == "__main__":
    main()
