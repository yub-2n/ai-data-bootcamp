# 가이드 검산: 2025 하반기 경복궁 직전 7일 평균 WAPE (가이드: 0 포함·휴관 평가 포함 50.2%, 문 연 날만·휴관 제외 36.7%)
import pandas as pd
from common import OUT
g=pd.read_parquet(OUT/'grid_site_day.parquet'); y=g[g.site=='경복궁'].set_index('date').total
grid=[pd.Timestamp('2025-07-01')+pd.Timedelta(days=7*i) for i in range(26)]
def p7(o,open_only):
    w=y[(y.index>=o-pd.Timedelta(days=7))&(y.index<o)].dropna()
    if open_only: w=w[w>0]
    return w.mean()
for ev in ('휴관일 평가 제외','휴관일도 평가에 포함'):
  for oo in (False,True):
    num=den=0
    for o in grid:
        m=p7(o,oo); a=y[(y.index>=o)&(y.index<o+pd.Timedelta(days=7))].dropna()
        if ev=='휴관일 평가 제외': a=a[a>0]
        num+=(a-m).abs().sum(); den+=a.sum()
    print(ev,'| 문 연 날만' if oo else '| 0 포함',round(num/den,3))
