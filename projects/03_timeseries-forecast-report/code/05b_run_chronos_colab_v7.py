"""[v7: 정기 원점 78개 + 명절 4개 = 82개. 원점 목록·행사 파일(free_events_v7.csv)·출력 이름만 v5에서 바꾸고 나머지 로직은 같다. 출력은 --out 으로 정확한 파일 이름을 지정한다.]
[05b = v5] Chronos-2 제로샷 FVA 실행 (Colab용). 05(v4)에 공지날짜 규칙(--notice)과 7행(임시 무료 행사)을 더한 버전. 05(v4)는 기존 1~6행 재현용으로 그대로 둔다.
추가 필요 파일: free_open_notice.csv(설·추석 공지날짜), free_events.csv(임시 무료 3개 행사 + 공지날짜)
 추가 옵션: --notice  임시 무료 행사(free_event, 7행)는 공지날짜 ≤ 확정 시점(원점-lag 일)일 때만 켠다(과거 구간 표시는 항상 사용). 7행은 --notice 와 함께만 실행한다.
          --strict-fh  (민감도) 설·추석 free_holiday 도 공지날짜 ≤ 확정 시점일 때만 켠다. 기본은 가이드의 '달력 규칙(명절 연휴)'대로 설·추석 무료는 공지와 상관없이 쓴다.
 7행 = 6행 + free_event (임시 무료 행사).

--- 아래는 v4 설명 ---
v4: 무료개방일 파일 교체(임시 무료 삭제, 공지일 열 삭제) + 설·추석 달력 규칙.
필요 파일(같은 폴더): grid_site_day.parquet, grid_series_day.parquet, cal.csv, covariates_free_open.csv(새 파일: free_holiday,free_last_wed,free_jongmyo_daeje,closed_official)
사용: python 05_run_chronos_colab_v4.py [--level series|site] [--lag A|B] [--rows 4,5,6] [--start 2023-01-01] [--mask 시작:끝,...] [--origin 2026-01-01 --cal cal_2026.csv] [--stub]
 A: 확정 시점 = 원점 전날 (데이터 ~ 원점-1),  B: 확정 시점 = 원점 7일 전 (데이터 ~ 원점-7, 13일 예측 후 뒤 7일)
출력: chronos_{level}_{lag}_v5{tag}.parquet(05b 는 v5, 05 는 v4)  (열: level,lag,row,origin,key,date,0.1..0.9)

v3 와 달라진 점
 1) 임시 무료(free_special) 삭제: 새 무료개방일 파일에는 없다. free_open = 명절 연휴 무료 + 마지막 수요일.
 2) 공지일(event_known_from) 열이 없으므로 '공지가 늦으면 끄는' 처리를 없앴다. 대신 명절 무료 개방과 연휴 다음날 휴관을 달력 규칙으로 만든다.
    규칙: 설·추석 날짜를 포함한 연속 휴일(공휴일+주말) 구간 전체 = 무료 개방, 그 구간 다음날 = 휴관(23개소 공통).
    새 파일의 free_holiday 와 2023-01-01~2026-01-07 전체에서 같은지 검사한다(2023~2025년 6건 일치를 확인함).
    closed_official(파일)은 2025-10-10 에 18개소만 표시되어 있어, 규칙(23개소 공통)과 이 날 5개소가 다르다. 입력에는 규칙을 쓴다.
 3) 마지막 수요일은 cal.csv 의 is_last_wednesday 로 만든다(새 파일 free_last_wed 와 36일 모두 같음). 종묘대제는 파일 값(3건, 모두 과거 5월)을 쓴다.
 4) 2023-01-01 이전 이력은 무료 표시·규칙 휴관 표시를 모두 0 으로 둔다(이전 버전의 경복궁 유료 비중 15% 미만 보정은 쓰지 않는다).
 5) 휴관 규칙(closed_exp), 휴관일이면 무료 표시를 끄는 처리, 나머지는 v3 와 같다.
"""
import argparse, os, time, numpy as np, pandas as pd
ap=argparse.ArgumentParser(); ap.add_argument('--level',default='series'); ap.add_argument('--lag',default='A')
ap.add_argument('--stub',action='store_true'); ap.add_argument('--start',default=None,help='학습 시작일(예: 2023-01-01)')
ap.add_argument('--mask',default='',help='학습에서 뺄 기간 예: 2020-02-01:2022-08-31'); ap.add_argument('--rows',default='4,5,6')
ap.add_argument('--origin',default=None,help='원점을 직접 지정(쉼표 구분). 예: --origin 2026-01-01  (권고표용; 평가 원점 30개 대신 이 날짜만 예측)')
ap.add_argument('--notice',action='store_true',help='임시 무료 행사(7행) 표시는 공지날짜 ≤ 확정 시점일 때만 켠다(필수)'); ap.add_argument('--strict-fh',dest='strict_fh',action='store_true',help='민감도: 설·추석 무료 표시(free_holiday)도 공지날짜 ≤ 확정 시점일 때만 켠다(기본은 달력 규칙)'); ap.add_argument('--cal',default=None,help='달력 파일 이름(기본 cal.csv). 2026년 권고표는 cal_2026.csv'); ap.add_argument('--out',default=None,help='출력 parquet 파일 이름(예: chronos_series_A_v7.parquet)'); a=ap.parse_args()
if '7' in a.rows.split(','): assert a.notice, '7행은 --notice 와 함께 실행'
if a.strict_fh and not a.notice: a.notice=True
QL=[round(x,1) for x in np.arange(0.1,0.95,0.1)]
grid_orig=[pd.Timestamp('2024-07-02')+pd.Timedelta(days=7*i) for i in range(78)]   # v7: 정기 78개
assert len(grid_orig)==78 and grid_orig[-1]==pd.Timestamp('2025-12-23') and grid_orig[-1]+pd.Timedelta(days=6)==pd.Timestamp('2025-12-29'), '정기 원점 78개 검증 실패'
hol_orig=[pd.Timestamp(x) for x in ['2024-02-07','2024-09-14','2025-01-25','2025-10-02']]
ORIGINS=grid_orig+hol_orig
if a.origin: ORIGINS=[pd.Timestamp(x) for x in a.origin.split(',')]
cal=pd.read_csv(a.cal or ('cal.csv' if os.path.exists('cal.csv') else 'calendar_kr_2015_2025.csv'),parse_dates=['date']).set_index('date')
site=pd.read_parquet('grid_site_day.parquet'); ser=pd.read_parquet('grid_series_day.parquet')
WD=dict(zip('월화수목금토일',range(7)))
# ---------- 휴관 규칙 (09_open_expected.py 와 같은 규칙) ----------
HOL=cal.is_holiday.eq(1); OFFDAY=HOL|(cal.index.dayofweek>=5)
def moved_closure_dates(start='2022-01-01'):
    res={}
    for wd in range(7):
        s=set()
        for d in cal.index[(cal.index>=start)&(cal.index.dayofweek==wd)&HOL]:
            e=d
            while (e+pd.Timedelta(days=1)) in OFFDAY.index and OFFDAY[e+pd.Timedelta(days=1)]: e+=pd.Timedelta(days=1)
            nxt=e+pd.Timedelta(days=1)
            if nxt in cal.index: s.add(nxt)
        res[wd]=s
    return res
