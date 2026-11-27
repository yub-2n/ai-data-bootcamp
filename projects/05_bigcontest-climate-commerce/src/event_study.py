"""
빅콘테스트 2026 — 호우 사건 전후 모형 (src/event_study.py)

- 전처리는 src/prep.py(전처리_명세서의 P1~P10)를 그대로 불러 씁니다.
- 이 파일은 아무 파일도 저장하지 않습니다. 결과는 화면에만 출력합니다.
- 난수 시드는 SEED(=2026)로 고정되어 있어, 같은 입력이면 항상 같은 결과가 나옵니다.
- 경로는 상대경로입니다. 프로젝트 폴더(bigcontest)에서 실행하세요:
      python3 src/event_study.py
"""
import contextlib
import io
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, 'src')                      # prep.py 위치 (프로젝트 폴더 기준 상대경로)
from prep import (DAYS, GROUPS, add_group, add_segment, build_event_table,
                  drop_excluded, load_asos, load_calendar, load_card2)

warnings.filterwarnings('ignore')

# ═══ 설정값 ═══
SEED = 2026          # 모든 난수의 시드
N_DRAW = 3000        # 계수 분포에서 뽑는 횟수 (90% 구간용)
N_SIM = 1000         # placebo 반복 횟수
HAC_LAGS = 3         # HAC 표준오차의 maxlags
REGION_CARD = {'춘천': '강원 춘천시', '강남': '서울 강남구'}   # 지역 → 카드 가맹점 지역
REGION_WX = {'춘천': '춘천', '강남': '서울'}                   # 지역 → 기상 지점 (강남은 서울 지점)
GROUP_NAMES = list(GROUPS)                                      # 업종 7그룹 이름
EVENT_1010 = (pd.Timestamp('2025-10-10'), pd.Timestamp('2025-10-11'))   # 춘천 10/10 사건
EVENT_SEOUL_1010 = (pd.Timestamp('2025-10-10'), pd.Timestamp('2025-10-10'))  # 서울 10/10 사건


# ═══════════════════════════════════════════════════════════════
# 1. 데이터 준비
# ═══════════════════════════════════════════════════════════════
def load_all(quiet=True):
    """카드·기상·호우 사건·달력을 한 번에 읽어 dict로 돌려줍니다. (prep.py의 검증 출력은 quiet로 숨김)"""
    ctx = contextlib.redirect_stdout(io.StringIO()) if quiet else contextlib.nullcontext()
    with ctx:
        card = add_segment(add_group(drop_excluded(load_card2())))   # 83업종, 그룹, 외지인/현지인 표시
        asos = load_asos()                                           # 7개 지점 기상
        ev = build_event_table(asos)                                 # 지점별 호우 사건·더미·표본 여부
        cal = load_calendar()                                        # 공휴일 달력(184일)
    return {'card': card, 'asos': asos, 'ev': ev, 'cal': cal.set_index('date')}


def series(data, reg, grp=None, seg='out'):
    """지역(reg)의 일별 결제건수. grp=None이면 83업종 합계, seg='out'이면 외지인, 'all'이면 전체."""
    s = data['card']
    s = s[s['MCT_SGG_CD'] == REGION_CARD[reg]]
    if seg == 'out':
        s = s[s['seg'] == 'out']
    if grp:
        s = s[s['group'] == grp]
    return s.groupby('date')['USE_CNT'].sum().reindex(DAYS)


def weather(data, reg):
    """지역에 연결된 기상 지점의 184일 자료."""
    a = data['asos']
    return a[a['region'] == REGION_WX[reg]].set_index('date').reindex(DAYS)


def lead_dummies(info, nlead=3):
    """
    L2, L3 더미: 사건 시작 2, 3일 전. 사이에 다른 호우일이 끼면 거기서 멈춥니다
    (P 더미의 '다음 호우일 앞에서 멈춤' 규칙과 같은 방식).
    """
    wet = set(d for s, e in info['events'] for d in pd.date_range(s, e))
    out = pd.DataFrame(0, index=DAYS, columns=[f'L{k}' for k in range(2, nlead + 1)])
    for s, e in info['kept']:
        for k in range(2, nlead + 1):
            if any((s - pd.Timedelta(days=j)) in wet for j in range(1, k + 1)):
                break
            d = s - pd.Timedelta(days=k)
            if d in out.index:
                out.loc[d, f'L{k}'] = 1
    return out


