# [v7] v6와 v7이 공유하는 30개 원점(정기 26 + 명절 4)의 개소·날짜 평가 값 대조 -> results_new/v6_v7_겹침원점_비교.md
# 1·2행(직전 7일 평균)은 결정적이라 같아야 한다. 3~7행(Chronos)은 같은 입력이면 같아야 하므로, 다르다면 실행 환경(GPU·라이브러리 버전 등) 차이이거나 입력 차이다.
# 입력 차이 점검: v7의 무료개방 행사 파일은 정기 휴관 요일도 표시하지만, 05b 는 휴관 예상일이면 무료 행사 표시를 끄므로 모델 공변량은 v6와 같다
#   (일회성 진단: 9개 계열 × 확정 시점 245일 × 전체 날짜 × 공변량 8개의 최대 차이 0. 이 진단에만 이전 행사 파일을 읽기 전용으로 비교에 썼고 v7 결과에는 쓰지 않았다).
import pandas as pd, numpy as np
from common import OUT
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
V6=pd.read_parquet(OUT/'v6_reference'/'eval_rows_v6.parquet'); V7=pd.read_parquet(OUT/'eval_rows_v7.parquet')
for d in (V6,V7): d['origin']=pd.to_datetime(d.origin); d['date']=pd.to_datetime(d.date)
V7=V7[V7.origin.isin(V6.origin.unique())]
k=['lag','row','origin','site','date']; m=V6.merge(V7,on=k,how='outer',suffixes=('_6','_7'),indicator=True)
TOL=1e-6; both=m[m._merge=='both'].copy()
for c in ['q50','q80','actual']: both['d_'+c]=(both[c+'_6']-both[c+'_7']).abs()
both['달라짐']=(both.d_q50>TOL)|(both.d_q80>TOL)
L=['# v6와 v7이 공유하는 30개 원점의 값 대조\n',f'- 키 기준 v6에만 있는 행 {int((m._merge=="left_only").sum())}개, v7에만 있는 행 {int((m._merge=="right_only").sum())}개, 양쪽에 있는 행 {len(both):,}개 (허용 오차 {TOL})',
 '- 입력 점검: v7의 무료개방 행사 파일은 행사 기간의 모든 날짜(정기 휴관 요일 포함)를 표시하지만, 05b 는 휴관 예상일이면 무료 행사 표시를 끄므로 모델에 들어가는 공변량은 v6와 같다(일회성 진단에서 최대 차이 0). 따라서 두 버전의 3~7행이 같아야 하고, 다르다면 실행 환경 차이다.\n']
t=both.groupby(['lag','row']).agg(행수=('달라짐','size'),달라진_행=('달라짐','sum'),q50_최대차이=('d_q50','max'),q80_최대차이=('d_q80','max')).reset_index(); t['달라진_행']=t.달라진_행.astype(int); L+=['## 행별 요약\n',t.round(6).to_markdown(index=False),'']
x=both[both.달라짐]; L+=[f'달라진 행: {len(x)}개 → '+('두 버전의 값이 모두 같다(실행 환경이 달라도 같은 값이 나왔다: v6와 v7은 서로 다른 Colab 세션에서 실행).' if len(x)==0 else '실행 환경 차이 또는 설명되지 않은 차이이므로 확인이 필요하다.'),'']
if len(x): L+=[x.groupby(['lag','row','origin']).agg(행=('달라짐','size'),q80_최대차이=('d_q80','max')).reset_index().round(4).head(40).to_markdown(index=False),'']
open(RES/'v6_v7_겹침원점_비교.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L[:8]))
