"""추후 방안: 2026 설 연휴·매월 마지막 수요일 인력 배치 (모형 재실행 없이 '지난 날 배수 규칙'으로 계산한 임시 안).
배수 = 무료 개방일 하루 관람객 ÷ 그 개소의 평소 평균(문 연 날, 직전 28일, 날짜 8일 전까지 자료). 개소 묶음(궁·종묘·왕릉)별 0.8 분위수를 쓴다.
확인: 과거 설·추석 6번을 하나씩 빼고(leave-one-out) 나머지 5번의 배수로 예측해 비용을 직전 7일 평균과 비교.  결과 → results_new/추후방안_2026설_마지막수요일.md"""
import numpy as np, pandas as pd
from common import OUT
CAP=2000; CU=600000; CO=150000
h=pd.read_parquet(OUT/'heritage_visitors_daily.parquet'); h['date']=pd.to_datetime(h.date)
V=h.pivot_table(index='date',columns='site',values='total',aggfunc='sum'); V=V.where(V>0)   # 0·기록 없음 = 휴관 → NaN
f=pd.read_csv(OUT/'free_open_notice.csv',parse_dates=['timestamp']).rename(columns={'item_id':'site','timestamp':'date'})
sites=pd.read_csv(OUT/'sites.csv'); GRP=dict(zip(sites.site,sites.group)); CW=dict(zip(sites.site,sites.closed_weekday))
def base(site,end):   # end 까지의 직전 28일 문 연 날 평균
    s=V[site].loc[end-pd.Timedelta(days=27):end].dropna(); return s.mean() if len(s)>=5 else np.nan
# 설·추석 연휴 묶음
fh=f[f.free_holiday==1].groupby('date').size().index; fh=pd.DatetimeIndex(sorted(fh)); cl=[]; cur=[fh[0]]
for d in fh[1:]:
    if (d-cur[-1]).days==1: cur.append(d)
    else: cl.append(cur); cur=[d]
cl.append(cur); NAME=lambda c: ('설' if c[0].month<=2 else '추석')+str(c[0].year)
rows=[]
for c in cl:
    st=c[0]
    for s in V.columns:
        b=base(s,st-pd.Timedelta(days=8))
        for d in c:
            v=V[s].get(d,np.nan)
            if np.isfinite(v) and np.isfinite(b): rows.append(dict(hol=NAME(c),kind=NAME(c)[:1] if NAME(c)[0]=='설' else '추',site=s,group=GRP[s],date=d,actual=v,base=b,ratio=v/b))
R=pd.DataFrame(rows); R['kind']=np.where(R.hol.str.startswith('설'),'설','추석')
def q80(x): return float(np.quantile(x,0.8))
tab=R.groupby(['kind','group']).ratio.agg(['count','median',q80]).round(2)
# leave-one-out 확인
res=[]
for hname in R.hol.unique():
    te=R[R.hol==hname]; tr=R[R.hol!=hname]; qq=tr.groupby('group').ratio.apply(q80)
    plan_m=te.base*te.group.map(qq)/CAP; plan_1=te.base/CAP; need=te.actual/CAP
    def cost(p): return (CU*np.maximum(need-p,0)+CO*np.maximum(p-need,0)).sum()
    res.append(dict(hol=hname,n=len(te),비용_직전7일평균=cost(plan_1),비용_배수규칙=cost(plan_m),적중_직전7일평균=(need<=plan_1).mean(),적중_배수규칙=(need<=plan_m).mean()))
L=pd.DataFrame(res); tot=L[['비용_직전7일평균','비용_배수규칙']].sum()
# 마지막 수요일
lw=f[(f.free_last_wed==1)].copy(); lw=lw[~lw.date.isin(fh)]; r2=[]
for _,r in lw.iterrows():
    v=V[r.site].get(r.date,np.nan); b=base(r.site,r.date-pd.Timedelta(days=8))
    if np.isfinite(v) and np.isfinite(b): r2.append(dict(group=GRP[r.site],date=r.date,ratio=v/b,actual=v,base=b))
W=pd.DataFrame(r2); wtab=W.groupby('group').ratio.agg(['count','median',q80]).round(2); wq=W.groupby('group').ratio.apply(q80)
# LOO(연도별)로 마지막 수요일 규칙 확인
W['yr']=W.date.dt.year; l2=[]
for y in sorted(W.yr.unique()):
    te=W[W.yr==y]; tr=W[W.yr!=y]; qq=tr.groupby('group').ratio.apply(q80); need=te.actual/CAP
    def c2(p): return (CU*np.maximum(need-p,0)+CO*np.maximum(p-need,0)).sum()
    l2.append(dict(연도=y,n=len(te),비용_직전7일평균=c2(te.base/CAP),비용_배수규칙=c2(te.base*te.group.map(qq)/CAP),적중_직전7일평균=(need<=te.base/CAP).mean(),적중_배수규칙=(need<=te.base*te.group.map(qq)/CAP).mean()))
