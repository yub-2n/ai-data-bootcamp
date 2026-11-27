"""2026-01-01~07 개소 × 날짜 인력 배치 권고표 (7행 모형, 확정 시점 A 만).  가이드: 근무표는 2025-12-31 에 정한다 → A 가 가이드 가정과 같다.
입력(data/): chronos_series_A_v7_o2026-01-01.parquet (Colab 결과, 7행, 2023-01-01 이후 데이터), grid_site_day.parquet, cal_2026.csv, sites.csv
사용: python 14_make_recommendation_table.py            (실제 결과)
      python 14_make_recommendation_table.py _stub      (스크립트 시험용: stub 파일 사용, 숫자는 의미 없음)
계산: 묶음(9개) 예측의 0.8 분위수 → 최근 4주 같은 날짜 유형 비중으로 개소에 나눔 → ÷2,000 = 소수 인원.
      휴관 예상일(정기 휴관 요일, 공휴일이면 열림)은 0명. 정수 인원 = 올림(소수 인원이 0보다 크면 최소 1명). 직전 7일 평균(1행)·서비스수준 보정(2행)에도 같은 규칙을 적용해 나란히 적는다."""
import sys, importlib.util, numpy as np, pandas as pd
from common import OUT, CODE
SUF=sys.argv[1] if len(sys.argv)>1 else ''
spec=importlib.util.spec_from_file_location('m07',CODE/'07_timing_direct_compare.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CAP=2000; O=pd.Timestamp('2026-01-01'); DAYS=pd.date_range(O,O+pd.Timedelta(days=6))
cal=pd.read_csv(OUT/'cal_2026.csv',parse_dates=['date']).set_index('date')
sites=pd.read_csv(OUT/'sites.csv'); CW=dict(zip(sites.site,sites.closed_weekday)); WD=dict(zip('월화수목금토일',range(7)))
HOL=cal.is_holiday.eq(1); OFFDAY=HOL|(cal.index.dayofweek>=5)
def moved(wd,start='2022-01-01'):                       # 휴관 요일이 공휴일이라 열었을 때, 휴관은 연속 휴일 구간 다음날로 옮겨진다(09_open_expected.py 와 같은 규칙)
    s=set()
    for d in cal.index[(cal.index>=start)&(cal.index.dayofweek==wd)&HOL]:
        e=d
        while (e+pd.Timedelta(days=1)) in OFFDAY.index and OFFDAY[e+pd.Timedelta(days=1)]: e+=pd.Timedelta(days=1)
        s.add(e+pd.Timedelta(days=1))
    return s
MV={w:moved(w) for w in range(7)}
def closed(site,d): wd=WD[CW[site]]; return bool((d.dayofweek==wd and not HOL[d]) or d in MV[wd])
def dtype_(d): r=cal.loc[d]; return 'LW' if r.is_last_wednesday==1 else 'HOL' if r.is_holiday==1 else 'WE' if d.dayofweek>=5 else 'WD'
def shares(lag,ss,d):                                    # 07 의 shares 와 같은 규칙(최근 4주 같은 날짜 유형의 개소 비중), 2026 달력 사용
    last=O-pd.Timedelta(days=lag); days=pd.date_range(last-pd.Timedelta(days=27),last); same=[x for x in days if dtype_(x)==dtype_(d)]
    use=same if len(same)>=3 else list(days)
    v=pd.Series({s:np.nansum([m.Y[s].get(x,np.nan) for x in use]) for s in ss}); return v/v.sum() if v.sum()>0 else pd.Series(1/len(ss),index=ss)
def integer(x): return np.where(x>0,np.ceil(x-1e-9),0).astype(int)
out=[]
for L in 'A':
    lag=1
    C=pd.read_parquet(OUT/f'chronos_series_{L}_v7_o2026-01-01{SUF}.parquet'); C=C[C.row==7]
    assert set(C.origin.unique())=={O} and C.date.min()==O and C.date.max()==O+pd.Timedelta(days=6), '원점·날짜 범위 확인'
    for key,grp in C.groupby('key'):
        ss=m.G2S[key]
        for _,r in grp.iterrows():
            sh=shares(lag,ss,r.date)
            for s in ss:
                cl=closed(s,r.date); f=lambda q: 0.0 if cl else max(r[q],0)*sh[s]/CAP
                y=m.Y[s]; last=O-pd.Timedelta(days=lag); p7=m.prev7(y,last); k=m.kfac(y,O,lag)
                out.append(dict(확정시점=L,site=s,group=m.GRP[s],date=r.date,휴관예상=int(cl),
                    소수인원_q80=f('0.8'),소수인원_q70=f('0.7'),소수인원_q90=f('0.9'),소수인원_q50=f('0.5'),
                    직전7일평균_소수인원=0.0 if cl else p7/CAP,직전7일평균_보정_소수인원=0.0 if cl else p7*k/CAP))
R=pd.DataFrame(out)
for c in [c for c in R.columns if c.startswith('소수') or c.startswith('직전')]: R[c.replace('소수인원','정수인원').replace('직전7일평균_보정_소수인원','직전7일평균_보정_정수인원').replace('직전7일평균_소수인원','직전7일평균_정수인원')]=integer(R[c].values)
R['date']=R.date.dt.strftime('%Y-%m-%d'); R=R.sort_values(['확정시점','group','site','date']).reset_index(drop=True)
import os; RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
R.to_csv(RES/f'권고표_2026-01-01_long{SUF}.csv',index=False,encoding='utf-8-sig')
md=['# 2026-01-01~07 인력 배치 권고표 (7행 모형, 0.8 분위수, 정수 = 올림, 휴관 예상일 0명)','','확정 시점 A = 데이터 ≤ 2025-12-31 (가이드 가정; 운영은 A). 숫자: 정수 인원(소수 인원).','']
for L in 'A':
    x=R[R.확정시점==L]; w=x.assign(v=x.apply(lambda r: f"{r.정수인원_q80}({r.소수인원_q80:.1f})" if not r.휴관예상 else '휴관',axis=1)).pivot(index=['group','site'],columns='date',values='v')
    md+= [f'## 확정 시점 {L}','',w.to_markdown(),'', '일별 합계(정수 인원): '+', '.join(f"{d} {int(v)}" for d,v in x.groupby('date').정수인원_q80.sum().items()),'']
    md+= ['비교: 같은 규칙의 직전 7일 평균(1행) 주간 합계 %d명, 서비스수준 보정(2행) %d명, 7행 모형 %d명(정수 인원 합).'%(x.직전7일평균_정수인원.sum(),x.직전7일평균_보정_정수인원.sum(),x.정수인원_q80.sum()),'']
open(RES/f'권고표_2026-01-01{SUF}.md','w',encoding='utf-8').write('\n'.join(md)); print('\n'.join(md[:30]))

# ---- 왕릉 관리소 예측 -> 각 왕릉 개소 배분 (최근 4주 개소별 비중, 같은 날짜 유형 우선, 같은 유형이 3일 미만이면 4주 전체) ----
Cx=pd.read_parquet(OUT/f'chronos_series_A_v7_o2026-01-01{SUF}.parquet'); Cx=Cx[Cx.row==7]; lastA=O-pd.Timedelta(days=1); days28=pd.date_range(lastA-pd.Timedelta(days=27),lastA)
al=['# 왕릉 관리소 예측 → 각 왕릉 개소 배분 (7행, 확정 시점 A, 0.8 분위수, 소수 인원)','','규칙: 최근 4주(2025-12-04~12-31) 개소별 관람객 비중으로 나눈다. 예측 날짜와 같은 유형(평일/주말/공휴일/마지막 수요일)의 과거 날짜를 우선 쓰고, 그런 날이 3일 미만이면 4주 전체를 쓴다. (표의 숫자는 배분 결과이고, 그 개소가 정기 휴관 요일이면 권고표에서는 0명으로 처리한다. 예: 월요일 왕릉.)','']
for key,grp in Cx.groupby('key'):
    ss=m.G2S[key]
    if len(ss)<2: continue
    rows=[]
    for _,r in grp.sort_values('date').iterrows():
        n_same=sum(dtype_(x)==dtype_(r.date) for x in days28); basis='같은 유형 %d일'%n_same if n_same>=3 else '4주 전체(같은 유형 %d일)'%n_same
        sh=shares(1,ss,r.date); tot=max(r['0.8'],0)/CAP
        rows.append([r.date.strftime('%m-%d'),dtype_(r.date),basis,f'{tot:.2f}']+[f"{sh[s]*100:.1f}% → {tot*sh[s]:.2f}" for s in ss])
    al+=[f'## {key} (개소 {len(ss)}곳)','',pd.DataFrame(rows,columns=['날짜','유형','비중 기준','관리소 예측(명)']+list(ss)).to_markdown(index=False),'']
open(RES/f'왕릉_개소배분_2026-01-01{SUF}.md','w',encoding='utf-8').write('\n'.join(al)); print('\n'.join(al[:25]))