def build_design(data, reg, leads=False, drop_event=None, holiday_controls=True):
    """
    설명변수 표(A1)를 만듭니다. 표본 날(sample=1)만 남깁니다.
      leads=True            : L2, L3 더미 추가 (사건 이전 날 검정)
      drop_event=(시작,끝)  : 그 사건의 [시작 전날, 끝+7일]을 표본에서 뺌 (jackknife)
      holiday_controls=False: is_holiday, is_pre_offday, is_post_offday를 뺌 (연휴 변수 제외 모형)
    반환: (설명변수 표, 표본 여부)
    """
    g = weather(data, reg)
    c = data['cal']
    D = data['ev'][REGION_WX[reg]]['D']
    X = D[['D0', 'L1'] + [f'P{k}' for k in range(1, 8)]].copy()      # 사건 더미
    if leads:
        X = X.join(lead_dummies(data['ev'][REGION_WX[reg]]))
    X['rain10'] = ((g['rain'] >= 10) & (g['rain'] < 30)).astype(int)  # 10~30mm 비
    X['hot'] = (g['tmax'] >= 33).astype(int)                          # 폭염
    for k in range(1, 7):
        X[f'dow{k}'] = (c.loc[DAYS, 'dow'] == k).astype(int)          # 요일 더미 (월=0 기준)
    if holiday_controls:
        for col in ['is_holiday', 'is_pre_offday', 'is_post_offday']:
            X[col] = c.loc[DAYS, col]
    for m in range(8, 13):
        X[f'm{m}'] = (DAYS.month == m).astype(int)                    # 월 더미 (7월 기준)
    samp = D['sample'].astype(bool).copy()
    if drop_event is not None:
        s, e = drop_event
        samp[(DAYS >= s - pd.Timedelta(days=1)) & (DAYS <= e + pd.Timedelta(days=7))] = False
    X = sm.add_constant(X.astype(float))
    return X[samp], samp


# ═══════════════════════════════════════════════════════════════
# 2. 추정과 효과 계산
# ═══════════════════════════════════════════════════════════════
def fit_ols(y, X):
    """ln(결제건수)를 OLS로 추정, 표준오차는 HAC. 표본에 한 번도 없는 더미 열은 뺍니다."""
    yy = np.log(y[X.index])
    ok = yy.notna() & np.isfinite(yy)
    X = X[ok]
    X = X.loc[:, X.abs().sum() > 0]
    return sm.OLS(yy[ok], X).fit(cov_type='HAC', cov_kwds={'maxlags': HAC_LAGS})


def effect_draws(res, ks=(5,)):
    """
    손실 L = 1-exp(D0), 반등 R_K = Σ(exp(P_k)-1), 순손실 N_K = L-R_K (단위 %).
    점추정(1개)과, 계수 분포에서 N_DRAW번 뽑은 값(시드 고정)을 함께 돌려줍니다.
    """
    names = list(res.params.index)
    ix = {n: i for i, n in enumerate(names)}
    b, V = res.params.values, res.cov_params().values
    draws = np.random.default_rng(SEED).multivariate_normal(b, V, N_DRAW, method='svd')

    def calc(B):
        L = 1 - np.exp(B[:, ix['D0']])
        out = {'L': 100 * L}
        for k in ks:
            R = sum(np.exp(B[:, ix[f'P{j}']]) - 1 for j in range(1, k + 1))
            out[f'R{k}'] = 100 * R
            out[f'N{k}'] = 100 * (L - R)
        return out
    return calc(b[None, :]), calc(draws)


def summarize(res, ks=(5,)):
    """{지표: (점추정, 5%, 95%)} — 90% 구간은 5%~95% 백분위수."""
    pt, dr = effect_draws(res, ks)
    return {k: (float(pt[k][0]), *np.percentile(dr[k], [5, 95])) for k in pt}


def main_model(data, reg, grp=None, seg='out', **design_kw):
    """주 모형(A1) 한 번: 설계 → 추정 → L, R5, N5와 90% 구간. design_kw는 build_design에 전달."""
    X, _ = build_design(data, reg, **design_kw)
    return summarize(fit_ols(series(data, reg, grp, seg), X))


def horizon_table(data, reg='춘천', seg='out'):
    """N3, N5, N7과 N7-N5 차이(같은 추출에서의 차이)의 90% 구간. 업종 83합계 + 7그룹."""
    X, _ = build_design(data, reg)
    rows = {}
    for lab, grp in [('외지인 83합계', None)] + [(g, g) for g in GROUP_NAMES]:
        pt, dr = effect_draws(fit_ols(series(data, reg, grp, seg), X), ks=(3, 5, 7))
        diff = dr['N7'] - dr['N5']
        rows[lab] = {'N3': float(pt['N3'][0]), 'N5': float(pt['N5'][0]), 'N7': float(pt['N7'][0]),
                     'diff': (float(pt['N7'][0] - pt['N5'][0]), *np.percentile(diff, [5, 95]))}
    return rows


