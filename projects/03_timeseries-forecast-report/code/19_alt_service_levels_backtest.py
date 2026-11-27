# 서비스 수준(분위수)·단가를 바꿔 백테스트 비용을 다시 계산한다 (Colab 불필요: chronos_*.parquet 에 0.1~0.9 분위수가 있음).
# 1행 = 직전 7일 평균(변경 없음), 2행 = 평균×k(k는 지난 12주 실적/예측 비율의 τ 분위수), 3~7행 = Chronos τ 분위수(0.1 단위 열 사이는 선형 보간).
# 시나리오: 서비스 수준 0.7/0.9(기본 단가), 단가를 바꾸고 최적 서비스 수준 τ*=Cu/(Cu+Co)로 인력을 다시 정한 경우. 기본(0.8)은 기존 표와 같아야 한다(검산).
import importlib.util, numpy as np, pandas as pd, sys
from common import OUT, CODE
spec=importlib.util.spec_from_file_location('m07',CODE/'07_timing_direct_compare.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
COLS=[f'{i/10:.1f}' for i in range(1,10)]
def qtau(r,tau):
    xs=np.array([float(c) for c in COLS]); ys=np.array([max(r[c],0) for c in COLS]); return float(np.interp(tau,xs,ys))
def chronos_tau(level,lag,tag,tau):
    C=pd.read_parquet(OUT/f'chronos_{level}_{lag}{tag}.parquet'); L=1 if lag=='A' else 7; rows=[]
    xs=np.array([float(c) for c in COLS])
    for (row,o,key),grp in C.groupby(['row','origin','key']):
        sites=m.G2S[key] if level=='series' else [key]
        Yq=np.clip(grp[COLS].values.astype(float),0,None); qt=np.array([np.interp(tau,xs,y) for y in Yq])      # qtau 와 같은 계산(벡터화)
        for i,(d,q5) in enumerate(zip(grp.date,grp['0.5'])):
            sh=m.shares_cached(o,key,sites,d,L)
            for s in sites:
                a=m.Y[s].get(d,np.nan)
                if np.isnan(a) or a==0: continue
                rows.append((m.kind(o),row,o,s,d,a,max(q5,0)*sh[s],qt[i]*sh[s]))
    return pd.DataFrame(rows,columns=['kind','row','origin','site','date','actual','q50','qt'])
def rows_for(lag,tau):
    m.Q80=tau; b=m.baseline(1 if lag=='A' else 7)      # 2행의 k를 τ 분위수로 (m.baseline 안의 kfac 이 모듈 전역 Q80 을 읽는다)
    r1=b.assign(row=1,qt=b.q50); r2=b.assign(row=2,qt=b.q80)
    c=chronos_tau('series',lag,'_v7',tau)             # v6 파일 하나에 3~7행이 모두 있다
    R=pd.concat([r1[['kind','row','origin','site','date','actual','q50','qt']],r2[['kind','row','origin','site','date','actual','q50','qt']],c],ignore_index=True)
    bad=R[R.qt.isna()][['origin','site','date']].drop_duplicates()      # v7: 직전 7일 평균이 없는 개소·날짜는 모든 행에서 제외(12번 스크립트와 같은 규칙)
    if len(bad): R=R.merge(bad.assign(_x=1),on=['origin','site','date'],how='left'); R=R[R._x.isna()].drop(columns='_x')
    return R
def cost(d,CAP=2000,Cu=60,Co=15):
    n=d.actual/CAP;p=d.qt/CAP; return (Cu*(n-p).clip(lower=0)+Co*(p-n).clip(lower=0)).sum()*1e4
def hit(d,CAP=2000): return float((d.actual/CAP<=d.qt/CAP).mean())
SC=[('기본(τ=0.8, Cu60·Co15)',0.8,60,15),('서비스 수준 0.7(Cu60·Co15)',0.7,60,15),('서비스 수준 0.9(Cu60·Co15)',0.9,60,15),
    ('Cu 30만 → 최적 τ=0.667',30/45,30,15),('Cu 90만 → 최적 τ=0.857',90/105,90,15),('Co 30만 → 최적 τ=0.667',60/90,60,30)]
if __name__=='__main__':
    cache={}; L=['# 서비스 수준·단가를 바꾼 백테스트 (격자 78개 원점, 관리소 나눔, 원 단위)\n']; rows=[]
    for lab,tau,Cu,Co in SC:
        for lag in 'AB':
            key=(lag,round(tau,4))
            if key not in cache: cache[key]=rows_for(lag,tau); print('done',key,flush=True)
            R=cache[key]; R=R[R.kind=='격자']; c={r:cost(R[R.row==r],Cu=Cu,Co=Co) for r in (1,2,3,4,5,6,7)}
            rows.append([lab,lag,f"{c[1]:,.0f}",f"{c[1]-c[2]:,.0f}",f"{c[2]-c[7]:,.0f}",f"{c[1]-c[7]:,.0f}",f"{(c[7]/c[1]-1)*100:+.1f}%",f"{hit(R[R.row==7]):.3f}",f"{hit(R[R.row==1]):.3f}"])
    L.append(pd.DataFrame(rows,columns=['가정','확정시점','1행 비용(직전7일평균)','서비스수준 보정 절감(1→2행)','모형 추가 절감(2→7행)','총 절감(1→7행)','7행/1행','7행 적중률','1행 적중률']).to_markdown(index=False))
    L.append('\n- 기본 행은 최종 FVA표(fva_final_tables.md)의 1행·7행 비용과 같아야 한다(검산).\n- τ=0.667·0.857은 Chronos 분위수 열(0.6/0.7, 0.8/0.9) 사이를 선형 보간한 값이다(근사). 2행의 k는 해당 τ 분위수로 다시 계산.\n- 단가가 바뀐 시나리오의 1행(직전 7일 평균)은 인력 수는 그대로이고 비용 단가만 바뀐다.')
    (OUT.parent/'results_new'/'가정바꾸기_백테스트.md').write_text('\n'.join(L),encoding='utf-8'); print('\n'.join(L))