L2=pd.DataFrame(l2)
# 2026 설 계획: 기준 = 2025-12-31 까지 직전 28일
END=pd.Timestamp('2025-12-31'); B26={s:base(s,END) for s in V.columns}
days=pd.date_range('2026-02-14','2026-02-18'); cal=pd.read_csv(OUT/'cal_2026.csv',parse_dates=['date']).set_index('date')
qs=R[R.kind=='설'].groupby('group').ratio.apply(q80); qa=R.groupby('group').ratio.apply(q80)
plan=[]
for s in V.columns:
    for d in days:
        p_all=B26[s]*qa[GRP[s]]/CAP; p_se=B26[s]*qs[GRP[s]]/CAP
        plan.append(dict(site=s,group=GRP[s],date=d,소수_평소=B26[s]/CAP,소수_설추석배수=p_all,소수_설만배수=p_se))
P=pd.DataFrame(plan)
ci=lambda x: np.where(x>0,np.ceil(x-1e-9),0).astype(int)
P['정수_평소']=ci(P.소수_평소.values); P['정수_설추석배수']=ci(P.소수_설추석배수.values); P['정수_설만배수']=ci(P.소수_설만배수.values)
D=P.groupby('date')[['정수_평소','정수_설추석배수','정수_설만배수']].sum()
G=P.groupby(['group','date']).정수_설추석배수.sum().unstack(0)
K=P[P.site=='경복궁'].set_index('date')[['정수_평소','정수_설추석배수']]
lwdates=cal[(cal.index.year==2026)&(cal.is_last_wednesday==1)].index
LW=pd.DataFrame({g:[None]*0 for g in []})
bj=pd.Series(B26)
ex=pd.DataFrame({'평소 평균(명/일)':bj.round(0)}).T
# 마지막 수요일 2026-01-28 예시
lwp=[]
for s in V.columns:
    p=B26[s]*wq[GRP[s]]/CAP; lwp.append(dict(site=s,group=GRP[s],평소인원_소수=B26[s]/CAP,마지막수요일_소수=p,평소_정수=int(ci(np.array([B26[s]/CAP]))[0]),마지막수요일_정수=int(ci(np.array([p]))[0])))
LWP=pd.DataFrame(lwp); LWG=LWP.groupby('group')[['평소_정수','마지막수요일_정수']].sum()
G5=P[P.date==P.date.min()].groupby('group')[['정수_평소','정수_설만배수','정수_설추석배수']].sum()
md=[]
md+=['# 추후 방안: 2026 설 연휴·마지막 수요일 인력 배치 (임시 안)','',
 '방법: Chronos 재실행 없이, 지난 설·추석 연휴(2023~2025, 6번)에서 "연휴 하루 관람객 ÷ 평소 평균"(배수)을 개소 묶음별로 구해 0.8 분위수를 쓴다. 평소 평균 = 직전 28일 문 연 날 평균(연휴 시작 8일 전 자료까지). 2026년 평소 평균은 자료의 끝(2025-12-31까지 28일)을 쓴 **임시값**이다.','',
 '## 1. 지난 설·추석 배수(0.8 분위수가 쓰는 값)','',tab.reset_index().to_markdown(index=False),'',
 '## 2. 이 규칙이 맞는지 확인(설·추석 6번 중 하나를 빼고 나머지로 예측)','',L.round(3).to_markdown(index=False),'',
 f'합계 비용: 직전 7일 평균 {tot.iloc[0]/1e8:.2f}억 → 배수 규칙 {tot.iloc[1]/1e8:.2f}억 ({(tot.iloc[1]/tot.iloc[0]-1)*100:+.1f}%)','',
 '## 3. 2026 설 연휴(2/14~2/18, 연속 휴일 전체 무료) 인원(정수 합계)','',D.reset_index().assign(date=lambda x:x.date.dt.strftime('%m-%d')).to_markdown(index=False),'',
 '묶음별(설·추석 배수 기준 정수):','',G.reset_index().assign(date=lambda x:x.date.dt.strftime('%m-%d')).to_markdown(index=False),'',
 '경복궁:','',K.reset_index().assign(date=lambda x:x.date.dt.strftime('%m-%d')).to_markdown(index=False),'',
 '## 4. 매월 마지막 수요일 배수','',wtab.reset_index().to_markdown(index=False),'',
 '연도별로 하나씩 빼고 확인:','',L2.round(3).to_markdown(index=False),'',
 f'2026 마지막 수요일 날짜: '+', '.join(d.strftime('%m-%d') for d in lwdates),'',
 '2026-01-28 예시(평소 평균은 2025-12-31까지 자료, 임시값). 개소 묶음별 정수 인원 합계:','',LWG.reset_index().to_markdown(index=False),'',
 '## 5. 2026 설 연휴 하루 인원, 설 배수만 쓴 경우(묶음별 정수 합계, 연휴 5일 동일)','',G5.reset_index().to_markdown(index=False),'','경복궁 등 개소별: `추후방안_2026설_개소별.csv`. 2026-02-19(설 다음날, 연속 휴일 다음날)는 휴관 규칙상 전 개소 휴관 예상.','']
open(OUT.parent/'results_new'/'추후방안_2026설_마지막수요일.md','w',encoding='utf-8').write('\n'.join(md)); print('\n'.join(md))
P.to_csv(OUT.parent/'results_new'/'추후방안_2026설_개소별.csv',index=False,encoding='utf-8-sig')
