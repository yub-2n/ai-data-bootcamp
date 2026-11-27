"""
빅콘테스트 2026 — 폭염 분석 (src/heat.py)

질문: 폭염 날에는 소비가 줄어드나, 아니면 낮에서 저녁으로 옮겨 가나?
      어느 업종·연령·시간대가 가장 크게 반응하나?

- 카드 데이터1(시간대 4구간, 성별·연령 있음, 거주지 없음)을 씁니다 → 외지인 구분 없이 "전체" 결제.
- 법인 결제와 제외 업종(데이터2와 같은 7개 + '통신요금(PC통신,무선호출)')은 뺍니다 → 83개 업종, 7그룹.
- 주 분석 기간: 2025-07-01 ~ 09-30 (폭염일이 7~9월에만 있음). 연휴 날(off_block_len ≥ 3)은 뺍니다.
- 폭염 정의: (A) 최고기온 33℃ 이상 (주 정의)  (B) 폭염특보(주의보·경보) 발효일
- 모형: ln(결제건수) ~ 폭염 + 비(10~30mm, 30mm↑, 호우 뒤 1~5일) + 요일 + 공휴일 + 월, 표준오차 HAC(maxlags=3)
- 파일을 저장하지 않습니다. 난수를 쓰지 않아 같은 입력이면 항상 같은 결과가 나옵니다.
- 프로젝트 폴더에서 실행:  python -B src/heat.py
"""
import re
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, 'src')
from prep import CARD_DIR, DAYS, EXCLUDE, GROUPS
from event_study import HAC_LAGS, REGION_CARD, load_all, weather
from model import calendar_features, weather_features

GROUP_NAMES = list(GROUPS)
EXCLUDE1 = EXCLUDE + ['통신요금(PC통신,무선호출)']          # 데이터1에만 있는 통신요금 업종도 뺌
AGE_BAND = {'10 대': '10~30대', '20 대': '10~30대', '30 대': '10~30대',
            '40 대': '40~50대', '50 대': '40~50대',
            '60 대': '60대 이상', '70 대': '60대 이상', '80 대': '60대 이상', '90 대': '60대 이상'}
BANDS = ['10~30대', '40~50대', '60대 이상']
BINS = ['00_05', '06_11', '12_17', '18_23']
HOT_C = 33           # 폭염 기준 (℃)
BIG_C = 35           # 강한 폭염 기준 (℃)
WARN_FILE = 'data/external/kma_weather_warnings_20250701_20251231.csv'


# ═══════════════════════════════════════════════════════════════
# 1. 카드 데이터1 읽기
# ═══════════════════════════════════════════════════════════════
def load_card1():
    """카드 데이터1을 읽고, 법인·제외 업종을 뺀 뒤 업종 그룹과 연령 묶음을 붙입니다."""
    d = pd.read_csv(CARD_DIR / '신한카드_빅콘테스트2026_데이터1.txt', sep='\t', encoding='cp949',
                    dtype={'TA_YMD': str})
    d['date'] = pd.to_datetime(d['TA_YMD'], format='%Y%m%d')
    d = d[(d['SEX_CCD'] != '법인') & ~d['MCT_RY_CD'].isin(EXCLUDE1)].copy()   # 개인 결제만, 제외 업종 빼기
    lookup = {ind: g for g, inds in GROUPS.items() for ind in inds}
    d['group'] = d['MCT_RY_CD'].map(lookup)
    missing = sorted(d.loc[d['group'].isna(), 'MCT_RY_CD'].unique())
    if missing:
        raise ValueError(f'그룹에 없는 업종이 있습니다: {missing}')
    d['band'] = d['AGE_CCD'].map(AGE_BAND)
    if d['band'].isna().any():
        raise ValueError(f"연령 코드가 예상과 다릅니다: {sorted(d.loc[d['band'].isna(), 'AGE_CCD'].unique())}")
    return d


