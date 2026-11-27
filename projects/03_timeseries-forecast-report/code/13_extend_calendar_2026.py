"""cal.csv 를 2026-12-31 까지 늘린다 (가이드: '2026년 권고표 날짜의 달력은 같은 패키지(holidays 0.103, holidays.KR)로 만든다').
검증: 같은 방법으로 2015~2025를 만들어 기존 cal.csv 와 모든 열이 같은지 확인한 뒤에만 2026을 붙인다.
사용: pip install holidays==0.103 후  python 13_extend_calendar_2026.py   (data/cal.csv 를 읽어 data/cal.csv 에 덮어쓰지 않고 data/cal_2026.csv 로 저장)"""
import pandas as pd, numpy as np, holidays
from common import OUT
c=pd.read_csv(OUT/'cal.csv',parse_dates=['date'])
c=c[c.date<='2025-12-31']                                           # 이미 늘려 놓았어도 원본 구간만 비교
H=holidays.KR(years=range(2015,2027))
WD='월화수목금토일'
def make(idx):
    df=pd.DataFrame({'date':idx})
    df['weekday']=[WD[d.dayofweek] for d in idx]
    df['holiday_name']=[H.get(d.date()) for d in idx]
    df['is_holiday']=df.holiday_name.notna().astype(int)
    for col,nm in [('seollal_offset','설날'),('chuseok_offset','추석')]:
        days=[pd.Timestamp(k) for k,v in H.items() if v==nm]
        off=pd.Series(np.nan,index=idx)
        for t in days:
            r=(idx-t).days; m=(abs(r)<=15); off[m]=r[m]
        df[col]=off.values
    df['is_last_wednesday']=[int(d.dayofweek==2 and (d+pd.Timedelta(days=7)).month!=d.month) for d in idx]
    return df
g=make(pd.date_range('2015-01-01','2025-12-31'))
same=all((g[col].fillna(-999).astype(str).values==c[col].fillna(-999).astype(str).values).all() if col in('weekday','holiday_name') else np.allclose(g[col].fillna(-999).values,c[col].fillna(-999).values) for col in ['weekday','holiday_name','is_holiday','seollal_offset','chuseok_offset','is_last_wednesday'])
print('2015~2025 재생성 결과가 기존 cal.csv 와 모든 열에서 같은가:',same)
assert same,'재생성 방법이 기존 달력과 다릅니다. 2026을 붙이지 않습니다.'
new=make(pd.date_range('2026-01-01','2026-12-31'))
out=pd.concat([c,new],ignore_index=True); out.to_csv(OUT/'cal_2026.csv',index=False,encoding='utf-8')
print(new[new.date<='2026-01-08'].to_string(index=False)); print('2026 공휴일 수',int(new.is_holiday.sum()),'| 2026 마지막 수요일',new[new.is_last_wednesday==1].date.dt.strftime('%m-%d').tolist())
