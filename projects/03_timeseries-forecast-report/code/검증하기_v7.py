"""패키지 구조 검증(v7). 실행: python code/검증하기_v7.py   (Colab 결과로 eval_rows_v7.parquet 를 만든 뒤)
확인: 원점 78+4개, 마지막 평가일, 모든 행의 평가 개소·일 수 동일, 이전 행사 파일 미사용, FVA 표 숫자가 eval_rows 에서 다시 계산한 값과 같은지."""
import hashlib, sys
import pandas as pd
from pathlib import Path
D=Path(__file__).resolve().parent.parent/'data'; R=Path(__file__).resolve().parent.parent/'results_new'
bad=0
def chk(name,ok,info=''):
    global bad; bad+=not ok; print('OK  ' if ok else 'FAIL',name,info)
chk('이전 행사 파일(free_events.csv, 무료개방일_행사_최종.csv)이 data 에 없음',not (D/'free_events.csv').exists() and not (D/'무료개방일_행사_최종.csv').exists())
h=hashlib.md5((D/'free_events_v7.csv').read_bytes()).hexdigest(); chk('free_events_v7.csv 가 제외 대상 이전 파일과 다름',h!='65c55255a8430f2aa89b7cb3002c2863',h)
N=pd.read_parquet(D/'eval_rows_v7.parquet'); N['origin']=pd.to_datetime(N.origin); N['date']=pd.to_datetime(N.date)
g=N[N.kind=='격자']; h4=N[N.kind=='명절']
chk('정기 원점 78개',g.origin.nunique()==78,g.origin.nunique()); chk('명절 원점 4개',h4.origin.nunique()==4,h4.origin.nunique())
chk('정기 첫 원점 2024-07-02, 마지막 2025-12-23',g.origin.min()==pd.Timestamp('2024-07-02') and g.origin.max()==pd.Timestamp('2025-12-23'))
chk('정기 마지막 평가일 <= 2025-12-29',g.date.max()<=pd.Timestamp('2025-12-29'),str(g.date.max().date()))
cnt=N.groupby(['lag','kind','row']).size().unstack('row'); chk('FVA 1~7행의 평가 개소·일 수가 (확정시점, 묶음)마다 같음',(cnt.nunique(axis=1)==1).all()); print(cnt.to_string())
chk('방법은 나눈 것 하나',N.method.unique().tolist()==['나눈 것']); print('전체 행 수',len(N))
CAP,Cu,Co=2000,60,15
def cost(x): n=x.actual/CAP;p=x.q80/CAP; return (Cu*(n-p).clip(lower=0)+Co*(p-n).clip(lower=0)).sum()*1e4
md=(R/'fva_final_tables.md').read_text(encoding='utf-8') if (R/'fva_final_tables.md').exists() else ''
if md:
    for lag in 'AB':
        for kind in ['격자','명절']:
            for r in range(1,8):
                s=f'{cost(N[(N.lag==lag)&(N.kind==kind)&(N.row==r)]):,.0f}'; chk(f'FVA 표 비용 {lag} {kind} {r}행',s in md,s)
print('\n결과:','모두 일치' if bad==0 else f'{bad}개 불일치'); sys.exit(1 if bad else 0)
