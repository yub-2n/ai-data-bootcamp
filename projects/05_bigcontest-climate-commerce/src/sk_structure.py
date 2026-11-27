"""
빅콘테스트 2026 — SK 유동인구 구조 비교: 춘천 대 강남 (src/sk_structure.py)

- SK 자료는 한 달 평균(일평균 유동인구, 기준년월)이라 비 온 날 분석은 하지 않습니다 (전처리 명세서 P10).
- 파일 읽기와 12월 중복 제거는 src/prep.py의 load_sk를 그대로 씁니다.
- 지역: BLOCK_CD 앞 5자리 32010 = 춘천, 11230 = 강남 (통계청 행정구역 코드 모양과 행 수로 본 추정).
  경계 근처 다른 시군구 블록은 뺍니다.
- 비중은 지역·월별로 모든 블록 값을 먼저 더한 뒤 계산합니다 (블록별 나눗셈 없음 → 0으로 나누지 않음).
- 비교용: 카드 데이터2 외지인 결제건수, 관광공사 외지인 방문자의 주말/평일 비율 (단순 합계·평균).
  세 자료의 "외지인"(또는 사람) 정의가 서로 다릅니다:
    카드 외지인 = 거주 시도가 가맹점 시도와 다른 결제자 / SK = 그 격자에 있던 사람 전부(거주지 없음) /
    관광공사 외지인 = KT 이동통신 기반, 일상생활권(거주·통근·통학) 밖에서 머문 사람 중 외지인(구분 기준 확인 못 함)
- 이 파일은 아무 파일도 저장하지 않습니다. 결과는 화면에만 출력합니다. 무작위 요소 없음.
- 프로젝트 폴더(bigcontest)에서 실행하세요:
      python3 -B src/sk_structure.py
"""
import contextlib
import io
import sys

import pandas as pd

sys.path.insert(0, 'src')
from prep import add_segment, drop_excluded, load_card2, load_sk, load_visitors

REGION_CODE = {'32010': '춘천', '11230': '강남'}            # BLOCK_CD 앞 5자리 → 지역 (추정)
VISIT_CODE = {'춘천': '51110', '강남': '11680'}              # 관광공사 시군구 코드
CARD_REGION = {'강원 춘천시': '춘천', '서울 강남구': '강남'}
HOURS = [f'TMST_{h:02d}' for h in range(24)]
BINS = {'00_05': range(0, 6), '06_11': range(6, 12), '12_17': range(12, 18), '18_23': range(18, 24)}
AGES = ['10G', '20G', '30G', '40G', '50G', '60GU']
DAYS_WK = ['MON', 'TUS', 'WED', 'THU', 'FRI']               # 파일의 열 이름 그대로 (화요일 = TUS)
DAYS_WE = ['SAT', 'SUN']


def read(kind):
    """SK 파일을 읽고(중복 제거) 춘천·강남 블록만 남겨 숫자로 바꿉니다."""
    with contextlib.redirect_stdout(io.StringIO()):
        d, _ = load_sk(kind)
    d['지역'] = d['BLOCK_CD'].str[:5].map(REGION_CODE)
    n_other = int(d['지역'].isna().sum())
    d = d[d['지역'].notna()].copy()
    val = [c for c in d.columns if c not in ('STD_YM', 'BLOCK_CD', 'X_COORD', 'Y_COORD', '지역')]
    d[val] = d[val].astype(float)
    print(f'  {kind}: 춘천·강남 블록 {len(d):,}행 (6개월), 뺀 경계 블록 {n_other}행, '
          f'0인 칸 비율 춘천 {100 * (d.loc[d["지역"] == "춘천", val] == 0).mean().mean():.1f}% / '
          f'강남 {100 * (d.loc[d["지역"] == "강남", val] == 0).mean().mean():.1f}%')
    return d, val


def pct(s):
    return (100 * s / s.sum()).round(1)


