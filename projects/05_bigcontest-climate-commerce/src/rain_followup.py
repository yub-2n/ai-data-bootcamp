"""
빅콘테스트 2026 — 호우 후속 분석 (src/rain_followup.py)

세 가지를 계산합니다. 주 모형(event_study.py의 A1)을 그대로 쓰고, 필요한 부분만 바꿉니다.
  A. 금액 환산 : 순손실(N5, 평소 하루치 대비 %)을 원(₩)으로 바꿈
  B. 반복성    : 사건마다 따로 손실과 이후 5일 변화를 추정해, 같은 방향이 반복되는지 셈
  C. 50mm 기준 : 호우일을 50mm 이상 / 30~50mm로 나눠 하루 손실(L)을 비교

- 파일을 저장하지 않고 화면에만 출력합니다. 시드는 event_study.py와 같은 2026입니다.
- 프로젝트 폴더에서 실행:  python -B src/rain_followup.py
"""
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, 'src')
from prep import DAYS, GROUPS
from event_study import (REGION_CARD, REGION_WX, SEED, N_DRAW, build_design,
                         effect_draws, fit_ols, load_all, series, weather)

GROUP_NAMES = list(GROUPS)
TAXI = '택시'          # 건당 금액이 실제 요금과 맞지 않아 금액 계산에서만 뺌


# ─────────────────────────────────────────────
# 공통: 결제액 일별 합계 (택시 제외)
# ─────────────────────────────────────────────
def amount_series(data, reg, grp=None, seg='out'):
    """지역(reg)의 일별 결제액(원). 택시 업종은 뺍니다."""
    s = data['card']
    s = s[(s['MCT_SGG_CD'] == REGION_CARD[reg]) & (s['MCT_RY_CD'] != TAXI)]
    if seg == 'out':
        s = s[s['seg'] == 'out']
    if grp:
        s = s[s['group'] == grp]
    return s.groupby('date')['TS_AT'].sum().reindex(DAYS)


def normal_days(X):
    """'평소 날': 표본 안에서 호우일(D0), 사건 전날(L1), 사건 뒤(P1~P7), 10~30mm 비가 모두 0인 날."""
    cols = ['D0', 'L1'] + [f'P{k}' for k in range(1, 8)] + ['rain10']
    cols = [c for c in cols if c in X.columns]
    return X.index[(X[cols] == 0).all(axis=1)]


def pct(a, lo=5, hi=95):
    return np.percentile(a, [lo, hi])


# ─────────────────────────────────────────────
# A. 금액 환산
# ─────────────────────────────────────────────
def money_table(data, reg, seg='out'):
    """
    두 가지 방법으로 '사건 1번당 사라진 결제액(원)'을 계산합니다.
      방법1: 건수 모형의 N5(%) × 평소 하루 결제액   (건당 금액이 비 때문에 변하지 않는다고 가정)
      방법2: 결제액 모형의 N5(%) × 평소 하루 결제액 (결제액 자체를 모형에 넣음)
    """
    X, _ = build_design(data, reg)
    base_idx = normal_days(X)
    n_kept = len(data['ev'][REGION_WX[reg]]['kept'])
    rows = []
    for lab, grp in [('83합계', None)] + [(g, g) for g in GROUP_NAMES]:
        amt = amount_series(data, reg, grp, seg)
        base = float(amt[base_idx].mean())                          # 평소 하루 결제액
        pc, dc = effect_draws(fit_ols(series(data, reg, grp, seg), X))
        pa, da = effect_draws(fit_ols(amt, X))
        m1 = pc['N5'][0] / 100 * base
        m1_lo, m1_hi = pct(dc['N5'] / 100 * base)
        m2 = pa['N5'][0] / 100 * base
        m2_lo, m2_hi = pct(da['N5'] / 100 * base)
        rows.append({'그룹': lab, '평소하루(만원)': base / 1e4,
                     '건수N5%': pc['N5'][0], '금액N5%': pa['N5'][0],
                     '방법1(만원/사건)': m1 / 1e4, '방법1_5%': m1_lo / 1e4, '방법1_95%': m1_hi / 1e4,
                     '방법2(만원/사건)': m2 / 1e4, '방법2_5%': m2_lo / 1e4, '방법2_95%': m2_hi / 1e4})
    t = pd.DataFrame(rows).set_index('그룹')
    return t, n_kept, len(base_idx)


# ─────────────────────────────────────────────
# B. 반복성 (사건별 추정)
# ─────────────────────────────────────────────
def per_event(data, reg, grp=None, seg='out'):
    """
    D0와 P1~P5를 사건마다 따로 둔 모형.
      D0_e : 사건 e의 호우일
      Q_e  : 사건 e 뒤 1~5일 (원래 P1~P5 더미가 1인 날 중 사건 e에 속한 날)
    P6, P7과 나머지 통제 변수는 주 모형과 같습니다.
    """
    X, _ = build_design(data, reg)
    info = data['ev'][REGION_WX[reg]]
    keep = [c for c in X.columns if c not in ['D0'] + [f'P{k}' for k in range(1, 6)]]
    Z = X[keep].copy()
    wet_all = sorted(d for s, e in info['events'] for d in pd.date_range(s, e))   # 모든 호우일(뺀 사건 포함)
    labels = []
    for i, (s, e) in enumerate(info['kept']):
        lab = s.strftime('%m/%d') + ('' if s == e else '~' + e.strftime('%m/%d'))
        labels.append(lab)
        d0 = ((Z.index >= s) & (Z.index <= e)).astype(float)
        later = [w for w in wet_all if w > e]                      # 다음 호우일 앞에서 멈춤 (P 더미 규칙과 같음)
        stop = min(e + pd.Timedelta(days=5), later[0] - pd.Timedelta(days=1)) if later else e + pd.Timedelta(days=5)
        post = ((Z.index > e) & (Z.index <= stop)).astype(float)   # 이 사건 자신의 뒤 1~5일만
        Z[f'D0_{i}'] = d0
        Z[f'Q_{i}'] = post
    res = fit_ols(series(data, reg, grp, seg), Z)
    rows = []
    for i, lab in enumerate(labels):
        b0 = res.params.get(f'D0_{i}', np.nan)
        bq = res.params.get(f'Q_{i}', np.nan)
        nq = int(Z[f'Q_{i}'].sum())
        L = 100 * (1 - np.exp(b0))
        R = 100 * nq * (np.exp(bq) - 1) if nq else np.nan          # 이후 며칠 동안의 합(평소 하루치 대비 %)
        rows.append({'사건': lab, '하루손실L%': L, '이후일수': nq, '이후변화R%': R, '순손실N%': L - (R if nq else 0)})
    return pd.DataFrame(rows)


