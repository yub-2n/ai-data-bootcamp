# 새 무료개방일 파일(covariates_free_open.csv)을 실제 관람객 기록으로 검증한다. (출처 문서는 파일을 만든 사람이 밝혀야 하고, 이 스크립트는 "데이터와 맞는가"만 확인한다.)
import pandas as pd
from common import OUT
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
h=pd.read_parquet(OUT/'heritage_visitors_daily.parquet'); h=h[(h.total>0)&(h.date>='2023-01-01')].copy(); h['fs']=h.free/h.total
cv=pd.read_csv(OUT/'covariates_free_open.csv',parse_dates=['timestamp']).rename(columns={'item_id':'site','timestamp':'date'})
m=h.merge(cv,on=['site','date']); m['grp']=m.site.map(lambda s:'궁' if s in['경복궁','덕수궁','창경궁','창덕궁'] else '종묘' if s=='종묘' else '왕릉')
L=['# 무료개방일 파일 검증 (실제 관람객 기록의 무료 비중 = free ÷ total, 문 연 개소·일, 2023-01-01~2025-12-31)\n',
   '파일의 표시가 데이터와 맞는지만 확인한다. 이 파일을 만든 근거 문서(공지·보도자료)는 데이터로 알 수 없다.\n']
rows=[]
for c,name in [('free_holiday','명절 연휴 무료(free_holiday)'),('free_last_wed','마지막 수요일(free_last_wed)'),('free_jongmyo_daeje','종묘대제(free_jongmyo_daeje)')]:
    for g in ['궁','종묘','왕릉']:
        a=m[(m.grp==g)&(m[c]==1)]; b=m[(m.grp==g)&(m[c]==0)]
        if len(a)==0: continue
        rows.append([name,g,len(a),f'{a.fs.mean():.3f}',f'{a.fs.median():.3f}',len(b),f'{b.fs.mean():.3f}'])
L.append('## 1. 표시한 날 대 표시하지 않은 날의 무료 비중\n'); L.append(pd.DataFrame(rows,columns=['표시','개소 유형','표시한 개소·일','무료 비중 평균','중앙값','표시 안 한 개소·일','그날들의 무료 비중 평균']).to_markdown(index=False))
core=m[m.site.isin(['경복궁','덕수궁','창경궁','창덕궁','종묘'])].copy(); core['flag']=core[['free_holiday','free_last_wed','free_jongmyo_daeje']].max(axis=1)
u=core[(core.flag==0)&(core.fs>=0.9)]
d=u.groupby('date').site.agg(lambda s:', '.join(sorted(s))).reset_index(); d.columns=['날짜','무료 비중 0.9 이상인데 표시 없는 4대궁·종묘']
L.append('\n## 2. 무료 비중이 0.9 이상인데 표시가 없는 날 (4대궁·종묘만; 왕릉은 원래 거의 무료인 개소가 있어 제외)\n')
L.append(d.to_markdown(index=False)); L.append('\n원인은 이 표만으로 알 수 없다. 2025-10-30~11-09는 임시 무료 개방(궁능유적본부 공지 확인, 7.2장), 2024-05-15~19는 이전 파일에 임시 무료로 있던 날(원인 미확인), 나머지는 원인 미확인.')
f=core[(core.flag==1)&(core.fs<0.9)]
L.append(f'\n## 3. 표시했는데 무료 비중이 0.9 미만인 개소·일: {len(f)}건 (창덕궁 후원 특별관람 등 유료 관람이 섞인 경우가 대부분인지는 미확인)\n')
L.append(f.groupby('site').size().rename('건수').reset_index().to_markdown(index=False))
(RES/'무료개방일파일_검증.md').write_text('\n'.join(L),encoding='utf-8'); print('\n'.join(L[:12]))
