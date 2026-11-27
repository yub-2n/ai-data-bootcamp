"""
빅콘테스트 2026 — 나머지 5개 지역 유형별 추정 (src/regions.py)

- 대상: 속초(90), 양평(202), 서귀포(189), 경주(283), 구미(279). 카드 자료가 없어 관광공사 외지인 방문자와
  기상 자료만 씁니다. 춘천·강남은 같은 방식으로 재서 기준으로 함께 보여 줍니다. 모든 결과는 "추정"입니다.
- 관광공사 방문자 자료(공공데이터포털 「한국관광공사_빅데이터_지역별 방문자수」 설명, 유빈 Claude 대화 확인):
  원천은 이동통신 데이터(내국인 KT, 외국인 SK텔레콤)로 카드(신한)·SK 유동인구(SKT)와 출처가 다름.
  방문자 = 거주·통근·통학 등 일상생활권을 벗어나 일정 시간 머문 사람(관광객과 같지 않음), 일자별 순방문자 수.
  현지인·외지인 구분 기준은 확인 못 함.
- 결과를 보기 전에 정한 규칙 (2026-10-22, 유빈 결정):
    · 추정 가능 = 남은 호우 사건 5개 이상. 4개 이하는 "추정 불가"
    · 유형 = 외지인 방문자의 주말/평일 비율로 전국 264개 시군구를 3등분
             (높은 1/3 = 관광형, 낮은 1/3 = 업무형, 가운데 = 중간). 외지인 비중은 참고로만 표시
- 측정: 카드 주 모형과 같은 구조(event_study.build_design)에 종속변수 ln(외지인 방문자 수).
  event_study.REGION_WX에 지역을 이 스크립트 안에서만 더해 씁니다 (event_study.py는 고치지 않음).
- 춘천·강남 카드 결과를 다른 지역에 곱해 금액을 만들지 않습니다.
- 이 파일은 아무 파일도 저장하지 않습니다. 난수는 event_study의 SEED(=2026)를 따릅니다.
- 프로젝트 폴더(bigcontest)에서 실행하세요:
      python3 -B src/regions.py
"""
import contextlib
import io
import sys
import warnings

import pandas as pd

sys.path.insert(0, 'src')
warnings.filterwarnings('ignore')
import event_study as es
from prep import load_visitors

MIN_EVENTS = 5                                 # 추정 가능 기준 (결과 보기 전에 정함)
REGIONS = {                                    # 지역: (관광공사 시군구 코드, 기상 지점 이름)
    '춘천': ('51110', '춘천'), '강남': ('11680', '서울'),
    '속초': ('51210', '속초'), '양평': ('41830', '양평'), '서귀포': ('50130', '서귀포'),
    '경주': ('47130', '경주'), '구미': ('47190', '구미'),
}
NOTE_WX = {'속초': '관측소(90)는 고성군에 있음', '구미': '2025-09-30 기상 행 없음', '강남': '관측소 108은 종로구'}


def weekend_ratio_all(vis):
    """시군구별 외지인 방문자의 주말 하루 평균 ÷ 평일 하루 평균, 외지인 비중(외지인 ÷ (현지인+외지인))."""
    out = vis[vis['touDivCd'] == 2]
    we = out[out['date'].dt.dayofweek >= 5].groupby('signguCode')['touNum'].mean()
    wk = out[out['date'].dt.dayofweek < 5].groupby('signguCode')['touNum'].mean()
    tot = vis[vis['touDivCd'].isin([1, 2])].pivot_table(index='signguCode', columns='touDivCd',
                                                        values='touNum', aggfunc='sum')
    return pd.DataFrame({'주말평일비': we / wk, '외지인비중%': 100 * tot[2] / (tot[1] + tot[2])})


