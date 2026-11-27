"""
빅콘테스트 2026 — 피해 규모 예측 모델 (src/model.py)

무엇을 하나요?
  "비가 오면 그날과 그 뒤 며칠 동안 결제건수가 평소보다 얼마나 줄어드는가"를
  날씨 정보만으로 미리 맞힐 수 있는지 평가합니다.

평가 방법: 사건 하나씩 빼고 검증 (leave-one-event-out, LOEO)
  1) 호우 사건 하나를 고릅니다.
  2) 그 사건 구간 [시작 전날, 끝+7일]을 학습 자료에서 뺍니다 (모델이 이 비를 못 보게).
  3) 나머지 날로 모델을 학습하고, 뺀 사건의 [시작일, 끝+5일]을 예측합니다.
  4) 모든 사건에 대해 반복하고, 예측 오차를 모읍니다.

비교하는 모델 3개
  base   : 날씨 없이 요일·월·공휴일만 쓰는 회귀 (기준 모델, "평소라면 얼마였을까")
  ols_wx : base + 날씨 변수, 회귀(OLS)
  gbm_wx : base + 날씨 변수, 트리 모델(gradient boosting)

- 쓰는 정보는 날씨와 달력뿐입니다. 결제건수의 과거값은 넣지 않아 미래 정보가 새지 않습니다.
- 표본(sample) 날은 주 모형(event_study.py)과 같습니다 (연휴 날, 뺀 사건 구간 제외).
- 파일을 저장하지 않습니다. 난수 시드는 2026입니다.
- 프로젝트 폴더에서 실행:  python -B src/model.py
"""
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import GradientBoostingRegressor

sys.path.insert(0, 'src')
from prep import DAYS, GROUPS
from event_study import REGION_WX, SEED, load_all, series, weather

GROUP_NAMES = list(GROUPS)
HEAVY_MM = 30        # 호우일 기준 (주 모형과 같음)
TEST_AFTER = 5       # 예측해 보는 구간: 사건 끝 뒤 며칠까지 (N5와 맞춤)
GAP_AFTER = 7        # 학습에서 빼는 구간: 사건 끝 뒤 며칠까지 (P1~P7과 맞춤)
MODELS = ['base', 'ols_wx', 'gbm_wx']


# ═══════════════════════════════════════════════════════════════
# 1. 설명 변수 만들기
# ═══════════════════════════════════════════════════════════════
def calendar_features(data):
    """달력 변수: 요일 더미 6개(월요일 기준), 공휴일 통제 3개, 월 더미 5개(7월 기준)."""
    c = data['cal'].loc[DAYS]
    X = pd.DataFrame(index=DAYS)
    for k in range(1, 7):
        X[f'dow{k}'] = (c['dow'] == k).astype(float)
    for col in ['is_holiday', 'is_pre_offday', 'is_post_offday']:
        X[col] = c[col].astype(float)
    for m in range(8, 13):
        X[f'm{m}'] = (DAYS.month == m).astype(float)
    return X


def weather_features(data, reg):
    """
    날씨 변수 (그날까지 관측된 날씨만 사용):
      rain     : 일강수량(mm)
      heavy    : 30mm 이상 (호우일)
      rain10   : 10~30mm
      hot      : 최고기온 33℃ 이상
      tmax     : 최고기온(℃)
      after1~5 : 가장 최근 호우일이 1~5일 전 (오늘은 호우일이 아님)
    """
    g = weather(data, reg)
    rain = g['rain'].fillna(0)
    W = pd.DataFrame(index=DAYS)
    W['rain'] = rain
    W['heavy'] = (rain >= HEAVY_MM).astype(float)
    W['rain10'] = ((rain >= 10) & (rain < HEAVY_MM)).astype(float)
    W['hot'] = (g['tmax'] >= 33).astype(float)
    W['tmax'] = g['tmax'].ffill()                       # 기온 빈칸은 전날 값으로 (서울·춘천은 빈칸 없음)
    last_heavy, since = None, []
    for d in DAYS:                                      # 가장 최근 호우일로부터 며칠 지났는지
        if W.loc[d, 'heavy'] == 1:
            last_heavy = d
            since.append(0)
        else:
            since.append((d - last_heavy).days if last_heavy is not None else 999)
    since = pd.Series(since, index=DAYS)
    for k in range(1, TEST_AFTER + 1):
        W[f'after{k}'] = (since == k).astype(float)
    return W


def sample_days(data, reg):
    """주 모형과 같은 표본 날 (True/False)."""
    return data['ev'][REGION_WX[reg]]['D']['sample'].astype(bool)


