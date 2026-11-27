#!/usr/bin/env python3
"""
금감원 분쟁조정결정례(보험) 수집 스크립트 — 교육·연구용

단계별로 실행한다(각 단계는 중단 후 다시 실행하면 이어서 진행).
  1) list      : 목록 페이지를 돌며 게시물 번호(nttId)와 제목을 모은다
  2) detail    : 상세 페이지에서 결정일, 조정번호, 첨부파일 링크를 모은다
  3) sample    : 시기 구간별 파일럿 표본(구간당 9건, 시드 42)을 뽑는다
  4) download  : 첨부파일(hwp 등)을 내려받는다  (--target pilot | all)

사용 예 (맥 터미널, 프로젝트 폴더에서):
  python3 -m pip install requests beautifulsoup4 pandas
  python3 fss_collect.py list
  python3 fss_collect.py detail
  python3 fss_collect.py sample
  python3 fss_collect.py download --target pilot
  python3 fss_collect.py download --target all

지키는 원칙 (수집근거표 2026-10-30):
  - 요청 사이 3초 이상 쉰다. 403/429가 오거나 연속 3번 실패하면 멈춘다.
  - 로그인, 차단 우회를 하지 않는다.
  - 작성자·담당자 이름, 이메일, 전화번호는 수집하지 않는다.
  - 받은 파일은 재배포하지 않는다. data/raw/ 는 GitHub에 올리지 않는다(.gitignore).
"""

import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://www.fss.or.kr"
LIST_URL = BASE + "/fss/bbs/B0000390/list.do"
VIEW_URL = BASE + "/fss/bbs/B0000390/view.do"
LIST_PARAMS = {  # 보험 분류(cl1Cd=B) 목록. 유빈 님이 확인한 주소의 파라미터 그대로
    "menuNo": "201193",
    "viewType": "",
    "searchCnd": "22",
    "searchWrd": "",
    "cl1Cd": "B",
}

OUT = Path("data/raw")
LIST_CSV = OUT / "fss_list.csv"
DETAIL_CSV = OUT / "fss_details.csv"
INTERIM = Path("data/interim")
ENRICHED_CSV = INTERIM / "fss_details_enriched.csv"   # sample 단계 결과(연도·구간·자동차 표시). data/raw는 건드리지 않음
SAMPLE_CSV = INTERIM / "pilot_sample.csv"
FILE_DIR = OUT / "decisions"
LOG_CSV = OUT / "collect_log.csv"

DELAY_MIN, DELAY_MAX = 3.0, 4.5     # 요청 간격(초)
MAX_CONSEC_FAIL = 3
MAX_PAGES = 200                     # 안전장치
PERIODS = [(1990, 2009, "~2009"), (2010, 2016, "2010-2016"), (2017, 2026, "2017-2026")]  # 10/30 회의 확정(1998년 결정 포함)
PER_PERIOD = 9
SEED = 42

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) edu-research-collector",
    "Accept-Language": "ko-KR,ko;q=0.9",
}


class StopCollection(Exception):
    pass


# ---------------------------------------------------------------- 공통
class Fetcher:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.consec_fail = 0
        OUT.mkdir(parents=True, exist_ok=True)

    def _log(self, url, status, note=""):
        new = not LOG_CSV.exists()
        with LOG_CSV.open("a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["time", "url", "status", "note"])
            w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), url, status, note])

    def get(self, url, params=None, referer=None, stream=False):
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        headers = {"Referer": referer} if referer else None
        try:
            r = self.s.get(url, params=params, headers=headers, timeout=30, stream=stream)
        except requests.RequestException as e:
            self.consec_fail += 1
            self._log(url, "ERR", str(e)[:200])
            if self.consec_fail >= MAX_CONSEC_FAIL:
                raise StopCollection(f"연속 {MAX_CONSEC_FAIL}회 실패: {e}")
            return None
        self._log(r.url, r.status_code)
        if r.status_code in (403, 429):
            raise StopCollection(f"HTTP {r.status_code} — 사이트가 거부했습니다. 수집을 멈춥니다.")
        if r.status_code != 200:
            self.consec_fail += 1
            if self.consec_fail >= MAX_CONSEC_FAIL:
                raise StopCollection(f"연속 {MAX_CONSEC_FAIL}회 실패 (마지막 HTTP {r.status_code})")
            return None
        self.consec_fail = 0
        return r


def ntt_id_from_href(href):
    q = parse_qs(urlparse(href).query)
    v = q.get("nttId", [None])[0]
    return v


DATE_RE = re.compile(r"(\d{4})[.\-]\s*(\d{1,2})[.\-]\s*(\d{1,2})")


def norm_date(m):
    y, mo, d = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"


