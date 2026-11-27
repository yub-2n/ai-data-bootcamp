# -*- coding: utf-8 -*-
"""분쟁조정 사례(참고용) 보험 종류·담보별 건수 집계.

입력: outputs/qual/사례목록_정리.csv
출력: outputs/qual/사례_담보집계_표1.csv  (보험(일반) 따로 묶음)
      outputs/qual/사례_담보집계_표2.csv  (보험(일반)을 제목으로 나눈 버전)
      outputs/qual/사례_일반배정표.csv    (보험(일반) 행별 배정)
      표준출력: 정성확인.md에 옮길 표(markdown)와 검증 결과

참고용 기술통계다(회귀 표본 아님, PROJECT.md 4-6). 결과(cited)와의 관계는 계산하지 않는다.
실행: python outputs/qual/사례_담보집계.py  (프로젝트 루트 어디서든)
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE / "사례목록_정리.csv"

# ② 보험(일반) 나누기 규칙: 제목에 아래 단어가 있으면 → (product_group, coverage)
# 이 CSV 안에서 사이트가 이미 분류한 행에 같은 단어가 나오는 범주로만 보낸다.
# 규칙 근거는 실행 때 check_rule_support()로 출력한다.
RULES = [
    ("종신보험", ("생명보험", "사망")),
]
UNCLASSIFIED = ("미분류", "")


def label(pg, cov):
    return f"{pg}({cov})" if cov else pg


def assign(title):
    hits = [(w, cat) for w, cat in RULES if w in title]
    cats = {cat for _, cat in hits}
    if len(cats) == 1:
        return hits[0][1], ", ".join(w for w, _ in hits)
    if len(cats) > 1:  # 여러 범주에 걸리면 억지로 넣지 않는다
        return UNCLASSIFIED, "여러 규칙 해당: " + ", ".join(w for w, _ in hits)
    return UNCLASSIFIED, "해당 단어 없음"


def count_table(df):
    t = (df.groupby(["product_group", "coverage"], dropna=False).size()
           .rename("건수").reset_index())
    t["coverage"] = t["coverage"].fillna("")
    sub = t.groupby("product_group")["건수"].transform("sum")
    t["종류_소계"] = sub
    t = t.sort_values(["종류_소계", "product_group", "건수"],
                      ascending=[False, True, False]).drop(columns="종류_소계")
    # 미분류는 맨 아래
    t = pd.concat([t[t.product_group != "미분류"], t[t.product_group == "미분류"]])
    n = int(t["건수"].sum())
    t["비율(%)"] = (t["건수"] / n * 100).round(1)
    return t.reset_index(drop=True), n


def md_table(t, n, denom_label):
    lines = ["| 보험 종류 | 담보 | 건수 | 비율(%) |", "|---|---|---:|---:|"]
    for pg, g in t.groupby("product_group", sort=False):
        for r in g.itertuples():
            lines.append(f"| {pg} | {r.coverage or '-'} | {r.건수} | {r._4} |")
        if len(g) > 1:
            s = int(g["건수"].sum())
            lines.append(f"| {pg} 소계 | | {s} | {round(s / n * 100, 1)} |")
    lines.append(f"| **합계** | | **{n}** | **100.0** |")
    lines.append("")
    lines.append(f"비율 분모: {denom_label} {n}건. 소수 첫째 자리 반올림이라 합이 100.0이 아닐 수 있다.")
    return "\n".join(lines)


def check_rule_support(classified):
    print("## 규칙 근거: 사이트 분류가 있는 행에서 규칙 단어가 나온 범주")
    for w, cat in RULES:
        m = classified[classified["title"].str.contains(w, regex=False)]
        print(f"- '{w}' → 규칙 범주 {label(*cat)}; 분류된 행 {len(m)}건:",
              m.groupby(["product_group", "coverage"]).size().to_dict(),
              "list_no", m["list_no"].tolist())


def main():
    d = pd.read_csv(SRC, encoding="utf-8-sig")
    print("## 검증")
    print("전체 행:", len(d))
    print("is_auto 값별:", d["is_auto"].value_counts(dropna=False).to_dict())
    na = d[d["is_auto"].isna()]
    print("is_auto 빈칸 행 list_no:", na["list_no"].tolist(), "type_raw:", na["type_raw"].tolist())

    n0 = d[d["is_auto"] == 0].copy()
    N = len(n0)
    print("is_auto = 0 건수:", N, "(사용자 제시 129와 차이", N - 129, ")")

    gen = n0[n0["product_group"] == "보험"].copy()
    print("보험(일반) 건수:", len(gen), "type_raw:", gen["type_raw"].unique().tolist(),
          "(사용자 제시 16과 차이", len(gen) - 16, ")")

    rd = pd.to_datetime(n0["reg_date"])
    print("is_auto=0 등록일 범위:", rd.min().date(), "~", rd.max().date())
    rda = pd.to_datetime(d["reg_date"])
    print("전체 160건 등록일 범위:", rda.min().date(), "~", rda.max().date())
    ok = rd.min() >= pd.Timestamp("2024-07-01") and rd.max() < pd.Timestamp("2026-02-01")
    print("'2024-07~2026-01' 안에 모두 있음:", ok)
    print("보험(일반) 등록일 범위:", pd.to_datetime(gen["reg_date"]).min().date(), "~",
          pd.to_datetime(gen["reg_date"]).max().date())

    # 표 ①
    t1, s1 = count_table(n0)
    assert s1 == N
    t1.to_csv(HERE / "사례_담보집계_표1.csv", index=False, encoding="utf-8-sig")

    # 표 ②
    classified = n0[n0["product_group"] != "보험"]
    check_rule_support(classified)
    rows = []
    for r in gen.sort_values("list_no").itertuples():
        (pg, cov), why = assign(r.title)
        rows.append({"list_no": r.list_no, "title": r.title, "배정_범주": label(pg, cov),
                     "product_group": pg, "coverage": cov, "근거_단어": why})
    asg = pd.DataFrame(rows)
    asg.to_csv(HERE / "사례_일반배정표.csv", index=False, encoding="utf-8-sig")

    n2 = n0.copy()
    m = asg.set_index("list_no")
    sel = n2["list_no"].isin(m.index)
    n2.loc[sel, "product_group"] = n2.loc[sel, "list_no"].map(m["product_group"])
    n2.loc[sel, "coverage"] = n2.loc[sel, "list_no"].map(m["coverage"])
    t2, s2 = count_table(n2)
    assert s2 == N
    t2.to_csv(HERE / "사례_담보집계_표2.csv", index=False, encoding="utf-8-sig")

    print("\n## 표 ①")
    print(md_table(t1, s1, "is_auto = 0"))
    print("\n## 표 ②")
    print(md_table(t2, s2, "is_auto = 0"))
    print("\n## 배정표")
    print("| list_no | 제목 | 배정 범주 | 근거 단어 |\n|---:|---|---|---|")
    for r in asg.itertuples():
        print(f"| {r.list_no} | {r.title} | {r.배정_범주} | {r.근거_단어} |")
    print("\n배정 결과 요약:", asg["배정_범주"].value_counts().to_dict())


if __name__ == "__main__":
    main()
