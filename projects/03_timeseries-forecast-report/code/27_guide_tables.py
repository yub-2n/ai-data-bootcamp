"""가이드 요구사항 대조용 표 모음(원 단위): ① FVA 표에 '앞 행 대비 줄어든 비용' ② 날짜 유형·개소 유형별 지표(가이드 3묶음 + 세분)
③ 원점별 지표(베이스라인 3개 + 최종 모형) + 학습 구간 날짜 → results_new/가이드요구사항_표모음.md   (입력: eval_rows_v7.parquet, baselines3_rows.parquet(04 실행 결과))"""
import pandas as pd, numpy as np
from common import OUT
RES=OUT.parent/'results_new'; CAP,CU,CO=2000,600000,150000
N=pd.read_parquet(OUT/'eval_rows_v7.parquet'); N=N[N.method=='나눈 것']; B=pd.read_parquet(OUT/'baselines3_rows_v7.parquet')
def cost(d): n=d.actual/CAP; p=d.q80/CAP; return (CU*(n-p).clip(lower=0)+CO*(p-n).clip(lower=0)).sum()
def wape(d): return (d.actual-d.q50).abs().sum()/d.actual.sum()
def hit(d): return ((d.actual/CAP)<=(d.q80/CAP)).mean()
NAMES={1:'직전 7일 평균(운영팀 현재 방식)',2:'+서비스 수준 보정(k)',3:'Chronos-2, 과거 관람객만',4:'+요일·정기 휴관 요일',5:'+공휴일·명절 연휴',6:'+무료 개방일(설·추석 연휴, 마지막 수요일)',7:'+임시 무료 행사(추가 분석)'}
won=lambda x: f'{x:,.0f}'
L=['# 가이드 요구사항 대조용 표 모음 (원 단위, 관리소 나눔 본표)','']
L+=['## 1. FVA 표: 행마다 더한 정보 · 1순위 지표(WAPE) · 비용(원) · 앞 행보다 줄어든 비용(원)','','비용이 늘어난 행은 부호를 +로 남겼다. 이웃 개소 휴관·날씨는 모형에 넣지 않아 행이 없고(날씨는 권고표 날짜에 실측이 없어 쓰지 않음), 따라서 「완벽한 예보 가정」 행도 없다.','']
for lag in 'AB':
    for kind in ['격자','명절']:
        x=N[(N.lag==lag)&(N.kind==kind)]; rows=[]; prev=None; first=None
        for r in sorted(x.row.unique()):
            y=x[x.row==r]; c=cost(y); first=c if first is None else first
            rows.append([r,NAMES[r],f'{wape(y)*100:.1f}%',won(c),'-' if prev is None else f'{(c-prev):+,.0f}',f'{hit(y):.3f}']); prev=c
        L+=[f'### 확정 시점 {lag} | {kind}','',pd.DataFrame(rows,columns=['행','더한 정보','WAPE','비용(원)','앞 행 대비 비용 변화(원, −는 줄어듦)','적중률']).to_markdown(index=False),'']
L+=['## 2. 날짜 유형별 · 개소 유형별 (1행 = 직전 7일 평균, 7행 = 최종 모형)','','가이드의 날짜 유형 3묶음 = 평일·주말 / 공휴일 / 무료 개방일. 우리는 무료 개방일을 마지막 수요일과 명절 연휴 무료로, 평일·주말을 따로 세분해 함께 적는다.','']
G3={'평일':'평일·주말','주말':'평일·주말','그 외 공휴일':'공휴일','마지막 수요일':'무료 개방일','명절 연휴 무료':'무료 개방일'}
def tab(x,key):
    rows=[]
    for k,d in x.groupby(key):
        a=d[d.row==1]; b=d[d.row==7]
        rows.append([k,len(b),f'{wape(a)*100:.1f}% → {wape(b)*100:.1f}%',f'{hit(a):.3f} → {hit(b):.3f}',won(cost(a)),won(cost(b)),won(cost(a)-cost(b))])
    return pd.DataFrame(rows,columns=[key if isinstance(key,str) else '유형','n(개소·일)','WAPE 1행 → 7행','적중률 1행 → 7행','비용 1행(원)','비용 7행(원)','줄어든 비용(원)'])
for lag in 'AB':
    for kind in ['격자','명절']:
        x=N[(N.lag==lag)&(N.kind==kind)&(N.row.isin([1,7]))].copy(); x['가이드 3묶음']=x.date_type.map(G3)
        L+=[f'### 확정 시점 {lag} | {kind} | 날짜 유형 (가이드 3묶음)','',tab(x,'가이드 3묶음').to_markdown(index=False),'',f'### 확정 시점 {lag} | {kind} | 날짜 유형 (세분)','',tab(x,'date_type').to_markdown(index=False),'',f'### 확정 시점 {lag} | {kind} | 개소 유형','',tab(x,'group').to_markdown(index=False),'']
L+=['## 3. 원점별 지표 (WAPE) — 베이스라인 3개와 최종 모형, 확정 시점 A','','나이브·계절 나이브·직전 7일 평균은 `04_baselines3_compare.py` 결과(계절 나이브는 값이 없는 날이 있어 n이 조금 적음). 최종 모형은 7행. B 열은 확정 시점 B의 7행. 학습 구간: 모든 개소 2023-01-01부터(2023~2025년만 사용) A는 원점 전날, B는 원점 7일 전까지. 코로나 기간은 처음부터 포함하지 않는다.','']
def w(d,m): d=d.dropna(subset=[m]); return (d.actual-d[m]).abs().sum()/d.actual.sum()
rows=[]
for (kind,o),d in B.groupby(['kind','origin']):
    a6=N[(N.lag=='A')&(N.row==7)&(N.origin==o)&(N.kind==kind)]; b6=N[(N.lag=='B')&(N.row==7)&(N.origin==o)&(N.kind==kind)]
    rows.append([kind,o.strftime('%Y-%m-%d'),(o-pd.Timedelta(days=1)).strftime('%Y-%m-%d'),(o-pd.Timedelta(days=7)).strftime('%Y-%m-%d'),f"{w(d,'나이브')*100:.1f}%",f"{w(d,'계절나이브')*100:.1f}%",f"{w(d,'직전7일평균')*100:.1f}%",f'{wape(a6)*100:.1f}%',f'{wape(b6)*100:.1f}%'])
L+=[pd.DataFrame(rows,columns=['묶음','원점','학습 끝(A)','학습 끝(B)','나이브','계절 나이브','직전 7일 평균','최종 모형 7행(A)','최종 모형 7행(B)']).to_markdown(index=False),'']
open(RES/'가이드요구사항_표모음.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L[:60]))
