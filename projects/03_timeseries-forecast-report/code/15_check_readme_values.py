"""README 검산값 7개 확인(가이드 요구사항 5: 파일을 읽은 직후 확인). 하나라도 다르면 AssertionError.  실행: python 15_check_readme_values.py
(이 스크립트가 문서에서 말하는 '검산값 확인'이다. 02_check_guide.py 는 가이드 예시 문장 50.2%/36.7% 재현용이다.)"""
import json, pandas as pd
from common import OUT
v=pd.read_parquet(OUT/'heritage_visitors_daily.parquet'); w=pd.read_parquet(OUT/'weather_daily.parquet')
c=pd.read_csv(OUT/'calendar_kr_2015_2025.csv'); a=json.load(open(OUT/'anchors.json',encoding='utf-8'))
F=['foreign_en','foreign_ja','foreign_zh','foreign_etc']; z=v[v.total==0]
checks=[('관람객 표 행 수',len(v),62028),('개소 수',v.site.nunique(),23),
 ('개소 수 궁·종묘·왕릉',tuple(v.groupby('group').site.nunique()[['궁','종묘','왕릉']]),(4,1,18)),
 ('total 합계',int(v.total.sum()),119991391),('paid 합계',int(v.paid.sum()),51277728),('free 합계',int(v.free.sum()),68713663),
 ('domestic 합계',int(v.domestic.sum()),95056379),('외국인 4열 합계',int(v[F].sum().sum()),22960148),
 ('total 0인 행',len(z),8832),('total 0인 행 궁·종묘·왕릉',tuple(z.groupby('group').size()[['궁','종묘','왕릉']]),(1951,159,6722)),
 ('날씨 행 수',len(w),92414),('달력 행 수',len(c),4018),('anchors.json 행 수',a['rows'],62028)]
bad=0
for n,got,exp in checks:
    ok=got==exp; bad+=not ok; print('OK  ' if ok else 'FAIL',n,got,'(기대',exp,')')
assert bad==0,f'{bad}개 불일치'; print('\n검산값 모두 일치')
