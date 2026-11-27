# -*- coding: utf-8 -*-
"""
analysis.py — stats 단계 분석 (agents/stats.md 1~10단계, docs/지시/stats_실행.md)

실행: insurance-cx 폴더에서  py -3.10 outputs/stats/analysis.py
입력: data/interim/cases.csv, data/interim/difficulty_id_map.csv, data/processed/difficulty.csv
      data/processed/issue_type_r2.csv (8단계 사후 민감도 1줄에만, stats_수정_3)
출력: outputs/stats/01_합치기점검.csv ~ 10_조항주제.csv, pred_curve.csv, 통계요약.md (모두 utf-8-sig, md는 utf-8)

고정 설정
- 시드 42 (부트스트랩 numpy default_rng(42)), 부트스트랩 1,000회. 6과 6-1은 같은 부트스트랩 표본·같은 적합 결과를 쓴다.
- 참조 범주: issue_type = 보상범위·정의, period = ~2009.
- 난이도 오즈비: 분석 표본(157건)의 해당 변수 표준편차(ddof=1) 1당. 민감도도 157건 기준 표준편차로 나눈 값을 넣는다(같은 척도).
- 일반 로지스틱: statsmodels Logit(뉴턴법), Wald 95% CI·p.
- Firth: firthlogist(프로파일 우도 95% CI, 벌점 우도비 검정 p). 소수 쪽 < 50 또는 (준)완전 분리면 Firth(기준값 9).
- 소수 쪽 < 30이면 exploratory = 1(기준값 10).
- 인용률 95% CI: Wilson.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from scipy.special import expit
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint, confint_proportions_2indep
from statsmodels.stats.contingency_tables import StratifiedTable, Table2x2
from firthlogist import FirthLogisticRegression as _FirthBase
from sklearn.utils.validation import check_X_y
from sklearn.utils.multiclass import check_classification_targets
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")


class FirthLogisticRegression(_FirthBase):
    """firthlogist 0.5.0은 scikit-learn 1.6+에서 없어진 BaseEstimator._validate_data를 부른다.
    계산은 그대로 두고 입력 검사만 같은 동작(check_X_y, float64, 최소 2표본, 2범주)으로 바꾼다."""

    def _validate_input(self, X, y):
        X, y = check_X_y(X, y, dtype=np.float64, ensure_min_samples=2)
        check_classification_targets(y)
        self.classes_ = np.unique(y)
        if len(self.classes_) != 2:
            raise ValueError(f"Got {len(self.classes_)} - only 2 classes supported.")
        y = LabelEncoder().fit_transform(y).astype(X.dtype, copy=False)
        return X, y

BASE = os.environ.get("CX_BASE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
OUT = os.path.join(BASE, "outputs", "stats")
SEED = 42
N_BOOT = 1000
REF_ISSUE = "보상범위·정의"
ISSUES = ["보상범위·정의", "면책", "고지·설명"]          # 첫 값이 참조
PERIODS = ["~2009", "2010-2016", "2017-2026"]           # 첫 값이 참조
DUP_KEY = "2009-29"
INST_POINTS = "2009(실손 표준화), 2017(3세대), 2021.7(4세대) — 표시용 메타데이터"
ENC = "utf-8-sig"


def p(*a):
    return os.path.join(BASE, *a)


def save(df, name):
    df.to_csv(os.path.join(OUT, name), index=False, encoding=ENC)


def wilson(k, n):
    if n == 0:
        return np.nan, np.nan
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
    return float(lo), float(hi)


def rnd(x, d=4):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return np.nan
        return round(float(x), d)
    except (TypeError, ValueError):
        return x


def pfmt(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    return float(f"{float(x):.4g}")


# =====================================================================
# 1. 합치기와 점검
# =====================================================================
cases = pd.read_csv(p("data", "interim", "cases.csv"), encoding=ENC, dtype={"case_key": str})
idmap = pd.read_csv(p("data", "interim", "difficulty_id_map.csv"), encoding=ENC, dtype=str)
diff = pd.read_csv(p("data", "processed", "difficulty.csv"), encoding=ENC)

# 0단계 확인
checks = {
    "cases.csv 행": (len(cases), 449),
    "difficulty_id_map.csv 행": (len(idmap), 261),
    "difficulty.csv 행": (len(diff), 261),
}
ana0 = cases[cases["exclude_reason"].isna()].copy()
checks.update({
    "분석 포함": (len(ana0), 157),
    "cited 1": (int((ana0["cited"] == 1).sum()), 106),
    "cited 0": (int((ana0["cited"] == 0).sum()), 51),
    "partial 1": (int((ana0["partial"] == 1).sum()), 6),
    "~2009": (int((ana0["period"] == "~2009").sum()), 75),
    "2010-2016": (int((ana0["period"] == "2010-2016").sum()), 42),
    "2017-2026": (int((ana0["period"] == "2017-2026").sum()), 40),
})
bad = {k: v for k, v in checks.items() if v[0] != v[1]}
if bad:
    sys.exit(f"0단계 확인 불일치: {bad}. 멈춥니다.")

# 2009-29 중복: 분석 포함 행의 clause_text와 같은 문구의 diff_id 하나만
dup_rows = cases[cases["case_key"] == DUP_KEY]
dup_ids = idmap.loc[idmap["case_key"] == DUP_KEY, "diff_id"].tolist()
ana_text = dup_rows.loc[dup_rows["exclude_reason"].isna(), "clause_text"].iloc[0]
other_text = dup_rows.loc[dup_rows["exclude_reason"].notna(), "clause_text"].iloc[0]
same_case_text = bool(str(ana_text).strip() == str(other_text).strip())
num_cols = [c for c in diff.columns if c not in ("diff_id", "issue_type", "clause_level", "clause_text_form")]
dd = diff[diff["diff_id"].isin(dup_ids)].set_index("diff_id")
same_metrics = bool(all(dd[c].nunique() == 1 for c in num_cols + ["issue_type", "clause_level", "clause_text_form"]))
DUP_CHOSEN = sorted(dup_ids)[0]          # D204
DUP_DROPPED = [x for x in dup_ids if x != DUP_CHOSEN]
idmap_u = idmap[~idmap["diff_id"].isin(DUP_DROPPED)]
assert not idmap_u["case_key"].duplicated().any()

dm = idmap_u.merge(diff, on="diff_id", how="left", validate="one_to_one", suffixes=("", "_diff"))
dm = dm.rename(columns={"issue_type": "issue_type_diff", "clause_level": "clause_level_diff",
                        "clause_text_form": "clause_text_form_diff"})
allc = cases[~((cases["case_key"] == DUP_KEY) & cases["exclude_reason"].notna())]   # 2009-29 '중복' 행 제외
# 그 밖의 case_key 중복(예: 2012-14 분석 포함 + 배포용 문서)은 분석 포함 행이 하나뿐인지만 확인한다
other_dup = sorted(allc.loc[allc["case_key"].duplicated(keep=False), "case_key"].unique())
assert not allc.loc[allc["exclude_reason"].isna(), "case_key"].duplicated().any()
allm = allc.merge(dm, on="case_key", how="left", validate="many_to_one")
ana = allm[allm["exclude_reason"].isna()].copy()
missing = ana[ana["difficulty_index"].isna()]
ana = ana[ana["difficulty_index"].notna()].copy()
issue_mismatch = int((ana["issue_type"] != ana["issue_type_diff"]).sum())

rows01 = [
    ("합친 수", len(ana)),
    ("빠진 수", len(missing)),
]
if len(missing):
    for k in missing["case_key"]:
        rows01.append((f"빠진 이유: {k} difficulty_id_map에 case_key 없음", 1))
else:
    rows01.append(("빠진 이유: 없음(분석 포함 157건 모두 difficulty 붙음)", 0))
rows01 += [
    ("입력: cases.csv 행", len(cases)),
    ("입력: cases.csv 분석 포함(exclude_reason 빈 행)", len(ana0)),
    ("입력: difficulty_id_map.csv 행", len(idmap)),
    ("입력: difficulty.csv 행", len(diff)),
    (f"중복 처리: case_key {DUP_KEY}의 diff_id {'/'.join(dup_ids)} 중 {DUP_CHOSEN} 사용, "
     f"{'/'.join(DUP_DROPPED)} 제외(cases.csv 두 행 문구 같음={int(same_case_text)}, 두 diff_id 지표 모두 같음={int(same_metrics)})",
     len(DUP_DROPPED)),
    ("점검: issue_type이 cases.csv와 difficulty.csv에서 다른 사건", issue_mismatch),
]
for k in other_dup:
    rr = allc[allc["case_key"] == k]
    rows01.append((f"점검: cases.csv case_key {k} 두 행(분석 포함 {int(rr['exclude_reason'].isna().sum())}, "
                   f"제외 {'/'.join(rr['exclude_reason'].dropna())}), difficulty_id_map에 {int((idmap['case_key'] == k).sum())}번 → 분석 포함 행에만 사용",
                   int(rr['exclude_reason'].isna().sum())))
save(pd.DataFrame(rows01, columns=["item", "n"]), "01_합치기점검.csv")

ana["cited"] = ana["cited"].astype(int)
ana["partial"] = ana["partial"].fillna(0).astype(int)
N = len(ana)
SD_MAIN = float(ana["difficulty_index"].std(ddof=1))

# =====================================================================
# 2. 기술통계
# =====================================================================
rows02 = []
for it in ISSUES + ["전체"]:
    for pe in PERIODS + ["전체"]:
        s = ana
        if it != "전체":
            s = s[s["issue_type"] == it]
        if pe != "전체":
            s = s[s["period"] == pe]
        n, k = len(s), int(s["cited"].sum())
        lo, hi = wilson(k, n)
        rows02.append(dict(issue_type=it, period=pe, n=n, n_cited=k,
                           cited_rate=rnd(k / n if n else np.nan), ci_low=rnd(lo), ci_high=rnd(hi)))
save(pd.DataFrame(rows02), "02_기술통계.csv")


def dist(s):
    q = np.percentile(s, [5, 25, 50, 75, 95])
    return dict(n=len(s), mean=s.mean(), sd=s.std(ddof=1), min=s.min(), p5=q[0], p25=q[1],
                median=q[2], p75=q[3], p95=q[4], max=s.max())


dist_rows = [dict(group="전체", **dist(ana["difficulty_index"]))]
for it in ISSUES:
    dist_rows.append(dict(group=f"issue_type={it}", **dist(ana.loc[ana["issue_type"] == it, "difficulty_index"])))
for pe in PERIODS:
    dist_rows.append(dict(group=f"period={pe}", **dist(ana.loc[ana["period"] == pe, "difficulty_index"])))
dist_df = pd.DataFrame(dist_rows)
hist_counts, hist_edges = np.histogram(ana["difficulty_index"], bins=10)

# =====================================================================
# 3. 집단 비교 (설명용)
# =====================================================================
MED = float(np.median(ana["difficulty_index"]))
ana["med_grp"] = np.where(ana["difficulty_index"] > MED, "상위(중앙값 초과)", "하위(중앙값 이하)")
tab_med = pd.crosstab(ana["med_grp"], ana["cited"]).reindex(
    index=["하위(중앙값 이하)", "상위(중앙값 초과)"], columns=[1, 0], fill_value=0)
fisher_or, fisher_p = stats.fisher_exact(tab_med.values)
ana["ter_grp"] = pd.qcut(ana["difficulty_index"], 3, labels=["하위 1/3", "중위 1/3", "상위 1/3"])
tab_ter = pd.crosstab(ana["ter_grp"], ana["cited"]).reindex(columns=[1, 0], fill_value=0)
chi2, chi_p, chi_dof, chi_exp = stats.chi2_contingency(tab_ter.values, correction=False)
rows03 = []
for split, col, labels, pv in (("median", "med_grp", ["하위(중앙값 이하)", "상위(중앙값 초과)"], fisher_p),
                               ("tertile", "ter_grp", ["하위 1/3", "중위 1/3", "상위 1/3"], chi_p)):
    for g in labels:
        s = ana[ana[col] == g]
        n, k = len(s), int(s["cited"].sum())
        lo, hi = wilson(k, n)
        rows03.append(dict(split=split, group=g, n=n, n_cited=k, cited_rate=rnd(k / n), ci_low=rnd(lo),
                           ci_high=rnd(hi), p=pfmt(pv)))
save(pd.DataFrame(rows03), "03_집단비교.csv")
hi_s, lo_s = ana[ana["med_grp"].str.startswith("상위")], ana[ana["med_grp"].str.startswith("하위")]
med_diff = hi_s["cited"].mean() - lo_s["cited"].mean()
med_diff_ci = confint_proportions_2indep(int(hi_s["cited"].sum()), len(hi_s), int(lo_s["cited"].sum()), len(lo_s),
                                         method="newcomb", compare="diff")
t22 = Table2x2(tab_med.loc[["상위(중앙값 초과)", "하위(중앙값 이하)"]].values)
med_or, med_or_ci = t22.oddsratio, t22.oddsratio_confint()

# =====================================================================
# 4. 층화 (쟁점 유형별, 중앙값 분할 난이도 상위 vs 하위)
# =====================================================================
ana["high"] = (ana["difficulty_index"] > MED).astype(int)
tables, rows04 = [], []
for it in ISSUES:
    s = ana[ana["issue_type"] == it]
    t = np.array([[((s.high == 1) & (s.cited == 1)).sum(), ((s.high == 1) & (s.cited == 0)).sum()],
                  [((s.high == 0) & (s.cited == 1)).sum(), ((s.high == 0) & (s.cited == 0)).sum()]], dtype=float)
    tables.append(t)
    tt = Table2x2(t, shift_zeros=True)
    lo, hi = tt.oddsratio_confint()
    rows04.append(dict(issue_type=it, odds_ratio=rnd(tt.oddsratio), ci_low=rnd(lo), ci_high=rnd(hi),
                       n=len(s), breslow_day_p=np.nan, zero_cell=int((t == 0).any())))
st = StratifiedTable([t for t in tables])
bd_p = st.test_equal_odds(adjust=False).pvalue
mh_lo, mh_hi = st.oddsratio_pooled_confint()
mh_p = st.test_null_odds(correction=False).pvalue
rows04.append(dict(issue_type="MH 합산", odds_ratio=rnd(st.oddsratio_pooled), ci_low=rnd(mh_lo), ci_high=rnd(mh_hi),
                   n=N, breslow_day_p=pfmt(bd_p), zero_cell=0))
df04 = pd.DataFrame(rows04)
zero_strata = df04.loc[df04["zero_cell"] == 1, "issue_type"].tolist()
save(df04.drop(columns=["zero_cell"]), "04_층화.csv")

# =====================================================================
# 5. 모형 공통 함수
# =====================================================================
TERM_NAMES = {"difficulty": "difficulty_index", "it_면책": "issue_type[면책]", "it_고지·설명": "issue_type[고지·설명]",
              "pe_2010-2016": "period[2010-2016]", "pe_2017-2026": "period[2017-2026]"}


def design(df, xcol, sd):
    """참조 범주 = 표본에 있는 범주 중 목록의 첫 값(전체 표본이면 보상범위·정의, ~2009).
    예: 2010년 이후만이면 period 참조는 2010-2016, 더미는 2017-2026 하나."""
    X = pd.DataFrame({"difficulty": df[xcol].astype(float).values / sd}, index=df.index)
    its = [v for v in ISSUES if (df["issue_type"] == v).any()]
    pes = [v for v in PERIODS if (df["period"] == v).any()]
    for it in its[1:]:
        X[f"it_{it}"] = (df["issue_type"] == it).astype(float)
    for pe in pes[1:]:
        X[f"pe_{pe}"] = (df["period"] == pe).astype(float)
    X.insert(0, "const", 1.0)
    if np.linalg.matrix_rank(X.values) < X.shape[1]:
        raise RuntimeError(f"설계 행렬 계수 부족: {list(X.columns)}")
    return X


def separation(X, y):
    """더미 범주 안에서 결과가 한쪽뿐이면 (준)완전 분리로 본다."""
    for c in X.columns:
        if c in ("const", "difficulty"):
            continue
        yy = y[X[c] == 1]
        if len(yy) == 0 or yy.nunique() < 2:
            return True
    return False


def fit_logit(X, y):
    m = sm.Logit(y, X).fit(method="newton", maxiter=100, disp=0)
    if not m.mle_retvals.get("converged", True):
        raise RuntimeError("수렴 안 됨")
    ci = m.conf_int().values
    return dict(coef=m.params.values, ci=ci, p=m.pvalues.values, cols=list(X.columns), ci_method="wald")


def fit_firth(X, y):
    """Firth. 프로파일 우도 CI·벌점 우도비 p를 모든 항에 구하고, 수치 문제로 실패하면
    난이도 항만 프로파일로, 그것도 실패하면 Wald로 구한다(ci_method에 기록)."""
    Xn = X.drop(columns=["const"])
    jd_ = list(Xn.columns).index("difficulty")
    tries = [("profile(all)", dict()), ("profile(difficulty only)", dict(test_vars=jd_)), ("wald", dict(wald=True))]
    last = None
    for name, kw in tries:
        try:
            f = FirthLogisticRegression(max_iter=100, pl_max_iter=200, **kw)
            f.fit(Xn.values, y.values)
            ci_ = np.asarray(f.ci_, dtype=float)
            pv_ = np.asarray(f.pvals_, dtype=float)
            if "test_vars" in kw:            # 난이도 외 항은 Wald로 채운다
                fw = FirthLogisticRegression(max_iter=100, wald=True).fit(Xn.values, y.values)
                ci_w, pv_w = np.asarray(fw.ci_, dtype=float), np.asarray(fw.pvals_, dtype=float)
                keep = np.isnan(ci_).any(axis=1)
                ci_[keep], pv_[np.isnan(pv_)] = ci_w[keep], pv_w[np.isnan(pv_)]
            if np.isnan(ci_[jd_]).any():
                raise RuntimeError("CI nan")
            coef = np.r_[f.intercept_, f.coef_]
            ci = np.vstack([ci_[-1], ci_[:-1]])
            pv = np.r_[pv_[-1], pv_[:-1]]
            return dict(coef=coef, ci=ci, p=pv, cols=list(X.columns), ci_method=name)
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def run_model(df, xcol, sd, ycol="cited", force=None):
    """기준값 9·10을 적용해 적합. force='logit'/'firth'면 그 방식으로."""
    y = df[ycol].astype(int)
    X = design(df, xcol, sd)
    n1 = int(y.sum())
    minority = int(min(n1, len(y) - n1))
    sep = separation(X, y)
    use_firth = (minority < 50) or sep
    if force == "logit":
        use_firth = False
    elif force == "firth":
        use_firth = True
    res = fit_firth(X, y) if use_firth else fit_logit(X, y)
    if not use_firth and np.nanmax(np.abs(res["coef"])) > 15:     # 분리 의심 → Firth
        res, use_firth, sep = fit_firth(X, y), True, True
    j = res["cols"].index("difficulty")
    res.update(n=len(y), n_cited=n1, n_minority=minority, firth=int(use_firth), separation=int(sep),
               exploratory=int(minority < 30), X=X, y=y,
               or_d=float(np.exp(res["coef"][j])), lo_d=float(np.exp(res["ci"][j, 0])),
               hi_d=float(np.exp(res["ci"][j, 1])), p_d=float(res["p"][j]), b_d=float(res["coef"][j]))
    return res


def model_table(res):
    rows = []
    for i, c in enumerate(res["cols"]):
        rows.append(dict(term="const" if c == "const" else TERM_NAMES[c], coef=rnd(res["coef"][i]),
                         odds_ratio=rnd(np.exp(res["coef"][i])), ci_low=rnd(np.exp(res["ci"][i, 0])),
                         ci_high=rnd(np.exp(res["ci"][i, 1])), p=pfmt(res["p"][i]), n=res["n"],
                         n_minority=res["n_minority"], firth=res["firth"], exploratory=res["exploratory"]))
    return rows


# =====================================================================
# 5. 주 모형
# =====================================================================
main = run_model(ana, "difficulty_index", SD_MAIN)
main_firth_ref = run_model(ana, "difficulty_index", SD_MAIN, force="firth")
rows05 = model_table(main)
if not main["firth"]:
    rows05 += model_table(main_firth_ref)        # 참고: Firth (PROJECT.md 4-8), firth = 1 행
save(pd.DataFrame(rows05), "05_주모형.csv")

# =====================================================================
# 6. 예측 인용 확률 + 6-1 곡선 (같은 부트스트랩 표본)
# =====================================================================
Q25, Q75 = np.percentile(ana["difficulty_index"], [25, 75])
P5, P95 = np.percentile(ana["difficulty_index"], [5, 95])
GRID = np.linspace(P5, P95, 20)
Xm = main["X"].values
ym = main["y"].values
jd = main["cols"].index("difficulty")


def avg_pred(X, beta, value):
    Xv = X.copy()
    Xv[:, jd] = value / SD_MAIN
    return float(expit(Xv @ beta).mean())


def _firth_beta(X, y):
    f = FirthLogisticRegression(skip_ci=True, skip_pvals=True, max_iter=100)
    f.fit(X[:, 1:], y)
    return np.r_[f.intercept_, f.coef_]


def fit_beta(X, y):
    """주 모형과 같은 방식으로 적합. 재표본에서 (준)완전 분리(수렴 안 됨 또는 |계수| > 15)가 생기면
    기준값 9(완전 분리면 Firth)를 그 재표본에도 적용한다. 반환: (계수, Firth 사용 여부)."""
    if main["firth"]:
        return _firth_beta(X, y), True
    try:
        m = sm.Logit(y, X).fit(method="newton", maxiter=100, disp=0)
        ok = m.mle_retvals.get("converged", True) and np.max(np.abs(m.params)) <= 15
    except Exception:  # noqa: BLE001
        ok = False
    if ok:
        return np.asarray(m.params), False
    return _firth_beta(X, y), True


beta0 = main["coef"]
pt_low, pt_high = avg_pred(Xm, beta0, Q25), avg_pred(Xm, beta0, Q75)
pt_curve = np.array([avg_pred(Xm, beta0, g) for g in GRID])

rng = np.random.default_rng(SEED)
boot_low, boot_high, boot_curve, n_fail, n_boot_firth = [], [], [], 0, 0
boot_is_firth = []   # 재표본별 Firth 사용 여부(stats_수정_1 ②: Firth 재표본을 뺀 CI 참고용)
for b in range(N_BOOT):
    idx = rng.integers(0, N, N)
    Xb, yb = Xm[idx], ym[idx]
    try:
        if np.any(Xb[:, 1:].std(axis=0) == 0):      # 범주가 통째로 빠진 재표본은 적합 불가
            raise RuntimeError
        beta, used_f = fit_beta(Xb, yb)
    except Exception:  # noqa: BLE001
        n_fail += 1
        continue
    n_boot_firth += int(used_f)
    boot_is_firth.append(bool(used_f))
    boot_low.append(avg_pred(Xb, beta, Q25))
    boot_high.append(avg_pred(Xb, beta, Q75))
    boot_curve.append([avg_pred(Xb, beta, g) for g in GRID])
boot_low, boot_high, boot_curve = np.array(boot_low), np.array(boot_high), np.array(boot_curve)
boot_diff = boot_high - boot_low
N_OK = len(boot_low)
boot_is_firth = np.array(boot_is_firth, dtype=bool)
ci = lambda a: np.percentile(a, [2.5, 97.5])
rows06 = []
for point, val, est, arr in (("low25", Q25, pt_low, boot_low), ("high25", Q75, pt_high, boot_high),
                             ("diff", np.nan, pt_high - pt_low, boot_diff)):
    lo, hi = ci(arr)
    rows06.append(dict(point=point, difficulty_value=rnd(val), pred=rnd(est), ci_low=rnd(lo), ci_high=rnd(hi),
                       n=N, n_boot=N_OK, seed=SEED))
save(pd.DataFrame(rows06), "06_예측확률.csv")

step = GRID[1] - GRID[0]
edges = np.r_[GRID[0] - step / 2, (GRID[:-1] + GRID[1:]) / 2, GRID[-1] + step / 2]
dvals = ana["difficulty_index"].values
n_near = [int(((dvals >= edges[i]) & (dvals < edges[i + 1])).sum()) if i < 19
          else int(((dvals >= edges[i]) & (dvals <= edges[i + 1])).sum()) for i in range(20)]
cl = np.percentile(boot_curve, [2.5, 97.5], axis=0)
curve = pd.DataFrame(dict(difficulty=np.round(GRID, 4), pred=np.round(pt_curve, 4), ci_low=np.round(cl[0], 4),
                          ci_high=np.round(cl[1], 4), n=N, n_near=n_near))
save(curve, "pred_curve.csv")

# =====================================================================
# 7. 필수 민감도 4개
# =====================================================================
NOT_DONE_2 = None
try:
    import kiwipiepy  # noqa: F401  (② 재계산에 필요)
except ImportError:
    NOT_DONE_2 = "수행하지 못함: py -3.10 환경에 kiwipiepy 없음(difficulty_colab.py compute에 필요, 설치는 사람이 함)"

sens = []


def sens_row(label, res, extra=None):
    r = dict(analysis=label, odds_ratio=rnd(res["or_d"]), ci_low=rnd(res["lo_d"]), ci_high=rnd(res["hi_d"]),
             n=res["n"], n_minority=res["n_minority"],
             direction_same=int(np.sign(res["b_d"]) == np.sign(main["b_d"])))
    if extra:
        r.update(extra)
    return r


# 마무리_정리 2 (2026-11-05): 07에만 맨 뒤 firth·exploratory 열(각 행 모형에서 실제로 쓴 방식, 기준값 9·10). 08은 그대로.
def sens7_row(label, res):
    r = sens_row(label, res)
    r.update(firth=int(res["firth"]), exploratory=int(res["exploratory"]))
    return r


sens_info = {}
sens.append(sens7_row("main", main))
sens_info["main"] = main

a1 = ana.copy()
a1["cited"] = np.where(a1["partial"] == 1, 0, a1["cited"])
r1 = run_model(a1, "difficulty_index", SD_MAIN)
sens.append(sens7_row("① 일부인용0", r1)); sens_info["① 일부인용0"] = r1

N_ARG = int(ana["arg_clause_text"].fillna("").str.strip().ne("").sum())
if NOT_DONE_2 is None:
    sys.path.insert(0, OUT)
    import difficulty_colab as dc
    terms = pd.read_csv(os.path.join(OUT, "term_dict.csv"), encoding=ENC)["term"].tolist()
    a2 = ana.copy()
    has_arg = a2["arg_clause_text"].fillna("").str.strip().ne("")
    ind = dc.compute(a2.loc[has_arg, "arg_clause_text"].tolist(), terms)
    ind["exception_count"] = ind[f"exception_count_{dc.EXC_MAIN}"]
    ind["ref_count"] = ind[f"ref_count_{dc.REF_MAIN}"]
    use = ["words_per_sentence", "exception_count", "ref_count"]
    if float((diff["term_ratio"] == 0).mean()) < dc.ZERO_RULE:
        use.append("term_ratio")
    z = pd.concat([(ind[c] - diff[c].mean()) / diff[c].std(ddof=0) for c in use], axis=1).mean(axis=1)
    a2.loc[has_arg, "difficulty_index"] = z.values
    r2 = run_model(a2, "difficulty_index", SD_MAIN)
    sens.append(sens7_row("② 판단↔주장", r2)); sens_info["② 판단↔주장"] = r2
else:
    sens.append(dict(analysis="② 판단↔주장", odds_ratio=NOT_DONE_2, ci_low="수행하지 못함", ci_high="수행하지 못함",
                     n="수행하지 못함", n_minority="수행하지 못함", direction_same="수행하지 못함",
                     firth="수행하지 못함", exploratory="수행하지 못함"))

SD_ART = float(ana["difficulty_index_article"].std(ddof=1))
r3 = run_model(ana, "difficulty_index_article", SD_ART)
sens.append(sens7_row("③ 조 전체", r3)); sens_info["③ 조 전체"] = r3

a4 = ana[ana["period"] != "~2009"].copy()
r4 = run_model(a4, "difficulty_index", SD_MAIN)
sens.append(sens7_row("④ 2010년 이후", r4)); sens_info["④ 2010년 이후"] = r4
save(pd.DataFrame(sens), "07_민감도_필수.csv")

# =====================================================================
# 8. 선택 민감도
# =====================================================================
NOT = "수행하지 않음"
opt, opt_info = [], {}


def opt_done(label, res):
    opt.append(sens_row(label, res, dict(done=1)))
    opt_info[label] = res


def opt_not(label, why):
    opt.append(dict(analysis=label, odds_ratio=NOT, ci_low=NOT, ci_high=NOT, n=NOT, n_minority=NOT,
                    direction_same=NOT, done=0))
    opt_info[label] = why


# 풀어 쓴 서술 포함 (필수로 수행, PROJECT.md 4-8)
fs = allm[(allm["exclude_reason"] == "풀어 쓴 서술")]
fs_with = fs[fs["difficulty_index"].notna() & fs["cited"].notna()].copy()
FS_TOTAL, FS_NODIFF = len(fs), int(fs["difficulty_index"].isna().sum())
FS_NOCITED = int((fs["difficulty_index"].notna() & fs["cited"].isna()).sum())
fs_with["cited"] = fs_with["cited"].astype(int)
a_fs = pd.concat([ana, fs_with], ignore_index=True)
opt_done("풀어 쓴 서술 포함", run_model(a_fs, "difficulty_index", SD_MAIN))

a_att = ana[ana["clause_text_source"] == "붙임"].copy()
opt_done("붙임 문구 사건만", run_model(a_att, "difficulty_index", SD_MAIN))
opt_not("처음 언급 대신 최댓값", "여러 조항의 난이도가 입력에 없음(difficulty.csv는 사건당 처음 언급 조항 1개)")
opt_not("처음 언급 대신 평균", "여러 조항의 난이도가 입력에 없음(difficulty.csv는 사건당 처음 언급 조항 1개)")
for ind_c in ["words_per_sentence", "exception_count", "term_ratio", "ref_count"]:
    opt_done(f"지표 하나씩: {ind_c}", run_model(ana, ind_c, float(ana[ind_c].std(ddof=1))))
a_ed = ana[ana["explained_duty"] != 1].copy()
opt_done("설명의무 위반 인정 사건 제외", run_model(a_ed, "difficulty_index", SD_MAIN))
opt_done("유형 안 표준화", run_model(ana, "diff_z_within_type", float(ana["diff_z_within_type"].std(ddof=1))))
opt_not("쟁점 판단 문장 한정(계획서 7-3)", "쟁점 정리 문장 안의 조항을 따로 뽑은 열이 입력에 없음")
opt_not("쟁점 문장에 가장 가까운 조항(PROJECT.md 4-8 ④)", "가장 가까운 조항을 뽑은 열이 입력에 없음")

# stats_수정_3 (2026-11-04, 사후·탐색적): issue_type만 R2(docs/issue_type_민감도_규칙.md)로 바꾼 주 모형
R2_LABEL = "쟁점 유형 R2(판단 안 면책 조항, 사후)"
r2tab = pd.read_csv(p("data", "processed", "issue_type_r2.csv"), encoding=ENC, dtype={"case_key": str})
if r2tab["case_key"].duplicated().any():
    sys.exit("issue_type_r2.csv에 case_key 중복. 멈춥니다.")
a_r2 = ana.merge(r2tab[["case_key", "issue_type_r2", "r2_source"]], on="case_key", how="left", validate="one_to_one")
R2_MISSING = a_r2.loc[a_r2["issue_type_r2"].isna(), "case_key"].tolist()
if R2_MISSING:
    sys.exit(f"issue_type_r2.csv에 없는 분석 사건 {len(R2_MISSING)}건: {R2_MISSING}. 멈춥니다.")
if not set(a_r2["issue_type_r2"]).issubset(ISSUES):
    sys.exit(f"issue_type_r2에 알 수 없는 값: {set(a_r2['issue_type_r2']) - set(ISSUES)}. 멈춥니다.")
R2_N_FILE, R2_N_MERGED = len(r2tab), len(a_r2)
R2_XTAB = pd.crosstab(a_r2["issue_type"], a_r2["issue_type_r2"]).reindex(index=ISSUES, columns=ISSUES, fill_value=0)
R2_CHANGED = int((a_r2["issue_type"] != a_r2["issue_type_r2"]).sum())
a_r2["issue_type"] = a_r2["issue_type_r2"]          # 같은 식·같은 참조 범주(보상범위·정의), issue_type 값만 교체
opt_done(R2_LABEL, run_model(a_r2, "difficulty_index", SD_MAIN))
save(pd.DataFrame(opt), "08_민감도_선택.csv")

# =====================================================================
# 9. 시계열
# =====================================================================
yr = ana["decision_year"].astype(int)
year_counts = yr.value_counts()
if (year_counts < 5).any():
    Y0 = int(yr.min())
    ana["year_bin"] = yr.map(lambda y: f"{Y0 + 3 * ((y - Y0) // 3)}-{min(Y0 + 3 * ((y - Y0) // 3) + 2, int(yr.max()))}")
    BIN_RULE = f"연도별 5건 미만인 해가 있어 3년 단위({Y0}년부터 3년씩, 사건이 있는 묶음만)"
else:
    ana["year_bin"] = yr.astype(str)
    BIN_RULE = "모든 해 5건 이상이라 연도별"
rows09 = []
for yb, s in sorted(ana.groupby("year_bin"), key=lambda x: x[0]):
    n, k = len(s), int(s["cited"].sum())
    lo, hi = wilson(k, n)
    r = dict(year_bin=yb, n=n, n_cited=k, cited_rate=rnd(k / n), ci_low=rnd(lo), ci_high=rnd(hi),
             mean_difficulty=rnd(s["difficulty_index"].mean()))
    for it in ISSUES:
        r[f"share_{it}"] = rnd((s["issue_type"] == it).mean())
    rows09.append(r)
df09 = pd.DataFrame(rows09)
save(df09, "09_시계열.csv")

# =====================================================================
# 10. 조항 주제
# =====================================================================
rows10 = []
for tp, s in ana.groupby("topic"):
    n = len(s)
    k = int(s["cited"].sum())
    # stats_수정_2: n_cited, 95% CI(02와 같은 Wilson). 5건 미만은 n_cited만, CI 빈칸
    lo, hi = wilson(k, n) if n >= 5 else (np.nan, np.nan)
    rows10.append(dict(topic=tp, n=n, cited_rate=rnd(s["cited"].mean()) if n >= 5 else np.nan,
                       mean_difficulty=rnd(s["difficulty_index"].mean()),
                       n_cited=k, ci_low=rnd(lo), ci_high=rnd(hi)))
df10 = pd.DataFrame(rows10).sort_values(["n", "topic"], ascending=[False, True]).head(10).reset_index(drop=True)
save(df10, "10_조항주제.csv")
# stats_수정_2: 우선순위 그림 기준선(값만. 판정·순위·새 점수 없음)
_k_all, _n_all = int(ana["cited"].sum()), len(ana)
_n_shown = [len(s) for _, s in ana.groupby("topic") if len(s) >= 5]
save(pd.DataFrame([
    dict(item="cited_rate_overall", value=rnd(_k_all / _n_all),
         설명=f"분석 포함 {_n_all}건 전체 인용률(= {_k_all}/{_n_all})"),
    dict(item="n_median_topics", value=float(np.median(_n_shown)),
         설명=f"인용률을 표시하는 주제(5건 이상) {len(_n_shown)}개의 건수 n 중앙값"),
]), "10_조항주제_기준선.csv")
N_TOPICS = ana["topic"].nunique()
ETC_SHARE = float((ana["topic"] == "기타").mean())

# =====================================================================
# 결과 문장 판정
# =====================================================================
if main["lo_d"] > 1:
    verdict, vkey = "난이도가 높을수록 인용되는 경향이 보였다(양의 연관)", "양의 연관"
elif main["hi_d"] < 1:
    verdict, vkey = "난이도가 높을수록 인용이 적은 경향이 보였다(음의 연관)", "음의 연관"
else:
    verdict, vkey = "연관이 뚜렷하지 않다(불확실)", "뚜렷하지 않음"
prefix = "탐색적으로 " if main["exploratory"] else ""
dir_changed = [s["analysis"] for s in sens if s["analysis"] != "main" and s["direction_same"] == 0]
suffix = " 조건에 따라 달라진다." if dir_changed else ""
d_lo, d_hi = ci(boot_diff)
if d_lo > 0:
    diff_key = "양의 연관"
elif d_hi < 0:
    diff_key = "음의 연관"
else:
    diff_key = "뚜렷하지 않음"
diff_agree = diff_key == vkey

# =====================================================================
# 통계요약.md
# =====================================================================
f3 = lambda x: f"{x:.3f}"
f4 = lambda x: f"{x:.4f}"


def pr(x):
    return f"{x:.3g}" if x >= 0.001 else f"{x:.2e}"


def ci_str(res):
    return f"{f3(res['or_d'])} [{f3(res['lo_d'])}, {f3(res['hi_d'])}]"


def mdt(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if (isinstance(v, float) and np.isnan(v)) else
                                     (f"{v:.4g}" if isinstance(v, float) else str(v)) for v in r) + " |")
    return "\n".join(out)


L = []
w = L.append
w("# 통계요약 (stats 단계, analysis.py 자동 생성)\n")
w("## 결과 문장 판정 (agents/stats.md 판정 규칙, 05_주모형.csv 난이도 오즈비 95% CI)\n")
w(f"- **판정: {vkey}**")
w(f"- **결과 문장: \"{prefix}{verdict}{suffix}\"**")
w(f"- 근거: 난이도 1 SD당 오즈비 {ci_str(main)}, p = {pr(main['p_d'])}, N = {main['n']}(소수 쪽 기각 {main['n_minority']}건), "
  f"{'Firth' if main['firth'] else '일반 로지스틱'}. p값은 판정에 쓰지 않았다.")
w(f"- 덧붙일 말: \"탐색적으로\" → {'붙임' if prefix else '붙이지 않음'}(소수 쪽 {main['n_minority']}건, 기준값 10). "
  f"\"조건에 따라 달라진다\" → {'붙임(방향이 바뀐 필수 민감도: ' + ', '.join(dir_changed) + ')' if dir_changed else '붙이지 않음(필수 민감도 중 계산한 행은 모두 방향 같음)'}"
  + ("" if NOT_DONE_2 is None else ". 단 ② 판단↔주장은 수행하지 못해 방향을 확인하지 못했다"))
w(f"- 보조(06_예측확률.csv diff): 상위 25% − 하위 25% 예측 인용 확률 차이 {f3(pt_high - pt_low)} "
  f"[{f3(d_lo)}, {f3(d_hi)}] → {diff_key}. 오즈비 판정과 {'일치' if diff_agree else '**어긋남**(오즈비 판정을 따른다)'}.")
w("- 해석 범위: 공개된 금감원 보험 분쟁조정 결정례(자동차보험 제외) 안의 연관성이다. 인과가 아니다. "
  "난이도 지수는 \"읽기 부담\"의 대리 지표로 읽는다(평가 일치도 카파 0.059, PROJECT.md 4-8).\n")

w("## 4줄 요약\n")
w(f"- 한 일: agents/stats.md 1~10단계(합치기, 기술통계, 집단 비교, 층화, 주 모형, 예측 확률·곡선, 필수 민감도, 선택 민감도, 시계열, 조항 주제)")
w(f"- 처리 건수: 분석 {N}건(인용·일부 인용 {int(ana['cited'].sum())}, 기각 {N - int(ana['cited'].sum())}), 합친 뒤 빠진 건 {len(missing)}")
w(f"- 제외한 것: cases.csv에서 exclude_reason이 있는 행(292). 2009-29 중복 diff_id {'/'.join(DUP_DROPPED)}")
w(f"- 불확실한 점: 필수 민감도 ②{' 수행하지 못함(kiwipiepy 없음)' if NOT_DONE_2 else ' 수행함'}, 주 결과 CI가 넓음, "
  "(n_near 정의·2009-29 D204·재표본 Firth 처리는 2026-11-04 사람 확인으로 확정)\n")

w("## 1. 합치기와 점검 (01_합치기점검.csv)\n")
w(f"- difficulty.csv(diff_id) → difficulty_id_map.csv → cases.csv(case_key). 합친 수 {N}, 빠진 수 {len(missing)}.")
w(f"- case_key {DUP_KEY}: diff_id {', '.join(dup_ids)} 두 개. cases.csv 두 행(nttId 64488 분석 포함, 64502 \"중복\")의 clause_text가 "
  f"{'같다' if same_case_text else '다르다'}. difficulty.csv에는 문구 열이 없어 diff_id별 문구를 직접 대조할 수 없었다. "
  f"두 diff_id의 지표·지수 값이 {'모두 같아' if same_metrics else '달라'} 어느 쪽을 써도 결과가 같다. "
  f"**{DUP_CHOSEN}를 사용**하고 {', '.join(DUP_DROPPED)}는 제외했다(2026-11-04 사람 확인으로 D204 확정).")
w(f"- issue_type이 cases.csv와 difficulty.csv에서 다른 사건: {issue_mismatch}건(분석은 cases.csv 값 사용).\n")

w("## 2. 기술통계 (02_기술통계.csv)\n")
tot = [r for r in rows02 if r["issue_type"] == "전체" and r["period"] == "전체"][0]
w(f"- 전체 {tot['n']}건 중 인용 {tot['n_cited']}, 인용률 {f3(tot['cited_rate'])} [{f3(tot['ci_low'])}, {f3(tot['ci_high'])}] (Wilson 95% CI).")
w("- 쟁점 유형 × 시기별 표는 02_기술통계.csv(각 유형·시기의 '전체' 행과 전체 합계 행 포함).")
w("\n난이도(difficulty_index) 분포 — 분석 표본:\n")
w(mdt(dist_df.round(4)))
w("\n히스토그램(10구간) 도수: " + ", ".join(f"[{hist_edges[i]:.2f}, {hist_edges[i+1]:.2f}): {c}" for i, c in enumerate(hist_counts)))
w(f"\n- 난이도 1 SD(분석 표본 157건, ddof=1) = **{SD_MAIN:.4f}** (difficulty_index). 조 전체 지수 SD = {SD_ART:.4f}.\n")

w("## 3. 집단 비교 — 설명용 (03_집단비교.csv)\n")
w(f"- 중앙값 {MED:.4f} 기준(이하 = 하위 / 초과 = 상위). 상위 − 하위 인용률 차이 {f3(med_diff)} "
  f"[{f3(med_diff_ci[0])}, {f3(med_diff_ci[1])}](Newcombe), 오즈비 {f3(med_or)} [{f3(med_or_ci[0])}, {f3(med_or_ci[1])}], "
  f"Fisher 정확검정 p = {pr(fisher_p)}.")
w(f"- 3분위: 카이제곱(자유도 {chi_dof}) p = {pr(chi_p)}, 최소 기대도수 {chi_exp.min():.2f}.\n")

w("## 4. 층화 (04_층화.csv)\n")
w(f"- 노출 = 난이도 중앙값 초과(전체 중앙값 기준), 층 = 쟁점 유형 3개. 층별 오즈비는 0인 칸이 있으면 0.5 보정(해당 층: "
  f"{', '.join(zero_strata) if zero_strata else '없음'}).")
w(f"- Mantel-Haenszel 합산 오즈비 {f3(st.oddsratio_pooled)} [{f3(mh_lo)}, {f3(mh_hi)}], MH 검정 p = {pr(mh_p)}, "
  f"Breslow-Day 동질성 p = {pr(bd_p)}.\n")
w(mdt(df04.drop(columns=["zero_cell"])) + "\n")

w("## 5. 주 모형 (05_주모형.csv)\n")
w(f"- `cited ~ difficulty_index + issue_type + period`, 항 5개. 참조 범주: issue_type = {REF_ISSUE}, period = ~2009.")
w(f"- 방식: {'Firth' if main['firth'] else '일반 로지스틱 회귀'}(소수 쪽 기각 {main['n_minority']}건 ≥ 50, 완전 분리 {'있음' if main['separation'] else '없음'}), "
  f"Wald 95% CI. exploratory = {main['exploratory']}.")
w(f"- **난이도 1 SD({SD_MAIN:.4f})당 오즈비 {ci_str(main)}, p = {pr(main['p_d'])}, N = {main['n']}(인용 {main['n_cited']}, 기각 {main['n_minority']}).**")
w(f"- 참고 Firth(05_주모형.csv의 firth = 1 행, 프로파일 우도 CI·벌점 우도비 p): 오즈비 {ci_str(main_firth_ref)}, p = {pr(main_firth_ref['p_d'])}, CI 방식 {main_firth_ref['ci_method']}.")
w("- 주 결과는 firth = 0 행이다(writer·dashboard는 firth = 0의 difficulty_index 행을 쓴다).\n")
w(mdt(pd.DataFrame(rows05)) + "\n")

w("## 6. 예측 인용 확률 (06_예측확률.csv)\n")
w(f"- 모든 사건({N}건)의 난이도를 하위 25% 값({Q25:.4f}) / 상위 25% 값({Q75:.4f})으로 바꿔 넣고(나머지 변수는 실제 값) 예측 확률을 평균.")
w(f"- 부트스트랩: 사건 단위 복원추출 {N_BOOT}회, 시드 {SEED}(numpy default_rng), 백분위 95% CI. 적합 실패로 뺀 표본 {n_fail}개 → 사용 {N_OK}개. "
  f"이 중 {n_boot_firth}개는 재표본 안에서 (준)완전 분리(어떤 범주의 결과가 한쪽뿐)가 생겨 기준값 9에 따라 Firth로 적합했다(계수만, 나머지는 일반 로지스틱).")
for r in rows06:
    w(f"  - {r['point']}: 예측 인용 확률 {f3(r['pred'])} [{f3(r['ci_low'])}, {f3(r['ci_high'])}]")
w(f"- 재표본 Firth 처리는 2026-11-04 사람 확인으로 인정했다(docs/지시/stats_수정_1.md ②). 06_예측확률.csv와 pred_curve.csv는 위 방식({N_OK}개 모두 사용) 그대로다.")
w(f"- 참고: Firth로 적합한 재표본 {int(boot_is_firth.sum())}개를 뺀 {int((~boot_is_firth).sum())}개로 구한 95% CI(같은 시드·같은 재표본, 점추정은 같음, 판정에 쓰지 않음):")
for _lab, _est, _arr in (("low25", pt_low, boot_low), ("high25", pt_high, boot_high), ("diff", pt_high - pt_low, boot_diff)):
    _lo, _hi = ci(_arr[~boot_is_firth])
    w(f"  - {_lab}: 예측 인용 확률 {f3(_est)} [{f3(_lo)}, {f3(_hi)}]")
w("- 사건별 예측값은 저장하지 않았다.\n")

w("## 6-1. 예측 확률 곡선 (pred_curve.csv)\n")
w(f"- 분석 표본 난이도 5 백분위({P5:.4f}) ~ 95 백분위({P95:.4f}) 사이 같은 간격 20개 지점. 6과 같은 부트스트랩 표본({N_OK}개, 시드 {SEED})의 같은 적합 결과로 지점별 95% CI(곡선 전체를 덮는 띠가 아님).")
w("- n = 모형 사건 수. n_near = 각 지점과 이웃 지점의 중간점 사이(양 끝은 반 칸 바깥까지)에 있는 실제 사건 수(2026-11-04 사람 확인으로 이 정의 확정). "
  f"n_near 합 = {sum(n_near)}(5~95 백분위 밖 사건은 세지 않음).\n")

w("## 7. 필수 민감도 (07_민감도_필수.csv)\n")
w("- 같은 모형식, 난이도는 157건 기준 SD로 나눔(③은 조 전체 지수의 157건 SD). 각 행에 기준값 9·10을 그대로 적용.\n")
sens_df = pd.DataFrame(sens)
w(mdt(sens_df))
w("")
for k, r in sens_info.items():
    w(f"- {k}: 오즈비 {ci_str(r)}, p = {pr(r['p_d'])}, N = {r['n']}(소수 쪽 {r['n_minority']}), "
      f"{'Firth' if r['firth'] else '일반 로지스틱'}(CI {r['ci_method']}), exploratory = {r['exploratory']}"
      + (" ← **방향이 main과 다름**" if np.sign(r['b_d']) != np.sign(main['b_d']) else ""))
w(f"- ① 일부 인용 {int(ana['partial'].sum())}건의 cited를 0으로.")
w(f"- ② 판단↔주장: arg_clause_text가 있는 분석 사건 {N_ARG}건. "
  + (NOT_DONE_2 if NOT_DONE_2 else
     f"이 사건들의 난이도를 주장 문구로 다시 계산(difficulty_colab.py compute, kiwipiepy {kiwipiepy.__version__}, "
     "difficulty.csv 261행 평균·SD로 z점수)해 바꿔 넣음. 재계산 전에 difficulty.csv 조항 5개를 같은 코드로 다시 계산해 원래 지표 값과 같음을 확인했다(docs/보고/stats_수정_1.md)."))
w(f"- ④ 2010년 이후: {r4['n']}건, 소수 쪽 {r4['n_minority']}건 → exploratory = {r4['exploratory']}, {'Firth' if r4['firth'] else '일반 로지스틱'}(기준값 9). "
  "period는 2017-2026 더미 1개(참조 2010-2016).")
if dir_changed:
    w(f"- **방향이 바뀐 행: {', '.join(dir_changed)}**")
w("")

w("## 8. 선택 민감도 (08_민감도_선택.csv)\n")
w(mdt(pd.DataFrame(opt)))
w("")
for k, r in opt_info.items():
    if isinstance(r, str):
        w(f"- {k}: 수행하지 않음 — {r}")
    else:
        w(f"- {k}: 오즈비 {ci_str(r)}, p = {pr(r['p_d'])}, N = {r['n']}(소수 쪽 {r['n_minority']}), "
          f"{'Firth' if r['firth'] else '일반 로지스틱'}(CI {r['ci_method']}), exploratory = {r['exploratory']}"
          + (" ← **방향이 main과 다름**" if np.sign(r['b_d']) != np.sign(main['b_d']) else ""))
w(f"- 풀어 쓴 서술 포함: 풀어 쓴 서술 {FS_TOTAL}건 중 difficulty 없음 {FS_NODIFF}건, cited 없음 {FS_NOCITED}건을 빼고 "
  f"**{len(fs_with)}건을 더함**(합계 {len(a_fs)}건). SD는 157건 기준.")
w("- 지표 하나씩: 각 원지표를 157건 기준 SD로 나눠 넣음. 유형 안 표준화: diff_z_within_type(157건 SD당).")
_r2 = opt_info[R2_LABEL]
_r2_cells = pd.crosstab(a_r2["issue_type"], a_r2["cited"]).reindex(index=ISSUES, columns=[1, 0], fill_value=0)
w(f"- **{R2_LABEL}: 사후 추가(2026-11-04, 탐색적).** 규칙은 docs/issue_type_민감도_규칙.md(결과 보기 전 기록, 골드 A셋 29/30). "
  f"data/processed/issue_type_r2.csv({R2_N_FILE}행)를 case_key로 합침: {R2_N_MERGED}건 모두 붙음, 빠진 건 0. "
  f"주 모형과 같은 식(난이도 + issue_type + period, 참조 {REF_ISSUE}·~2009)에서 issue_type만 R2로 바꿈. "
  f"R1과 다른 사건 {R2_CHANGED}건. R2 유형별 사건 수(인용/기각): "
  + ", ".join(f"{it} {int(_r2_cells.loc[it].sum())}({int(_r2_cells.loc[it, 1])}/{int(_r2_cells.loc[it, 0])})" for it in ISSUES)
  + f". 0인 칸 {'있음' if (_r2_cells.values == 0).any() else '없음'}, 완전 분리 {'있음' if _r2['separation'] else '없음'} → "
  f"{'Firth' if _r2['firth'] else '일반 로지스틱'}(기준값 9). "
  f"난이도 오즈비 {ci_str(_r2)}, p = {pr(_r2['p_d'])}, 방향 main과 {'같음' if np.sign(_r2['b_d']) == np.sign(main['b_d']) else '**다름**'}. "
  f"위 행의 exploratory = {_r2['exploratory']}는 기준값 10(소수 쪽 < 30) 기준이고, \"탐색적\"은 사후에 정한 분석이라 붙인 표시다. "
  "사후 민감도이므로 판정 문구는 주 결과를 따른다(바꾸지 않음).\n")

w("## 9. 시계열 (09_시계열.csv)\n")
w(f"- 연도 기준: decision_year. 묶음: {BIN_RULE}. 5건 미만인 묶음: "
  f"{', '.join(df09.loc[df09['n'] < 5, 'year_bin']) or '없음'}(그대로 표시).")
w(f"- 제도 시점: {INST_POINTS}. 검정·회귀 없음.")
w("- 시기 변화는 결정례 공개 방식·결정문 양식 변화일 수 있다.\n")
w(mdt(df09) + "\n")

w("## 10. 조항 주제 (10_조항주제.csv)\n")
w(f"- cases.csv `topic`(PROJECT.md 4-8 합치기 규칙). 분석 표본의 주제는 {N_TOPICS}개라 상위 10개 = 전부. "
  f"\"기타\" 비율 {ETC_SHARE:.3f}(20% 미만이라 키워드 보태기 해당 없음). 인용률은 5건 이상만.")
w("- 검정 없음. 조항이 쓰이는 빈도(노출량)를 모르므로 사건 수가 많은 주제가 더 문제라는 뜻은 아니다.\n")
w(mdt(df10[["topic", "n", "cited_rate", "mean_difficulty"]]) + "\n")  # 요약 표는 기존 4열 유지(n_cited·CI는 csv)

w("## 한계\n")
w(f"- 표본: 분석 {N}건, 기각 {N - int(ana['cited'].sum())}건으로 작아 CI가 넓다. 분쟁조정을 신청하고 결정문이 공개된 사건뿐이다.")
w("- 선택 편향: 풀어 쓴 서술 91건이 빠졌고 인용률이 14.2%p 낮다(기준값 11 초과, PROJECT.md 4-8 수치). 선택 민감도 \"풀어 쓴 서술 포함\" 결과는 8장. 조항을 뽑을 수 있었던 사건만 들어 있다.")
w("- 시대 차이: 결정문 양식·약관 문구가 시기마다 다르다(옛 결정 75건). 전문용어 사전은 현행 표준약관 기준이다.")
w("- 지수 타당성: 평가 일치도 카파 0.059(기준값 13 미달), 예외 표현 0 비율 62.5%(PROJECT.md 4-8·인계 문서 수치).")
w("- R2는 A셋에서 R1이 틀린 사건의 모양을 알고 만든 규칙이라 A셋 29/30도 완전히 독립된 검증이 아니다.")
w("- 조항 주제(10번, 우선순위 그림)도 처음 언급 조항 기준이라 같은 문제가 있다.")

with open(os.path.join(OUT, "통계요약.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")

print("판정:", vkey, "|", prefix + verdict + suffix)
print("주 모형 난이도 OR", ci_str(main), "p", pr(main["p_d"]), "SD", round(SD_MAIN, 4))
print("예측", rows06)
print("필수 민감도\n", sens_df.to_string(index=False))
print("선택 민감도\n", pd.DataFrame(opt).to_string(index=False))
print("boot fail", n_fail, "boot firth", n_boot_firth)
