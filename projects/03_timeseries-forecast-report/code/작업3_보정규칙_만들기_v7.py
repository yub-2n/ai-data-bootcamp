from pathlib import Path
PACK=Path(__file__).resolve().parent.parent   # 패키지 폴더(code의 상위)
DATA=PACK/'data'; RES=PACK/'results_new'; RES.mkdir(exist_ok=True)
import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
D=DATA
d=pd.read_parquet(D/'eval_rows_v7.parquet'); cv=pd.read_csv(D/'covariates_free_open.csv',parse_dates=['timestamp'])
CAP,Cu,Co=2000,60,15
b=d[(d.method=='나눈 것')&(d.row==7)].copy()
b['date']=pd.to_datetime(b.date); b['origin']=pd.to_datetime(b.origin)
c=cv.rename(columns={'item_id':'site','timestamp':'date'})[['site','date','free_holiday','free_last_wed']]
b=b.merge(c,on=['site','date'],how='left')
TYPES=['명절 연휴 무료','마지막 수요일']
b['lagdays']=np.where(b.lag=='A',1,7); b['K']=b.origin-pd.to_timedelta(b.lagdays,unit='D')
# 그 날 유형의 표시가 확정 시점에 알려져 있었나
def known(r):
    return r.date_type in ('명절 연휴 무료','마지막 수요일')   # 둘 다 달력 규칙이라 확정 시점과 상관없이 알 수 있다
b['known']=b.apply(known,axis=1)
b['ratio']=b.actual/b.q80
def cost(act,q): 
    need=act/CAP; plan=q/CAP
    return Cu*np.clip(need-plan,0,None)+Co*np.clip(plan-need,0,None)
b['q80_new']=b.q80
b['mult']=1.0
MINN=30
for (lag,),g in b.groupby(['lag']):
    for o in sorted(g.origin.unique()):
        K=g[g.origin==o].K.iloc[0]
        for t in TYPES:
            hist=g[(g.date_type==t)&g.known&(g.date<=K)&(g.origin<o)]
            if len(hist)>=MINN:
                m=hist.ratio.quantile(0.8)
                idx=(b.lag==lag)&(b.origin==o)&(b.date_type==t)&b.known
                b.loc[idx,'mult']=m; b.loc[idx,'q80_new']=b.loc[idx,'q80']*m
b['cost0']=cost(b.actual,b.q80); b['cost1']=cost(b.actual,b.q80_new)
b['short0']=(b.actual/CAP-b.q80/CAP).clip(lower=0); b['short1']=(b.actual/CAP-b.q80_new/CAP).clip(lower=0)
b['hit0']=(b.actual<=b.q80); b['hit1']=(b.actual<=b.q80_new)
print('규칙 적용된 행(배수≠1):',(b.mult!=1).sum(),'/ 알려진 무료일 행',b.known.sum())
def summ(x): return pd.Series({'n':len(x),'적용 n':(x.mult!=1).sum(),'비용 전(원)':x.cost0.sum()*1e4,'비용 후(원)':x.cost1.sum()*1e4,'변화%':100*(x.cost1.sum()/x.cost0.sum()-1),'적중률 전':x.hit0.mean(),'적중률 후':x.hit1.mean()})
print('\n전체'); print(b.groupby(['lag','kind']).apply(summ).round(3).to_string())
print('\n유형별 (적용된 것만 의미)'); print(b.groupby(['lag','kind','date_type']).apply(summ).round(3).to_string())
print('\n원점별'); print(b[b.mult!=1].groupby(['lag','kind','origin']).apply(summ).round(3).to_string())
print('\n배수 값'); print(b[b.mult!=1].groupby(['lag','date_type']).mult.agg(['min','median','max','count']).round(2))
b.to_parquet(RES/'t3_rows_v7.parquet')