# ═══════════════════════════════════════════════════════════════
# 3. 사건 이전 날 검정(lead test)과 겹침 점검
# ═══════════════════════════════════════════════════════════════
def overlap_days(X):
    """L1~L3 중 하나가 1이면서 같은 날 다른 사건의 P1~P7도 1인 날 (True/False 시리즈)."""
    p_any = X[[f'P{k}' for k in range(1, 8)]].sum(axis=1) > 0
    lead_any = X[['L1', 'L2', 'L3']].sum(axis=1) > 0
    return lead_any & p_any


def lead_test(data, reg, grp=None, seg='out', exclude_overlap=False):
    """L1~L3 계수와 90% 구간(계수 ± 1.645×HAC 표준오차). exclude_overlap=True면 겹치는 날을 뺍니다."""
    X, _ = build_design(data, reg, leads=True)
    if exclude_overlap:
        X = X[~overlap_days(X)]
    res = fit_ols(series(data, reg, grp, seg), X)
    out = {}
    for k in ('L1', 'L2', 'L3'):
        b, se = float(res.params[k]), float(res.bse[k])
        out[k] = (b, b - 1.645 * se, b + 1.645 * se)
    return out


# ═══════════════════════════════════════════════════════════════
# 4. placebo (가짜 사건)
# ═══════════════════════════════════════════════════════════════
def real_windows(data, reg):
    """실제 호우 사건(30mm 이상 전부)의 [시작 전날, 끝+7일]에 들어가는 날 집합."""
    real = set()
    for s, e in data['ev'][REGION_WX[reg]]['events']:
        real |= set(pd.date_range(s - pd.Timedelta(days=1), e + pd.Timedelta(days=7)))
    return real


def placebo_candidates(data, reg, rain_limit, win_len=6):
    """
    가짜 D0 후보 날: 일강수량이 rain_limit(mm) 미만이고, win_len일 창(D0, P1~)이
    모두 표본 안이며 실제 사건 구간과 겹치지 않는 날.
    """
    g = weather(data, reg)
    samp = data['ev'][REGION_WX[reg]]['D']['sample'].astype(bool)
    real = real_windows(data, reg)
    out = []
    for d in DAYS:
        win = [d + pd.Timedelta(days=k) for k in range(win_len)]
        if g['rain'][d] < rain_limit and all((x in samp.index) and samp[x] and x not in real for x in win):
            out.append(d)
    return out


def make_sampler(starts, win_len=6, n_fake=5):
    """
    서로 겹치지 않는 가짜 창 n_fake개를 '균등하게' 뽑는 함수와 전체 조합 수를 돌려줍니다.
    (동적계획법으로 남은 조합 수를 세어 가며 뽑아서, 모든 조합이 같은 확률)
    """
    n = len(starts)
    nxt = []                                       # i번째 창 다음에 올 수 있는 첫 번째 창 위치
    for i in range(n):
        j = i
        while j < n and (starts[j] - starts[i]).days < win_len:
            j += 1
        nxt.append(j)
    ways = [[0] * (n + 1) for _ in range(n_fake + 1)]   # ways[j][i]: i번째부터 j개를 뽑는 조합 수
    for i in range(n + 1):
        ways[0][i] = 1
    for j in range(1, n_fake + 1):
        for i in range(n - 1, -1, -1):
            ways[j][i] = ways[j][i + 1] + ways[j - 1][nxt[i]]

    def draw(rng):
        chosen, i = [], 0
        for j in range(n_fake, 0, -1):
            r = int(rng.random() * 1e15) * ways[j][i] // 10 ** 15
            while True:
                w = ways[j - 1][nxt[i]]
                if r < w:
                    chosen.append(starts[i])
                    i = nxt[i]
                    break
                r -= w
                i += 1
        return chosen
    return draw, ways[n_fake][0]


