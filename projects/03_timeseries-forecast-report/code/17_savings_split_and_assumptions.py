# 절감액 분해(원) + 가정 바꾸기(백테스트·권고표). 실행: python 17_savings_split_and_assumptions.py
from pathlib import Path
PACK=Path(__file__).resolve().parent.parent; DATA=PACK/'data'; RES=PACK/'results_new'; RES.mkdir(exist_ok=True)
import pandas as pd, numpy as np
N=pd.read_parquet(DATA/'eval_rows_v7.parquet'); N=N[N.method=='나눈 것']
def cost(d,CAP=2000,Cu=60,Co=15):
    n=d.actual/CAP; p=d.q80/CAP
    return (Cu*(n-p).clip(lower=0)+Co*(p-n).clip(lower=0)).sum()*1e4   # 만원 -> 원
def split(lag,kind,**kw):
    x=N[(N.lag==lag)&(N.kind==kind)]; c={r:cost(x[x.row==r],**kw) for r in (1,2,7)}
    return c[1],c[1]-c[2],c[2]-c[7],c[1]-c[7]
L=['# 절감액 분해와 가정 바꾸기 (원, 관리소 나눔, 비용 = Cu×모자란 명수 + Co×남는 명수, 소수 인원 그대로)\n']
f=lambda v:f'{v:,.0f}'
rows=[]
for lag in 'AB':
    for kind in ['격자','명절']:
        c1,s12,s26,t=split(lag,kind)
        rows.append([lag,kind,f(c1),f(s12),f'{s12/c1*100:.1f}%',f(s26),f'{s26/c1*100:.1f}%',f(t),f'{t/c1*100:.1f}%'])
L.append('## 1. 기본 가정(Cu 60만, Co 15만, 1명=2,000명, 서비스 수준 0.8) 절감액 분해\n')
L.append(pd.DataFrame(rows,columns=['확정시점','묶음','직전7일평균 비용(원)','서비스수준 보정 절감(1→2행)','비율','모형 추가 절감(2→7행)','비율','총 절감(1→7행)','비율']).to_markdown(index=False))
L.append('\n격자 78개 원점과 명절 4개 원점은 합치지 않았습니다.\n')
rows=[]
for lab,kw in [('기본',{}),('1명이 맡는 관람객 1,500명',{'CAP':1500}),('1명이 맡는 관람객 2,500명',{'CAP':2500}),('Cu 30만(Co 15만)',{'Cu':30}),('Cu 90만(Co 15만)',{'Cu':90}),('Co 30만(Cu 60만)',{'Co':30})]:
    for lag in 'AB':
        c1,s12,s26,t=split(lag,'격자',**kw)
        rows.append([lab,lag,f(c1),f(s12),f(s26),f(t),f'{t/c1*100:.1f}%'])
L.append('## 2. 가정을 바꾼 백테스트 비용 (격자 78개 원점, 7행 모형(최종))\n')
L.append(pd.DataFrame(rows,columns=['가정','확정시점','직전7일평균 비용(원)','서비스수준 보정 절감','모형 추가 절감','총 절감','1행 대비']).to_markdown(index=False))
L.append('\n- 1명이 맡는 관람객 수를 바꾸면 인력 수(예측÷CAP)와 필요 인력(실제÷CAP)이 같이 바뀌므로 위 값은 정확한 재계산입니다.\n- Cu·Co를 바꾼 값은 **인력 수를 기본(0.8 분위수)에 그대로 둔 채 비용 단가만 바꾼 값**입니다. 비용 단가가 바뀌면 최적 서비스 수준은 Cu/(Cu+Co)로 달라지는데(Cu 30 → 0.67, Cu 90 → 0.86, Co 30 → 0.67), 그 분위수로 다시 정한 인력 수의 백테스트는 아직 하지 않았습니다(필요하면 Colab에서 해당 분위수 열이 필요).\n')
# 권고표 민감도
R=pd.read_csv(RES/'권고표_2026-01-01_long.csv',encoding='utf-8-sig')
import math
def ceil_rule(v,closed): 
    return np.where(closed==1,0,np.where(v>0,np.maximum(1,np.ceil(v-1e-9)),0))
rows=[]
for lag in 'A':
    r=R[R.확정시점==lag]; cl=r.휴관예상.values
    base=r['직전7일평균_소수인원'].values
    for lab,col,cap in [('기본 q80, 2,000명','소수인원_q80',2000),('서비스 수준 0.7','소수인원_q70',2000),('서비스 수준 0.9','소수인원_q90',2000),('q80, 1명 1,500명','소수인원_q80',1500),('q80, 1명 2,500명','소수인원_q80',2500)]:
        v=r[col].values*2000/cap; b=base*2000/cap
        rows.append([lag,lab,int(ceil_rule(v,cl).sum()),int(ceil_rule(b,cl).sum()),round(float(np.where(cl==1,0,v).sum()),1)])
L.append('## 3. 권고표(2026-01-01~07, 7행 A)가 가정에 따라 달라지는 정도 (정수 인원 주간 합, 올림 규칙)\n')
L.append(pd.DataFrame(rows,columns=['확정시점','가정','모형 정수 인원 합','직전7일평균(1행, 같은 규칙) 정수 인원 합','모형 소수 인원 합']).to_markdown(index=False))
L.append('\n서비스 수준을 바꿀 때 직전 7일 평균은 기준(1행)이라 그대로입니다. 2행(서비스수준 보정)을 0.7·0.9로 다시 맞춘 값은 계산하지 않았습니다.')
open(RES/'절감액분해_가정바꾸기.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
