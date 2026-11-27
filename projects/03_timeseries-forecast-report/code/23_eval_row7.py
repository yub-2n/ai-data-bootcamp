# [v6] ① 7행(임시 무료 행사 반영)과 6행 비교  ② 공지 민감도 확인(A): 설·추석 무료 표시를 '공지가 확정 시점 이전일 때만' 인정하는 엄격 기준(strict)이 A 에서는 정식 결과와 같은지 날짜로 점검한다.
# 입력(data/): eval_rows_v7.parquet, free_open_notice.csv, free_events.csv, cal.csv    출력: results_new/v7_7행_민감도.md
# 민감도는 A(운영 시점)만 본다. B 는 백테스트 비교용이라 민감도·직접·권고표를 만들지 않았다.
import numpy as np, pandas as pd, importlib.util
from common import OUT, CODE
spec=importlib.util.spec_from_file_location('m07',CODE/'07_timing_direct_compare.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
E=pd.read_parquet(OUT/'eval_rows_v7.parquet'); R=E[E.row.isin([1,2,5,6,7])].assign(name=lambda d:d.row.astype(str))
f=lambda x:x.round(3)
out=['# v7 평가: 7행(임시 무료 행사 반영)과 공지 민감도 점검 (2023-01-01 이후 데이터, 관리소 나눔)\n','Cu 60만 / Co 15만 / CAP 2,000 / 서비스 수준 0.8. 1=직전7일평균, 2=+보정, 5=명절 달력, 6=+무료개방(설·추석 무료는 달력 규칙), 7=6행+임시 무료 행사(공지가 확정 시점 이전인 것만).']
t=R.groupby(['lag','kind','name']).apply(m.metr,include_groups=False); t['비용(억원)']=(t['비용(만원)']/1e4).round(3)
out+=['\n### 전체 (원점 묶음별)\n',f(t.drop(columns='비용(만원)')).to_markdown()]
EV=[pd.Timestamp('2025-10-28'),pd.Timestamp('2025-11-04')]
q=R[R.origin.isin(EV)&R.name.isin(['1','2','5','6','7'])].groupby(['lag','origin','name']).apply(m.metr,include_groups=False); q['비용(억원)']=(q['비용(만원)']/1e4).round(3)
out+=['\n### 그랜드 페스티벌이 걸린 원점(2025-10-28, 11-04)\n',f(q.drop(columns='비용(만원)')).to_markdown()]
fe=pd.read_csv(OUT/'free_events_v7.csv',parse_dates=['timestamp'])
fl=fe[fe.free_korea_grand_festival==1][['item_id','timestamp']].rename(columns={'item_id':'site','timestamp':'date'}); fl['k']=1
x=R.merge(fl,on=['site','date'],how='left'); x=x[x.k==1]
q=x[x.name.isin(['5','6','7'])].groupby(['lag','name']).apply(m.metr,include_groups=False); q['비용(억원)']=(q['비용(만원)']/1e4).round(3)
out+=['\n### 그랜드 페스티벌 개방일(10-29~11-09)만, 평가에 들어간 개소·일\n',f(q.drop(columns='비용(만원)')).to_markdown()]
rest=R[(R.kind=='격자')&~R.origin.isin(EV)&R.name.isin(['6','7'])].groupby(['lag','name']).apply(m.metr,include_groups=False); rest['비용(억원)']=(rest['비용(만원)']/1e4).round(3)
out+=['\n### 격자 중 코리아 그랜드 페스티벌이 안 걸린 76개 원점: 6 vs 7 (세종대왕 2025-05 행사가 걸린 원점 포함)\n',f(rest.drop(columns='비용(만원)')).to_markdown()]
# ② A 공지 민감도 점검: 예측 구간(원점~원점+6)에 든 설·추석 무료 개방일 각각의 공지날짜가 A 확정 시점(원점-1) 이전인가
nt=pd.read_csv(OUT/'free_open_notice.csv',parse_dates=['timestamp','free_holiday_notice_date']); nt=nt[nt.free_holiday==1].groupby('timestamp').free_holiday_notice_date.min()
cal=pd.read_csv(OUT/'cal.csv',parse_dates=['date']).set_index('date'); orgs=sorted(E.origin.unique()); rows=[]
for o in orgs:
    fut=[d for d in pd.date_range(o,o+pd.Timedelta(days=6)) if d in nt.index]
    late=[d for d in fut if nt[d]>o-pd.Timedelta(days=1)]
    if fut: rows.append((str(o.date()),len(fut),len(late),min((o-pd.Timedelta(days=1)-nt[d]).days for d in fut)))
out+=['\n### A 시점 공지 민감도 점검 (설·추석 무료 개방일이 예측 구간에 든 원점)\n',pd.DataFrame(rows,columns=['원점','예측 구간 안 설·추석 무료일 수','그중 공지가 확정 시점(원점-1)보다 늦은 날 수','가장 빠듯한 날의 여유(일)']).to_markdown(index=False),
 ('\n공지가 확정 시점(원점-1)보다 늦은 날이 모든 원점에서 0이므로, A 에서는 엄격 기준을 적용해도 입력이 바뀌지 않는다.' if sum(r[2] for r in rows)==0 else '\n공지가 확정 시점보다 늦은 날이 있는 원점이 있다(위 표). 그 원점에서는 엄격 기준 적용 시 입력이 달라지므로 별도 민감도 계산이 필요하다.')+' (B 는 운영에 쓰지 않아 민감도를 새로 만들지 않았다.)']
print('A 에서 공지가 확정 시점보다 늦은 설·추석 무료일 수:',sum(r[2] for r in rows))
cost=[]
for L in 'AB':
    for k in ['격자','명절']:
        c=lambda n: m.metr(R[(R.lag==L)&(R.kind==k)&(R.name==n)])['비용(만원)']/1e4
        cost.append((L,k,round(c('1'),2),round(c('6'),2),round(c('7'),2),round(1-c('6')/c('1'),3),round(1-c('7')/c('1'),3)))
out+=['\n### 비용(억원)과 절감률(1행 대비)\n',pd.DataFrame(cost,columns=['시점','묶음','1행(억)','6행','7행','절감률_6','절감률_7']).to_markdown(index=False)]
open(OUT.parent/'results_new'/'v7_7행_민감도.md','w',encoding='utf-8').write('\n'.join(out)); print('\n'.join(out))
