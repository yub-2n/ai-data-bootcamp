"""
빅콘테스트 2026 — 30년 호우 빈도 (src/rain_freq.py)

- 읽는 파일: data/external/asos_rain_30yr/asos_108_101_daily_rain_19950701_20250630.csv 하나뿐입니다.
  (서울 108·춘천 101 일강수량, 1995-07-01~2025-06-30. 원본에 행이 없던 날은 0으로 채워져 있음 = 가정)
- 카드·손실 결과는 쓰지 않습니다. 이 파일은 아무 파일도 저장하지 않고, 결과는 화면에만 출력합니다.
- 사건 정의: 일강수량이 기준(30mm 또는 50mm) 이상인 날이 이어지면 한 사건.
  50mm 사건도 "50mm 이상인 날이 이어진 묶음"이며, 30mm 사건 안의 최대값 기준이 아닙니다.
- 기간: 7~12월(1995~2024, 30시즌)과 7월~다음 해 6월(1995/96~2024/25, 30년, 보험 연간 빈도 기준).
  사건은 시작일이 속한 기간에 셉니다.
- 무작위 요소가 없어 같은 입력이면 항상 같은 결과가 나옵니다.
- 경로는 상대경로입니다. 프로젝트 폴더(bigcontest)에서 실행하세요:
      python3 -B src/rain_freq.py
"""
import pandas as pd

RAIN30_FILE = 'data/external/asos_rain_30yr/asos_108_101_daily_rain_19950701_20250630.csv'
THRESHOLDS = [30, 50]                                   # 호우 기준 (mm)
STATIONS = ['서울', '춘천']                             # 지점명 (서울 108, 춘천 101)
YEARS = range(1995, 2025)                               # 시즌(7~12월) 또는 연도(7~익년6월)의 시작 연도
DECADES = [(1995, 2004), (2005, 2014), (2015, 2024)]    # 10년 구간
PERIODS = {'h2': '7~12월', 'jj': '7~익년6월'}
UNITS = {'event': '사건', 'day': '날'}

# 2026-10-22 보고값 (사건 기준 평균). 실행 결과가 이 값과 같은지 마지막에 대조합니다.
EXPECT = {
    ('춘천', 30, 'h2'): 7.17, ('서울', 30, 'h2'): 7.70,
    ('춘천', 50, 'h2'): 4.10, ('서울', 50, 'h2'): 4.87,
    ('춘천', 30, 'jj'): 9.93, ('서울', 30, 'jj'): 10.87,
    ('춘천', 50, 'jj'): 5.27, ('서울', 50, 'jj'): 6.10,
}


def load_rain():
    """30년 일강수량을 읽어 지점별 Series(날짜 → mm)로 돌려줍니다."""
    r = pd.read_csv(RAIN30_FILE, encoding='utf-8-sig', parse_dates=['일시'])
    print(f'읽은 파일: {RAIN30_FILE}')
    print(f'행 수: {r.groupby("지점명").size().to_dict()}, 기간: {r["일시"].min().date()} ~ {r["일시"].max().date()}, '
          f'강수 빈칸: {r["일강수량(mm)"].isna().sum()}')
    return {n: g.set_index('일시')['일강수량(mm)'].fillna(0).sort_index() for n, g in r.groupby('지점명')}


def event_starts(rain, thr):
    """기준 이상인 날이 이어지면 한 사건으로 묶고, 사건마다 시작일을 돌려줍니다."""
    days = rain.index[rain >= thr]
    gap = days.to_series().diff().dt.days               # 앞 호우일과의 간격(일)
    return days[(gap != 1).values]                      # 간격이 1일이 아니면 새 사건의 시작