# ---------------------------------------------------------------- 1) list
def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for a in soup.select('a[href*="/fss/bbs/B0000390/view.do"]'):
        nid = ntt_id_from_href(a.get("href", ""))
        if not nid:
            continue
        title = " ".join(a.get_text(" ", strip=True).split())
        row_el = a.find_parent(["tr", "li"]) or a.parent
        row_text = " ".join(row_el.get_text(" ", strip=True).split()) if row_el else ""
        m = DATE_RE.search(row_text.replace(title, ""))
        rows.append({
            "nttId": nid,
            "title": title,
            "list_date": norm_date(m) if m else "",
            "row_text": row_text[:300],
        })
    total = None
    m = re.search(r"총\s*([\d,]+)\s*건", soup.get_text(" ", strip=True))
    if m:
        total = int(m.group(1).replace(",", ""))
    return rows, total


def cmd_list(f):
    seen = {}
    if LIST_CSV.exists():
        for r in pd.read_csv(LIST_CSV, dtype=str).fillna("").to_dict("records"):
            seen[r["nttId"]] = r
    total_reported = None
    for page in range(1, MAX_PAGES + 1):
        params = dict(LIST_PARAMS, pageIndex=str(page))
        r = f.get(LIST_URL, params=params)
        if r is None:
            print(f"  page {page}: 실패, 건너뜀")
            continue
        rows, total = parse_list(r.text)
        total_reported = total_reported or total
        new = [x for x in rows if x["nttId"] not in seen]
        for x in rows:
            x["page"] = page
            seen.setdefault(x["nttId"], x)
        print(f"  page {page}: 게시물 {len(rows)}개 (새로 {len(new)}개), 누적 {len(seen)}개")
        if page == 1 and not rows:
            print("\n[중요] 1페이지에서 게시물 링크를 찾지 못했습니다.")
            print("목록이 자바스크립트로 불러와지는 구조일 수 있습니다. 결과를 Claude에게 알려주세요.")
            break
        if not new:
            break
        pd.DataFrame(list(seen.values())).to_csv(LIST_CSV, index=False, encoding="utf-8-sig")
    pd.DataFrame(list(seen.values())).to_csv(LIST_CSV, index=False, encoding="utf-8-sig")
    print(f"\n목록 저장: {LIST_CSV} ({len(seen)}건)")
    if total_reported:
        print(f"사이트 표시 총 건수: {total_reported}건")
        if total_reported != len(seen):
            print("  → 모은 건수와 다릅니다. 다시 실행하거나 Claude에게 알려주세요.")