def card1_series(card1, reg, bin_=None, grp=None, band=None):
    """지역의 일별 결제건수 (184일). bin_/grp/band가 None이면 전체를 합칩니다."""
    s = card1[card1['MCT_SGG_CD'] == REGION_CARD[reg]]
    if bin_:
        s = s[s['TIME_GB'] == bin_]
    if grp:
        s = s[s['group'] == grp]
    if band:
        s = s[s['band'] == band]
    return s.groupby('date')['USE_CNT'].sum().reindex(DAYS)


# ═══════════════════════════════════════════════════════════════
# 2. 폭염특보 날짜 만들기 (기상특보 CSV)
# ═══════════════════════════════════════════════════════════════
def split_top(s):
    """'경기도(광명. 과천). 서울' 처럼 괄호 밖의 '.'로만 나눕니다."""
    parts, depth, cur = [], 0, ''
    for ch in s:
        depth += (ch == '(') - (ch == ')')
        if ch == '.' and depth == 0:
            parts.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def covers(area, reg):
    """
    특보 해당지역 문자열(area)에 우리 지역이 들어가는지 판단합니다.
      춘천: '강원도(... 춘천 ...)'에 춘천이 있으면 포함 ('제외'가 붙은 목록이면 반대로)
      강남: 서울동남권으로 가정 (팀원B 메모 규칙)
            '서울' → 포함, '서울(서울동남권)' → 포함, '서울(서울동남권 제외)' → 제외,
            '서울(다른 권역 제외)' → 포함, '서울(다른 권역)' → 제외
    """
    key, name = ('강원도', '춘천') if reg == '춘천' else ('서울', '서울동남권')
    for sec in split_top(area):
        m = re.match(rf'^{key}(?:\((.*)\))?$', sec.strip())
        if not m:
            continue
        inner = m.group(1)
        if inner is None:                               # 괄호 없이 '서울' / '강원도' 전체
            return True
        listed = name in inner
        return (not listed) if '제외' in inner else listed
    return False


def warning_levels(reg):
    """
    날짜별 폭염특보 단계 (0 없음, 1 주의보, 2 경보)를 돌려줍니다.
    그날 하루 중 한 번이라도 발효 중이면 그 단계로 셉니다 (하루 중 가장 높은 단계).
    """
    w = pd.read_csv(WARN_FILE, encoding='cp949')
    w = w[w['지역'] != '전국']                              # '전국' 행은 다른 행과 겹침 → 뺌
    acts = []
    for _, r in w.iterrows():
        times = dict(re.findall(r'\((\d+)\)\s*폭염(?:주의보|경보)\s*\S+\s*:\s*(\d{4}년 \d{2}월 \d{2}일 \d{2}시 \d{2}분)',
                                str(r['발효시각'])))
        for no, kind, act, area in re.findall(r'\((\d+)\)\s*폭염(주의보|경보)\s*(\S+)\s*:\s*([^/]+)', str(r['해당지역'])):
            if no not in times or not covers(area.strip(), reg):
                continue
            t = pd.to_datetime(times[no], format='%Y년 %m월 %d일 %H시 %M분')
            if act == '해제':
                lvl = 0
            else:                                          # 발표·변경: 그 종류의 단계가 됨
                lvl = 2 if kind == '경보' else 1
            acts.append((t, lvl, kind, act))
    acts.sort(key=lambda x: (x[0], x[3] != '해제'))     # 같은 시각이면 해제를 먼저 (경보 해제 → 주의보 변경 순서)
    level = pd.Series(0, index=DAYS)
    cur, cur_t = 0, None
    for t, lvl, kind, act in acts + [(DAYS[-1] + pd.Timedelta(days=1), 0, '', '끝')]:
        if cur > 0 and cur_t is not None:                 # 이전 상태가 이어진 구간의 날짜에 단계 표시
            for d in pd.date_range(cur_t.normalize(), t.normalize()):
                if d in level.index:
                    level[d] = max(level[d], cur)
        if act == '해제' and kind == '주의보' and cur == 2:
            pass                                           # 경보 중 주의보 해제 문구는 상태를 바꾸지 않음
        else:
            cur = lvl
        cur_t = t
    return level, pd.DataFrame(acts, columns=['시각', '단계', '종류', '동작'])