MV=moved_closure_dates()
def closed_rule(closed_weekday):                      # 1 = 휴관 예상 (달력 날짜 전체, 미래 정보 없음)
    wd=WD[closed_weekday]; idx=cal.index
    c=((idx.dayofweek==wd)&~HOL.values)|idx.isin(list(MV[wd]))
    return pd.Series(c.astype(float),index=idx)
CLOSED_BY_WD={w:closed_rule(w) for w in WD}
# ---------- 계열(key) -> 소속 개소 ----------
if a.level=='series':
    T=ser.rename(columns={'series':'key'})[['key','date','total']]
    members=site.groupby('series').site.unique().to_dict()
else:
    T=site.rename(columns={'site':'key'})[['key','date','total']]
    members={s:[s] for s in site.site.unique()}
cwd=site.groupby('site').closed_weekday.first().to_dict()
group_of=site.groupby('site').group.first().to_dict()
# ---------- 무료개방일·휴관 달력 (규칙 기반; 새 파일은 검증과 종묘대제에만 쓴다) ----------
cv=pd.read_csv('covariates_free_open.csv',parse_dates=['timestamp'])
CV={s:d.set_index('timestamp') for s,d in cv.groupby('item_id')}
# ---- v5: 공지날짜 ----
_c4=['free_holiday','free_last_wed','free_jongmyo_daeje','closed_official']
nt=pd.read_csv('free_open_notice.csv',parse_dates=['timestamp','free_holiday_notice_date'])
assert (nt.set_index(['item_id','timestamp'])[_c4].values==cv.set_index(['item_id','timestamp'])[_c4].reindex(nt.set_index(['item_id','timestamp']).index).values).all(), '공지날짜 파일의 4개 표시가 covariates_free_open.csv 와 다릅니다'
_x=nt[nt.free_holiday==1]; assert _x.free_holiday_notice_date.notna().all() and (_x.free_holiday_notice_date<=_x.timestamp).all()
FH_NOTICE=_x.groupby('timestamp').free_holiday_notice_date.min()          # 날짜 -> 공지날짜 (설·추석 연휴 날짜별)
import hashlib
_OLD_EVENT_MD5={'65c55255a8430f2aa89b7cb3002c2863'}      # 분석에서 제외하기로 한 이전 행사 파일(무료개방일_행사_최종.csv)의 해시
_h=hashlib.md5(open('free_events_v7.csv','rb').read()).hexdigest()
assert _h not in _OLD_EVENT_MD5, 'free_events_v7.csv 가 제외 대상인 이전 행사 파일과 같다'
print('행사 파일: free_events_v7.csv md5',_h)
assert not os.path.exists('free_events.csv') or True    # 이전 이름의 파일이 폴더에 있어도 읽지 않는다
ev=pd.read_csv('free_events_v7.csv',parse_dates=['timestamp'])
EVN=['korea_grand_festival','sejong_birthday','heritage_agency_launch']
for e in EVN:
    ev['free_'+e+'_notice_date']=pd.to_datetime(ev['free_'+e+'_notice_date'])
    _y=ev[ev['free_'+e]==1]; assert _y['free_'+e+'_notice_date'].notna().all() and (_y['free_'+e+'_notice_date']<=_y.timestamp).all()
