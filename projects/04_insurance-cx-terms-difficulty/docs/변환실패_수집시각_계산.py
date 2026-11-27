"""docs/변환실패.md 와 docs/수집근거표.md(수집 실행 시각)의 숫자를 계산하는 코드.

실행: python3 docs/변환실패_수집시각_계산.py > docs/변환실패_수집시각_계산_결과.txt   (프로젝트 폴더에서)
입력(읽기만): data/interim/decisions.csv, data/interim/fss_details_enriched.csv, data/interim/pilot_sample.csv,
             data/interim/texts/, data/raw/collect_log.csv
"""
import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
INT = Path("data/interim")


def conversion_failures():
    dec = pd.read_csv(INT / "decisions.csv", dtype=str).fillna("")
    det = pd.read_csv(INT / "fss_details_enriched.csv", dtype=str).fillna("")
    fail = dec[dec["오류"] != ""].merge(det[["nttId", "period"]], on="nttId", how="left")
    print("## 1. 변환 실패(오류 열이 비어 있지 않은 행)")
    print("decisions.csv 행:", len(dec), "/ 실패 행:", len(fail))
    print("오류별 건수:", fail["오류"].value_counts().to_dict())
    print("형식별 건수:", fail["형식"].value_counts().to_dict())
    print("구간×오류:\n" + pd.crosstab(fail["period"], fail["오류"]).to_markdown())

    def txt_info(name):
        p = INT / "texts" / (name.rsplit(".", 1)[0] + ".txt")
        return (p.stat().st_size, p.read_text(encoding="utf-8")[:40]) if p.exists() else (None, "")

    info = fail["파일명"].apply(txt_info)
    fail["txt_바이트"] = [i[0] for i in info]
    fail["txt_앞부분"] = [i[1] for i in info]
    print("\n" + fail[["파일명", "nttId", "형식", "오류", "period", "txt_바이트"]].to_markdown(index=False))
    prot = fail[fail["오류"].str.startswith("배포용")]
    print("\n배포용 안내문 txt 있음:", int(prot["txt_바이트"].notna().sum()), "/", len(prot),
          " 바이트 값:", prot["txt_바이트"].value_counts().to_dict(),
          " 앞부분:", prot["txt_앞부분"].unique().tolist())
    print("tif/pdf txt 있음:", int(fail[~fail["오류"].str.startswith("배포용")]["txt_바이트"].notna().sum()))


def collect_times():
    log = pd.read_csv(RAW / "collect_log.csv", dtype=str).fillna("")
    log["단계"] = log["url"].str.extract(r"/(list|view|fileDown)\.do")[0].map(
        {"list": "목록(list)", "view": "상세(detail)", "fileDown": "다운로드(download)"}).fillna("구분 불가")
    log["t"] = pd.to_datetime(log["time"], errors="coerce")
    log["간격초"] = log["t"].diff().dt.total_seconds()
    # 같은 종류 요청이 이어지고 간격이 60초 이하면 한 번의 실행으로 본다(실행 경계는 로그에 없어 간격으로 추정)
    log["실행"] = ((log["단계"] != log["단계"].shift()) | (log["간격초"] > 60)).cumsum()
    print("\n## 2. 수집 실행 시각(collect_log.csv)")
    print("로그 행:", len(log), "/ 시각 없음:", int(log["t"].isna().sum()),
          "/ 단계 구분 불가:", int((log["단계"] == "구분 불가").sum()))
    print("상태 코드:", log["status"].value_counts().to_dict(), "/ note 있음:", int((log["note"] != "").sum()))
    runs = log.groupby("실행").agg(단계=("단계", "first"), 요청수=("t", "size"), 시작=("t", "min"), 끝=("t", "max"),
                                   상태=("status", lambda s: ",".join(f"{k}:{v}" for k, v in s.value_counts().items())),
                                   최소간격초=("간격초", lambda s: s.iloc[1:].min() if len(s) > 1 else None))
    print(runs.to_markdown())
    # 파일럿 다운로드 구분 검증: 첫 다운로드 실행의 URL이 파일럿 표본 첨부 URL과 같은지
    smp = pd.read_csv(INT / "pilot_sample.csv", dtype=str).fillna("")
    pilot_urls = {a["url"] for x in smp["attachments"] for a in json.loads(x or "[]")}
    for rid, g in log[log["단계"] == "다운로드(download)"].groupby("실행"):
        urls = set(g["url"])
        print(f"다운로드 실행 {rid}: 요청 {len(g)}, 파일럿 첨부 URL과 겹침 {len(urls & pilot_urls)}/{len(pilot_urls)}")
    print("전체 최소 요청 간격(초):", log["간격초"].min())


if __name__ == "__main__":
    conversion_failures()
    collect_times()