# ---------------------------------------------------------------- 2) detail
def parse_detail(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # 결정일·조정번호: "2026. 7. 24.자 금융분쟁조정위원회 조정결정서 2026-9호 ..." 같은 문장
    body_line = next((ln for ln in lines if "조정결정" in ln and ("게시" in ln or "자 " in ln)), "")
    if not body_line:
        body_line = next((ln for ln in lines if "조정결정" in ln), "")
    m_date = DATE_RE.search(body_line) if body_line else None
    m_no = re.search(r"(\d{4})\s*[-–]\s*(\d+)\s*호", body_line) if body_line else None

    m_reg = re.search(r"등록일\s*[|ㅣ]?\s*(\d{4}-\d{2}-\d{2})", text)

    atts = []
    for a in soup.select('a[href*="fileDown.do"]'):
        href = urljoin(BASE, a.get("href", ""))
        sr = a.select_one(".sr-only")
        name = " ".join((sr.get_text(" ", strip=True) if sr else a.get_text(" ", strip=True)).split())
        name = re.sub(r"\(파일크기[^)]*\)", "", name).strip()
        if href not in [x["url"] for x in atts]:
            atts.append({"name": name, "url": href})

    return {
        "decision_date": norm_date(m_date) if m_date else "",
        "decision_no": f"{m_no.group(1)}-{m_no.group(2)}" if m_no else "",
        "reg_date": m_reg.group(1) if m_reg else "",
        "body_line": body_line[:300],
        "attachments": json.dumps(atts, ensure_ascii=False),
        "n_attachments": len(atts),
    }


def view_url(nid):
    return f"{VIEW_URL}?nttId={nid}&menuNo={LIST_PARAMS['menuNo']}"


def cmd_detail(f):
    if not LIST_CSV.exists():
        sys.exit("먼저 list 단계를 실행하세요.")
    lst = pd.read_csv(LIST_CSV, dtype=str).fillna("")
    done = {}
    if DETAIL_CSV.exists():
        for r in pd.read_csv(DETAIL_CSV, dtype=str).fillna("").to_dict("records"):
            done[r["nttId"]] = r
    todo = [r for r in lst.to_dict("records") if r["nttId"] not in done]
    print(f"상세 페이지 {len(todo)}건 남음 (예상 {len(todo) * 3.75 / 60:.0f}분)")
    for i, r in enumerate(todo, 1):
        url = view_url(r["nttId"])
        resp = f.get(url, referer=LIST_URL)
        if resp is None:
            continue
        d = parse_detail(resp.text)
        d.update({"nttId": r["nttId"], "title": r["title"], "view_url": url})
        done[r["nttId"]] = d
        if i % 20 == 0 or i == len(todo):
            pd.DataFrame(list(done.values())).to_csv(DETAIL_CSV, index=False, encoding="utf-8-sig")
            print(f"  {i}/{len(todo)} 저장")
    df = pd.DataFrame(list(done.values()))
    df.to_csv(DETAIL_CSV, index=False, encoding="utf-8-sig")
    print(f"\n상세 저장: {DETAIL_CSV} ({len(df)}건)")
    print(f"  결정일을 못 찾은 건: {(df['decision_date'] == '').sum()}건")
    print(f"  첨부파일 없는 건: {(df['n_attachments'].astype(int) == 0).sum()}건")


# ---------------------------------------------------------------- 3) sample
def period_of(year):
    for lo, hi, name in PERIODS:
        if lo <= year <= hi:
            return name
    return ""


AUTO_KW = r"자동차보험|자배법|자동차손해배상|대인배상|대물배상|무보험\s*자동차|무보험차|자기신체사고"
NO_NEW = re.compile(r"(?<!\d)((?:19|20)\d{2})\s*[-–]\s*\d{1,3}(?!\d)")  # 제2011-55호, (2001-20), 2011-55-게시용.hwp
NO_OLD = re.compile(r"(?<!\d)L?(\d{2})\s*-\s*\d+(?=\)|\.hwp|\s|$)")   # (98-33), L98-06.hwp


def infer_year(r):
    """결정 연도: 결정일 → 조정번호(제목·첨부 이름) → 등록일 순서로 찾는다."""
    if r.get("decision_date"):
        return int(r["decision_date"][:4]), "결정일"
    names = " ".join(a["name"] for a in json.loads(r.get("attachments") or "[]"))
    text = f"{r.get('decision_no', '')} {r.get('title', '')} {names}"
    m = NO_NEW.search(text)
    if m:
        return int(m.group(1)), "조정번호"
    m = NO_OLD.search(text)
    if m:
        yy = int(m.group(1))
        return (1900 + yy if yy >= 90 else 2000 + yy), "조정번호(옛 형식)"
    if r.get("reg_date"):
        return int(r["reg_date"][:4]), "등록일"
    return 0, "없음"


def cmd_sample(_f=None):
    if not DETAIL_CSV.exists():
        sys.exit("먼저 detail 단계를 실행하세요.")
    df = pd.read_csv(DETAIL_CSV, dtype=str).fillna("")
    # 자동차보험 제외(10/30 확정): 사이트 분류가 "자동차보험"인 게시물은 파일럿에서 뺀다.
    # 제목에 자동차 관련 말이 있는 건은 후보로만 표시하고, 최종 판정은 case-parser가 본문으로 한다.
    lst = pd.read_csv(LIST_CSV, dtype=str).fillna("")[["nttId", "row_text"]]
    df = df.drop(columns=[c for c in ["row_text"] if c in df]).merge(lst, on="nttId", how="left").fillna("")
    df["site_auto"] = df["row_text"].str.match(r"^\d+\s+보험\s+자동차보험").astype(int)
    df["auto_candidate"] = df["title"].str.contains(AUTO_KW).astype(int)
    print(f"사이트 분류 자동차보험: {df['site_auto'].sum()}건 → 파일럿에서 제외")
    print(f"제목으로 본 자동차 후보(사이트 분류 아님): {((df['auto_candidate'] == 1) & (df['site_auto'] == 0)).sum()}건 → case-parser가 본문으로 판정")
    yrs = df.apply(lambda r: infer_year(r.to_dict()), axis=1)
    df["year"] = [y for y, _ in yrs]
    df["year_source"] = [s for _, s in yrs]
    df["period"] = df["year"].apply(period_of)
    print("결정 연도를 어디서 찾았는지:")
    print(df["year_source"].value_counts().to_string())
    print("\n시기 구간별 게시물 수:")
    print(df["period"].replace("", "(구간 밖/날짜 없음)").value_counts().to_string())
    print(f"\n첨부파일이 2개 이상인 게시물: {(df['n_attachments'].astype(int) >= 2).sum()}건"
          " (게시물 하나에 결정문이 여러 개일 수 있음)")

    INTERIM.mkdir(parents=True, exist_ok=True)
    df["is_casebook"] = df["title"].str.contains("사례집").astype(int)
    df.to_csv(ENRICHED_CSV, index=False, encoding="utf-8-sig")   # data/raw/fss_details.csv 는 수정하지 않는다
    print(f"\n연도·구간·자동차 표시 저장: {ENRICHED_CSV}")

    legacy = OUT / "pilot_sample.csv"   # 예전 버전이 data/raw에 저장한 파일럿 표본
    if SAMPLE_CSV.exists() or legacy.exists():
        if not SAMPLE_CSV.exists():
            SAMPLE_CSV.write_bytes(legacy.read_bytes())          # 복사만 한다(원본은 그대로)
        print(f"파일럿 표본이 이미 있어 새로 뽑지 않습니다: {SAMPLE_CSV}")
        print("(파일럿을 다시 뽑으면 규칙을 정한 표본이 바뀌므로 덮어쓰지 않음)")
        return

    picks = []
    pool = df[(df["site_auto"] == 0) & (~df["title"].str.contains("사례집"))]
    print("\n자동차보험(사이트 분류) 제외 후 시기 구간별 게시물 수:")
    print(pool["period"].replace("", "(구간 밖/날짜 없음)").value_counts().to_string())
    for _, _, name in PERIODS:
        g = pool[pool["period"] == name].sort_values("nttId")
        n = min(PER_PERIOD, len(g))
        if n:
            picks.append(g.sample(n=n, random_state=SEED))
    sample = pd.concat(picks) if picks else df.head(0)
    sample.to_csv(SAMPLE_CSV, index=False, encoding="utf-8-sig")
    print(f"\n파일럿 표본 저장: {SAMPLE_CSV} ({len(sample)}건)")
    print(sample[["nttId", "year", "year_source", "period", "title"]].to_string(index=False))


# ---------------------------------------------------------------- 4) download
SAFE = re.compile(r'[\\/:*?"<>|\s]+')


def cmd_download(f, target):
    src = SAMPLE_CSV if target == "pilot" else ENRICHED_CSV
    if not src.exists():
        sys.exit("먼저 sample 단계를 실행하세요.")
    df = pd.read_csv(src, dtype=str).fillna("")
    if target == "all":
        # 분석에서 뺄 게시물은 받지 않는다: 사이트 분류 자동차보험, 사례집
        skip = (df.get("site_auto", "0").astype(str) == "1") | df["title"].str.contains("사례집")
        print(f"받지 않음: 자동차보험(사이트 분류) {int((df.get('site_auto', '0').astype(str) == '1').sum())}건, "
              f"사례집 {int(df['title'].str.contains('사례집').sum())}건")
        df = df[~skip]
    FILE_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for r in df.to_dict("records"):
        for k, att in enumerate(json.loads(r["attachments"] or "[]"), 1):
            ext = Path(att["name"]).suffix.lower() or ".bin"
            stem = SAFE.sub("_", Path(att["name"]).stem)[:60]
            out = FILE_DIR / f"{r['nttId']}_{k}_{stem}{ext}"
            if not out.exists():
                jobs.append((r, att, out))
    print(f"내려받을 파일 {len(jobs)}개 (예상 {len(jobs) * 3.75 / 60:.0f}분)")
    ok = 0
    for i, (r, att, out) in enumerate(jobs, 1):
        resp = f.get(att["url"], referer=r.get("view_url") or view_url(r["nttId"]), stream=True)
        if resp is None:
            continue
        ctype = resp.headers.get("Content-Type", "")
        if "text/html" in ctype:
            f._log(att["url"], "HTML", "파일 대신 HTML이 왔음")
            print(f"  [{i}] {out.name}: 파일 대신 웹페이지가 와서 건너뜀")
            continue
        tmp = out.with_suffix(out.suffix + ".part")
        with tmp.open("wb") as fp:
            for chunk in resp.iter_content(65536):
                fp.write(chunk)
        tmp.rename(out)
        ok += 1
        print(f"  [{i}/{len(jobs)}] {out.name} ({out.stat().st_size // 1024}KB)")
    print(f"\n완료: {ok}개 저장 → {FILE_DIR}")
    exts = pd.Series([p.suffix.lower() for p in FILE_DIR.iterdir() if p.is_file()]).value_counts()
    print("파일 형식별 개수:\n" + exts.to_string())


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="금감원 분쟁조정결정례(보험) 수집 — 교육·연구용")
    ap.add_argument("step", choices=["list", "detail", "sample", "download"])
    ap.add_argument("--target", choices=["pilot", "all"], default="pilot")
    a = ap.parse_args()
    f = Fetcher()
    try:
        if a.step == "list":
            cmd_list(f)
        elif a.step == "detail":
            cmd_detail(f)
        elif a.step == "sample":
            cmd_sample()
        else:
            cmd_download(f, a.target)
    except StopCollection as e:
        print(f"\n[멈춤] {e}")
        print("지금까지 받은 결과는 저장되어 있습니다. 같은 명령으로 다시 실행하면 이어서 진행합니다.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n중단했습니다. 같은 명령으로 다시 실행하면 이어서 진행합니다.")


if __name__ == "__main__":
    main()