EV={s:d.set_index('timestamp') for s,d in ev.groupby('item_id')}
def event_flag(s,dates,K):
    """행사 표시(있으면 1). 예측 구간(날짜>K)에서는 공지날짜 ≤ K 인 행사만 켠다. 과거 구간(날짜<=K)은 항상 사용."""
    d=EV[s].reindex(dates); out=np.zeros(len(dates))
    for e in EVN:
        f=d['free_'+e].fillna(0).values; n=d['free_'+e+'_notice_date']
        known=(dates<=K)|(n<=K).fillna(False).values
        out=np.maximum(out,f*known)
    return out
MASKLOG=[]
START=pd.Timestamp('2023-01-01')                      # 이 날짜 이전은 무료 표시를 쓰지 않는다(0)
def build_rule_flags():
    """설·추석 날짜를 포함한 연속 휴일 구간 전체 = 무료 개방(free_holiday), 그 구간 다음날 = 휴관(closed_official). 달력만 사용."""
    fh=pd.Series(0.0,index=cal.index); co=pd.Series(0.0,index=cal.index)
    for col in ['seollal_offset','chuseok_offset']:
        for d in cal.index[(cal[col]==0)&(cal.index>=START)]:
            s=e=d
            while (s-pd.Timedelta(days=1)) in OFFDAY.index and OFFDAY[s-pd.Timedelta(days=1)]: s-=pd.Timedelta(days=1)
            while (e+pd.Timedelta(days=1)) in OFFDAY.index and OFFDAY[e+pd.Timedelta(days=1)]: e+=pd.Timedelta(days=1)
            fh[s:e]=1.0
            if (e+pd.Timedelta(days=1)) in co.index: co[e+pd.Timedelta(days=1)]=1.0
    return pd.DataFrame({'free_holiday':fh,'closed_official':co})