def main():
    print('== 읽기 (지역 코드 대응은 추정: 32010 = 춘천, 11230 = 강남) ==')
    t, th = read('time')
    a, ac = read('age')
    w, wc = read('wkdy')

    # ① 시간대 비중 (6개월 합계 기준)
    tot = t.groupby('지역')[HOURS].sum()
    print('\n== ① 시간대 비중 (%, 24시간 합 = 100, 2025-07~12 블록 합계) ==')
    print(pd.DataFrame({b: tot[[HOURS[h] for h in hs]].sum(axis=1) for b, hs in BINS.items()})
          .apply(pct, axis=1).to_string())
    peak = tot.idxmax(axis=1).str[-2:]
    print('  가장 붐비는 시각:', {r: f'{h}시' for r, h in peak.items()})

    # ② 연령 비중 (남녀 합)
    ag = pd.DataFrame({g: a.groupby('지역')[[f'MAN_FLOW_POP_CNT_{g}', f'WMAN_FLOW_POP_CNT_{g}']].sum().sum(axis=1)
                       for g in AGES})
    ag.columns = ['10대', '20대', '30대', '40대', '50대', '60대 이상']
    print('\n== ② 연령 비중 (%, 남녀 합, 2025-07~12 블록 합계) ==')
    print(ag.apply(pct, axis=1).to_string())

    # ③ 주말/평일 비율 (주말 하루 평균 ÷ 평일 하루 평균)
    sums = w.groupby('지역')[[f'FLOW_POP_CNT_{d}' for d in DAYS_WK + DAYS_WE]].sum()
    wk = sums[[f'FLOW_POP_CNT_{d}' for d in DAYS_WK]].sum(axis=1) / 5
    we = sums[[f'FLOW_POP_CNT_{d}' for d in DAYS_WE]].sum(axis=1) / 2
    sk_ratio = (we / wk).round(2)

    # ④ 월별 변화 (7월 = 100, 시간대 파일 24시간 합 기준)
    mon = t.groupby(['지역', 'STD_YM'])[HOURS].sum().sum(axis=1).unstack()
    print('\n== ④ 월별 유동인구 지수 (7월 = 100, 시간대 파일 블록 합계) ==')
    print((100 * mon.div(mon.iloc[:, 0], axis=0)).round(1).to_string())

    # 비교: 카드 외지인 결제건수, 관광공사 외지인 방문자 (요일로만 나눔, 184일 전체, 공휴일 구분 없음)
    with contextlib.redirect_stdout(io.StringIO()):
        card = add_segment(drop_excluded(load_card2()))
        vis = load_visitors()
    vis['signguCode'] = vis['signguCode'].astype(str)          # 시군구 코드를 글자로 (다른 두 파일과 같게)
    card['지역'] = card['MCT_SGG_CD'].map(CARD_REGION)
    card['date'] = pd.to_datetime(card['TA_YMD'].astype(str))
    rows = []
    for reg in ['춘천', '강남']:
        c = card[card['지역'] == reg]
        out_share = 100 * c.loc[c['seg'] == 'out', 'USE_CNT'].sum() / c.loc[c['seg'].isin(['out', 'loc']), 'USE_CNT'].sum()
        daily = c[c['seg'] == 'out'].groupby('date')['USE_CNT'].sum()
        card_ratio = daily[daily.index.dayofweek >= 5].mean() / daily[daily.index.dayofweek < 5].mean()
        v = vis[(vis['signguCode'] == VISIT_CODE[reg]) & (vis['touDivCd'] == 2)].set_index('date')['touNum']
        vis_ratio = v[v.index.dayofweek >= 5].mean() / v[v.index.dayofweek < 5].mean()
        vv = vis[vis['signguCode'] == VISIT_CODE[reg]].groupby('touDivCd')['touNum'].sum()
        rows.append({'지역': reg, 'SK 주말/평일': sk_ratio[reg], '카드 외지인 주말/평일': round(card_ratio, 2),
                     '방문자 외지인 주말/평일': round(vis_ratio, 2), '카드 외지인 비중%': round(out_share, 1),
                     '방문자 외지인 비중%': round(100 * vv[2] / (vv[1] + vv[2]), 1)})
    print('\n== ③ 주말/평일 비율과 외지인 비중: 세 자료 비교 (2025-07~12) ==')
    print('   주말/평일 = 주말 하루 평균 ÷ 평일 하루 평균. 1보다 크면 주말에 더 많음')
    print('   카드 외지인 비중 = 외지인 ÷ (외지인 + 현지인) 결제건수, 정보없음 제외 (업종 83개 합계)')
    print('   방문자 외지인 비중 = 외지인 ÷ (외지인 + 현지인) 방문자 수 (외국인 제외)')
    print(pd.DataFrame(rows).set_index('지역').to_string())
    print('   정의 차이: 카드 = 거주 시도 기준 결제자(출퇴근자 포함), SK = 격자에 있던 사람 전부(SKT), '
          '관광공사 = KT 기반, 통근·통학 제외 방문자 (외지인 구분 기준 확인 못 함)')


if __name__ == '__main__':
    main()