def run_placebo(data, reg, targets, rain_limit, win_len=6, n_fake=5, n_sim=N_SIM):
    """
    가짜 사건 placebo. 실제 사건 더미는 그대로 두고, 가짜 창(D0, P1~P5)의 더미 6개를 추가해
    N5를 구하는 일을 n_sim번 반복합니다. targets: [(이름, 업종그룹 또는 None, 'out'|'all'), ...]
    반환: (결과 dict, (후보 날 수, 조합 수))
    """
    starts = placebo_candidates(data, reg, rain_limit, win_len)
    draw, n_comb = make_sampler(starts, win_len, n_fake)
    X0, _ = build_design(data, reg)
    X0 = X0.loc[:, X0.abs().sum() > 0]
    names = list(X0.columns)
    Y = np.column_stack([np.log(series(data, reg, g, seg)[X0.index].values) for _, g, seg in targets])

    def n5(B, a, bs):                              # N5 = L - R5 (비율)
        return (1 - np.exp(B[a])) - sum(np.exp(B[b]) - 1 for b in bs)

    real_b = np.linalg.lstsq(X0.values, Y, rcond=None)[0]
    real_n5 = 100 * n5(real_b, names.index('D0'), [names.index(f'P{k}') for k in range(1, 6)])
    rng = np.random.default_rng(SEED)
    idx = {d: i for i, d in enumerate(X0.index)}
    p = X0.shape[1]
    fake = np.zeros((n_sim, len(targets)))
    for it in range(n_sim):
        F = np.zeros((len(X0), win_len))
        for s in draw(rng):
            for k in range(win_len):
                F[idx[s + pd.Timedelta(days=k)], k] = 1
        B = np.linalg.lstsq(np.hstack([X0.values, F]), Y, rcond=None)[0]
        fake[it] = 100 * n5(B, p, range(p + 1, p + win_len))
    out = {}
    for j, (name, _, _) in enumerate(targets):
        f = fake[:, j]
        p5, p95 = np.percentile(f, [5, 95])
        out[name] = {'mean': float(f.mean()), 'p5': float(p5), 'p95': float(p95),
                     'real': float(real_n5[j]), 'pct': float(100 * np.mean(f < real_n5[j])),
                     'over': bool(real_n5[j] > p95),                         # 평균 기준
                     'over0': bool(real_n5[j] > p95 - f.mean())}             # 0보정 기준
    return out, (len(starts), n_comb)


def placebo_targets(reg):
    """H, H2에서 쓴 대상 목록."""
    if reg == '춘천':
        return ([('외지인 83합계', None, 'out')] + [(g, g, 'out') for g in GROUP_NAMES]
                + [('전체 83합계', None, 'all')])
    return [('외지인 83합계', None, 'out')]


# ═══════════════════════════════════════════════════════════════
# 5. 실행과 보고 숫자 대조
# ═══════════════════════════════════════════════════════════════
RESULT = {'일치': 0, '다름': 0}


def check(name, got, expect, nd=1):
    """계산값(got)을 소수점 nd째 자리까지 반올림해 보고했던 값(expect)과 비교해 출력합니다."""
    ok = abs(round(float(got), nd) - expect) < 1e-9
    RESULT['일치' if ok else '다름'] += 1
    print('[일치]' if ok else '[다름]', name, '| 결과:', round(float(got), nd), '| 보고값:', expect)