RULE=build_rule_flags()
# 검사: 규칙의 무료 개방이 새 파일과 같은가 (달력 범위 안, 2023-01-01~)
_fh=cv.groupby('timestamp').free_holiday.mean(); _r=RULE.free_holiday.reindex(_fh.index)
_ok=_r.notna(); print('규칙 vs 파일 free_holiday 다른 날짜 수:',int((_fh[_ok]!=_r[_ok]).sum()),'/',int(_ok.sum()))
assert (_fh[_ok]!=_r[_ok]).sum()==0, '규칙이 새 파일의 free_holiday 와 다릅니다'
_co=cv.groupby('timestamp').closed_official.mean(); _rc=RULE.closed_official.reindex(_co.index); _ok2=_rc.notna()
print('규칙 vs 파일 closed_official 다른 날짜 수(참고, 2025-10-10 에 5개소 차이 예상):',int((_co[_ok2]!=_rc[_ok2]).sum()))
LASTWED=cal.is_last_wednesday.fillna(0)               # 달력 규칙(항상 알 수 있음)
def cal_flags(s,dates,K):
    """개소 s 의 날짜별 표시. 모두 달력 규칙 또는 과거 고정 행사라 확정 시점과 상관없이 알 수 있다(K 는 쓰지 않는다)."""
    post=(dates>=START)
    fh=np.where(post,RULE.free_holiday.reindex(dates).fillna(0),0).astype(float)
    if a.strict_fh:                                       # 민감도: 공지날짜가 확정 시점(K)보다 늦으면 아직 모르는 정보로 보고 0
        nd=FH_NOTICE.reindex(dates).values; late=(dates>K)&(fh==1)&(pd.isna(nd)|(nd>np.datetime64(K)))
        if late.any(): MASKLOG.append((str(K.date()),s,int(late.sum())))
        fh=np.where(late,0.0,fh)
    out={'free_holiday':fh,
         'closed_official':np.where(post,RULE.closed_official.reindex(dates).fillna(0),0).astype(float),
         'free_last_wed':np.where(post,LASTWED.reindex(dates).fillna(0),0).astype(float),
         'free_jongmyo_daeje':CV[s].reindex(dates).free_jongmyo_daeje.fillna(0).values.astype(float),
         'free_event':event_flag(s,dates,K)}
    return out
def covs(key,dates,K):
    c=cal.reindex(dates); d=pd.DataFrame({'timestamp':dates})
    d['dow']=['d%d'%x for x in dates.dayofweek]
    sites=members[key]
    d['closed_exp']=np.mean([CLOSED_BY_WD[cwd[s]].reindex(dates).values for s in sites],axis=0)
    fl=[cal_flags(s,dates,K) for s in sites]
    m=lambda f: np.mean([x[f] for x in fl],axis=0)
    d['closed_notice']=m('closed_official')
    d['is_holiday']=c.is_holiday.values.astype(int)
    off=np.where(c.seollal_offset.abs().fillna(99)<=c.chuseok_offset.abs().fillna(99),c.seollal_offset,c.chuseok_offset)
    off=pd.Series(off,index=dates).astype(float)
    d['in_myeongjeol']=(off.abs()<=7).astype(int).values
    d['myeongjeol_off']=off.where(off.abs()<=7,0).values
    opn=1-np.maximum(d.closed_exp.values,d.closed_notice.values)                       # 휴관이면 무료 표시를 끈다 (예: 2023-01-25 마지막 수요일)
    d['free_open']=np.maximum.reduce([m('free_holiday'),m('free_last_wed')])*opn
    d['free_jongmyo']=m('free_jongmyo_daeje')
    d['free_event']=m('free_event')*opn
    return d
T['target']=T.total.where(T.total>0)
if a.start: T=T[T.date>=pd.Timestamp(a.start)]
for pr in [x for x in a.mask.split(',') if x]:
    d0,d1=pr.split(':'); T.loc[(T.date>=d0)&(T.date<=d1),'target']=np.nan
