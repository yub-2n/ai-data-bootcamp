"""평가 일치도(기준값 13): 두 평가자 가중 카파 + 지수와 평가 평균의 스피어만 상관.
실행: insurance-cx 폴더에서  py outputs\\stats\\eval_agree.py
입력: data/processed/평가점수.csv(eval_id, 정유빈, 팀원C)
      outputs/stats/eval_map.csv(eval_id, diff_id)  ← 팀원B만 보관
      data/processed/difficulty.csv(diff_id, difficulty_index, difficulty_index_article ...)
출력: outputs/stats/평가일치도.md  (diff_id·조항 문구·사건 정보는 적지 않음)
결과(cited)는 읽지 않는다.
"""
import numpy as np
import pandas as pd

SEED, B = 42, 2000
S = pd.read_csv("data/processed/평가점수.csv")
M = pd.read_csv("outputs/stats/eval_map.csv")
D = pd.read_csv("data/processed/difficulty.csv")
for bad in ("cited", "partial", "case_key"):
    assert bad not in D.columns, f"가림 규칙 위반: difficulty.csv에 {bad} 열"
X = S.merge(M, on="eval_id", how="left").merge(D, on="diff_id", how="left")
assert len(X) == len(S) and X["difficulty_index"].notna().all(), "평가 번호 연결 실패"
a, b = X["정유빈"].to_numpy(float), X["팀원C"].to_numpy(float)


def qwk(x, y, k=5):
    x, y = x.astype(int) - 1, y.astype(int) - 1
    O = np.zeros((k, k))
    for i, j in zip(x, y):
        O[i, j] += 1
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (W * O).sum() / (W * E).sum()


def spear(x, y):
    return pd.Series(x).rank().corr(pd.Series(y).rank())


def boot(f, *cols):
    rng = np.random.default_rng(SEED); n = len(cols[0]); out = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        v = f(*[c[i] for c in cols])
        if np.isfinite(v):
            out.append(v)
    return np.percentile(out, [2.5, 97.5])


mean = (a + b) / 2
rows = [("두 평가자 가중 카파(quadratic)", qwk(a, b), boot(qwk, a, b))]
for col, name in [("difficulty_index", "지수"), ("difficulty_index_article", "조 전체 지수")]:
    v = X[col].to_numpy(float)
    rows.append((f"스피어만: {name} vs 평가 평균", spear(v, mean), boot(spear, v, mean)))
    rows.append((f"스피어만: {name} vs 정유빈", spear(v, a), boot(spear, v, a)))
    rows.append((f"스피어만: {name} vs 팀원C", spear(v, b), boot(spear, v, b)))

k = rows[0][1]
with open("outputs/stats/평가일치도.md", "w", encoding="utf-8") as f:
    f.write("# 평가 일치도 (기준값 13)\n\n")
    f.write(f"- 평가 조항 {len(X)}개, 평가자 2명(정유빈, 팀원C), 1~5점. 95% CI는 부트스트랩 {B}회(시드 {SEED})\n")
    f.write(f"- 완전 일치 {np.mean(a == b):.3f}, 1점 차 이내 {np.mean(abs(a - b) <= 1):.3f}, "
            f"평균 정유빈 {a.mean():.2f} / 팀원C {b.mean():.2f}\n\n")
    f.write("| 항목 | 값 | 95% CI |\n|---|---|---|\n")
    for n_, v, ci in rows:
        f.write(f"| {n_} | {v:.3f} | {ci[0]:.3f} ~ {ci[1]:.3f} |\n")
    f.write("\n## 판정\n\n")
    f.write(f"- 가중 카파 {k:.3f} → " + ("0.4 이상" if k >= 0.4 else "**0.4 미만이라 한계에 적는다**(계획서 6-3)") + "\n")
print(open("outputs/stats/평가일치도.md", encoding="utf-8").read())
