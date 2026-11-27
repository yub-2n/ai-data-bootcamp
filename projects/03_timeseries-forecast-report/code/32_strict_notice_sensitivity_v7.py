# [v7] 설·추석 무료개방 공지 시점 엄격 적용 민감도 (확정 시점 A만).
# 대상: 공지날짜가 A 확정 시점(원점 전날)보다 늦은 설·추석 무료일이 예측 구간에 든 원점 = 2024-09-10, 2025-01-21 (23번 스크립트 결과, 공지가 원점 당일).
# Colab: 05b --lag A --rows 6,7 --notice --strict-fh --origin 2024-09-10,2025-01-21 --out chronos_series_A_v7_strictfh.parquet  (공지 전 날짜의 설·추석 무료 표시를 끈다)
# 비교: 기본(달력 규칙으로 미리 안다고 보는 정식 결과, eval_rows_v7) 대 엄격(공지 이후에만 인정). 입력: data/chronos_series_A_v7_strictfh.parquet
import importlib.util, pandas as pd, numpy as np
from common import OUT, CODE
spec=importlib.util.spec_from_file_location('m07',CODE/'07_timing_direct_compare.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True); CAP,CU,CO=2000,60,15
S=m.chronos_rows('series','A','_v7_strictfh'); S['origin']=pd.to_datetime(S.origin); S['date']=pd.to_datetime(S.date)
E=pd.read_parquet(OUT/'eval_rows_v7.parquet'); E['origin']=pd.to_datetime(E.origin); E['date']=pd.to_datetime(E.date)
E=E[(E.lag=='A')&E.origin.isin(S.origin.unique())&E.row.isin(S.row.unique())]
k=['row','origin','site','date']; M=E.merge(S[k+['q50','q80']],on=k,suffixes=('','_엄격'),how='inner')     # 공통 평가 집합(제외행 반영)만
assert len(M)==len(E), '엄격 기준 결과에 없는 평가 행이 있다'
def cost(a,p): n=a/CAP; pl=p/CAP; return (CU*(n-pl).clip(lower=0)+CO*(pl-n).clip(lower=0)).sum()*1e4
rows=[]
for (r,o),d in M.groupby(['row','origin']):
    cb,cs=cost(d.actual,d.q80),cost(d.actual,d.q80_엄격); rows.append([r,o.date(),len(d),int((abs(d.q80-d.q80_엄격)>1e-6).sum()),f'{cb:,.0f}',f'{cs:,.0f}',f'{(cs/cb-1)*100:+.1f}%',f'{((d.actual/CAP)<=(d.q80/CAP)).mean():.3f}',f'{((d.actual/CAP)<=(d.q80_엄격/CAP)).mean():.3f}'])
t=pd.DataFrame(rows,columns=['행','원점','평가 개소·일','q80이 달라진 행','비용 기본(원)','비용 엄격(원)','엄격-기본','적중률 기본','적중률 엄격'])
tot=[]
for r,d in M.groupby('row'):
    cb,cs=cost(d.actual,d.q80),cost(d.actual,d.q80_엄격); tot.append([r,len(d),f'{cb:,.0f}',f'{cs:,.0f}',f'{(cs/cb-1)*100:+.1f}%'])
L=['# 설·추석 무료개방 공지 시점 엄격 적용 민감도 (v7, 확정 시점 A, 해당 2개 원점)\n','공지날짜가 확정 시점(원점 전날)보다 늦은 설·추석 무료일이 예측 구간에 든 원점(2024-09-10: 추석 2024 공지 09-10, 2025-01-21: 설 2025 공지 01-21)에서, 설·추석 무료 표시를 「공지 이후에만 인정」하는 엄격 기준으로 6·7행을 다시 예측해 정식 결과와 비교한다. 정식 결과는 설·추석 연휴를 달력 규칙으로 미리 아는 정보로 처리한다.\n','## 원점별\n',t.to_markdown(index=False),'','## 두 원점 합계(정기 원점 합산이 아니라 이 2개 원점만)\n',pd.DataFrame(tot,columns=['행','평가 개소·일','비용 기본(원)','비용 엄격(원)','엄격-기본']).to_markdown(index=False),'','해석: 엄격 기준에서 값이 달라지면 정식 결과가 공지 전 정보를 미리 알고 있었다는 뜻이다. 차이의 크기는 위 표를 그대로 읽는다.']
open(RES/'공지시점_엄격기준_민감도_v7.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L[:12]))