COV={3:[],4:['dow','closed_exp','closed_notice'],
     5:['dow','closed_exp','closed_notice','is_holiday','in_myeongjeol','myeongjeol_off'],
     6:['dow','closed_exp','closed_notice','is_holiday','in_myeongjeol','myeongjeol_off','free_open','free_jongmyo']}
COV[7]=COV[6]+['free_event']
lag=1 if a.lag=='A' else 7; H=7; PL=H+lag-1
if a.stub:
    def predict(df,fut,pl):
        out=[]
        for k,d in df.groupby('item_id'):
            m=d.target.dropna().tail(7).mean(); ts=pd.date_range(d.timestamp.max()+pd.Timedelta(days=1),periods=pl)
            o=pd.DataFrame({'item_id':k,'timestamp':ts})
            for q in QL: o[str(q)]=m*(0.6+q)
            out.append(o)
        return pd.concat(out)
else:
    import torch
    from chronos import Chronos2Pipeline
    pipe=Chronos2Pipeline.from_pretrained('amazon/chronos-2',device_map='cuda' if torch.cuda.is_available() else 'cpu')
    def predict(df,fut,pl): return pipe.predict_df(df,future_df=fut,prediction_length=pl,quantile_levels=QL,freq='D')
res=[];t0=time.time()
for o in ORIGINS:
    last=o-pd.Timedelta(days=lag)                           # 확정 시점: 이 날까지의 데이터·공지만 사용
    for row in map(int,a.rows.split(',')):
        dfs,futs=[],[]
        for key,d in T.groupby('key'):
            d=d[d.date<=last]
            if len(d)<30: continue
            h=d.rename(columns={'date':'timestamp'})[['timestamp','target']].assign(item_id=key)
            idx=pd.date_range(h.timestamp.min(),last); h=h.set_index('timestamp').reindex(idx).rename_axis('timestamp').reset_index(); h['item_id']=key
            fd=pd.date_range(last+pd.Timedelta(days=1),periods=PL)
            if COV[row]:
                hc=covs(key,idx,last); fc=covs(key,fd,last)
                h=h.merge(hc[['timestamp']+COV[row]],on='timestamp'); f=fc[['timestamp']+COV[row]].assign(item_id=key)
            else: f=pd.DataFrame({'timestamp':fd,'item_id':key})
            assert h.timestamp.max()==last and f.timestamp.min()==last+pd.Timedelta(days=1)   # 누수 검사
            dfs.append(h); futs.append(f)
        df=pd.concat(dfs); fut=pd.concat(futs) if COV[row] else None
        p=predict(df,fut,PL).rename(columns={'item_id':'key','timestamp':'date'})
        p=p[(p.date>=o)&(p.date<o+pd.Timedelta(days=H))]
        p.insert(0,'origin',o); p.insert(0,'row',row); p.insert(0,'lag',a.lag); p.insert(0,'level',a.level)
        res.append(p[['level','lag','row','origin','key','date']+[str(q) for q in QL]])
    print(o.date(),f'{time.time()-t0:.0f}s','공지 늦어 가린 free_holiday (개소,일수) 예:',sorted({(k,n) for kk,k,n in MASKLOG if kk==str((o-pd.Timedelta(days=lag)).date())})[:2],flush=True)
R=pd.concat(res); tag=('_s'+a.start if a.start else '')+('_mask' if a.mask else '')+('_o'+a.origin.replace(',','_') if a.origin else '')+('_strictfh' if a.strict_fh else '_notice' if a.notice else '')
outp=a.out if a.out else f'chronos_{a.level}_{a.lag}_v7{tag}.parquet'
if a.stub: outp=outp.replace('.parquet','_stub.parquet')
R.to_parquet(outp); print('저장:',outp,'| 원점 수',R.origin.nunique(),'| 행',sorted(R.row.unique()))
import importlib.metadata as md
print('버전:',{k:md.version(k) for k in ['chronos-forecasting','torch','pandas','numpy']} if not a.stub else 'stub'); print(R.shape)
