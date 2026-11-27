"""
빅콘테스트 2026 — 날씨지수 보험(호우) 설계 계산 (src/insurance.py)

- 날씨지수 보험: 관측소 일강수량이 기준을 넘으면, 피해 조사 없이 정해진 돈을 주는 보험입니다.
- 이 파일은 이미 있는 결과를 모아 보험 숫자로 바꿀 뿐, 새 모형을 만들지 않습니다.
    · 사건당 손실: src/rain_followup.py의 money_table (방법1, 택시 제외, 외지인, 신한카드 결제분만)
    · 점포 수: src/priority.py의 store_counts (상가정보 2025-10, 업종연결표)
    · 연간 빈도: src/rain_freq.py의 counts (30년, 7~익년6월, 30mm 사건)
    · 사건별 손실: src/model.py의 loeo (춘천 외지인 83합계, 실제손실%·예측손실%)
- 팀 결정(2026-10-22): 발동 = 일강수량 30mm 이상, 이어진 비는 1회. 춘천(101) 중심.
  강남은 108과 AWS 400을 나란히 보여 주되 금액은 쓰지 않음("근거 부족").
- 가게 손해 = 매출 손실 × 12.6%(소상공인실태조사 2023 평균 영업이익률) ~ × 100% (범위로만 보여 줌).
- 연간 기대 지급액은 순보험료(운영비·이윤 없음)입니다.
- 이 파일은 아무 파일도 저장하지 않습니다. 결과는 화면에만 출력합니다.
- 난수는 event_study.py의 SEED(=2026)를 그대로 따르므로 같은 입력이면 같은 결과가 나옵니다.
- 경로는 상대경로입니다. 프로젝트 폴더(bigcontest)에서 실행하세요:
      python3 -B src/insurance.py
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, 'src')
from event_study import load_all
from model import loeo
from priority import load_mapping, store_counts
from rain_followup import money_table
from rain_freq import counts, event_starts, load_rain

TRIGGER_MM = 30                               # 발동 기준 (팀 결정, 바꾸지 않음)
MARGIN = 0.126                                # 영업이익률 (소상공인실태조사 2023 전체 평균)
GOV_SUPPORT = 0.55                            # 가정: 풍수해보험처럼 정부가 보험료의 55% 지원 (행안부 보도자료 2026-06-29)
LOSS_SHARE = {'이익만 잃은 경우(12.6%)': MARGIN, '매출 전체(100%)': 1.0}
TOP_CELLS = ['여가', '교통·숙박', '외식']      # 춘천 지원 1순위 칸 (강남 교통·숙박은 금액 미사용)
ASOS_2025 = {'108(종로)': '강남구_ASOS.csv', '101(춘천)': '춘천시_ASOS.csv'}
AWS_400 = 'data/external/강남_AWS.csv'


def rain_2025(path):
    """2025 하반기 일강수량 (빈칸 = 0, 가정)."""
    w = pd.read_csv(path, encoding='cp949')
    return w.set_index(pd.to_datetime(w['일시']))['일강수량(mm)'].fillna(0)


def part_trigger():
    """(가) 발동 조건: 2025 하반기 지점별 30mm 날·사건 수."""
    print('\n== (가) 발동 조건: 일강수량 30mm 이상, 이어진 비는 1회 (2025-07~12) ==')
    series = {k: rain_2025(v) for k, v in ASOS_2025.items()}
    series['400(강남 AWS)'] = rain_2025(AWS_400)
    for k, r in series.items():
        days = r.index[r >= TRIGGER_MM]
        print(f'  {k}: 관측 {len(r)}일, 30mm 이상 날 {len(days)}일, 사건 {len(event_starts(r, TRIGGER_MM))}개')
    d108 = set(series['108(종로)'].index[series['108(종로)'] >= TRIGGER_MM])
    d400 = set(series['400(강남 AWS)'].index[series['400(강남 AWS)'] >= TRIGGER_MM])
    print(f'  강남 기준 비교: 108만 {len(d108 - d400)}일, 400만 {len(d400 - d108)}일, 둘 다 {len(d108 & d400)}일 → 강남 "근거 부족"')


def part_frequency():
    """(나) 연간 발동 빈도: 30년(7~익년6월) 30mm 사건."""
    print('\n== (나) 연간 발동 빈도 (30mm 사건, 7~익년6월, 1995/96~2024/25, 30년) ==')
    rain = load_rain()
    freq = {}
    for st in ['춘천', '서울']:
        c = counts(rain[st], TRIGGER_MM, 'jj', 'event')
        h2 = counts(rain[st], TRIGGER_MM, 'h2', 'event')
        freq[st] = {'평균': c.mean(), '10%': c.quantile(.1), '90%': c.quantile(.9)}
        print(f'  {st}: 연평균 {c.mean():.2f}회 (10~90% {c.quantile(.1):.1f}~{c.quantile(.9):.1f}, 최대 {c.max()}) | '
              f'7~12월 평균 {h2.mean():.2f}, 최대 {h2.max()}')
    for k, v in ASOS_2025.items():
        print(f'  2025 하반기 {k}: 30mm 사건 {len(event_starts(rain_2025(v), TRIGGER_MM))}개 (30년 7~12월 최대와 비교)')
    return freq


def part_payout(money, stores, freq):
    """(다) 보험금 크기와 (라) 연간 기대 지급액 (순보험료)."""
    f = freq['춘천']
    rows = [('춘천 전체(83합계)', '83합계', 1)] + [(f'춘천 {g} (점포당)', g, int(stores.loc[g, '춘천'])) for g in TOP_CELLS]
    print('\n== (다) 사건당 보험금 크기 (춘천 외지인, 방법1, 택시 제외, 신한카드 결제분만) ==')
    print('   단위: 지역 전체는 만원, 점포당은 원. [ ]는 90% 구간')
    out = []
    for lab, grp, n in rows:
        m = money.loc[grp]
        unit = 1 if n == 1 else 1e4 / n                       # 만원 → 지역 전체는 만원, 점포당은 원
        pt, lo, hi = m['방법1(만원/사건)'] * unit, m['방법1_5%'] * unit, m['방법1_95%'] * unit
        for sh_lab, sh in LOSS_SHARE.items():
            print(f'  {lab:<18} 점포 {n if n > 1 else "-":>5} | {sh_lab:<16} {pt*sh:>12,.1f} [{lo*sh:,.1f}, {hi*sh:,.1f}]')
            out.append({'대상': lab, '손해 비율': sh_lab, '사건당': pt * sh, '사건당_5%': lo * sh, '사건당_95%': hi * sh})
    print('\n== (라) 연간 기대 지급액 = 연간 빈도 × 사건당 보험금 (순보험료, 운영비·이윤 없음) ==')
    print(f'   빈도: 춘천 연평균 {f["평균"]:.2f}회 (10~90% {f["10%"]:.1f}~{f["90%"]:.1f})')
    print('   가운데 값 = 평균 빈도 × 점추정. 범위 = (10% 빈도 × 5% 손실) ~ (90% 빈도 × 95% 손실), 두 끝을 단순히 곱한 넓은 범위')
    for r in out:
        mid = f['평균'] * r['사건당']
        low, high = f['10%'] * r['사건당_5%'], f['90%'] * r['사건당_95%']
        print(f'  {r["대상"]:<18} {r["손해 비율"]:<16} {mid:>12,.1f} [{low:,.1f}, {high:,.1f}]')
        if '점포당' in r['대상']:                          # 가정: 풍수해보험처럼 정부가 보험료 55% 지원
            print(f'  {"":<18} {"":<16} → 가게 부담 보험료(가정: 정부 55% 지원) = 기대 지급액 × 45% = {mid * (1 - GOV_SUPPORT):,.1f}')


def part_basis(data):
    """(마) 기준 위험: 정액 지급(모든 사건에 평균 손실만큼)과 사건별 실제 손실 비교."""
    t = loeo(data, '춘천')
    L = t['실제손실%']
    avg = L.mean()
    ratio = L / avg                                        # 실제 손실 ÷ 정액(평균) 손실
    print('\n== (마) 기준 위험: 춘천 외지인 83합계, 사건 12개 (model.py 실제손실%, 2025-07~12) ==')
    print('   정액 지급 = 모든 사건에 평균 손실만큼 준다고 가정. 비율 = 실제 손실 ÷ 평균')
    print(t[['사건', '실제손실%', '예측손실%_ols_wx', '예측손실%_gbm_wx']].assign(비율=ratio.round(2)).round(1).to_string(index=False))
    print(f'  평균 손실 {avg:.1f}% (범위 {L.min():.1f}~{L.max():.1f})')
    print(f'  실제 < 평균 (정액이 더 많이 줌): {(L < avg).sum()}개 / 실제 > 평균 (정액이 덜 줌): {(L > avg).sum()}개')
    print(f'  실제가 평균의 절반 미만 (2배 넘게 더 줌): {(ratio < 0.5).sum()}개 / 평균의 1.5배 초과: {(ratio > 1.5).sum()}개')
    for m in ('ols_wx', 'gbm_wx'):
        print(f'  사건별 실제 손실과 예측의 상관 {m}: {np.corrcoef(L, t[f"예측손실%_{m}"])[0, 1]:.2f} (12개, 관련성의 크기만 뜻함)')


def main():
    print('데이터를 읽는 중...')
    data = load_all()
    money, n_kept, n_base = money_table(data, '춘천')
    stores = store_counts(load_mapping())
    print(f'춘천: 남은 호우 사건 {n_kept}개, 평소 날 {n_base}일, 점포 수 기준 상가정보 2025-10')
    part_trigger()
    freq = part_frequency()
    part_payout(money, stores, freq)
    part_basis(data)


if __name__ == '__main__':
    main()
