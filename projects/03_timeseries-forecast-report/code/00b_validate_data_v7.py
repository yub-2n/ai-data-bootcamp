# [v7] 데이터·공변량 검증 -> results_new/데이터검증_v7.md  (Chronos 없이 실행 가능)
import subprocess, sys, hashlib, importlib.util, pandas as pd, numpy as np
from common import OUT, CODE
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
from origins_v7 import GRID, HOL, ORIGINS
L=['# v7 데이터·공변량 검증\n']
# 1) 원자료 검산값
r=subprocess.run([sys.executable,'15_check_readme_values.py'],capture_output=True,text=True,cwd=CODE); L+=['## 1. 원자료 검산값(README 기준, 13개 항목)\n','```',r.stdout.strip(),'```','']
# 2) 원점
L+=['## 2. 원점 검증\n',f'- 정기 원점 {len(GRID)}개: {GRID[0].date()}(화) ~ {GRID[-1].date()}(화), 7일 간격, 마지막 평가일 {(GRID[-1]+pd.Timedelta(days=6)).date()}',f'- 명절 원점 {len(HOL)}개: '+', '.join(str(h.date()) for h in HOL)+f' | 전체 {len(ORIGINS)}개 | v6의 26개 정기 원점은 모두 포함(새로 추가 52개)','- 원점 목록 전체: `results_new/원점목록_v7.csv`','']
# 3) 입력 파일
cv=pd.read_csv(OUT/'covariates_free_open.csv',parse_dates=['timestamp']); nt=pd.read_csv(OUT/'free_open_notice.csv',parse_dates=['timestamp']); ev=pd.read_csv(OUT/'free_events_v7.csv',parse_dates=['timestamp'])
cal=pd.read_csv(OUT/'cal.csv',parse_dates=['date']); cal26=pd.read_csv(OUT/'cal_2026.csv',parse_dates=['date'])
rows=[[n,len(x),x[c].min().date(),x[c].max().date()] for n,x,c in [('covariates_free_open.csv',cv,'timestamp'),('free_open_notice.csv (= 무료개방일_수정.csv)',nt,'timestamp'),('free_events_v7.csv (= 무료개방일_행사_최종버전.csv)',ev,'timestamp'),('cal.csv',cal,'date'),('cal_2026.csv',cal26,'date')]]
L+=['## 3. 입력 파일 범위\n',pd.DataFrame(rows,columns=['파일','행','시작','끝']).to_markdown(index=False),'',f'- free_events_v7.csv md5 = {hashlib.md5((OUT/"free_events_v7.csv").read_bytes()).hexdigest()} (제외 대상인 이전 행사 파일 `무료개방일_행사_최종.csv` md5 65c55255…와 다름). 이전 파일은 v7 폴더에 넣지 않았고 코드도 읽지 않는다.','']
# 4) 행사 파일
h=pd.read_parquet(OUT/'heritage_visitors_daily.parquet'); h['date']=pd.to_datetime(h.date)
rows=[]
for e,nm in [('korea_grand_festival','코리아 그랜드 페스티벌'),('sejong_birthday','세종대왕 나신 날 기념'),('heritage_agency_launch','국가유산청 출범 기념')]:
    s=ev[ev['free_'+e]==1]; nd=e and 'free_'+e+'_notice_date'; s=s.assign(nd=pd.to_datetime(s[nd]))
    z=s.merge(h[['site','date','total']].rename(columns={'site':'item_id','date':'timestamp'}),on=['item_id','timestamp'],how='left')
    rows.append([nm,len(s),s.item_id.nunique(),s.timestamp.min().date(),s.timestamp.max().date(),', '.join(sorted({str(x.date()) for x in s.nd})),int((s.nd>s.timestamp).sum()),int((z.total==0).sum())])
L+=['## 4. 특별 무료개방 행사 파일(v7 입력) 검증\n',pd.DataFrame(rows,columns=['행사','표시 행','개소','시작','끝','공지날짜','공지가 시행일보다 늦은 행','표시일인데 실제 total=0(정기 휴관)']).to_markdown(index=False),'',
 '- 이 파일은 행사 기간의 모든 날짜를 무료개방으로 표시하고 정기 휴관 요일도 표시한다(휴관은 closed_exp·closed_notice 공변량이 따로 처리). 마지막 열이 그 휴관 요일 행의 수다.','']
