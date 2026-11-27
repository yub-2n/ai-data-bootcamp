# [v7] 부트스트랩: (1) 원점 단위 재추출(v6와 같은 방식, 정기 78개 원점, 5,000회) (2) 블록 부트스트랩(보조 검증: 연속된 원점을 블록으로 묶어 재추출)
# + 원점별 개선 집중도. 입력: eval_rows_v7.parquet, results_new/원점목록_v7.csv  출력: results_new/부트스트랩_v7.md
import pandas as pd, numpy as np
from common import OUT
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
N=pd.read_parquet(OUT/'eval_rows_v7.parquet'); N['origin']=pd.to_datetime(N.origin)
CAP,Cu,Co=2000,60,15; B=5000
def cst(d): n=d.actual/CAP;p=d.q80/CAP; return (Cu*(n-p).clip(lower=0)+Co*(p-n).clip(lower=0)).sum()   # 만원
def orig_boot(c,orig,pairs,seed=0):   # v6 의 boot() 와 같은 절차
    rng=np.random.default_rng(seed); out={}
    for a,b in pairs:
        f=lambda idx: sum(c[(b,orig[i])] for i in idx)/sum(c[(a,orig[i])] for i in idx)-1
        bs=[f(rng.integers(0,len(orig),len(orig))) for _ in range(B)]; out[(a,b)]=(f(range(len(orig)))*100,*np.percentile(bs,[2.5,97.5])*100)
    return out
def block_boot(c,orig,pairs,Lb,seed):  # 이동 블록 부트스트랩(원점 날짜 순서, 길이 Lb 블록을 복원추출해 n개로 자름)
    rng=np.random.default_rng(seed); n=len(orig); nb=int(np.ceil(n/Lb)); out={}
    for a,b in pairs:
        f=lambda idx: sum(c[(b,orig[i])] for i in idx)/sum(c[(a,orig[i])] for i in idx)-1
        bs=[]
        for _ in range(B):
            st=rng.integers(0,n-Lb+1,nb); bs.append(f(np.concatenate([np.arange(s,s+Lb) for s in st])[:n]))
        out[(a,b)]=tuple(np.percentile(bs,[2.5,97.5])*100)
    return out
V6PAIRS=[(1,6),(3,6),(5,6),(6,7)]; EXTRA=[(1,7),(2,7)]; PAIRS=[(1,7),(2,7),(1,6),(3,6),(5,6),(6,7)]
OT=pd.read_csv(RES/'원점목록_v7.csv',parse_dates=['원점']); OT=OT[OT.구분=='격자']
def grp(r): return '코리아 그랜드 페스티벌 원점' if r.코리아그랜드페스티벌_걸림 else '세종대왕 2025-05 원점' if r.세종대왕_걸림 else '설·추석 연휴 걸린 원점' if r.설추석연휴_걸림 else '그 외 원점'
G=dict(zip(OT.원점,OT.apply(grp,axis=1)))
L=['# v7 부트스트랩 (정기 78개 원점 기준, 비용 변화율의 95% 구간)\n','**방법**: (1) 원점 단위 재추출 = 78개 정기 원점을 복원추출해 78개로 다시 만들고 비용 변화율을 계산하는 것을 5,000회 반복(v6와 같은 절차, 시드 0). (2) 블록 부트스트랩(보조) = 연속된 원점 4개(약 1개월) 또는 8개를 한 블록으로 묶어 복원추출. 정기 원점은 7일 간격 연속 주라서 인접한 주끼리 계절·행사·기준선이 비슷할 수 있다. 원점 단위 재추출은 주를 서로 독립으로 보는 근사라 구간이 실제보다 좁게 나올 수 있고, 블록 방식은 이 의존성을 일부 반영하는 대신 독립 표본이 줄어 구간이 넓어진다. 명절 원점 4개는 표본이 너무 적어 하지 않았다. 구간은 이 78개 주 안에서의 안정성만 보여주며 다른 해나 다른 행사에서의 효과를 보장하지 않는다.\n']
for lag in 'AB':
    x=N[(N.lag==lag)&(N.kind=='격자')]; orig=sorted(x.origin.unique()); assert len(orig)==78,len(orig)
    c={(r,o):cst(x[(x.row==r)&(x.origin==o)]) for r in range(1,8) for o in orig}
    o1=orig_boot(c,orig,V6PAIRS,0); o1.update(orig_boot(c,orig,EXTRA,1)); b4=block_boot(c,orig,PAIRS,4,2); b8=block_boot(c,orig,PAIRS,8,3)
    rows=[]
    for a,b in PAIRS:
        d=np.array([c[(a,o)]-c[(b,o)] for o in orig]); tot=d.sum()
        rows.append([f'{a}→{b}행',f'{o1[(a,b)][0]:+.1f}%',f'[{o1[(a,b)][1]:+.1f}, {o1[(a,b)][2]:+.1f}]',f'[{b4[(a,b)][0]:+.1f}, {b4[(a,b)][1]:+.1f}]',f'[{b8[(a,b)][0]:+.1f}, {b8[(a,b)][1]:+.1f}]',f'{int((d>0).sum())} / {int((d<0).sum())} / {int((d==0).sum())}',f'{tot:,.0f}'])
    L+=[f'## 확정 시점 {lag} | 정기 78개 원점\n',pd.DataFrame(rows,columns=['비교','점추정','원점 재추출 95% 구간','블록 4주 95% 구간','블록 8주 95% 구간','비용이 줄어든/늘어난/같은 원점 수','총 절감(만원)']).to_markdown(index=False),'']
    for a,b in [(5,6),(6,7),(1,7),(2,7)]:
        d=pd.Series({o:c[(a,o)]-c[(b,o)] for o in orig}); tot=d.sum(); gg=d.groupby(d.index.map(G)).agg(['sum','count']); gg['총 절감 대비 몫']=((gg['sum']/tot*100).round(1).astype(str)+'%') if tot!=0 else '-'; gg['원점당 평균(만원)']=(gg['sum']/gg['count']).round(1); gg['sum']=gg['sum'].round(0)
        gg.columns=['절감액 합(만원)','원점 수','총 절감 대비 몫','원점당 평균(만원)']
        top=d.sort_values(ascending=False); L+=[f'### {lag} | {a}→{b}행 원점 유형별 절감 집중도 (총 {tot:,.0f}만원)\n',gg.to_markdown(),'',f'가장 큰 3개 원점의 절감: '+', '.join(f'{o.date()} {v:,.0f}만원' for o,v in top.head(3).items())+f' (3개 합 {top.head(3).sum()/tot*100 if tot!=0 else 0:.1f}%) | 가장 크게 늘어난 원점: {top.index[-1].date()} {top.iloc[-1]:,.0f}만원\n']
open(RES/'부트스트랩_v7.md','w',encoding='utf-8').write('\n'.join(L)); print('\n'.join(L[:8]))
