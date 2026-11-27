# 메인 주제 표: 무료 개방일·명절 연휴가 평소 대비 얼마나 많고, 직전 7일 평균이 그것을 얼마나 놓치는가 (백테스트 행 기준)
from pathlib import Path
PACK=Path(__file__).resolve().parent.parent; DATA=PACK/'data'; RES=PACK/'results_new'
import pandas as pd, numpy as np
d=pd.read_parquet(DATA/'eval_rows_v7.parquet'); d=d[d.method=='나눈 것']
CAP,Cu,Co=2000,60,15
d['need']=d.actual/CAP; d['plan']=d.q80/CAP
d['short']=(d.need-d.plan).clip(lower=0); d['excess']=(d.plan-d.need).clip(lower=0); d['cost']=(Cu*d.short+Co*d.excess)*1e4
L=['# 메인 주제 표 (확정 시점별, 격자·명절 따로, 관리소 나눔)\n','배수 = 그 날짜 유형의 개소·일 평균 관람객 ÷ 같은 개소 유형의 평일·주말 평균 관람객(같은 평가 구간). 모자란 몫 = Σ모자란 명수 ÷ Σ필요 명수. 비용은 원.\n']
for lag in 'AB':
  for kind in ['격자','명절']:
    x=d[(d.lag==lag)&(d.kind==kind)]
    ref=x[(x.row==1)&(x.date_type.isin(['평일','주말']))].groupby('group').actual.mean()
    rows=[]
    for dt in ['평일','주말','그 외 공휴일','마지막 수요일','명절 연휴 무료']:
        for g in ['궁','종묘','왕릉']:
            a=x[(x.row==1)&(x.date_type==dt)&(x.group==g)]
            if len(a)==0: continue
            b=x[(x.row==7)&(x.date_type==dt)&(x.group==g)]
            rows.append([dt,g,len(a),f'{a.actual.mean():,.0f}',f'{a.actual.mean()/ref[g]:.2f}',f'{a.short.sum()/a.need.sum()*100:.1f}%',f'{b.short.sum()/b.need.sum()*100:.1f}%',f'{a.cost.sum():,.0f}',f'{b.cost.sum():,.0f}'])
    tot=x[x.row==1]; 
    L.append(f'\n## 확정 시점 {lag} | {kind}\n\n'+pd.DataFrame(rows,columns=['날짜 유형','개소 유형','n(개소·일)','평균 관람객','평소 대비 배수','1행 모자란 몫','7행 모자란 몫','1행 비용(원)','7행 비용(원)']).to_markdown(index=False))
    for lab,sel in [('무료 개방일(명절 무료+마지막 수요일)',['명절 연휴 무료','마지막 수요일'])]:
        a=x[(x.row==1)&x.date_type.isin(sel)]; b=x[(x.row==7)&x.date_type.isin(sel)]; A=x[x.row==1]; B=x[x.row==7]
        L.append(f'\n{lab}: 개소·일 비중 {len(a)/len(A)*100:.1f}%, 방문객 비중 {a.actual.sum()/A.actual.sum()*100:.1f}%, 1행 비용 비중 {a.cost.sum()/A.cost.sum()*100:.1f}%, 7행 비용 비중 {b.cost.sum()/B.cost.sum()*100:.1f}%')
open(RES/'메인주제표.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