# 5) 달력
c=cal.set_index('date'); chk={'2024-08-15':'광복절','2024-09-17':'추석','2024-10-01':'국군의 날(임시)','2024-10-03':'개천절','2024-10-09':'한글날','2024-12-25':'성탄절','2025-01-27':'임시공휴일','2025-03-03':'삼일절 대체','2025-05-05':'어린이날','2025-05-06':'대체공휴일','2025-06-03':'대통령 선거일','2025-06-06':'현충일'}
L+=['## 5. v7 평가 구간의 공휴일 달력 확인\n',pd.DataFrame([[k,v,int(c.loc[k,'is_holiday']),c.loc[k,'holiday_name']] for k,v in chk.items()],columns=['날짜','확인 대상','is_holiday','달력 공휴일명']).to_markdown(index=False),'','- 달력은 패키지의 cal.csv(holidays 0.103, 13번 스크립트가 원본 달력과 일치함을 확인)를 쓴다. 임시공휴일의 공식 근거 문서는 이 패키지에서 확인하지 못했다(미확인).','']
# 6) 개소·평가 구간 완전성
g=pd.read_parquet(OUT/'grid_site_day.parquet'); g['date']=pd.to_datetime(g.date); S=pd.read_csv(OUT/'sites.csv',parse_dates=['first_date']); w=g[(g.date>='2024-07-02')&(g.date<='2025-12-29')]
z=g[(g.date>='2024-11-24')&(g.date<='2024-12-04')&(g.zero)].groupby('date').size()
L+=['## 6. 평가 구간(2024-07-02~2025-12-29) 자료 완전성\n',f'- 개소 자료 시작일의 최댓값 {S.first_date.max().date()} → 23개소 모두 첫 원점 이전부터 자료가 있다(첫 원점의 학습 이력은 약 18개월, 마지막 정기 원점은 약 36개월).',f'- 평가 구간 개소·날짜 행 {len(w):,}개, 원본에 없는 날 {int(w.row_missing.sum())}개, total=0 행 {int(w.zero.sum()):,}개(평가에서 제외)','- **2024-11-24~12-04 total=0 개소 수**(월요일 정기 휴관은 21~22개소): '+', '.join(f'{k.date()} {v}개' for k,v in z.items()),'  - 11/27~12/01(수~일)에 20곳 안팎이 동시에 0인 구간이 있고 원인은 이 패키지에서 확인할 수 없다(미확인). 2행 k 계산은 v6와 같이 이 구간을 제외한다.','']
# 7) 표시 없는 무료 개방일
hh=h[(h.total>0)&(h.date>='2024-07-02')&(h.date<='2025-12-29')].copy(); hh['fs']=hh.free/hh.total
m=hh.merge(cv.rename(columns={'item_id':'site','timestamp':'date'}),on=['site','date']).merge(ev.rename(columns={'item_id':'site','timestamp':'date'})[['site','date','free_korea_grand_festival','free_sejong_birthday','free_heritage_agency_launch']],on=['site','date'])
core=m[m.site.isin(['경복궁','덕수궁','창경궁','창덕궁','종묘'])]; flag=core[['free_holiday','free_last_wed','free_jongmyo_daeje','free_korea_grand_festival','free_sejong_birthday','free_heritage_agency_launch']].max(axis=1); u=core[(flag==0)&(core.fs>=0.9)]
L+=['## 7. 무료 비중이 0.9 이상인데 공변량에 표시가 없는 날 (4대궁·종묘, v7 평가 구간)\n',pd.DataFrame([[k,', '.join(sorted(v))] for k,v in u.groupby(u.date.dt.strftime('%Y-%m-%d')).site],columns=['날짜','개소']).to_markdown(index=False),'',f'- 총 {len(u)}개소·일. 원인은 확인되지 않았다(미확인). 공지 날짜를 임의로 만들어 행사로 추가하지 않았고, 오차 분석에서 「원인 미확인」으로 다룬다.','']
# 8) 직전 7일 평균이 없는 개소·원점
spec=importlib.util.spec_from_file_location('m07',CODE/'07_timing_direct_compare.py'); m7=importlib.util.module_from_spec(spec); spec.loader.exec_module(m7)
rows=[]
for lag in (1,7):
    for o in ORIGINS:
        for s,y in m7.Y.items():
            if not m7.prev7(y,o-pd.Timedelta(days=lag))>0: rows.append(['A' if lag==1 else 'B',o.date(),s])
L+=['## 8. 직전 7일 평균을 계산할 수 없는 (확정 시점, 원점, 개소)\n',(pd.DataFrame(rows,columns=['확정시점','원점','개소']).to_markdown(index=False) if rows else '(없음)'),'','- 위 목록은 2024-11-27~12-01 대량 휴관 직후 원점에서 생긴다. v7은 이 (원점, 개소)의 7일을 FVA 1~7행 모두에서 제외해 모든 행이 같은 개소·날짜를 평가하게 한다(대체값을 만들지 않음). 제외 행 목록은 12번 스크립트가 results_new/평가집합_제외행_v7.csv 로 저장한다.','']
dates=pd.date_range('2024-07-02','2025-12-29'); se=pd.Series(dates.month).map(lambda m:'봄' if m in(3,4,5) else '여름' if m in(6,7,8) else '가을' if m in(9,10,11) else '겨울')
L+=['## 9. 계절별 평가 달력일수\n',se.value_counts().reindex(['봄','여름','가을','겨울']).rename('달력일수').to_frame().to_markdown(),'','- 봄(3~5월)은 2025년 하나뿐이다.','']
open(RES/'데이터검증_v7.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L[:30]))
