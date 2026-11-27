"""파일럿 수집 보고(docs/파일럿_수집보고.md)의 숫자를 계산하는 코드. (2차: 전체 변환 후)

실행: python3 docs/파일럿_수집보고_계산.py > docs/파일럿_수집보고_계산_결과.txt   (프로젝트 폴더에서)
입력(읽기만): data/interim/decisions.csv(전체 변환 결과), data/interim/pilot_sample.csv(파일럿 27건),
             data/interim/fss_details_enriched.csv(게시물별 구간·site_auto·is_casebook), data/raw/collect_log.csv,
             data/interim/texts/
가림 규칙(4-7): 주문·위원회 판단은 "찾았는지(비어 있지 않은지)"만 센다. 내용(인용/기각)과 난이도는 보지 않는다.
"""
import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
INT = Path("data/interim")
PERIODS = ["~2009", "2010-2016", "2017-2026"]

dec = pd.read_csv(INT / "decisions.csv", dtype=str).fillna("")
smp = pd.read_csv(INT / "pilot_sample.csv", dtype=str).fillna("")
det = pd.read_csv(INT / "fss_details_enriched.csv", dtype=str).fillna("")
log = pd.read_csv(RAW / "collect_log.csv", dtype=str).fillna("")

dec["변환성공"] = (dec["오류"] == "").astype(int)
dec["배포용"] = dec["오류"].str.startswith("배포용").astype(int)
dec = dec.merge(det[["nttId", "period"]], on="nttId", how="left")


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.1f}%)" if b else f"{a}/0"


# ------------------------------------------------------------ 0. 건수 맞추기
print("## 0. 건수 확인")
keep = det[(det["site_auto"] != "1") & (det["is_casebook"] != "1")]
n_att = sum(len(json.loads(a or "[]")) for a in keep["attachments"])
print("게시물 전체:", len(det), "/ 사이트 자동차보험:", int((det["site_auto"] == "1").sum()),
      "/ 사례집:", int((det["is_casebook"] == "1").sum()), "/ 대상 게시물:", len(keep))
print("대상 게시물 첨부 수:", n_att, "/ decisions.csv 행 수:", len(dec))
print("오류별:", dec["오류"].replace("", "(성공)").value_counts().to_dict())
n_ok, n_prot = int(dec["변환성공"].sum()), int(dec["배포용"].sum())
n_tif = int((dec["오류"] == "지원하지 않는 형식(.tif)").sum())
n_pdf = int((dec["오류"] == "지원하지 않는 형식(.pdf)").sum())
print(f"366 = 344+19+2+1 ? → 행 {len(dec)} = 성공 {n_ok} + 배포용 {n_prot} + tif {n_tif} + pdf {n_pdf} = "
      f"{n_ok + n_prot + n_tif + n_pdf} → {'일치' if len(dec) == n_ok + n_prot + n_tif + n_pdf else '불일치'}")
print("decisions.csv nttId 수:", dec["nttId"].nunique(), "/ 대상 게시물에 없는 nttId:",
      sorted(set(dec["nttId"]) - set(keep["nttId"])), "/ decisions.csv에 없는 대상 게시물:",
      sorted(set(keep["nttId"]) - set(dec["nttId"])))
texts = {p.stem for p in (INT / "texts").glob("*.txt")}
prot_with_txt = [f for f in dec[dec["배포용"] == 1]["파일명"] if f.rsplit(".", 1)[0] in texts]
print("texts/ 파일 수:", len(texts), "/ 그중 배포용 문서의 안내문 텍스트:", len(prot_with_txt))
dl = log[log["url"].str.contains("fileDown.do")]
print("로그 첨부 요청 상태:", dl["status"].value_counts().to_dict(),
      "/ 로그 전체 403·429:", int(log["status"].isin(["403", "429"]).sum()))

# ------------------------------------------------------------ 1. 파일럿
print("\n## 1. 파일럿 27건(구간별, nttId로 연결)")
pil = dec[dec["nttId"].isin(smp["nttId"])].drop(columns=["period"]).merge(
    smp[["nttId", "period", "auto_candidate"]], on="nttId", how="left")
