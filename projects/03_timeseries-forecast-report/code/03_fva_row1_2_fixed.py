# FVA 1~2행: 직전 7일 평균(1행), 서비스 수준 보정(2행).  is_closed 가 휴관 판정(팀원 open_expected 로 교체할 곳)
import pandas as pd, numpy as np
CAP,CU,CO,Q,WEEKS=2000,60,15,0.8,12
from common import OUT
g=pd.read_parquet(OUT/'grid_site_day.parquet')
Y={s:d.set_index('date').total for s,d in g.groupby('site')}   # NaN=원본에 행 없음
EXCL=(pd.Timestamp('2024-11-27'),pd.Timestamp('2024-12-01'))   # k 계산에서 제외(20곳 동시 0)
from origins_v7 import GRID as grid, HOL as hol
ORG=[('격자',o) for o in grid]+[('명절',o) for o in hol]
def is_closed(site,date):            # ★ 팀원 open_expected 규칙이 나오면 이 함수만 교체
    return Y[site].get(date,np.nan)==0
def prev7(y,o,open_only):
    w=y[(y.index>=o-pd.Timedelta(days=7))&(y.index<o)].dropna()
    if open_only: w=w[w>0]
    return w.mean() if len(w) else np.nan
def higher_q(r,q):                       # np.quantile(method='higher') 와 같은 값 (구버전 numpy 에서도 동작)
    r=np.sort(np.asarray(r,dtype=float)); return r[int(np.ceil(q*(len(r)-1)))]
def kfac(y,o,open_only):
    r=[]
    for j in range(1,WEEKS+1):
        w0=o-pd.Timedelta(days=7*j); m=prev7(y,w0,open_only)
        if not m>0: continue
        a=y[(y.index>=w0)&(y.index<w0+pd.Timedelta(days=7))]
        a=a[(a>0)&~((a.index>=EXCL[0])&(a.index<=EXCL[1]))]
        r+=list(a.values/m)
    return higher_q(r,Q) if len(r)>=10 else np.nan
out=[]
for kind,o in ORG:
    for s,y in Y.items():
        if y.index.min()>o-pd.Timedelta(days=14): continue
        days=pd.date_range(o,o+pd.Timedelta(days=6))
        for oo in (True,False):
            m=prev7(y,o,oo); k=kfac(y,o,oo) if oo else np.nan
            for d in days:
                a=y.get(d,np.nan)
                if np.isnan(a) or is_closed(s,d): continue
                out.append((kind,o,s,d,oo,a,m,k))
R=pd.DataFrame(out,columns=['kind','origin','site','date','open_only','actual','m','k'])
R['need']=R.actual/CAP
def cost(need,plan): return CU*(need-plan).clip(lower=0)+CO*(plan-need).clip(lower=0)
R['plan1']=R.m/CAP; R['plan2']=R.m*R.k/CAP
R['c1']=cost(R.need,R.plan1); R['c2']=cost(R.need,R.plan2)
R.to_parquet(OUT/'baseline_rows.parquet')
def summ(d):
    ok1=d.dropna(subset=['m']); ok2=d.dropna(subset=['m','k'])
    return pd.Series({'n':len(ok1),'WAPE':(ok1.actual-ok1.m).abs().sum()/ok1.actual.sum(),
      '비용1(만원)':ok1.c1.sum(),'적중1':(ok1.need<=ok1.plan1).mean(),
      'n2':len(ok2),'비용1(공통)':ok2.c1.sum(),'비용2(만원)':ok2.c2.sum(),'적중2':(ok2.need<=ok2.plan2).mean()})
pd.set_option('display.width',200)
print(pd.DataFrame({k:summ(d) for k,d in R.groupby(['kind','open_only'])}).T.round(3).to_string())
# 가이드 검산: 2025 하반기 경복궁 WAPE
d=R[(R.site=='경복궁')&(R.kind=='격자')&(R.origin>='2025-07-01')].dropna(subset=['m'])   # v7: 가이드 검산은 v6 구간(2025 하반기)만
for oo in (False,True):
    x=d[d.open_only==oo]; print('경복궁 격자 WAPE open_only=',oo,round((x.actual-x.m).abs().sum()/x.actual.sum(),3),len(x))
