# [v7] v6와 v7 핵심 지표 나란히 비교 -> results_new/v6_v7_비교표.md
# v6 = 정기 26개 원점(2025-07-01~12-23), v7 = 정기 78개 원점(2024-07-02~2025-12-23). 두 버전은 서로 다른 평가 기간을 쓰는 독립된 분석이다(이 표는 v7을 보조 분석으로 취급하려는 것이 아니다).
# 입력: data/v6_reference/eval_rows_v6.parquet (v6 평가 표), eval_rows_v7.parquet, (있으면) 권고표_2026-01-01_long.csv
import pandas as pd, numpy as np, os
from common import OUT
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
V6=pd.read_parquet(OUT/'v6_reference'/'eval_rows_v6.parquet'); V7=pd.read_parquet(OUT/'eval_rows_v7.parquet')
CAP,Cu,Co=2000,60,15
def cst(d): n=d.actual/CAP;p=d.q80/CAP; return (Cu*(n-p).clip(lower=0)+Co*(p-n).clip(lower=0)).sum()
def wape(d): return (d.actual-d.q50).abs().sum()/d.actual.sum()
def hit(d): return float(((d.actual/CAP)<=(d.q80/CAP)).mean())
def summ(N,lag,kind):
    x=N[(N.lag==lag)&(N.kind==kind)]; out={}
    for r in range(1,8):
        y=x[x.row==r]; out[r]=dict(n=len(y),wape=wape(y),cost=cst(y)/1e4,hit=hit(y))
    b=out[1]['cost']
    for r in out: out[r]['sav']=(out[r]['cost']/b-1)*100
    return out
L=['# v6 대 v7 핵심 지표 비교 (비용은 억 원, 소수 인원 기준, 관리소 나눔)\n','- v6: 정기 원점 26개(2025-07-01~12-23) + 명절 4개. v7: 정기 원점 78개(2024-07-02~2025-12-23) + 명절 4개.\n- 두 버전은 평가 기간이 다른 독립된 완성 분석이다. 정기 격자와 명절은 합치지 않는다.\n- v7은 Chronos 결과를 82개 원점 전부 새로 실행해서 쓴다. 명절 4개 원점은 v6와 같은 원점이다. 무료개방 행사 파일은 휴관 요일도 표시하도록 바뀌었지만(free_events_v7.csv) 05b의 「휴관 예상일이면 무료 표시를 끈다」 처리 때문에 모델 입력은 바뀌지 않았다(31번 스크립트 참고).\n']
for lag in 'AB':
    for kind in ['격자','명절']:
        a=summ(V6,lag,kind); b=summ(V7,lag,kind)
        rows=[[r,f'{a[r]["n"]:,}',f'{a[r]["wape"]*100:.1f}%',f'{a[r]["cost"]:.2f}',f'{a[r]["sav"]:+.1f}%',f'{a[r]["hit"]:.3f}',f'{b[r]["n"]:,}',f'{b[r]["wape"]*100:.1f}%',f'{b[r]["cost"]:.2f}',f'{b[r]["sav"]:+.1f}%',f'{b[r]["hit"]:.3f}'] for r in range(1,8)]
        L+=[f'## 확정 시점 {lag} | {kind}\n',pd.DataFrame(rows,columns=['행','v6 n','v6 WAPE','v6 비용','v6 1행 대비','v6 적중률','v7 n','v7 WAPE','v7 비용','v7 1행 대비','v7 적중률']).to_markdown(index=False),'']
L+=['## 핵심 비교 (A 정기 격자)\n']
a=summ(V6,'A','격자'); b=summ(V7,'A','격자'); pr=lambda s,x,y:f'{(s[y]["cost"]/s[x]["cost"]-1)*100:+.1f}%'
L+=[pd.DataFrame([['1→7행 비용 변화',pr(a,1,7),pr(b,1,7)],['2→7행',pr(a,2,7),pr(b,2,7)],['5→6행',pr(a,5,6),pr(b,5,6)],['6→7행',pr(a,6,7),pr(b,6,7)],['7행 WAPE',f'{a[7]["wape"]*100:.1f}%',f'{b[7]["wape"]*100:.1f}%'],['7행 적중률',f'{a[7]["hit"]:.3f}',f'{b[7]["hit"]:.3f}']],columns=['지표','v6','v7']).to_markdown(index=False),'']
rows=[]
for kind in ['격자','명절']:
    for nm,N in [('v6',V6),('v7',V7)]:
        rows.append([kind,nm]+[f'{(cst(N[(N.lag=="B")&(N.kind==kind)&(N.row==r)])/cst(N[(N.lag=="A")&(N.kind==kind)&(N.row==r)])-1)*100:+.1f}%' for r in (1,6,7)])
L+=['## A 대비 B 비용 (B가 A보다)\n',pd.DataFrame(rows,columns=['묶음','버전','1행','6행','7행']).to_markdown(index=False),'']
p=RES/'권고표_2026-01-01_long.csv'; q=OUT/'v6_reference'/'권고표_2026-01-01_long_v6.csv'
if p.exists() and q.exists():
    n7=pd.read_csv(p,encoding='utf-8-sig'); n6=pd.read_csv(q,encoding='utf-8-sig'); k=['site','date']; m=n6.merge(n7,on=k,suffixes=('_6','_7'))
    rows=[['정수 인원 합(7행 q80)',int(n6.정수인원_q80.sum()),int(n7.정수인원_q80.sum())],['직전 7일 평균(1행)',int(n6.직전7일평균_정수인원.sum()),int(n7.직전7일평균_정수인원.sum())],['서비스수준 보정(2행)',int(n6.직전7일평균_보정_정수인원.sum()),int(n7.직전7일평균_보정_정수인원.sum())],['소수 인원 합(7행 q80)',round(n6.소수인원_q80.sum(),1),round(n7.소수인원_q80.sum(),1)],['정수 인원이 달라진 개소·일',0,int((m.정수인원_q80_6!=m.정수인원_q80_7).sum())],['소수 인원 최대 차이',0,round(float((m.소수인원_q80_6-m.소수인원_q80_7).abs().max()),4)]]
    L+=['## 2026-01-01~07 권고표 (A, 7행)\n',pd.DataFrame(rows,columns=['항목','v6','v7']).to_markdown(index=False),'','같은 학습 데이터·같은 달력이고 행사 파일 변경이 모델 입력을 바꾸지 않으므로 같은 값이 나올 것으로 예상하지만, 가정하지 않고 위 표의 실제 계산값으로 판단한다.','']
else: L+=['## 2026-01-01~07 권고표\n','(권고표 v7 결과 파일이 아직 없다: Colab 실행 후 14번 스크립트 실행)\n']
open(RES/'v6_v7_비교표.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L[:10]))
