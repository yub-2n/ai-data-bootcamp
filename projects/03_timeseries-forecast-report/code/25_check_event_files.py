# 팀원이 만든 무료개방일 보강 파일 2개를 검증한다. 출력: results_new/무료개방일_행사파일_검증_v7.md
#  free_open_notice.csv (= 무료개방일_수정.csv): 설·추석 공지날짜 포함 / free_events.csv (= 무료개방일_행사_최종버전.csv, v7): 임시 무료 행사 3개와 공지날짜
import pandas as pd
from common import OUT
RES=OUT.parent/'results_new'
base=pd.read_csv(OUT/'covariates_free_open.csv',parse_dates=['timestamp']); nt=pd.read_csv(OUT/'free_open_notice.csv',parse_dates=['timestamp','free_holiday_notice_date']); import hashlib
_h=hashlib.md5(open(OUT/'free_events_v7.csv','rb').read()).hexdigest(); assert _h!='65c55255a8430f2aa89b7cb3002c2863','제외 대상인 이전 행사 파일과 같다'
ev=pd.read_csv(OUT/'free_events_v7.csv',parse_dates=['timestamp'])
for _c in [c for c in ev.columns if c.endswith('notice_date')]: ev[_c]=pd.to_datetime(ev[_c])
c4=['free_holiday','free_last_wed','free_jongmyo_daeje','closed_official']; L=['# 무료개방일 보강 파일 검증\n']
k=['item_id','timestamp']; b=base.set_index(k); n=nt.set_index(k).reindex(b.index)
L.append(f'## 1. 설·추석 공지날짜 파일(free_open_notice.csv)\n- 행 {len(nt):,}, 기존 파일과 같은 키 {len(b)==len(nt) and (nt.set_index(k).index==b.index).all()}, 기존 4개 표시 열 값이 다른 칸 수: {int((n[c4].values!=b[c4].values).sum())}')
x=nt[nt.free_holiday==1]; g=x.groupby('timestamp').free_holiday_notice_date.agg(['min','max']); ev6=[]
for d0,d1 in [('2023-01-21','2023-01-24'),('2023-09-28','2023-10-03'),('2024-02-09','2024-02-12'),('2024-09-14','2024-09-18'),('2025-01-25','2025-01-30'),('2025-10-03','2025-10-09')]:
    s=x[(x.timestamp>=d0)&(x.timestamp<=d1)]; nd=sorted(set(s.free_holiday_notice_date.dt.date.astype(str)))
    ev6.append(f'  - {d0}~{d1}: 공지날짜 {nd}, 원점 {d0} 기준 {(pd.Timestamp(d0)-pd.Timestamp(nd[0])).days}일 전')
L+=['- 설·추석 6건의 공지날짜(공식 사이트 공지 기준, 팀원 확인; 공지 글 개별 URL은 정리되지 않았고 메인 `https://royal.khs.go.kr/ROYAL/main/index.do`만 받음):']+ev6
L.append(f'- 공지날짜가 개방일보다 늦은 행: {int((x.free_holiday_notice_date>x.timestamp).sum())}, 공지날짜 빠진 무료일 행: {int(x.free_holiday_notice_date.isna().sum())}, 무료가 아닌 날에 공지날짜가 있는 행: {int(nt[nt.free_holiday==0].free_holiday_notice_date.notna().sum())}')
L.append('- 마지막 수요일·종묘대제는 달력 규칙(종묘대제는 5월 첫 일요일 고정)이라 공지날짜 열을 비워 둔 것이 맞다(팀원 설명).')
L.append('\n## 2. 임시 무료 행사 파일(free_events_v7.csv = 무료개방일_행사_최종버전.csv)\n'+f'- 행 {len(ev):,}, 키 {len(ev)==len(base)}')
rows=[]; m=ev.merge(base,on=k)
for e,name in [('korea_grand_festival','코리아 그랜드 페스티벌'),('sejong_birthday','세종대왕 나신 날 기념'),('heritage_agency_launch','국가유산청 출범 기념')]:
    f='free_'+e; s=ev[ev[f]==1]; nd=f+'_notice_date'; mm=m[m[f]==1]
    for y,gg in s.groupby(s.timestamp.dt.year):
        rows.append([name,y,gg.timestamp.min().date(),gg.timestamp.max().date(),gg.timestamp.nunique(),gg.item_id.nunique(),', '.join(sorted(set(gg[nd].dropna().dt.date.astype(str)))),int((gg[nd]>gg.timestamp).sum()),int(gg[nd].isna().sum()),int(mm[mm.timestamp.dt.year==y].free_holiday.sum()),int(mm[mm.timestamp.dt.year==y].closed_official.sum())])
L.append(pd.DataFrame(rows,columns=['행사','연도','시작','끝','개방일 수','개소 수','공지날짜','공지가 개방일보다 늦은 행','공지날짜 빠진 행','설·추석 무료와 겹침','공식 휴관과 겹침']).to_markdown(index=False))
L.append('\n- 세종대왕유적만 대상이다(2023·2024년은 5/15 하루, 2025년은 5/15~6/1 18일 전체 표시이며 정기 휴관일(월요일)도 표시된다. 실제 휴관은 별도 공변량(closed_exp)이 처리한다). 2023년 공지날짜(5/13)는 직접 확인한 것이 아니라 2024·2025년 공지가 모두 5/13이라 같다고 둔 값이다.')
L.append('- 국가유산청 출범 기념은 덕수궁·종묘 2개소만, 개소마다 공지날짜가 다르다(종묘 2024-04-16, 덕수궁 2024-04-26).')
L.append('- 코리아 그랜드 페스티벌은 2025-10-29~11-09, 공지 2025-10-16, 23개소 × 12일 전체 표시(정기 휴관 요일도 표시, 휴관은 closed_exp 가 처리). 궁능유적본부 공지 원문(사용자가 준 본문)과 일치한다.')
L.append('- 예측에는 공지날짜가 확정 시점(A 원점 전날, B 원점 7일 전) 이전인 행사만 쓴다. v7 평가 원점 82개 중 예측 구간에 걸리는 행사는 코리아 그랜드 페스티벌(원점 2025-10-28, 11-04)과 세종대왕 나신 날 2025(원점 2025-05-13, 05-20, 05-27)이다. 그랜드 페스티벌은 공지(10-16)가 A·B 확정 시점보다 먼저이고, 세종대왕 2025는 공지(5-13)가 원점 05-13의 A 확정 시점(05-12)보다 늦어 그 원점에서는 모형이 행사를 모른다. 국가유산청 출범 기념(2024-05)은 첫 정기 원점(2024-07-02)보다 앞서 과거 구간(context)에만 들어간다.')
open(RES/'무료개방일_행사파일_검증_v7.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L))
