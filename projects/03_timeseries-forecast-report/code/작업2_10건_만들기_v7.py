from pathlib import Path
PACK=Path(__file__).resolve().parent.parent   # 패키지 폴더(code의 상위)
DATA=PACK/'data'; RES=PACK/'results_new'; RES.mkdir(exist_ok=True)
import pandas as pd, numpy as np
pd.set_option('display.width',250); pd.set_option('display.max_columns',30)
D=DATA
d=pd.read_parquet(D/'eval_rows_v7.parquet'); cal=pd.read_csv(DATA/'cal.csv'); cv=pd.read_csv(D/'covariates_free_open.csv')
CAP,Cu,Co=2000,60,15
d['need']=d.actual/CAP; d['plan']=d.q80/CAP; d['short']=(d.need-d.plan).clip(lower=0)
d['ratio']=d.actual/d.q80
b=d[(d.method=='나눈 것')&(d.row==7)].copy()
b['date']=pd.to_datetime(b.date); b['origin']=pd.to_datetime(b.origin)
cv['timestamp']=pd.to_datetime(cv.timestamp)
cal['date']=pd.to_datetime(cal.date); cald=cal.set_index('date')
out=[]
for lag in 'AB':
  for kind in ['격자','명절']:
    x=b[(b.lag==lag)&(b.kind==kind)]
    assert not x.duplicated(['site','date']).any(), (lag,kind,'중복')
    top=x.sort_values('short',ascending=False).head(10).copy()
    # 같은 날 같은 개소 유형의 중앙 actual/q80
    key=x.groupby(['date','group']).ratio.median().rename('같은날같은유형_중앙_실제/예측')
    top=top.join(key,on=['date','group'])
    top['달력']=top.date.map(cald.holiday_name)
    m=top.merge(cv.rename(columns={'item_id':'site','timestamp':'date'})[['site','date','free_holiday','free_last_wed']],on=['site','date'],how='left')
    m['lag']=lag; m['kind']=kind
    out.append(m[['lag','kind','site','date','date_type','달력','origin','actual','q80','short','같은날같은유형_중앙_실제/예측','free_holiday','free_last_wed']])
r=pd.concat(out)
r['actual']=r.actual.round(0);r['q80']=r.q80.round(0);r['short']=r.short.round(1);r['같은날같은유형_중앙_실제/예측']=r['같은날같은유형_중앙_실제/예측'].round(2)
for (lag,kind),g in r.groupby(['lag','kind']):
    print(f'\n## {lag} {kind}'); print(g.drop(columns=['lag','kind']).to_string(index=False))
# 전체 대비
for lag in 'AB':
  for kind in ['격자','명절']:
    x=b[(b.lag==lag)&(b.kind==kind)]; t=x.sort_values('short',ascending=False).head(10)
    print(lag,kind,'상위10 부족인원합 비중',round(t.short.sum()/x.short.sum(),3),'부족비용 비중',round(Cu*x.short.sum()/(Cu*x.short.sum()+Co*(x.plan-x.need).clip(lower=0).sum()),3), '상위10 날짜 분포',t.date.dt.strftime('%Y-%m-%d').value_counts().to_dict())
r.to_csv(RES/'top10_7row_v7.csv',index=False)

# ---- 원인 칸(가이드 7번: 원인은 지정 출처로 확인한 것만 쓴다) 와 마크다운 저장 ----
CAUSE_TMP='궁능유적본부 공지(2025-10-16 게시): 코리아 그랜드 페스티벌 기간 무료개방 2025-10-29~11-09. 달력에 없는 임시 행사. 7행은 공지가 확정 시점 이전이라 입력했지만 예측이 여전히 모자람(크기를 학습할 같은 종류 행사가 없었기 때문이라는 설명은 추정, 미확인)'
def cause(row):
    d=pd.Timestamp(row.date)
    if pd.Timestamp('2025-10-29')<=d<=pd.Timestamp('2025-11-09'): return CAUSE_TMP
    if row.free_holiday==1: return '원인 미확인(무료 개방으로 표시된 날인데 예측이 작았음)'
    return '원인 미확인'
r['원인']=r.apply(cause,axis=1)
md=['# 작업 2 결과(v7): 인력이 가장 모자랐던 10건 (나눈 것, 7행(최종 모형), (개소,날짜) 기준, 격자와 명절 따로)\n',
    'short=모자란 인원(명)=max(실제/2000−q80/2000,0). 같은날같은유형_중앙_실제/예측=같은 날 같은 개소 유형의 실제÷예측 중앙값. 무료 개방 표시는 새 파일(free_holiday)과 달력 규칙 기준.\n',
    '원인 칸: 궁능유적본부 공지 원문으로 확인한 것만 적었다. 확인하지 못한 것은 「원인 미확인」이다. 7행에는 임시 행사(공지가 확정 시점 이전인 것)가 입력으로 들어 있다.\n']
for (lag,kind),g in r.groupby(['lag','kind']):
    md.append(f'\n## 확정시점 {lag} | {kind}\n'); md.append(g.drop(columns=['lag','kind']).assign(date=g.date.dt.strftime('%Y-%m-%d'),origin=g.origin.dt.strftime('%Y-%m-%d')).to_markdown(index=False))
(RES/'작업2_모자란10건_v7.md').write_text('\n'.join(md),encoding='utf-8')
