"""제외 사유 표 다시 만들기 (2026-11-03) — 지금 data/interim/cases.csv 기준(읽기만).

사용:  python3 docs/제외사유_계산.py
출력:  docs/제외사유_비교표.csv, docs/제외사유.md (덮어쓰기)
기준값 11: 분석 포함 vs 제외 사유별 인용률·시기 분포. 차이 10%p 이상 표시. cited가 없는 사유는 '미확인'.
난이도는 쓰지 않는다.
"""
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
C = pd.read_csv(os.path.join(ROOT, "data", "interim", "cases.csv"), dtype={"exclude_reason": str})
C["exclude_reason"] = C["exclude_reason"].fillna("")
C["grp"] = C["exclude_reason"].replace("", "분석 포함")
P = ["~2009", "2010-2016", "2017-2026"]
CLAUSE = ["조항 미추출", "조항 문구 없음", "풀어 쓴 서술"]

inc = C[C["grp"] == "분석 포함"]
r_inc = (inc["cited"] == 1).sum() / inc["cited"].notna().sum()


def row(name, sub):
    known = sub[sub["cited"].notna()]
    n_known = len(known)
    n1 = int((known["cited"] == 1).sum())
    rate = n1 / n_known if n_known else None
    diff = None if (rate is None or name == "분석 포함") else abs(rate - r_inc) * 100
    return {"구분": name, "건수 N": len(sub), "결과 판정된 건": n_known, "인용·일부 인용 수": n1,
            "인용률": "미확인" if rate is None else round(rate, 3),
            "분석 포함과 차이(%p)": "" if diff is None else round(diff, 1),
            "10%p 이상": "" if diff is None else ("예" if diff >= 10 else "아니오"),
            **{p: int((sub["period"] == p).sum()) for p in P}}


order = ["분석 포함"] + C.loc[C["grp"] != "분석 포함", "grp"].value_counts().index.tolist()
rows = [row(g, C[C["grp"] == g]) for g in order]
rows.append(row("(묶음) 조항 관련 제외: 조항 미추출 + 조항 문구 없음 + 풀어 쓴 서술", C[C["exclude_reason"].isin(CLAUSE)]))
rows.append(row("(합계) 전체", C))
T = pd.DataFrame(rows)
T.to_csv(os.path.join(DOCS, "제외사유_비교표.csv"), index=False, encoding="utf-8-sig")


def md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(v) for v in r.values) + " |")
    return "\n".join(out)


N = len(C)
n_inc = len(inc)
flag = T[T["10%p 이상"] == "예"]["구분"].tolist()
site_auto = int(((C["exclude_reason"] == "자동차보험") & (C["post_level_only"] == 1)).sum())
md = f"""# 제외 사유 (2026-11-03 갱신: 조항 문구 점검·사람 확인 반영 후)

- 숫자 출처: `docs/제외사유_계산.py` → `docs/제외사유_비교표.csv`. 입력은 지금 `data/interim/cases.csv`(읽기만).
- 단위: 결정문 1건. `cases.csv` {N}행 = 분석 포함 {n_inc} + 제외 {N - n_inc}.
- 인용률 = 인용·일부 인용 / 결과(cited)가 판정된 건. cited가 없는 사유(본문을 받지 못했거나 변환하지 못한 건, 각하)는 **미확인**.
- 난이도는 쓰지 않았다.

## 기준값 11 비교표

{md_table(T)}

- 분석 포함 인용률: {r_inc:.3f}.
- **10%p 이상 차이 나는 사유**: {", ".join(flag) if flag else "없음"}.
- 기준값 11의 판정 대상(분석 포함 vs 조항 미추출): 차이 {T.loc[T['구분'] == '조항 미추출', '분석 포함과 차이(%p)'].iloc[0]}%p.
- 자동차보험 중 {site_auto}건은 사이트 분류로만 제외한 게시물이라 본문이 없어 cited가 없다(위 '결과 판정된 건'에서 빠짐).
"""
open(os.path.join(DOCS, "제외사유.md"), "w", encoding="utf-8").write(md)
pd.set_option("display.width", 250)
print(T.to_string(index=False))
