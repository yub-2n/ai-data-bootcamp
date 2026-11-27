# 개소×날짜 표(grid_site_day)와 9개 계열 표(grid_series_day) 만들기.  필요: pip install pandas pyarrow
import pandas as pd, numpy as np
from common import find, OUT
v=pd.read_parquet(find('heritage_visitors_daily.parquet')); s=pd.read_csv(find('sites.csv'),parse_dates=['first_date','last_date'])
M={"동부":["동구릉","광릉","홍유릉","사릉"],"중부":["태릉","정릉","헌릉","선릉","의릉","영휘원"],
   "서부":["서오릉","서삼릉","융릉","파주삼릉","파주장릉","김포장릉","양주온릉"],"세종":["세종대왕유적"]}
s2m={x:k for k,l in M.items() for x in l}; assert len(s2m)==18
rows=[]
for _,r in s.iterrows():                      # 자료 기간의 모든 날짜를 행으로 (원본에 없는 날은 NaN)
    d=pd.DataFrame({'date':pd.date_range(r.first_date,r.last_date)}); d['site']=r.site; d['group']=r.group
    d['closed_weekday']=r.closed_weekday; rows.append(d)
g=pd.concat(rows,ignore_index=True).merge(v[['date','site','paid','free','total']],on=['date','site'],how='left')
g['row_missing']=g.total.isna(); g['zero']=(g.total==0)
g['series']=np.where(g.group=='왕릉',g.site.map(s2m).map(lambda x:'왕릉-'+x if isinstance(x,str) else x),g.site)
sr=g.groupby(['series','date']).agg(total=('total',lambda x:x.sum(min_count=len(x))),n_sites=('total','size'),n_zero=('zero','sum')).reset_index()
g.to_parquet(OUT/'grid_site_day.parquet'); sr.to_parquet(OUT/'grid_series_day.parquet')
print('개소×날짜 행:',len(g),'(기대 63194) | 원본 행:',len(v),'| 원본에 없는 날 행:',int(g.row_missing.sum()),'(기대 1166)')
print('total=0 행:',int(g.zero.sum()),'(기대 8832) | 계열 수:',sr.series.nunique(),'| series×day 행:',len(sr),'(기대 27396)')
