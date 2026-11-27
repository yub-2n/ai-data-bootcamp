# [v7] 확정 시점 A(원점 전날) vs B(원점 7일 전) 공용 함수 + 관리소 예측을 개소로 나누기.
# v6의 07을 v7용으로 바꾼 것: (1) 원점 목록은 origins_v7.py (2) 개소 비중(shares) 계산 결과를 캐시해 속도 개선(값은 v6와 같다)
# (3) 방법론(직전 7일 평균, k, 비중, 비용)은 v6와 동일하다. v6의 kfac 안 `len(r)>=0` 조건은 그대로 둔다(효과 없음, v6와 동일 동작 유지).
# 입력: data/chronos_series_{A,B}_v7.parquet (Colab 결과, 2023-01-01 이후 데이터).
import pandas as pd, numpy as np
from common import OUT, find
from origins_v7 import GRID, HOL
CAP,CU,CO,Q80,WEEKS=2000,60,15,0.8,12
EXCL=(pd.Timestamp('2024-11-27'),pd.Timestamp('2024-12-01'))
g=pd.read_parquet(OUT/'grid_site_day.parquet'); cal=pd.read_csv(find('calendar_kr_2015_2025.csv'),parse_dates=['date']).set_index('date')
Y={s:d.set_index('date').total for s,d in g.groupby('site')}
S2G=g.groupby('site').series.first().to_dict(); G2S={}
for s,k in S2G.items(): G2S.setdefault(k,[]).append(s)
GRP={s:g[g.site==s].group.iloc[0] for s in Y}
def kind(o): return '격자' if o in GRID else '명절'
def higher_q(r,q): r=np.sort(np.asarray(r,float)); return r[int(np.ceil(q*(len(r)-1)))]
# ---------- 베이스라인 1·2행 (확정 시점 lag: A=1, B=7) ----------
def prev7(y,last):                                  # last 까지의 7일 중 문 연 날 평균
    w=y[(y.index>last-pd.Timedelta(days=7))&(y.index<=last)].dropna(); w=w[w>0]; return w.mean() if len(w) else np.nan
def kfac(y,o,lag):
    r=[]; last=o-pd.Timedelta(days=lag)
    for j in range(1,WEEKS+8):
        w0=o-pd.Timedelta(days=7*j)
        if w0+pd.Timedelta(days=6)>last: continue   # 그 주 실적이 확정 시점까지 알려진 것만
        if len(r)>=0 and j>WEEKS+(0 if lag==1 else 1): break
        m=prev7(y,w0-pd.Timedelta(days=lag))
        if not m>0: continue
        a=y[(y.index>=w0)&(y.index<w0+pd.Timedelta(days=7))]; a=a[(a>0)&~((a.index>=EXCL[0])&(a.index<=EXCL[1]))]
        r+=list(a.values/m)
    return higher_q(r,Q80) if len(r)>=10 else np.nan
def baseline(lag):
    """1·2행 기준 행. 직전 7일 평균(m)이 없는 개소·원점은 q50·q80 이 NaN 으로 남는다 -> 12번 스크립트가 모든 행에서 공통으로 제외한다."""
    rows=[]
    for o in [*GRID,*HOL]:
        last=o-pd.Timedelta(days=lag)
        for s,y in Y.items():
            if y.index.min()>o-pd.Timedelta(days=14): continue
            m=prev7(y,last); k=kfac(y,o,lag)
            for d in pd.date_range(o,o+pd.Timedelta(days=6)):
                a=y.get(d,np.nan)
                if np.isnan(a) or a==0: continue
                rows.append((kind(o),o,s,d,a,m,m*k))
    return pd.DataFrame(rows,columns=['kind','origin','site','date','actual','q50','q80'])
# ---------- Chronos 결과 -> 개소 단위 ----------
def dtype_(d):
    r=cal.loc[d]; return 'LW' if r.is_last_wednesday==1 else 'HOL' if r.is_holiday==1 else 'WE' if d.dayofweek>=5 else 'WD'
CT=cal.index.to_series().map(dtype_)
def shares(o,sites,d,lag):
    last=o-pd.Timedelta(days=lag); days=pd.date_range(last-pd.Timedelta(days=27),last); same=[x for x in days if CT[x]==CT[d]]
    use=same if len(same)>=3 else list(days)
    v=pd.Series({s:np.nansum([Y[s].get(x,np.nan) for x in use]) for s in sites}); return v/v.sum() if v.sum()>0 else pd.Series(1/len(sites),index=sites)
_SH={}
def shares_cached(o,key,sites,d,lag):
    """shares 는 (원점, 계열, 날짜 유형, lag)에만 의존하므로 캐시한다(값은 shares 와 같다)."""
    k=(o,key,CT[d],lag)
    if k not in _SH: _SH[k]=shares(o,sites,d,lag) if len(sites)>1 else pd.Series(1.0,index=sites)
    return _SH[k]
def chronos_rows(level,lag,tag=''):
    C=pd.read_parquet(OUT/f'chronos_{level}_{lag}{tag}.parquet'); L=1 if lag=='A' else 7; rows=[]
    for (row,o,key),grp in C.groupby(['row','origin','key']):
        sites=G2S[key] if level=='series' else [key]
        for d,q5,q8 in zip(grp.date,grp['0.5'],grp['0.8']):
            sh=shares_cached(o,key,sites,d,L)
            for s in sites:
                a=Y[s].get(d,np.nan)
                if np.isnan(a) or a==0: continue
                rows.append((kind(o),row,o,s,d,a,max(q5,0)*sh[s],max(q8,0)*sh[s]))   # 음수 분위수는 0으로
    return pd.DataFrame(rows,columns=['kind','row','origin','site','date','actual','q50','q80'])
def metr(d):
    need=d.actual/CAP; plan=d.q80/CAP; c=CU*(need-plan).clip(lower=0)+CO*(plan-need).clip(lower=0)
    return pd.Series({'n':len(d),'WAPE':(d.actual-d.q50).abs().sum()/d.actual.sum(),'비용(만원)':c.sum(),'적중':(need<=plan).mean()})
if __name__=='__main__':      # 관리소 나눔(series)만. chronos_series_{A,B}_v7.parquet 의 3~7행 + 1·2행 비교표 (제외 규칙 적용 전 원자료 기준)
    pd.set_option('display.width',200)
    T={}
    for lag in 'AB':
        b=baseline(1 if lag=='A' else 7).dropna(subset=['q50']); b1=b.assign(q80=b.q50)
        r1=b1.groupby('kind').apply(metr,include_groups=False); r2=b.groupby('kind').apply(metr,include_groups=False)
        for k in ['격자','명절']: T[(lag,k,1)]=r1.loc[k]; T[(lag,k,2)]=r2.loc[k].copy(); T[(lag,k,2)]['WAPE']=r1.loc[k,'WAPE']
        R=chronos_rows('series',lag,'_v7'); m=R.groupby(['kind','row']).apply(metr,include_groups=False)
        for (k,row),v in m.iterrows(): T[(lag,k,row)]=v
    out=pd.DataFrame(T).T; out.index.names=['확정시점','원점묶음','행']; print(out.round(3).to_string())