# ═══════════════════════════════════════════════════════════════
# 2. 모델 학습과 예측
# ═══════════════════════════════════════════════════════════════
def fit_predict(name, y_tr, Xc_tr, W_tr, Xc_te, W_te):
    """모델 하나를 학습하고 예측값(로그 결제건수)을 돌려줍니다."""
    if name == 'base':
        A_tr, A_te = Xc_tr, Xc_te
    else:
        A_tr, A_te = Xc_tr.join(W_tr), Xc_te.join(W_te)
    if name in ('base', 'ols_wx'):
        keep = A_tr.columns[A_tr.abs().sum() > 0]       # 학습 자료에 한 번도 없는 더미는 뺌
        res = sm.OLS(y_tr, sm.add_constant(A_tr[keep], has_constant='add')).fit()
        return res.predict(sm.add_constant(A_te[keep], has_constant='add'))
    gbm = GradientBoostingRegressor(n_estimators=300, max_depth=2, learning_rate=0.03,
                                    subsample=0.8, min_samples_leaf=5, random_state=SEED)
    gbm.fit(A_tr.values, y_tr.values)
    return pd.Series(gbm.predict(A_te.values), index=A_te.index)


def loeo(data, reg, grp=None, seg='out'):
    """
    사건 하나씩 빼고 검증. 사건마다 한 줄씩 결과 표를 돌려줍니다.
    D0(호우일)가 표본에 하루도 없는 사건은 평가할 수 없어 건너뜁니다
    (예: 서울 10/10 사건은 앞 10/06 사건(연휴로 제외)의 구간 안에 있어 표본 밖).
    """
    y = np.log(series(data, reg, grp, seg))
    Xc, W = calendar_features(data), weather_features(data, reg)
    samp = sample_days(data, reg) & y.notna() & np.isfinite(y)
    rows = []
    for s, e in data['ev'][REGION_WX[reg]]['kept']:
        test = samp & (DAYS >= s) & (DAYS <= e + pd.Timedelta(days=TEST_AFTER))
        d0 = test & (DAYS <= e)                        # 사건의 호우일 중 표본 안인 날
        if d0.sum() == 0:
            continue
        gap = (DAYS >= s - pd.Timedelta(days=1)) & (DAYS <= e + pd.Timedelta(days=GAP_AFTER))
        train = samp & ~gap
        pred = {m: fit_predict(m, y[train], Xc[train], W[train], Xc[test], W[test]) for m in MODELS}
        yt = y[test]
        row = {'사건': s.strftime('%m/%d') + ('' if s == e else '~' + e.strftime('%m/%d')),
               '시험일수': int(test.sum()), '학습일수': int(train.sum())}
        for m in MODELS:
            row[f'MAE_{m}'] = float(np.mean(np.abs(yt - pred[m])))      # 로그 오차 평균 (0.01 ≈ 1%)
        # 호우일 손실: 실제 = 평소 예측(base) 대비 실제 감소, 예측 = 날씨 모델이 본 감소
        base_d0 = pred['base'][d0[test].values]
        row['실제손실%'] = 100 * float(np.mean(1 - np.exp(y[d0] - base_d0)))
        for m in ('ols_wx', 'gbm_wx'):
            row[f'예측손실%_{m}'] = 100 * float(np.mean(1 - np.exp(pred[m][d0[test].values] - base_d0)))
        rows.append(row)
    return pd.DataFrame(rows)


def summarize(t):
    """사건별 표를 한 줄 요약으로: 평균 오차, 기준 모델 대비 개선률, 이긴 사건 수, 손실 예측 오차."""
    out = {'평가 사건 수': len(t)}
    for m in MODELS:
        out[f'MAE_{m}'] = t[f'MAE_{m}'].mean()
    for m in ('ols_wx', 'gbm_wx'):
        out[f'개선률%_{m}'] = 100 * (1 - t[f'MAE_{m}'].mean() / t['MAE_base'].mean())
        out[f'base보다_나은_사건_{m}'] = f"{int((t[f'MAE_{m}'] < t['MAE_base']).sum())}/{len(t)}"
        out[f'손실오차%p_{m}'] = float(np.mean(np.abs(t[f'예측손실%_{m}'] - t['실제손실%'])))
    out['실제손실%_평균'] = t['실제손실%'].mean()
    return out


def run_all(data, seg='out'):
    """춘천(83합계 + 7그룹), 강남(83합계)의 LOEO 결과와 요약."""
    targets = [('춘천', '83합계', None)] + [('춘천', g, g) for g in GROUP_NAMES] + [('강남', '83합계', None)]
    detail, summary = {}, []
    for reg, lab, grp in targets:
        t = loeo(data, reg, grp, seg)
        detail[(reg, lab)] = t
        summary.append({'지역': reg, '대상': lab, **summarize(t)})
    return detail, pd.DataFrame(summary)


def main():
    data = load_all()
    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', lambda v: f'{v:,.3f}')
    detail, summary = run_all(data)
    print('== 사건 하나씩 빼고 검증: 외지인 결제건수 ==')
    print(summary.to_string(index=False))
    for key in [('춘천', '83합계'), ('강남', '83합계')]:
        print(f'\n== 사건별 결과: {key[0]} 외지인 {key[1]} ==')
        print(detail[key].to_string(index=False))


if __name__ == '__main__':
    main()
