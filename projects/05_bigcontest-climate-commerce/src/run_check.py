import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from prep import *

# P1 ~ P4
card = load_card2()
card = drop_excluded(card)
card = add_group(card)
card = add_segment(card)

# P5: 외지인 그룹 일평균 (184일 기준, 없는 날은 0으로 계산)
EXPECT_OUT = {
    ('춘천', '식료품'): 19166, ('춘천', '외식'): 16603, ('춘천', '교통·숙박'): 3041,
    ('춘천', '의료·약국'): 1844, ('춘천', '상품쇼핑'): 2079, ('춘천', '여가'): 4231,
    ('춘천', '생활·교육서비스'): 475,
    ('강남', '식료품'): 446122, ('강남', '상품쇼핑'): 428876, ('강남', '외식'): 227086,
}
print('\n== P5 외지인 그룹 일평균 건수 ==')
t_out = daily_table(card, 'group', seg='out')
mean_out = t_out.fillna(0).mean(axis=1)
region_name = {'서울 강남구': '강남', '강원 춘천시': '춘천'}
for (reg, grp), exp in EXPECT_OUT.items():
    key = [k for k in mean_out.index if k[0] == [r for r, n in region_name.items() if n == reg][0] and k[1] == grp]
    got = round(mean_out.loc[key[0]]) if key else None
    diff = None if got is None else round((got - exp) / exp * 100, 2)
    check(f'P5 {reg} 외지인 {grp} 일평균 (차이 {diff}%)', got, exp)
print('외지인 그룹 결측 칸 수 (참고):', int(t_out.isna().sum().sum()))
print(t_out.isna().sum(axis=1).to_string())

# P6
asos = load_asos()
print('\n== P6 폭염일 수 (33℃↑) ==')
print(hot_days(asos).to_dict())

# P7 ~ P8
print('\n== P7 호우 사건 ==')
ev = build_event_table(asos)
for region, info in ev.items():
    print(region, 'kept:', [(s.date().isoformat(), e.date().isoformat()) for s, e in info['kept']])
    print('   dropped:', [(s.date().isoformat(), e.date().isoformat()) for s, e in info['dropped']])
    print('   표본 날 수:', int(info['D']['sample'].sum()), '/ 184')

# P9
print('\n== P9 방문자 ==')
vis = load_visitors()

# P10
print('\n== P10 SK 통신 ==')
for kind in ['age', 'time', 'wkdy']:
    load_sk(kind)