# ═══════════════════════════════════════════════════════════════
# 3. 설명 변수와 표본
# ═══════════════════════════════════════════════════════════════
def design(data, reg, exposure='hot', months=(7, 8, 9)):
    """
    설명 변수 표와 표본 날.
      exposure='hot'   : hot (33℃↑)
      exposure='dose'  : hot_mid (33~35℃), hot_big (35℃↑)
      exposure='warn'  : warn1 (폭염주의보), warn2 (폭염경보)
    """
    g = weather(data, reg)
    X = calendar_features(data)
    W = weather_features(data, reg)
    X = X.join(W[['rain10', 'heavy'] + [f'after{k}' for k in range(1, 6)]])
    if exposure == 'hot':
        X['hot'] = (g['tmax'] >= HOT_C).astype(float)
    elif exposure == 'dose':
        X['hot_mid'] = ((g['tmax'] >= HOT_C) & (g['tmax'] < BIG_C)).astype(float)
        X['hot_big'] = (g['tmax'] >= BIG_C).astype(float)
    elif exposure == 'warn':
        lv, acts = warning_levels(reg)
        X['warn1'] = (lv == 1).astype(float)
        X['warn2'] = (lv == 2).astype(float)
    holiday_block = data['cal'].loc[DAYS, 'off_block_len'] >= 3
    samp = pd.Series(DAYS.month.isin(months), index=DAYS) & ~holiday_block
    if exposure == 'warn':
        # 특보 CSV는 7/1부터라, 첫 기록 전의 특보 상태(6월에 발표된 특보가 이어졌는지)를 알 수 없음 → 그 날들은 뺌
        samp &= pd.Series(DAYS >= acts['시각'].min().normalize(), index=DAYS)
    return X, samp


def fit(y, X, samp):
    """ln(y)를 OLS로 추정, HAC 표준오차. 표본에 없는 더미 열은 뺍니다."""
    ly = np.log(y)
    ok = samp & ly.notna() & np.isfinite(ly)
    A = X[ok]
    A = A.loc[:, A.abs().sum() > 0]
    return sm.OLS(ly[ok], sm.add_constant(A, has_constant='add')).fit(
        cov_type='HAC', cov_kwds={'maxlags': HAC_LAGS}), int(ok.sum())


def pct_effect(res, var):
    """계수 b를 %로: 100(exp(b)-1), 90% 구간은 b ± 1.645×SE를 변환."""
    if var not in res.params:
        return (np.nan, np.nan, np.nan)
    b, se = res.params[var], res.bse[var]
    return tuple(100 * (np.exp(v) - 1) for v in (b, b - 1.645 * se, b + 1.645 * se))


# ═══════════════════════════════════════════════════════════════
# 4. 결과 표
# ═══════════════════════════════════════════════════════════════
def effect_table(data, card1, reg, exposure='hot', months=(7, 8, 9), by=None):
    """
    시간대별 폭염 효과(%) 표. by=None이면 전체, 'group'이면 업종 7그룹, 'band'이면 연령 3묶음.
    열: 하루 전체, 00_05, 06_11, 12_17, 18_23 (각 칸: 점추정 [5%, 95%])
    """
    X, samp = design(data, reg, exposure, months)
    var = {'hot': ['hot'], 'dose': ['hot_mid', 'hot_big'], 'warn': ['warn1', 'warn2']}[exposure]
    labels = [None] if by is None else (GROUP_NAMES if by == 'group' else BANDS)
    rows = []
    for lab in labels:
        for v in var:
            row = {'대상': lab or '전체', '변수': v}
            for b in [None] + BINS:
                y = card1_series(card1, reg, b, lab if by == 'group' else None, lab if by == 'band' else None)
                res, n = fit(y, X, samp)
                row[b or '하루'] = pct_effect(res, v)
                row['표본일수'] = n
            rows.append(row)
    return pd.DataFrame(rows)