def main():
    data = load_all()

    print('== A1 주 모형: 춘천 외지인 (L, R5, N5) ==')
    rep = {'외지인 83합계': (21.5, -26.9, 48.3), '식료품': (20.2, -26.9, 47.2), '외식': (20.9, -20.7, 41.6),
           '의료·약국': (11.0, -19.8, 30.8), '교통·숙박': (25.3, -53.4, 78.7), '여가': (35.2, -44.1, 79.2),
           '상품쇼핑': (23.9, -25.8, 49.7), '생활·교육서비스': (4.6, -13.5, 18.1)}
    for lab, grp in [('외지인 83합계', None)] + [(g, g) for g in GROUP_NAMES]:
        r = main_model(data, '춘천', grp)
        for key, exp in zip(['L', 'R5', 'N5'], rep[lab]):
            check(f'춘천 {lab} {key}', r[key][0], exp)

    print('\n== 연휴 변수 제외 모형 (이번 대화에서 보고한 숫자가 없어 대조 없이 출력만) ==')
    r = main_model(data, '춘천', holiday_controls=False)
    print('춘천 외지인 83합계 (is_holiday 등 3개 제외):', {k: tuple(round(x, 1) for x in v) for k, v in r.items()})

    print('\n== 10/10 사건 제외(jackknife): 춘천 외지인 83합계 ==')
    r = main_model(data, '춘천', drop_event=EVENT_1010)
    for key, exp in [('L', (17.2, 12.3, 21.8)), ('R5', (-8.8, -34.7, 21.4)), ('N5', (26.1, -8.0, 55.9))]:
        for part, e in zip(['점추정', '5%', '95%'], exp):
            check(f'춘천 제외 {key} {part}', r[key][['점추정', '5%', '95%'].index(part)], e)

    print('\n== 서울 10/10 사건 구간 제외 변형: 강남 ==')
    for seg, lab, mainN5, varN5 in [('out', '외지인', (3.5, -5.6, 12.7), (8.4, -0.8, 17.3)),
                                    ('all', '전체', (1.3, -6.2, 8.5), (4.1, -4.4, 12.1))]:
        m = main_model(data, '강남', seg=seg)['N5']
        v = main_model(data, '강남', seg=seg, drop_event=EVENT_SEOUL_1010)['N5']
        for part, i in [('점추정', 0), ('5%', 1), ('95%', 2)]:
            check(f'강남 {lab} 83합계 주모형 N5 {part}', m[i], mainN5[i])
            check(f'강남 {lab} 83합계 변형 N5 {part}', v[i], varN5[i])
    m = main_model(data, '강남')
    check('강남 외지인 L 점추정', m['L'][0], 4.3)

    print('\n== lead test: L1~L3 계수 (춘천 외지인 83합계, 강남 외지인 83합계) ==')
    for reg, exp in [('춘천', {'L1': -0.100, 'L2': -0.009, 'L3': -0.011}),
                     ('강남', {'L1': -0.021, 'L2': 0.005, 'L3': -0.003})]:
        lt = lead_test(data, reg)
        for k in ('L1', 'L2', 'L3'):
            check(f'{reg} {k} 계수', lt[k][0], exp[k], nd=3)

    print('\n== 겹침 점검 (춘천) ==')
    X, _ = build_design(data, '춘천', leads=True)
    ov = overlap_days(X)
    for k, exp in [('L1', 8), ('L2', 6), ('L3', 3)]:
        check(f'{k}=1이면서 P1~P7도 1인 날 수', int(((X[k] == 1) & ov).sum()), exp, nd=0)
    check('합집합 겹침 일수', int(ov.sum()), 17, nd=0)
    check('겹침 제외 후 표본 일수', int((~ov).sum()), 146, nd=0)
    lt = lead_test(data, '춘천', exclude_overlap=True)
    for k, exp in [('L1', -0.128), ('L2', -0.094), ('L3', -0.004)]:
        check(f'겹침 제외 {k} 계수', lt[k][0], exp, nd=3)

    print('\n== placebo H (1mm 미만)와 H2 (10mm 미만) ==')
    expect = {  # (후보, 조합, 가짜평균, 5%, 95%, 실제 N5, 백분위) — 춘천/강남 외지인 83합계
        ('춘천', 1): (69, 2830318, -10.1, -55.1, 30.6, 48.3, 99.3),
        ('춘천', 10): (78, 5318953, -7.0, -51.5, 32.6, 48.3, 99.2),
        ('강남', 1): (78, 6516537, 0.3, -11.1, 11.3, 3.5, 67.6),
        ('강남', 10): (85, 10107024, 0.3, -10.9, 11.3, 3.5, 67.2)}
    for (reg, lim), e in expect.items():
        res, (ncand, ncomb) = run_placebo(data, reg, placebo_targets(reg), lim)
        r = res['외지인 83합계']
        tag = f'{reg} {lim}mm'
        check(f'{tag} 후보 날 수', ncand, e[0], nd=0)
        check(f'{tag} 5개 조합 수', ncomb, e[1], nd=0)
        for key, ev_, val in [('가짜 평균', e[2], r['mean']), ('가짜 5%', e[3], r['p5']), ('가짜 95%', e[4], r['p95']),
                              ('실제 N5', e[5], r['real']), ('백분위', e[6], r['pct'])]:
            check(f'{tag} {key}', val, ev_)

    print('\n== N3, N5, N7 (춘천 외지인) ==')
    h = horizon_table(data)
    for key, exp in [('N3', 42.2), ('N5', 48.3), ('N7', 49.4)]:
        check(f'83합계 {key}', h['외지인 83합계'][key], exp)
    check('83합계 N7-N5', h['외지인 83합계']['diff'][0], 1.1)
    check('생활·교육서비스 N7', h['생활·교육서비스']['N7'], -12.9)

    print(f"\n대조 결과: 일치 {RESULT['일치']}개, 다름 {RESULT['다름']}개")


if __name__ == '__main__':
    main()
