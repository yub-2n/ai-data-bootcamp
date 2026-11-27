# 휴관 규칙(open_expected): 정기 휴관 요일 + 공휴일에는 문 열고, 연휴가 끝난 뒤 첫 평일에 휴관이 넘어가는 규칙.
# 달력과 sites.csv 만 쓴다(공지·실제 관람객 수는 쓰지 않음). 검증용으로만 실제 0 과 비교한다.
import pandas as pd, numpy as np
from common import OUT, find
WD=dict(zip('월화수목금토일',range(7)))
cal=pd.read_csv(find('calendar_kr_2015_2025.csv'),parse_dates=['date']).set_index('date')
HOL=cal.is_holiday.eq(1); OFFDAY=HOL|(cal.index.dayofweek>=5)              # 공휴일 또는 주말
def moved_closure_dates(start='2022-01-01'):
    """정기 휴관 요일이 공휴일이라 문을 연 경우, 그 연휴(공휴일·주말 연속)가 끝난 뒤 첫 평일로 휴관이 넘어간다."""
    res={}                                                                   # {휴관요일: set(옮겨진 날짜)}
    for wd in range(7):
        s=set()
        for d in cal.index[(cal.index>=start)&(cal.index.dayofweek==wd)&HOL]:
            e=d
            while (e+pd.Timedelta(days=1)) in OFFDAY.index and OFFDAY[e+pd.Timedelta(days=1)]: e+=pd.Timedelta(days=1)
            nxt=e+pd.Timedelta(days=1)
            if nxt in cal.index: s.add(nxt)
        res[wd]=s
    return res
def open_expected(closed_weekday,moved_start='2022-01-01'):
    mv=moved_closure_dates(moved_start); wd=WD[closed_weekday]; idx=cal.index
    closed=(idx.dayofweek==wd)&~HOL.values                                   # 정기 휴관 요일, 공휴일이면 열림
    closed=closed|idx.isin(list(mv[wd]))                                    # 옮겨진 휴관일
    return pd.Series(~closed,index=idx)
if __name__=='__main__':
    g=pd.read_parquet(OUT/'grid_site_day.parquet'); g=g[~g.row_missing].copy()
    for label,ms in [('기본 규칙(정기 휴관, 공휴일엔 열림)','2100-01-01'),('확장 규칙(연휴 후 첫 평일로 이동, 2022~)','2022-01-01')]:
        oe={cw:open_expected(cw,ms) for cw in g.closed_weekday.unique()}
        g['exp_open']=[oe[c][d] for c,d in zip(g.closed_weekday,g.date)]
        print('\n==',label)
        for yr,a,b in [('2019~2025','2019-01-01','2025-12-31'),('2023~2025','2023-01-01','2025-12-31'),('2024~2025','2024-01-01','2025-12-31')]:
            x=g[(g.date>=a)&(g.date<=b)]; agree=((x.exp_open)==(~x.zero)).mean()
            print(f'{yr}: 개소×날 {len(x):6d} | 일치율 {agree:.4f} | 열 것으로 예상했는데 휴관 {int((x.exp_open&x.zero).sum())} | 휴관 예상했는데 열림 {int((~x.exp_open&~x.zero).sum())}')
    x=g[(g.date>='2023-01-01')]; oe={cw:open_expected(cw) for cw in g.closed_weekday.unique()}; x=x.assign(exp_open=[oe[c][d] for c,d in zip(x.closed_weekday,x.date)])
    bad=x[x.exp_open==x.zero]                                                # 어긋난 날(확장 규칙)
    print('\n확장 규칙에서 어긋난 개소×날 (2023~2025):',len(bad)); print(bad.groupby('date').size().sort_values(ascending=False).head(12).to_string())
