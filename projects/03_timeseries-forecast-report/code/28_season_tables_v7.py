# [v7 신규] 계절별 예측 성능 (평가 날짜 기준 계절: 봄 3~5월, 여름 6~8월, 가을 9~11월, 겨울 12~2월). 날씨·계절 공변량은 쓰지 않았다.
# 입력: eval_rows_v7.parquet  출력: results_new/계절별성능_v7.md   (비용은 원, 소수 인원 기준)
# 해석 주의: 계절 차이는 그 시기의 행사·공휴일·휴관·이력 길이 등과 섞여 있어 날씨의 영향이라고 해석할 수 없다.
import pandas as pd, numpy as np
from common import OUT
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
N=pd.read_parquet(OUT/'eval_rows_v7.parquet'); N['date']=pd.to_datetime(N.date); N['origin']=pd.to_datetime(N.origin)
CAP,CU,CO=2000,600000,150000
def cost(d): n=d.actual/CAP; p=d.q80/CAP; return (CU*(n-p).clip(lower=0)+CO*(p-n).clip(lower=0)).sum()
def wape(d): return (d.actual-d.q50).abs().sum()/d.actual.sum()
def hit(d): return float(((d.actual/CAP)<=(d.q80/CAP)).mean())
SEAS=lambda m:'봄' if m in(3,4,5) else '여름' if m in(6,7,8) else '가을' if m in(9,10,11) else '겨울'
def label(d):
    s=SEAS(d.month)
    if s!='겨울': return f'{d.year} {s}'
    return f'{d.year}-{d.year+1} 겨울' if d.month==12 else f'{d.year-1}-{d.year} 겨울'
N['계절']=N.date.dt.month.map(SEAS); N['계절구간']=N.date.map(label)
def table(x,key,order=None):
    rows=[]
    for k,d in x.groupby(key):
        a=d[d.row==1]; b=d[d.row==7]
        if len(b)==0: continue
        c1,c7=cost(a),cost(b); rows.append((d.date.min(),[k,len(b),f'{wape(a)*100:.1f}% → {wape(b)*100:.1f}%',f'{c1:,.0f}',f'{c7:,.0f}',f'{(c7/c1-1)*100:+.1f}%' if c1>0 else '-',f'{hit(a):.3f} → {hit(b):.3f}']))
    rows=sorted(rows,key=lambda r:(order.index(r[1][0]) if order else r[0]))
    return pd.DataFrame([r[1] for r in rows],columns=[key,'n(개소·일)','WAPE 1행 → 7행','비용 1행(원)','비용 7행(원)','7행 비용 변화','적중률 1행 → 7행'])
L=['# v7 계절별 예측 성능 (평가 날짜 기준, FVA 1행 대 7행, 관리소 나눔)\n','계절은 평가 날짜의 월로 나눴다(봄 3~5월, 여름 6~8월, 가을 9~11월, 겨울 12~2월). 날씨·월·계절 공변량은 모형에 넣지 않았다. **계절별 차이는 그 시기의 행사, 공휴일, 휴관, 학습 이력 길이와 섞여 있으므로 날씨 공변량의 부재 때문이라고 단정하지 않는다.** 정기 격자와 명절 원점은 합치지 않고 따로 낸다.\n',
   '표본 구성 주의: 평가 구간은 2024-07-02~2025-12-29이라 봄(3~5월)은 2025년 하나뿐이고, 겨울은 2024-12, 2025-01~02, 2025-12의 서로 다른 구간이다. 초기 원점(2024년 하반기)은 모형이 본 학습 이력이 18개월 안팎으로 짧다.\n']
ORD=['봄','여름','가을','겨울']
for lag in 'AB':
    for kind in ['격자','명절']:
        x=N[(N.lag==lag)&(N.kind==kind)&(N.row.isin([1,7]))]
        if len(x)==0: continue
        L+=[f'## 확정 시점 {lag} | {kind} | 계절별\n',table(x,'계절',ORD).to_markdown(index=False),'',f'### 확정 시점 {lag} | {kind} | 계절 구간별(연도 구분)\n',table(x,'계절구간').to_markdown(index=False),'']
# ---- 겨울 집중 (2026년 1월과 가장 비슷한 계절) ----
L+=['## 겨울 집중: 2025년 1~2월 (최종 예측 대상인 2026년 1월과 가장 비슷한 계절)\n','2025-01-25~01-30은 설 연휴라 겨울 수치에 명절 효과가 섞인다. 그래서 「전체」와 「명절 연휴 무료일을 뺀 날」을 함께 낸다.\n']
for lag in 'AB':
    x=N[(N.lag==lag)&(N.kind=='격자')&(N.row.isin([1,7]))&(N.date>='2025-01-01')&(N.date<='2025-02-28')].copy()
    if len(x)==0: continue
    x['구분']='2025-01~02 전체'; y=x[x.date_type!='명절 연휴 무료'].copy(); y['구분']='2025-01~02 (설 연휴 무료일 제외)'
    L+=[f'### 확정 시점 {lag} | 격자\n',table(pd.concat([x,y]),'구분',['2025-01~02 전체','2025-01~02 (설 연휴 무료일 제외)']).to_markdown(index=False),'']
    t=x[x.row==7].date_type.value_counts().rename('개소·일').reset_index(); t.columns=['날짜 유형','개소·일']; L+=['2025-01~02 평가 날짜 유형 구성:\n',t.to_markdown(index=False),'']
open(RES/'계절별성능_v7.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L[:14]))
