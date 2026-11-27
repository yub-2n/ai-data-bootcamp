from pathlib import Path
PACK=Path(__file__).resolve().parent.parent   # 패키지 폴더(code의 상위)
DATA=PACK/'data'; RES=PACK/'results_new'; RES.mkdir(exist_ok=True)
import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
d=pd.read_parquet(DATA/'eval_rows_v7.parquet')
CAP,Cu,Co=2000,60,15
d['need']=d.actual/CAP; d['plan']=d.q80/CAP
d['short']=(d.need-d.plan).clip(lower=0); d['excess']=(d.plan-d.need).clip(lower=0)
d['cost']=Cu*d.short+Co*d.excess; d['hit']=(d.need<=d.plan).astype(int); d['ae']=(d.actual-d.q50).abs()
g3={'평일':'평일·주말','주말':'평일·주말','그 외 공휴일':'공휴일','명절 연휴 무료':'무료 개방일','마지막 수요일':'무료 개방일','종묘대제':'종묘대제'}
d['type3']=d.date_type.map(g3)
def agg(x):
    return pd.Series({'n':len(x),'WAPE':x.ae.sum()/x.actual.sum(),'비용':x.cost.sum(),'적중률':x.hit.mean()})
base=d[(d.method=='나눈 것')]
out=['# 작업 1 결과(v7): 날짜 유형별·개소 유형별 (나눈 것, 1행=직전7일평균, 7행=최종 모형). 비용 단위 만원. 적중률=need<=plan 비율, n은 개소·일 수']
# 재현 검산
x=base[(base.lag=='A')&(base.kind=='격자')]
print('검산 비용',x.groupby('row').cost.sum().round(0).to_dict())
for key,name in [('date_type','세분 날짜 유형'),('group','개소 유형'),('type3','본표 날짜 유형')]:
  for lag in 'AB':
    for kind in ['격자','명절']:
      s=base[(base.lag==lag)&(base.kind==kind)&(base.row.isin([1,7]))]
      t=s.groupby([key,'row']).apply(agg).unstack('row')
      t.columns=[f'{a}{b}' for a,b in t.columns]
      t=t[['n1','WAPE1','WAPE7','비용1','비용7','적중률1','적중률7']].rename(columns={'n1':'n'})
      out.append(f'\n### {name} | 확정시점 {lag} | {kind}\n\n'+t.round(3).to_markdown())

open(RES/'작업1_결과표_v7.md','w').write('\n'.join(out))
