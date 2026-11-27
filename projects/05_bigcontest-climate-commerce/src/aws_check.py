"""
강남 호우 사건을 서울 ASOS(108) 대신 강남 AWS(400)로 잡았을 때 결과 비교 (src/aws_check.py)
- 프로젝트 폴더에서 실행: python3 -B src/aws_check.py
- 파일을 저장하지 않고 화면에만 출력합니다. event_study.py, prep.py를 그대로 불러 씁니다.
- 필요 파일: data/external/강남_AWS.csv (기상자료개방포털 방재기상관측 AWS 일자료, 지점 400)
"""
import sys, io, contextlib, warnings
sys.path.insert(0,'src'); warnings.filterwarnings('ignore')
import pandas as pd, numpy as np
import event_study as es, prep
with contextlib.redirect_stdout(io.StringIO()):
    base = es.load_all()
def fmt(r): return ' '.join(f"{k} {v[0]:.1f} [{v[1]:.1f},{v[2]:.1f}]" for k,v in r.items())
aws = pd.read_csv('data/external/강남_AWS.csv',encoding='cp949',dtype=str)
aws['date']=pd.to_datetime(aws['일시'])
aws=aws.set_index('date').reindex(prep.DAYS)
a=base['asos'].copy()
m=a['region']=='서울'
idx=a.loc[m,'date']
print('AWS 누락일:', list(aws.index[aws['일강수량(mm)'].isna()].date))
for src,dst in [('평균기온(°C)','tavg'),('최저기온(°C)','tmin'),('최고기온(°C)','tmax'),('일강수량(mm)','rain')]:
    a.loc[m,dst]=pd.to_numeric(aws[src],errors='coerce').reindex(idx).values
a.loc[m,'r1h']=np.nan
with contextlib.redirect_stdout(io.StringIO()):
    ev2=prep.build_event_table(a)
d2=dict(base); d2['asos']=a; d2['ev']=ev2
for nm,ev in [('108(ASOS)',base['ev']['서울']),('400(AWS)',ev2['서울'])]:
    print(nm,'사건',[(str(s.date()),str(e.date())) for s,e in ev['events']])
    print('  남는',len(ev['kept']),'뺀',[(str(s.date()),str(e.date())) for s,e in ev['dropped']],'표본일',int(ev['D']['sample'].sum()))
print('hot days 108/400:',int((base['asos'].query("region=='서울'").tmax>=33).sum()),int((a[m].tmax>=33).sum()))
for lab,d in [('108',base),('400',d2)]:
    print('==',lab)
    print(' 강남 외지인 83합계', fmt(es.main_model(d,'강남')))
    print(' 강남 전체   83합계', fmt(es.main_model(d,'강남',seg='all')))
    for g in es.GROUP_NAMES:
        print(' ',g, fmt(es.main_model(d,'강남',g)))
