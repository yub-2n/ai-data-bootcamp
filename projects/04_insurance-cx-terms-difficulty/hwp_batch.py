"""금감원 분쟁조정결정례 일괄 텍스트 추출 + 항목 분리 스크립트.

사용:  python3 hwp_batch.py data/raw/decisions data/interim
      python3 hwp_batch.py data/raw/decisions data/interim --reparse   (텍스트는 그대로, 항목만 다시 뽑기)
      python3 hwp_batch.py data/raw/decisions data/interim --only <파일명>
          (파일 1개만 변환해 decisions.csv의 그 행만 바꿈. 다른 행은 바이트 그대로)
결과:  data/interim/texts/<파일명>.txt (원문 텍스트)
       data/interim/decisions.csv     (결정문 1건 = 1행, 항목별 정리)

지원 형식
  - 한글 5.0 이상(.hwp, 2002년 이후 대부분): olefile로 직접 읽음
  - 한글 3.0(.hwp, 2000~2001년 결정 일부): LibreOffice가 있으면 변환해서 읽음
      맥 설치: https://www.libreoffice.org 에서 내려받아 설치(무료)
      설치 후 별도 설정 없이 /Applications/LibreOffice.app 을 자동으로 찾음
  - pdf(2026-11-03 PROJECT.md 4-6-1): 글자를 뽑을 수 있는 pdf만 pdfplumber로 읽음.
      글자가 나오지 않는 pdf(스캔 이미지 등)는 변환하지 않고 오류로 기록(OCR 쓰지 않음)
  - tif 등: 읽지 않고 "지원하지 않는 형식"으로 기록

필요 패키지: pip install olefile pandas pdfplumber
주의: 원문 텍스트는 공개 저장소(GitHub)에 올리지 마세요.
"""
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

import olefile
import pandas as pd

# ---------------------------------------------------------------- 텍스트 추출
SKIP8 = set(list(range(1, 10)) + [11, 12] + list(range(14, 24)))


