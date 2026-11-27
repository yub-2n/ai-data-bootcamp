"""
빅콘테스트 2026 — 관광공사 방문자로 카드 외지인 결과 교차 확인 (src/visitor_check.py)

- 질문: 호우일에 관광공사 "외지인 방문자"도 카드 "외지인 결제건수"와 같은 방향으로 줄었나?
- 관광공사 "외지인"의 정의는 확인 못 함 (카드 외지인 = 거주 시도가 다른 결제자와 같은 개념인지 모름).
- 관광공사 방문자 자료(공공데이터포털 「한국관광공사_빅데이터_지역별 방문자수」 설명, 유빈 Claude 대화 확인):
  원천은 이동통신 데이터(내국인 KT, 외국인 SK텔레콤)로 카드(신한)·SK 유동인구(SKT)와 출처가 다름.
  방문자 = 거주·통근·통학 등 일상생활권을 벗어나 일정 시간 머문 사람(관광객과 같지 않음), 일자별 순방문자 수.
  현지인·외지인 구분 기준은 확인 못 함.
- 1단계: 기존 문서값(방문자 외지인 비 온 날 춘천 −14%, 강남 +2%)의 계산 규칙을 모르므로,
  카드에서 재현된 단순 비교 규칙(호우일 ÷ 같은 요일 맑은 날 평균, 맑은 날 = 일강수량 1mm 미만, 빈칸 = 0)을
  먼저 카드에 적용해 규칙이 맞게 짜였는지 확인(기준값 춘천 0.862, 강남 0.947)한 뒤 방문자에 적용합니다.
- 2단계: 카드 주 모형과 같은 구조(event_study.build_design: 사건 더미·rain10·hot·요일·공휴일·월 통제,
  연휴와 겹치는 사건 제외)에 종속변수만 ln(방문자 수)로 바꿔 L, R5, N5와 90% 구간을 구합니다.
- 판정은 카드와 방향(부호)이 같은지만 봅니다.
- 이 파일은 아무 파일도 저장하지 않습니다. 난수는 event_study의 SEED(=2026)를 따릅니다.
- 프로젝트 폴더(bigcontest)에서 실행하세요:
      python3 -B src/visitor_check.py
"""
import contextlib
import io
import sys
import warnings

import pandas as pd

sys.path.insert(0, 'src')
warnings.filterwarnings('ignore')
from event_study import DAYS, build_design, fit_ols, load_all, main_model, series, summarize, weather
from prep import load_visitors

VISIT_CODE = {'춘천': '51110', '강남': '11680'}
SEG_NAME = {1: '현지인', 2: '외지인'}
CARD_EXPECT = {'춘천': {'L': 21.5, 'N5': 48.3}, '강남': {'L': 4.3, 'N5': 3.5}}   # 검증된 event_study 출력값
SIMPLE_EXPECT = {'춘천': 0.862, '강남': 0.947}                                  # 카드 단순 비교 재현값 (명세서 A2)
OLD_VISIT = {'춘천': -14, '강남': 2}                                            # 기존 문서값 (계산 규칙 모름)


def visitor_series(vis, code, div):
    """시군구 코드·구분(1 현지인, 2 외지인)의 일별 방문자 수 (184일)."""
    v = vis[(vis['signguCode'] == code) & (vis['touDivCd'] == div)]
    return v.set_index('date')['touNum'].reindex(DAYS)


def simple_ratio(y, data, reg):
    """호우일(남은 사건의 D0, 표본 날) 값 ÷ 같은 요일 맑은 날(1mm 미만) 평균의 평균."""
    X, _ = build_design(data, reg)
    rain = weather(data, reg)['rain']
    clear = rain < 1
    wet_days = X.index[X['D0'] == 1]
    ratios = [y[d] / y[clear & (DAYS.dayofweek == d.dayofweek)].mean() for d in wet_days]
    return sum(ratios) / len(ratios), len(wet_days)


def fmt(v):
    return f'{v[0]:6.1f} [{v[1]:6.1f}, {v[2]:6.1f}]'


def main():
    data = load_all()
    with contextlib.redirect_stdout(io.StringIO()):
        vis = load_visitors()
    vis['signguCode'] = vis['signguCode'].astype(str)

    print('== 1단계: 단순 비교 (호우일 ÷ 같은 요일 맑은 날 평균) ==')
    for reg in ['춘천', '강남']:
        r_card, n = simple_ratio(series(data, reg), data, reg)
        r_vis, _ = simple_ratio(visitor_series(vis, VISIT_CODE[reg], 2), data, reg)
        ok = '일치' if abs(r_card - SIMPLE_EXPECT[reg]) <= 0.01 else '다름'
        print(f'  {reg} (호우일 {n}일): 카드 외지인 {r_card:.3f} (재현값 {SIMPLE_EXPECT[reg]}, {ok}) | '
              f'방문자 외지인 {r_vis:.3f} → {100 * (r_vis - 1):+.1f}% (기존 문서값 {OLD_VISIT[reg]:+d}%)')

    print('\n== 2단계: 주 모형과 같은 구조 (L 손실, R5 반등, N5 순손실, %, [90% 구간]) ==')
    print('   기간 2025-07~12, 연휴 날과 연휴에 겹친 사건 구간 제외 (카드 주 모형과 같은 표본)')
    for reg in ['춘천', '강남']:
        X, _ = build_design(data, reg)
        n_ev = len(data['ev'][{'춘천': '춘천', '강남': '서울'}[reg]]['kept'])
        card = main_model(data, reg)
        print(f'\n  [{reg}] 남은 사건 {n_ev}개, 표본 {len(X)}일')
        print(f'    카드 외지인 결제건수   L {fmt(card["L"])} | N5 {fmt(card["N5"])}')
        for k in ('L', 'N5'):
            assert abs(card[k][0] - CARD_EXPECT[reg][k]) < 0.05, (reg, k, card[k][0])   # 검증값과 같은지
        for div in (2, 1):
            v = summarize(fit_ols(visitor_series(vis, VISIT_CODE[reg], div), X))
            same = ('같음' if (v['L'][0] > 0) == (card['L'][0] > 0) else '다름') if div == 2 else '-'
            print(f'    방문자 {SEG_NAME[div]:<4}         L {fmt(v["L"])} | N5 {fmt(v["N5"])} | '
                  f'카드 외지인과 L 방향: {same}')
    print('\n  주의: 관광공사 방문자는 KT 이동통신 기반, 일상생활권(거주·통근·통학)을 벗어나 머문 사람만 셈. '
          '현지인·외지인 구분 기준은 확인 못 함. 강남은 카드 외지인(출퇴근자 포함)과 방문자(통근·통학 제외)의 '
          '정의가 달라 결과가 다를 수 있음.')
    print('  방향이 같아도 같은 사람들을 센 것인지는 모름.')


if __name__ == '__main__':
    main()
