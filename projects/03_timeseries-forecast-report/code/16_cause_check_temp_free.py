"""큰 오차(2025-11-04·08·09 등)의 원인 후보 확인: 2025-10-29~11-09 임시 무료 개방. 새 무료개방일 파일에는 이 구간이 없어 모형이 몰랐다.
(1) 데이터로 확인: 경복궁 유료 비중. (2) 모형 오차에서 이 12일이 차지하는 몫(7행, 관리소 나눔, 격자).  실행: python 16_cause_check_temp_free.py
출처(2차, 지정 출처 원문은 열지 못함): 이랜드 매거진 2025-10-17 '국가유산청에 따르면 ... 10월 29일~11월 9일 4대 궁·종묘·조선왕릉·세종대왕유적 무료 개방, 코리아 그랜드 페스티벌 연계(창덕궁 후원 특별관람은 유료)' https://www.eland.co.kr/mgzn/viewMgzn?mgznIdx=1443&categoryIdx=6
        연합뉴스(다음) 2025-10-29 '오늘부터 4대 궁 무료개방(11월 9일까지)' https://v.daum.net/v/20251029122516924?f=p"""
import pandas as pd, numpy as np
from common import OUT
g=pd.read_parquet(OUT/'grid_site_day.parquet'); k=g[g.site=='경복궁'].set_index('date').loc['2025-10-25':'2025-11-13']
k=k.assign(유료비중=(100*k.paid/k.total).round(1))
print('경복궁 유료 비중(%), 휴관일은 NaN\n',k[['paid','free','total','유료비중']].to_string())
d=pd.read_parquet(OUT/'eval_rows_v7.parquet'); d=d[(d.method=='나눈 것')&(d.row==7)].copy(); d['date']=pd.to_datetime(d.date)
CAP,Cu,Co=2000,60,15
d['need']=d.actual/CAP; d['plan']=d.q80/CAP; d['short']=(d.need-d.plan).clip(lower=0); d['excess']=(d.plan-d.need).clip(lower=0); d['cost']=Cu*d.short+Co*d.excess
d['임시무료']=d.date.between('2025-10-29','2025-11-09'); L=['\n## 오차에서 10/29~11/09(12일)가 차지하는 몫 (7행, 관리소 나눔, 격자 78개 원점)']
for lag in 'AB':
    x=d[(d.lag==lag)&(d.kind=='격자')]; a=x[x.임시무료]; t=x.sort_values('short',ascending=False).head(10)
    L.append(f"- 확정시점 {lag}: 개소·일 {len(a)}/{len(x)}({100*len(a)/len(x):.0f}%) → 부족 인원 {100*a.short.sum()/x.short.sum():.1f}%, 비용 {100*a.cost.sum()/x.cost.sum():.1f}%({a.cost.sum():,.0f}/{x.cost.sum():,.0f} 만원), 적중률 {(a.need<=a.plan).mean():.3f}(나머지 포함 전체 {(x.need<=x.plan).mean():.3f}), 모자란 10건 중 {int(t.임시무료.sum())}건")
print('\n'.join(L)); (OUT.parent/'results_new').mkdir(exist_ok=True); open(OUT.parent/'results_new'/'원인확인_임시무료_v7.md','w',encoding='utf-8').write('\n'.join(L))