def para_text(data):
    units = struct.unpack("<%dH" % (len(data) // 2), data[: len(data) // 2 * 2])
    out, i = [], 0
    while i < len(units):
        u = units[i]
        if u in SKIP8:
            i += 8
            continue
        if u in (10, 13):
            out.append(10)
        elif u >= 32:
            out.append(u)
        i += 1
    return struct.pack("<%dH" % len(out), *out).decode("utf-16le", errors="replace")


def extract_hwp5(path):
    ole = olefile.OleFileIO(path)
    flags = struct.unpack("<I", ole.openstream("FileHeader").read()[36:40])[0]
    if flags & 2:
        raise RuntimeError("암호화된 파일")
    if flags & 4:
        # 배포용 문서: 작성자가 복사·편집을 막아 둔 보호 문서. 보호를 풀어서 읽지 않는다(저작권법상 기술적 보호조치).
        raise RuntimeError("배포용(보호) 문서 — 본문 추출하지 않음")
    secs = sorted([e for e in ole.listdir() if len(e) == 2 and e[0] == "BodyText" and e[1].startswith("Section")],
                  key=lambda e: int(e[1][7:]))
    texts = []
    for sec in secs:
        raw = ole.openstream(sec).read()
        if flags & 1:
            raw = zlib.decompress(raw, -15)
        pos = 0
        while pos + 4 <= len(raw):
            h = struct.unpack("<I", raw[pos:pos + 4])[0]
            tag, size = h & 0x3FF, (h >> 20) & 0xFFF
            pos += 4
            if size == 0xFFF:
                size = struct.unpack("<I", raw[pos:pos + 4])[0]
                pos += 4
            body = raw[pos:pos + size]
            pos += size
            if tag == 67:
                t = para_text(body).strip()
                if t:
                    texts.append(t)
    return "\n".join(texts)


def find_soffice():
    for c in [shutil.which("soffice"), shutil.which("libreoffice"),
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"]:
        if c and os.path.exists(c):
            return c
    return None


def extract_hwp3(path):
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError("한글 3.0 형식 — LibreOffice 설치 필요")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([soffice, "--headless", "--convert-to", "txt:Text (encoded):UTF8",
                        "--outdir", tmp, path], check=True, capture_output=True, timeout=180)
        out = [f for f in os.listdir(tmp) if f.endswith(".txt")]
        if not out:
            raise RuntimeError("한글 3.0 변환 실패")
        with open(os.path.join(tmp, out[0]), encoding="utf-8-sig") as f:
            return f.read()


def extract_pdf(path):
    """글자 추출 가능한 pdf만 읽는다. 페이지 텍스트를 줄바꿈으로 이어 붙인다(OCR 쓰지 않음)."""
    import pdfplumber  # pdf가 있을 때만 필요
    with pdfplumber.open(path) as pdf:
        text = "\n".join((pg.extract_text() or "") for pg in pdf.pages)
    if not text.strip():
        raise RuntimeError("pdf 글자 추출 안 됨(스캔 이미지 등) — 변환하지 않음")
    return text


def file_kind(path):
    with open(path, "rb") as f:
        head = f.read(32)
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"HWP Document File V3"):
        return "hwp3"
    if olefile.isOleFile(path):
        return "hwp5"
    return "other"


def extract(path):
    kind = file_kind(path)
    if kind == "hwp5":
        return extract_hwp5(path), "hwp5"
    if kind == "hwp3":
        return extract_hwp3(path), "hwp3"
    if kind == "pdf":
        return extract_pdf(path), "pdf"
    raise RuntimeError("지원하지 않는 형식")


# ---------------------------------------------------------------- 항목 분리
DATE = r"(\d{4})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?"


def norm(m, i=1):
    return f"{int(m.group(i)):04d}-{int(m.group(i + 1)):02d}-{int(m.group(i + 2)):02d}"


def find_date(text):
    """결정일: 정해진 표기에서만 찾는다(본문 속 아무 날짜나 잡지 않음)."""
    pats = [
        r"(?:조정|결정)\s*일\s*자\s*:?\s*" + DATE,                 # 결정일자 : 2010.1.26. / 조정일자 :\n2021. 9. 1.
        r"의\s*결\s*\n\s*(?:년\s*월\s*일\s*\n\s*)?" + DATE,         # 의    결\n년 월 일\n2026. 7. 24.
        r"\(\s*" + DATE + r"\s*결정",                             # (2006. 2. 28. 결정 제2006-3호)
    ]
    for p in pats:
        m = re.search(p, text[:3000])
        if m:
            return norm(m), "본문"
    return "", ""


def find_no(text, fname):
    pats = [
        r"(?:조정|의안)\s*번\s*호\s*:?\s*\n?\s*제?\s*(\d{4})\s*-\s*(\d+)\s*호?",
        r"결정\s*제\s*(\d{4})\s*-\s*(\d+)\s*호",
        r"제\s*(\d{4})\s*-\s*(\d+)\s*호",
    ]
    for p in pats:
        m = re.search(p, text[:3000])
        if m:
            return f"{m.group(1)}-{m.group(2)}", "본문"
    m = re.search(r"(?<!\d)((?:19|20)\d{2})\s*-\s*(\d{1,3})(?!\d)", fname)
    if m:
        return f"{m.group(1)}-{m.group(2)}", "파일명"
    m = re.search(r"(?<!\d)L?(\d{2})-(\d{1,3})(?!\d)", fname)
    if m:
        yy = int(m.group(1))
        return f"{1900 + yy if yy >= 90 else 2000 + yy}-{m.group(2)}", "파일명"
    return "", ""


H = r"^[ \t]*(?:[○□◦·\-ㆍ]\s*)?"  # 줄 시작(앞에 ○ - □ 같은 기호가 있어도 됨)


def section(text, start, ends):
    m = re.search(H + start + r"[ \t]*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    cut = [x.start() for x in (re.search(H + e, rest, re.M) for e in ends) if x]
    return (rest[:min(cut)] if cut else rest).strip()


JUMUN = r"(?:\d\s*\.\s*)?주\s*문"
CHWIJI = r"(?:\d\s*\.\s*)?신\s*청\s*취\s*지"
IYU = r"(?:\d\s*\.\s*)?이\s*유"
APP = r"(?:(?:가\s*\.|\(1\))\s*)?신청인(?:들)?(?:의)?\s*주장"
RESP = r"(?:(?:나\s*\.|\(2\))\s*)?피신청인(?:들)?(?:의)?\s*주장"
PARTY = r"(?:(?:\d\s*\.|[가-하]\s*\.)\s*)?당사자(?:의)?\s*주장"
JUDGE = r"(?:\d\s*\.|[가-하]\s*\.)\s*(?:(?:당?\s*위원회(?:의)?\s*)?판\s*단|쟁점(?:에\s*대한)?\s*(?:검토|판단))"
CONCL = r"(?:\d\s*\.|[가-하]\s*\.|\(\d\))\s*결\s*론"
BUT = r"[<\[]\s*붙\s*임\s*\d*\s*[>\]]"


def parse(text, fname):
    date, date_src = find_date(text)
    no, no_src = find_no(text, fname)
    m = re.search(r"(?:안|사)\s*건\s*명\s*:?\s*(.+)", text)
    title = m.group(1).strip() if m else ""

    jumun = section(text, JUMUN, [CHWIJI, IYU])
    chwiji = section(text, CHWIJI, [IYU, r"(?:\d\s*\.\s*)?당\s*사\s*자"])
    app = section(text, APP, [RESP])
    resp = section(text, RESP, [JUDGE, r"\(3\)", r"\d\s*\.\s*", r"[다라마]\s*\.\s*\S"])
    party = section(text, PARTY, [JUDGE, r"\d\s*\.\s*\S", r"다\s*\.\s*"])
    judge = section(text, JUDGE, [CONCL, BUT + r"[ \t]*$"])
    judge_src = "제목" if judge else ""
    if not judge:
        # '3. 약관상 ○○ 조항 및 판단 기준'처럼 제목이 다른 경우: 당사자 주장 다음 큰 제목부터 결론 전까지
        pm = re.search(H + PARTY + r"[ \t]*$", text, re.M)
        if pm:
            rest = text[pm.end():]
            nx = re.search(H + r"\d\s*\.\s*\S", rest, re.M)
            if nx:
                body = rest[nx.start():]
                c = re.search(H + CONCL + r"[ \t]*$", body, re.M)
                judge = (body[:c.start()] if c else body).strip()
                judge_src = "추정(당사자 주장 다음~결론 전)"
    concl = section(text, CONCL, [BUT + r"[ \t]*$"])

    # 붙임: 결론(없으면 판단) 시작 뒤에 나오는 '<붙임>' 단독 줄부터
    attach = ""
    anchor = re.search(H + CONCL + r"[ \t]*$", text, re.M) or re.search(H + JUDGE + r"[ \t]*$", text, re.M)
    if anchor:
        b = re.search(H + BUT + r"[ \t]*$", text[anchor.end():], re.M)
        if b:
            attach = text[anchor.end() + b.start():].strip()

    clause_lines = len(re.findall(r"제\s*\d+\s*조\s*[\(（【]", text))
    return {
        "조정번호": no, "조정번호_출처": no_src,
        "조정일자": date, "조정일자_출처": date_src,
        "안건명": title,
        "주문": jumun,
        "신청취지": chwiji,
        "당사자_주장": party,
        "신청인_주장": app,
        "피신청인_주장": resp,
        "위원회_판단": judge, "위원회_판단_추출": judge_src,
        "결론": concl,
        "붙임": attach,
        "약관_붙임_포함": bool(attach),
        "약관_조문_표기_수": clause_lines,   # "제○조(" 형태가 본문 어디든 몇 번 나오는지(붙임이 없어도 약관 인용 여부 참고)
    }


# ---------------------------------------------------------------- main
LEN_COLS = ["주문", "당사자_주장", "신청인_주장", "피신청인_주장", "위원회_판단", "결론", "붙임"]


def update_one(src, dst, name):
    """파일 1개만 변환해 decisions.csv의 해당 행(파일명 일치)만 바꾼다.
    다른 행·열 순서·인코딩(utf-8-sig)·줄바꿈(LF)은 그대로 둔다. 셀 표기는 main()의 pandas 출력과 맞춘다."""
    import csv
    import io
    path = os.path.join(src, name)
    tdir = os.path.join(dst, "texts")
    os.makedirs(tdir, exist_ok=True)
    ntt = name.split("_", 1)[0] if name.split("_", 1)[0].isdigit() else ""
    try:
        text, kind = extract(path)
        tpath = os.path.join(tdir, name[:-4] + ".txt")
        with open(tpath, "w", encoding="utf-8") as f:
            f.write(text)
        row = {"파일명": name, "nttId": ntt, "형식": kind, **parse(text, name), "오류": ""}
    except Exception as e:
        row = {"파일명": name, "nttId": ntt, "형식": os.path.splitext(name)[1].lower(), "오류": str(e) or repr(e)}
    for col in LEN_COLS:
        row[col + "_글자수"] = len(row.get(col, "") or "")
    if "약관_조문_표기_수" in row:          # pandas 출력에서 빈칸이 섞인 열이라 실수형(예: 3.0)으로 적혀 있음
        row["약관_조문_표기_수"] = float(row["약관_조문_표기_수"])

    cpath = os.path.join(dst, "decisions.csv")
    with open(cpath, "rb") as f:
        raw = f.read()
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))
    head = rows[0]
    hit = [i for i, r in enumerate(rows[1:], 1) if r[head.index("파일명")] == name]
    if len(hit) != 1:
        raise SystemExit(f"decisions.csv에서 '{name}' 행이 {len(hit)}개 — 중단")
    rows[hit[0]] = ["" if row.get(c) is None else str(row.get(c, "")) for c in head]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    with open(cpath, "wb") as f:
        f.write(("\ufeff" + buf.getvalue()).encode("utf-8"))
    print(("OK  " if not row["오류"] else "FAIL"), name, row["오류"])


def main(src, dst, reparse=False):
    os.makedirs(dst, exist_ok=True)
    tdir = os.path.join(dst, "texts")
    os.makedirs(tdir, exist_ok=True)
    if not find_soffice():
        print("[안내] LibreOffice가 없어 한글 3.0 파일은 건너뜁니다(오류 열에 기록).")
    rows = []
    for name in sorted(os.listdir(src)):
        low = name.lower()
        if low.endswith((".part", ".ds_store")) or name.startswith("."):
            continue
        ntt = name.split("_", 1)[0] if name.split("_", 1)[0].isdigit() else ""
        base = {"파일명": name, "nttId": ntt, "형식": os.path.splitext(name)[1].lower()}
        if not low.endswith((".hwp", ".pdf")):
            rows.append({**base, "오류": "지원하지 않는 형식(" + os.path.splitext(name)[1] + ")"})
            print("SKIP", name)
            continue
        try:
            tpath = os.path.join(tdir, name[:-4] + ".txt")
            if reparse and os.path.exists(tpath) and file_kind(os.path.join(src, name)) != "other":
                kind = file_kind(os.path.join(src, name))
                if kind == "hwp5":
                    with olefile.OleFileIO(os.path.join(src, name)) as ole:
                        fl = struct.unpack("<I", ole.openstream("FileHeader").read()[36:40])[0]
                    if fl & 4:
                        raise RuntimeError("배포용(보호) 문서 — 본문 추출하지 않음")
                with open(tpath, encoding="utf-8") as f:
                    text = f.read()
            else:
                text, kind = extract(os.path.join(src, name))
                with open(tpath, "w", encoding="utf-8") as f:
                    f.write(text)
            row = {**base, "형식": kind, **parse(text, name), "오류": ""}
        except Exception as e:
            row = {**base, "오류": str(e) or repr(e)}
        rows.append(row)
        print(("OK  " if not row["오류"] else "FAIL"), name, ("" if not row["오류"] else "— " + row["오류"]))
    df = pd.DataFrame(rows)
    for col in LEN_COLS:
        if col in df:
            df[col + "_글자수"] = df[col].fillna("").str.len()
    df.to_csv(os.path.join(dst, "decisions.csv"), index=False, encoding="utf-8-sig")
    ok = (df["오류"].fillna("") == "").sum()
    print(f"\n완료: {len(df)}개 파일 중 {ok}개 변환 → {os.path.join(dst, 'decisions.csv')}")
    if ok:
        d = df[df["오류"].fillna("") == ""]
        for col, label in [("조정일자", "결정일"), ("조정번호", "조정번호"), ("주문", "주문"),
                           ("위원회_판단", "위원회 판단"), ("붙임", "붙임")]:
            print(f"  {label} 찾음: {(d[col].fillna('') != '').sum()}/{ok}")


if __name__ == "__main__":
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        rest = sys.argv[1:i] + sys.argv[i + 2:]
        if len(rest) != 2 or i + 1 >= len(sys.argv):
            sys.exit("사용법: python3 hwp_batch.py <원본 폴더> <출력 폴더> --only <파일명>")
        update_one(rest[0], rest[1], sys.argv[i + 1])
        sys.exit(0)
    args = [a for a in sys.argv[1:] if a != "--reparse"]
    if len(args) != 2:
        sys.exit("사용법: python3 hwp_batch.py <hwp 폴더> <출력 폴더> [--reparse]\n"
                 "  --reparse : 이미 만든 texts/로 항목만 다시 뽑기(변환 생략, 빠름)")
    main(args[0], args[1], reparse="--reparse" in sys.argv)
