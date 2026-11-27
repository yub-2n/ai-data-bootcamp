# [v7] Chronos 없이 계산되는 부분: 베이스라인 3개 비교 + FVA 1·2행(A/B) -> results_new/베이스라인3개_v7.md, FVA_1_2행_부분결과_v7.md
# (3~7행은 Colab 결과가 필요하다. 이 파일의 결과는 '부분 결과'이며 FVA 전체 표는 최종FVA표_만들기.py 가 만든다.)
import importlib.util, pandas as pd, numpy as np
from common import OUT, CODE
spec=importlib.util.spec_from_file_location('m07',CODE/'07_timing_direct_compare.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True); CAP,CU,CO=2000,60,15
def met(d,col):
    d=d.dropna(subset=[col]); need=d.actual/CAP; plan=d[col]/CAP; c=CU*(need-plan).clip(lower=0)+CO*(plan-need).clip(lower=0)
    return pd.Series({'n':len(d),'WAPE':(d.actual-d[col]).abs().sum()/d.actual.sum(),'비용(원)':c.sum()*1e4,'적중률':(need<=plan).mean()})
# ---- 베이스라인 3개 (확정 시점 A 기준, 04 결과) ----
B=pd.read_parquet(OUT/'baselines3_rows_v7.parquet'); M=['나이브','계절나이브','직전7일평균']; L=['# 베이스라인 3개 비교 (v7, 확정 시점 A, 비용은 소수 인원 기준, 원)\n','계절 나이브는 정기 휴관 요일에 공휴일이라 문을 연 날 등 참고할 과거 개방일이 없으면 값이 없어 평가 행이 적다. 그래서 「세 방법 모두 값이 있는 같은 행」 표를 함께 낸다.\n']
for kind in ['격자','명절']:
    d=B[B.kind==kind]; common=d.dropna(subset=M)
    for scope,x in [('전체(방법별 가능한 모든 행)',d),('공통 행(세 방법 모두 값이 있는 행)',common),('무료 개방일·공휴일 제외(공통 행)',common[~common.special])]:
        t=pd.DataFrame({k:met(x,k) for k in M}).T; t['n']=t.n.astype(int); t['WAPE']=(t.WAPE*100).round(1).astype(str)+'%'; t['비용(원)']=t['비용(원)'].map('{:,.0f}'.format); t['적중률']=t['적중률'].round(3)
        L+=[f'## {kind} | {scope}\n',t.to_markdown(),'']
open(RES/'베이스라인3개_v7.md','w',encoding='utf-8').write('\n'.join(L))
# ---- FVA 1·2행 (A/B) ----
L=['# FVA 1·2행 부분 결과 (v7, Chronos 없이 계산되는 행만)\n','1행 = 직전 7일 평균, 2행 = 평균 × 서비스수준 보정 k(지난 12주 0.8 분위수). 직전 7일 평균이 없는 개소·원점은 평가에서 제외했다(12번 스크립트와 같은 규칙).\n']
KEY=['origin','site','date']; allrows=[]
for lag in 'AB':
    b=m.baseline(1 if lag=='A' else 7); bad=b[b.q50.isna()][KEY].drop_duplicates(); good=b.dropna(subset=['q50']); 
    L.append(f'- 확정 시점 {lag}: 직전 7일 평균이 없어 제외한 (원점, 개소, 날짜) {len(bad)}개 ({", ".join(sorted({f"{o.date()} {s}" for o,s in zip(bad.origin,bad.site)}))})')
    for r,col in [(1,'q50'),(2,'q80')]:
        x=good.copy(); x['pl']=x[col]
        x['lag']=lag; x['row']=r; allrows.append(x.assign(pl=x[col]))
A=pd.concat(allrows); rows=[]
for (lag,kind,r),d in A.groupby(['lag','kind','row']):
    s=met(d.assign(q50x=d.q50,plx=d.pl),'plx'); s['WAPE']=(d.actual-d.q50).abs().sum()/d.actual.sum(); rows.append([lag,kind,r,int(s.n),f'{s.WAPE*100:.1f}%',f'{s["비용(원)"]:,.0f}',f'{s.적중률:.3f}'])
L+=['\n'+pd.DataFrame(rows,columns=['확정시점','묶음','행','n(개소·일)','WAPE','비용(원)','적중률']).to_markdown(index=False)]
SE=lambda mo:'봄' if mo in(3,4,5) else '여름' if mo in(6,7,8) else '가을' if mo in(9,10,11) else '겨울'
A['계절']=A.date.dt.month.map(SE); rows=[]
for (lag,r,se),d in A[A.kind=='격자'].groupby(['lag','row','계절']):
    s=met(d.assign(plx=d.pl),'plx'); rows.append([lag,r,se,int(s.n),f'{(d.actual-d.q50).abs().sum()/d.actual.sum()*100:.1f}%',f'{s["비용(원)"]:,.0f}',f'{s.적중률:.3f}'])
L+=['\n## 계절별 1·2행 (격자 78개 원점, 평가 날짜 기준 계절; 7행 포함 전체 계절 표는 28번 스크립트)\n',pd.DataFrame(rows,columns=['확정시점','행','계절','n','WAPE','비용(원)','적중률']).to_markdown(index=False)]
open(RES/'FVA_1_2행_부분결과_v7.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L[:12]))