def share_table(data, card1, reg, months=(7, 8, 9)):
    """시간대 비중의 변화: ln(시간대 건수 / 하루 건수) ~ hot. 양수면 그 시간대 비중이 커짐(옮겨 옴)."""
    X, samp = design(data, reg, 'hot', months)
    day = card1_series(card1, reg)
    row = {'지역': reg}
    for b in BINS:
        res, _ = fit(card1_series(card1, reg, b) / day, X, samp)
        row[b] = pct_effect(res, 'hot')
    return row


def heat_runs(data, reg, months=(7, 8, 9)):
    """연속된 폭염일 묶음 목록 [(시작, 끝), ...]."""
    tmax = weather(data, reg)['tmax']
    hot = (tmax >= HOT_C) & pd.Series(DAYS.month.isin(months), index=DAYS)
    runs, start = [], None
    for d in DAYS:
        if hot[d] and start is None:
            start = d
        if not hot[d] and start is not None:
            runs.append((start, d - pd.Timedelta(days=1)))
            start = None
    if start is not None:
        runs.append((start, DAYS[-1]))
    return runs


def drop_one_run(data, card1, reg, bin_=None, months=(7, 8, 9)):
    """폭염 묶음 하나씩 빼고(앞뒤 하루 포함) 다시 추정한 hot 효과(%)."""
    X, samp = design(data, reg, 'hot', months)
    y = card1_series(card1, reg, bin_)
    rows = []
    for s, e in heat_runs(data, reg, months):
        drop = (DAYS >= s - pd.Timedelta(days=1)) & (DAYS <= e + pd.Timedelta(days=1))
        res, n = fit(y, X, samp & ~drop)
        pt, lo, hi = pct_effect(res, 'hot')
        rows.append({'뺀 묶음': f"{s:%m/%d}~{e:%m/%d}", '일수': (e - s).days + 1, '효과%': pt, '5%': lo, '95%': hi})
    return pd.DataFrame(rows)


# placebo(가짜 폭염일)는 넣지 않았습니다: 7~8월 표본에서 폭염이 아닌 날이 춘천 30일·강남 35일뿐이라,
# 실제 폭염일 수(29일·25일)만큼 가짜로 고르면 후보를 거의 다 쓰게 되어 비교가 의미 없습니다 (2026-10-21 시험 실행에서 확인).


def fmt(t):
    """(점추정, 5%, 95%) → '−3.1 [−5.0, −1.2]'"""
    if isinstance(t, tuple):
        return f'{t[0]:5.1f} [{t[1]:5.1f}, {t[2]:5.1f}]'
    return t


def show(df):
    """튜플 칸을 보기 좋은 글자로 바꿉니다."""
    return df.apply(lambda c: c.map(fmt))


def main():
    data = load_all()
    card1 = load_card1()
    pd.set_option('display.width', 250)
    for reg in ['춘천', '강남']:
        lv, acts = warning_levels(reg)
        print(f'\n######## {reg} ########')
        print('폭염특보 발효일: 주의보', int((lv == 1).sum()), '일, 경보', int((lv == 2).sum()), '일 | 특보 기록', len(acts), '건')
        for exp in ['hot', 'dose', 'warn']:
            print(f'\n== 시간대별 효과 (%), 노출={exp} ==')
            print(show(effect_table(data, card1, reg, exp)).to_string(index=False))
        print('\n== 시간대 비중 변화 (%), hot ==')
        print({k: fmt(v) for k, v in share_table(data, card1, reg).items()})
        print('\n== 업종 그룹별 (hot) ==')
        print(show(effect_table(data, card1, reg, 'hot', by='group')).to_string(index=False))
        print('\n== 연령별 (hot) ==')
        print(show(effect_table(data, card1, reg, 'hot', by='band')).to_string(index=False))
        print('\n== 폭염 묶음 하나씩 빼기 (하루 전체) ==')
        print(drop_one_run(data, card1, reg).round(1).to_string(index=False))


if __name__ == '__main__':
    main()
