# 베이스라인 3개(나이브, 계절 나이브, 직전 7일 평균) 비교표와 원점별 WAPE
import pandas as pd, numpy as np
CAP,CU,CO=2000,60,15
from common import OUT, find
g=pd.read_parquet(OUT/'grid_site_day.parquet'); cal=pd.read_csv(find('calendar_kr_2015_2025.csv'),parse_dates=['date']).set_index('date')
Y={s:d.set_index('date').total for s,d in g.groupby('site')}
from origins_v7 import GRID as grid, HOL as hol
ORG=[('격자',o) for o in grid]+[('명절',o) for o in hol]
def is_closed(site,d): return Y[site].get(d,np.nan)==0       # ★ 교체 지점(팀원 open_expected)
# 무료 개방일(과거 분석용 정의): 경복궁이 문 연 날 중 유료비중<15% — 날짜 단위
gb=g[g.site=='경복궁'].set_index('date'); FREE=set(gb.index[(gb.total>0)&(gb.paid/gb.total<0.15)])
def naive(y,o):
    w=y[y.index<o].dropna(); w=w[w>0]; return w.iloc[-1] if len(w) else np.nan
def prev7(y,o):
    w=y[(y.index>=o-pd.Timedelta(days=7))&(y.index<o)].dropna(); w=w[w>0]; return w.mean() if len(w) else np.nan
def snaive(y,o,d):
    k=1
    while k<=8:                               # 같은 요일, 원점 전 값 중 문 연 가장 가까운 날
        t=d-pd.Timedelta(days=7*k)
        if t<o and y.get(t,np.nan)>0: return y[t]
        k+=1
    return np.nan
rows=[]
for kind,o in ORG:
    for s,y in Y.items():
        if y.index.min()>o-pd.Timedelta(days=14): continue
        n,p=naive(y,o),prev7(y,o)
        for d in pd.date_range(o,o+pd.Timedelta(days=6)):
            a=y.get(d,np.nan)
            if np.isnan(a) or is_closed(s,d): continue
            rows.append((kind,o,s,d,a,n,snaive(y,o,d),p))
R=pd.DataFrame(rows,columns=['kind','origin','site','date','actual','나이브','계절나이브','직전7일평균'])
R['special']=R.date.map(lambda d: d in FREE or cal.loc[d,'is_holiday']==1)
R.to_parquet(OUT/'baselines3_rows_v7.parquet')
M=['나이브','계절나이브','직전7일평균']
def met(d,m):
    d=d.dropna(subset=[m]); need=d.actual/CAP; plan=d[m]/CAP
    c=CU*(need-plan).clip(lower=0)+CO*(plan-need).clip(lower=0)
    return pd.Series({'WAPE':(d.actual-d[m]).abs().sum()/d.actual.sum(),'비용':c.sum(),'적중':(need<=plan).mean(),'n':len(d)})
pd.set_option('display.width',220)
print('특수일(무료·공휴일) 비율:',R.groupby('kind').special.mean().round(3).to_dict())
for scope,f in [('전체',lambda d:d),('무료 개방일·공휴일 제외',lambda d:d[~d.special])]:
    print('\n=====',scope)
    t=pd.concat({(k,m):met(f(d),m) for k,d in R.groupby('kind') for m in M},axis=1).T
    print(t.round(3).to_string())
# 원점별 WAPE
print('\n===== 원점별 WAPE (전체)')
W=pd.DataFrame({m:{(k,o):met(d,m).WAPE for (k,o),d in R.groupby(['kind','origin'])} for m in M})
print(W.round(3).to_string())
print('\n원점 묶음별 요약(원점 WAPE 중앙값/최소/최대, 원점별 최저 WAPE 횟수)')
for k in ['격자','명절']:
    w=W.xs(k); print(k,w.median().round(3).to_dict(),w.min().round(3).to_dict(),w.max().round(3).to_dict(),w.idxmin(axis=1).value_counts().to_dict())