def sign_test(k, n):
    """양측 부호검정 p값 (k: 한쪽 방향 개수, n: 전체)."""
    from math import comb
    m = min(k, n - k)
    p = sum(comb(n, j) for j in range(0, m + 1)) / 2 ** n * 2
    return min(1.0, p)


# ─────────────────────────────────────────────
# C. 50mm 이상 vs 30~50mm
# ─────────────────────────────────────────────
def big_vs_mid(data, reg, grp=None, seg='out'):
    """D0를 50mm 이상(D0_big)과 30~50mm(D0_mid)로 나눕니다. 나머지는 주 모형과 같습니다."""
    X, _ = build_design(data, reg)
    rain = weather(data, reg)['rain'].reindex(X.index)
    Z = X.drop(columns=['D0']).copy()
    Z['D0_big'] = ((X['D0'] == 1) & (rain >= 50)).astype(float)
    Z['D0_mid'] = ((X['D0'] == 1) & (rain < 50)).astype(float)
    res = fit_ols(series(data, reg, grp, seg), Z)
    names = list(res.params.index)
    ix = {n: i for i, n in enumerate(names)}
    B = np.random.default_rng(SEED).multivariate_normal(res.params.values, res.cov_params().values,
                                                       N_DRAW, method='svd')
    Lb = 100 * (1 - np.exp(B[:, ix['D0_big']]))
    Lm = 100 * (1 - np.exp(B[:, ix['D0_mid']]))
    pb = 100 * (1 - np.exp(res.params['D0_big']))
    pm = 100 * (1 - np.exp(res.params['D0_mid']))
    return {'big_days': int(Z['D0_big'].sum()), 'mid_days': int(Z['D0_mid'].sum()),
            'L_big': (pb, *pct(Lb)), 'L_mid': (pm, *pct(Lm)),
            'diff': (pb - pm, *pct(Lb - Lm))}


def fmt(t):
    return f'{t[0]:6.1f} [{t[1]:6.1f}, {t[2]:6.1f}]'


def main():
    data = load_all()
    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', lambda v: f'{v:,.1f}')

    print('== A. 금액 환산 (외지인, 택시 제외, 사건 1번당 사라진 결제액, 90% 구간) ==')
    for reg in ['춘천', '강남']:
        t, n_kept, n_base = money_table(data, reg)
        print(f'\n[{reg}] 남은 사건 {n_kept}개, 평소 날 {n_base}일 기준')
        print(t.to_string())
        tot = t.loc['83합계']
        print(f'  → 83합계, 사건 {n_kept}개 누적(방법1): 약 {tot["방법1(만원/사건)"] * n_kept:,.0f}만 원 '
              f'(신한카드 외지인 결제분만, 카드사 전체 아님)')

    print('\n== B. 반복성: 사건별 손실과 이후 5일 변화 (외지인 83합계 건수) ==')
    for reg in ['춘천', '강남']:
        t = per_event(data, reg)
        print(f'\n[{reg}]')
        print(t.to_string(index=False))
        v = t.dropna(subset=['이후변화R%'])
        n = len(v)
        k_loss = int((t['하루손실L%'] > 0).sum())
        k_neg = int((v['이후변화R%'] < 0).sum())
        print(f'  하루 손실이 양수인 사건: {k_loss}/{len(t)} (부호검정 p={sign_test(k_loss, len(t)):.3f})')
        print(f'  이후 변화가 음수(되돌아오지 않고 더 줄어듦)인 사건: {k_neg}/{n} (부호검정 p={sign_test(k_neg, n):.3f})')
        w = t.dropna(subset=['순손실N%'])
        k_net = int((w['순손실N%'] > 0).sum())
        print(f'  순손실이 양수(사라진 소비가 남음)인 사건: {k_net}/{len(w)} (부호검정 p={sign_test(k_net, len(w)):.3f})')

    print('\n== C. 50mm 이상 vs 30~50mm 호우일의 하루 손실 L (%, 90% 구간) ==')
    for reg in ['춘천', '강남']:
        print(f'\n[{reg}]')
        for lab, grp in [('외지인 83합계', None)] + ([(g, g) for g in GROUP_NAMES] if reg == '춘천' else []):
            r = big_vs_mid(data, reg, grp)
            print(f'  {lab:10s} 50mm↑({r["big_days"]}일) {fmt(r["L_big"])} | '
                  f'30~50mm({r["mid_days"]}일) {fmt(r["L_mid"])} | 차이 {fmt(r["diff"])}')


if __name__ == '__main__':
    main()
