"""
빅콘테스트 2026 — 2026년 호우 참고 비교 (src/rain_2026.py)

규칙 (2026-10-23, 2026년 자료를 보기 전에 유빈이 정함. 결과를 본 뒤 바꾸지 않음):
- 지점: 서울 108, 춘천 101 (ASOS 일자료)
- 사건: 일강수량 30mm 이상인 날이 이어지면 1번 (빈칸은 0). 사건은 시작한 날짜로 셈 (rain_freq.py와 같음)
- 기간: 해마다 1월 1일 ~ 10월 22일에 시작한 사건
- 비교: 2026년을 1996~2025년 30개 해의 같은 기간과 비교 (1995년은 1~6월 자료가 없어 뺌)
- 쓰임: 보고서·발표의 "참고" 한 줄. 보험 빈도(9.93회)·우선순위 숫자는 바꾸지 않음

읽는 파일:
- data/external/asos_rain_30yr/asos_108_101_daily_rain_19950701_20250630.csv (1995-07 ~ 2025-06)
- 강남구_ASOS.csv(서울 108), 춘천시_ASOS.csv(춘천 101) (2025-07 ~ 2025-12)
- data/external/asos_2026/2026_춘천서울_ASOS.csv (2026-01-01 ~ 2026-10-22, cp949)
파일을 저장하지 않습니다. 프로젝트 폴더에서 실행:  python3 -B src/rain_2026.py
"""
import pandas as pd

RAIN30_FILE = 'data/external/asos_rain_30yr/asos_108_101_daily_rain_19950701_20250630.csv'
ASOS_2025 = {'서울': '강남구_ASOS.csv', '춘천': '춘천시_ASOS.csv'}
ASOS_2026 = 'data/external/asos_2026/2026_춘천서울_ASOS.csv'
CODE = {'서울': 108, '춘천': 101}
THR, END_MMDD = 30, 1022
BASE = range(1996, 2026)
EXPECT = {('서울', 2026): 9, ('춘천', 2026): 8, ('서울', 2025): 16, ('춘천', 2025): 17}   # 2026-10-23 결과


def series(st, r30, n26):
    """1995-07 ~ 2026-10-22 일강수량 하나로 잇기 (빈칸은 0)."""
    s30 = r30[r30['지점명'] == st].set_index('일시')['일강수량(mm)']
    d25 = pd.read_csv(ASOS_2025[st], encoding='cp949', parse_dates=['일시']).set_index('일시')['일강수량(mm)']
    d26 = n26[n26['지점'] == CODE[st]].set_index('일시')['일강수량(mm)']
    s = pd.concat([s30, d25, d26]).sort_index()
    assert not s.index.duplicated().any(), '날짜가 겹칩니다'
    full = pd.date_range(s.index.min(), s.index.max())
    print(f'{st}: {s.index.min().date()} ~ {s.index.max().date()}, 빠진 날 {len(full) - len(s)}일')
    return s.reindex(full).fillna(0)


def main():
    r30 = pd.read_csv(RAIN30_FILE, encoding='utf-8-sig', parse_dates=['일시'])
    n26 = pd.read_csv(ASOS_2026, encoding='cp949', parse_dates=['일시'])
    table, ok = {}, 0
    for st in ['서울', '춘천']:
        s = series(st, r30, n26)
        days = s.index[s >= THR]
        starts = pd.Series(days[(days.to_series().diff().dt.days != 1).values])   # 사건 시작일
        win = starts[starts.dt.month * 100 + starts.dt.day <= END_MMDD]
        cnt = win.dt.year.value_counts().reindex(range(1996, 2027), fill_value=0)
        table[st] = cnt
        base = cnt.loc[list(BASE)]
        rank = lambda y: int((cnt > cnt[y]).sum()) + 1                      # 더 많은 해 수 + 1
        print(f'  2026년 {cnt[2026]}회 | 1996~2025 평균 {base.mean():.2f}회 (최소 {base.min()}, 최대 {base.max()}) '
              f'| 2026 순위 {rank(2026)}/31 | 2025년 {cnt[2025]}회, 순위 {rank(2025)}/31')
        print('  2026년 사건 시작일:', [str(d.date()) for d in win if d.year == 2026])
        for y in (2025, 2026):
            same = cnt[y] == EXPECT[(st, y)]
            ok += same
            print(f'  [{"일치" if same else "다름"}] {st} {y} | 결과: {cnt[y]} | 기대값: {EXPECT[(st, y)]}')
    print('\n== 해마다 1/1~10/22 시작 30mm 사건 수 ==')
    print(pd.DataFrame(table).T.to_string())
    print(f'\n대조 결과: 일치 {ok}개, 다름 {len(EXPECT) - ok}개')


if __name__ == '__main__':
    main()
