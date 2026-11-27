# 6.6 확정 시점 A vs B (원점 재추출 95% 구간)를 eval_rows_v7.parquet 로 만든다. 출력: results_new/AB비교.md  (v6: 개소별 직접 비교는 하지 않음)
from pathlib import Path
PACK=Path(__file__).resolve().parent.parent; DATA=PACK/'data'; RES=PACK/'results_new'
import pandas as pd, numpy as np
N=pd.read_parquet(DATA/'eval_rows_v7.parquet'); CAP,Cu,Co=2000,60,15
def cst(d): n=d.actual/CAP;p=d.q80/CAP; return (Cu*(n-p).clip(lower=0)+Co*(p-n).clip(lower=0)).sum()
x=N[(N.kind=='격자')&(N.method=='나눈 것')]; orig=sorted(x.origin.unique())
c={(l,r,o):cst(x[(x.lag==l)&(x.row==r)&(x.origin==o)]) for l in 'AB' for r in range(1,8) for o in orig}
NM={1:'1 직전 7일 평균',2:'2 서비스수준 보정',3:'3 Chronos-2',4:'4 + 휴관 규칙',5:'5 + 공휴일·명절',6:'6 + 무료개방일',7:'7 + 임시 무료 행사'}
rng=np.random.default_rng(0); idx=[rng.integers(0,len(orig),len(orig)) for _ in range(5000)]
L=['# 6.6 확정 시점 A vs B (격자 78개, 관리소 나눔, 비용 만원, 구간 = 원점 78개 재추출 5,000회 95%)\n','A·B 모두 가이드의 달력 규칙(설·추석 연휴, 마지막 수요일)대로 무료 개방 표시를 그대로 쓴 값이다(2023-01-01 이후 데이터만 사용).\n','| 행 | A 비용 | B 비용 | B가 A보다 | 구간 |','|---|---|---|---|---|']
for r in range(1,8):
    f=lambda ii: sum(c[('B',r,orig[i])] for i in ii)/sum(c[('A',r,orig[i])] for i in ii)-1
    a=sum(c[('A',r,o)] for o in orig); b=sum(c[('B',r,o)] for o in orig); bs=np.percentile([f(i) for i in idx],[2.5,97.5])*100
    L.append(f'| {NM[r]} | {a:,.0f} | {b:,.0f} | {(b/a-1)*100:+.1f}% | [{bs[0]:+.1f}, {bs[1]:+.1f}] |')
open(RES/'AB비교.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