print("파일럿 게시물:", len(smp), "/ 연결된 파일:", len(pil), "/ 연결 안 된 게시물:",
      sorted(set(smp["nttId"]) - set(pil["nttId"])))
rows = []
for p in PERIODS:
    g = pil[pil["period"] == p]
    n, ok = len(g), int(g["변환성공"].sum())
    rows.append({
        "구간": p, "파일 수": n, "변환 성공": ok, "성공률(%)": round(100 * ok / n, 1) if n else None,
        "기준값6(50%)": ("미달" if n and ok / n < 0.5 else "충족"),
        "형식": ", ".join(f"{k} {v}" for k, v in g["형식"].value_counts().items()),
        "배포용": int(g["배포용"].sum()),
        "조정일자 찾음": int((g["조정일자"] != "").sum()),
        "붙임 약관 있음": int((g["약관_붙임_포함"] == "True").sum()),
        "auto_candidate": int(g["auto_candidate"].astype(int).sum()),
    })
print(pd.DataFrame(rows).to_markdown(index=False))
print("파일럿 전체 변환:", pct(int(pil["변환성공"].sum()), len(pil)))
print(pil[pil["변환성공"] == 0][["파일명", "period", "형식", "오류"]].to_markdown(index=False))

# ------------------------------------------------------------ 2. 배포용 문서(시기별, 전체)
print("\n## 2. 배포용(보호) 문서 — 전체 첨부 기준 시기별")
rows = []
for p in PERIODS:
    g = dec[dec["period"] == p]
    rows.append({"구간": p, "첨부 수": len(g), "변환 성공": int(g["변환성공"].sum()),
                 "성공률(%)": round(100 * g["변환성공"].mean(), 1) if len(g) else None,
                 "배포용": int(g["배포용"].sum()),
                 "tif": int((g["오류"] == "지원하지 않는 형식(.tif)").sum()),
                 "pdf": int((g["오류"] == "지원하지 않는 형식(.pdf)").sum()),
                 "hwp3 성공": int(((g["형식"] == "hwp3") & (g["변환성공"] == 1)).sum()),
                 "hwp5 성공": int(((g["형식"] == "hwp5") & (g["변환성공"] == 1)).sum())})
print(pd.DataFrame(rows).to_markdown(index=False))
print("구간 없는 행:", int((dec["period"].isna() | (dec["period"] == "")).sum()))
print("배포용 파일:", dec[dec["배포용"] == 1][["파일명", "period"]].to_dict("records"))

# ------------------------------------------------------------ 3. 전체 변환 성공분 항목 추출
print("\n## 3. 변환 성공분 항목별 추출 건수")
ok = dec[dec["변환성공"] == 1]
items = [("결정일(조정일자)", "조정일자"), ("조정번호", "조정번호"), ("주문", "주문"),
         ("위원회 판단", "위원회_판단"), ("붙임(본문 분리)", "붙임"), ("약관 붙임 포함", "약관_붙임_포함")]
rows = []
for label, col in items:
    if col not in ok:
        rows.append({"항목": label, "열": col, "찾은 건수": "미확인", "비율": "미확인"})
        continue
    hit = (ok[col] == "True") if col == "약관_붙임_포함" else (ok[col].str.strip() != "")
    rows.append({"항목": label, "열": col, "찾은 건수": int(hit.sum()), "비율": f"{100 * hit.mean():.1f}%"})
print("분모(변환 성공):", len(ok))
print(pd.DataFrame(rows).to_markdown(index=False))
print("조정일자 출처:", ok["조정일자_출처"].replace("", "(없음)").value_counts().to_dict())
print("조정번호 출처:", ok["조정번호_출처"].replace("", "(없음)").value_counts().to_dict())
print("위원회_판단_추출:", ok["위원회_판단_추출"].replace("", "(없음)").value_counts().to_dict())
print("\n구간별 추출(변환 성공분):")
rows = []
for p in PERIODS:
    g = ok[ok["period"] == p]
    rows.append({"구간": p, "n": len(g),
                 **{label: int(((g[col] == "True") if col == "약관_붙임_포함" else (g[col].str.strip() != "")).sum())
                    for label, col in items}})
print(pd.DataFrame(rows).to_markdown(index=False))