def main():
    data = es.load_all()
    with contextlib.redirect_stdout(io.StringIO()):
        vis = load_visitors()
    vis['signguCode'] = vis['signguCode'].astype(str)

    # 1. 유형 경계: 전국 264개 시군구 3등분 (먼저 출력, 이 값을 보고 바꾸지 않음)
    allr = weekend_ratio_all(vis)
    lo, hi = allr['주말평일비'].quantile([1 / 3, 2 / 3])
    print(f'== 1. 유형 경계 (외지인 방문자 주말/평일 비율, 전국 {len(allr)}개 시군구, 2025-07~12) ==')
    print(f'   업무형 < {lo:.3f} ≤ 중간 < {hi:.3f} ≤ 관광형')

    def kind(r):
        return '관광형' if r >= hi else ('업무형' if r < lo else '중간')

    # 2. 지역별 유형과 추정 가능 여부
    print(f'\n== 2. 지역별 유형과 추정 가능 여부 (기준: 남은 호우 사건 {MIN_EVENTS}개 이상) ==')
    rows = []
    for reg, (code, wx) in REGIONS.items():
        info = data['ev'][wx]
        r = allr.loc[code]
        n_kept = len(info['kept'])
        rows.append({'지역': reg, '유형': kind(r['주말평일비']), '주말평일비': round(r['주말평일비'], 2),
                     '외지인비중%(참고)': round(r['외지인비중%'], 1), '호우 사건': len(info['events']),
                     '남은 사건': n_kept, '판단': '추정' if n_kept >= MIN_EVENTS else '추정 불가'})
    t = pd.DataFrame(rows).set_index('지역')
    print(t.to_string())

    # 3. 호우일 외지인 방문자 변화 (주 모형 구조)
    print('\n== 3. 호우일 외지인 방문자 변화 (추정, %, [90% 구간], 2025-07~12) ==')
    print('   L = 호우일 감소, N5 = L - 이후 5일 반등. 표본은 연휴 날과 연휴에 겹친 사건 구간 제외')
    res = []
    for reg, (code, wx) in REGIONS.items():
        if t.loc[reg, '판단'] != '추정':
            res.append({'유형': t.loc[reg, '유형'], '지역': reg, '결과': '추정 불가 (남은 사건 '
                        f'{t.loc[reg, "남은 사건"]}개)', '메모': NOTE_WX.get(reg, '')})
            continue
        es.REGION_WX.setdefault(reg, wx)                     # 이 실행 안에서만 지역 → 기상 지점 연결
        X, _ = es.build_design(data, reg)
        y = vis[(vis['signguCode'] == code) & (vis['touDivCd'] == 2)].set_index('date')['touNum'].reindex(es.DAYS)
        v = es.summarize(es.fit_ols(y, X))
        res.append({'유형': t.loc[reg, '유형'], '지역': reg,
                    '결과': f'L {v["L"][0]:5.1f} [{v["L"][1]:5.1f}, {v["L"][2]:5.1f}] | '
                            f'N5 {v["N5"][0]:6.1f} [{v["N5"][1]:6.1f}, {v["N5"][2]:6.1f}] | '
                            f'사건 {t.loc[reg, "남은 사건"]}개, 표본 {len(X)}일',
                    '메모': NOTE_WX.get(reg, '')})
    out = pd.DataFrame(res)
    out['순서'] = out['유형'].map({'관광형': 0, '중간': 1, '업무형': 2})
    for k, g in out.sort_values(['순서', '지역']).groupby('순서', sort=True):
        print(f'\n  [{g["유형"].iloc[0]}] (추정)')
        for _, r in g.iterrows():
            print(f'    {r["지역"]:<4} {r["결과"]}' + (f'  ※ {r["메모"]}' if r['메모'] else ''))
    print('\n  주의: 관광공사 방문자는 KT 이동통신 기반, 일상생활권(거주·통근·통학)을 벗어나 머문 사람만 셈. '
          '현지인·외지인 구분 기준은 확인 못 함. 강남은 카드 외지인(출퇴근자 포함)과 방문자(통근·통학 제외)의 '
          '정의가 달라 결과가 다를 수 있음.')
    print('  방문자 감소이지 매출 감소가 아님. 금액 환산 안 함.')


if __name__ == '__main__':
    main()