def count_by_year(dates, period):
    """날짜 목록을 기간(시작 연도)별로 셉니다. 사건이 없는 해는 0으로 채웁니다."""
    if period == 'h2':                                  # 7~12월만, 그해
        dates = dates[dates.month >= 7]
        key = dates.year
    else:                                               # 7월~다음 해 6월, 7월이 속한 해
        key = dates.year.where(dates.month >= 7, dates.year - 1)
    return pd.Series(key).value_counts().reindex(list(YEARS), fill_value=0)


def counts(rain, thr, period, unit):
    """한 지점·기준·기간·단위의 연도별 횟수."""
    dates = event_starts(rain, thr) if unit == 'event' else rain.index[rain >= thr]
    return count_by_year(dates, period)


def main():
    rain = load_rain()

    # 1. 기간 전체 요약 (평균, 10~90%, 최소~최대)
    rows = []
    for st in STATIONS:
        for thr in THRESHOLDS:
            for p, plab in PERIODS.items():
                for u, ulab in UNITS.items():
                    c = counts(rain[st], thr, p, u)
                    rows.append({'지점': st, '기준': f'{thr}mm', '기간': plab, '단위': ulab,
                                 '평균': round(c.mean(), 2), '10%': c.quantile(.1), '90%': c.quantile(.9),
                                 '최소': c.min(), '최대': c.max(), '해 수': len(c)})
    print('\n== 시즌당·연간 빈도 (1995~2024 시작, 30개) ==')
    print(pd.DataFrame(rows).to_string(index=False))

    # 2. 10년 구간별 평균 (숫자만, 추세 판단은 하지 않음)
    print('\n== 10년 구간별 평균 ==')
    for p, plab in PERIODS.items():
        rows = []
        for st in STATIONS:
            for thr in THRESHOLDS:
                for u, ulab in UNITS.items():
                    c = counts(rain[st], thr, p, u)
                    rows.append({'지점': st, '기준': f'{thr}mm', '단위': ulab,
                                 **{f'{a}~{b}': round(c.loc[a:b].mean(), 2) for a, b in DECADES}})
        print(f'[{plab}]')
        print(pd.DataFrame(rows).to_string(index=False))

    # 3. 1~6월이 더하는 사건 수 (7~익년6월 − 7~12월, 사건 기준 평균)
    print('\n== 1~6월이 더하는 사건 수 (평균) ==')
    for st in STATIONS:
        for thr in THRESHOLDS:
            add = counts(rain[st], thr, 'jj', 'event').mean() - counts(rain[st], thr, 'h2', 'event').mean()
            print(f'  {st} {thr}mm: {add:.2f}')

    # 3-1. 6월에 시작해 7월로 이어진 사건 수 (6월 30일과 7월 1일이 모두 기준 이상)
    #      이런 사건은 시작일 기준으로 앞 해에 세므로, 7~12월 집계에서는 빠집니다. 1995-06-30은 파일 밖이라 확인 못 함
    print('\n== 6월에 시작해 7월로 이어진 사건 수 (1996~2024년 경계, 29번) ==')
    for st in STATIONS:
        for thr in THRESHOLDS:
            r = rain[st]
            hit = [y for y in range(1996, 2025)
                   if r.get(pd.Timestamp(f'{y}-06-30'), 0) >= thr and r.get(pd.Timestamp(f'{y}-07-01'), 0) >= thr]
            print(f'  {st} {thr}mm: {len(hit)}개 {hit}')

    # 4. 보고값과 대조 (소수 둘째 자리)
    ok = 0
    print('\n== 보고값 대조 ==')
    for (st, thr, p), want in EXPECT.items():
        got = round(counts(rain[st], thr, p, 'event').mean(), 2)
        same = abs(got - want) < 1e-9
        ok += same
        print(f'[{"일치" if same else "다름"}] {st} {thr}mm {PERIODS[p]} 사건 | 결과: {got:.2f} | 기대값: {want:.2f}')
    print(f'\n대조 결과: 일치 {ok}개, 다름 {len(EXPECT) - ok}개')


if __name__ == '__main__':
    main()
