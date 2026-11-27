# [v7] 원점 목록 검증과 원점표 저장 -> results_new/원점목록_v7.csv
import pandas as pd, numpy as np
from common import OUT
from origins_v7 import GRID, HOL, ORIGINS
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
V6=[pd.Timestamp('2025-07-01')+pd.Timedelta(days=7*i) for i in range(26)]
assert len(GRID)==78 and GRID[0]==pd.Timestamp('2024-07-02') and GRID[-1]==pd.Timestamp('2025-12-23')
assert GRID[-1]+pd.Timedelta(days=6)==pd.Timestamp('2025-12-29'), '마지막 평가일은 2025-12-29 여야 한다'
assert all((GRID[i+1]-GRID[i]).days==7 for i in range(77)) and {d.dayofweek for d in GRID}=={1}
assert set(V6)<=set(GRID) and len(ORIGINS)==82
cv=pd.read_csv(OUT/'covariates_free_open.csv',parse_dates=['timestamp']); ev=pd.read_csv(OUT/'free_events_v7.csv',parse_dates=['timestamp'])
fh=set(cv[cv.free_holiday==1].timestamp.unique())
EV={e:set(ev[ev['free_'+e]==1].timestamp.unique()) for e in ['korea_grand_festival','sejong_birthday','heritage_agency_launch']}
def win(o): return set(pd.date_range(o,o+pd.Timedelta(days=6)))
SEAS=lambda m:'봄' if m in(3,4,5) else '여름' if m in(6,7,8) else '가을' if m in(9,10,11) else '겨울'
rows=[]
for o in ORIGINS:
    w=win(o); kind='격자' if o in GRID else '명절'
    ov=[h.date().isoformat() for h in HOL if kind=='격자' and w&win(h)]
    rows.append(dict(구분=kind,원점=o.date(),요일='월화수목금토일'[o.dayofweek],평가_마지막일=(o+pd.Timedelta(days=6)).date(),
        A확정일=(o-pd.Timedelta(days=1)).date(),B확정일=(o-pd.Timedelta(days=7)).date(),v6의_26개에_포함=(o in V6) or kind=='명절',
        시작일_계절=SEAS(o.month),설추석연휴_걸림=bool(w&fh),코리아그랜드페스티벌_걸림=bool(w&EV['korea_grand_festival']),
        세종대왕_걸림=bool(w&EV['sejong_birthday']),출범기념_걸림=bool(w&EV['heritage_agency_launch']),겹치는_명절원점=','.join(ov)))
T=pd.DataFrame(rows); T.to_csv(RES/'원점목록_v7.csv',index=False,encoding='utf-8-sig')
print('정기 원점',len(GRID),GRID[0].date(),'~',GRID[-1].date(),'| 마지막 평가일',(GRID[-1]+pd.Timedelta(days=6)).date(),'| 전체',len(ORIGINS),'| v6의 26개 포함:',set(V6)<=set(GRID),'| 새로 추가',len(set(GRID)-set(V6)))
print(T.groupby('구분')[['설추석연휴_걸림','코리아그랜드페스티벌_걸림','세종대왕_걸림','출범기념_걸림']].sum().to_string())
