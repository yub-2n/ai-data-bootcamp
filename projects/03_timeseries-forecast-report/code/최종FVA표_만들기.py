from pathlib import Path
PACK=Path(__file__).resolve().parent.parent   # 패키지 폴더(code의 상위)
DATA=PACK/'data'; RES=PACK/'results_new'; RES.mkdir(exist_ok=True)
import pandas as pd, numpy as np
N=pd.read_parquet(DATA/'eval_rows_v7.parquet')
CAP,Cu,Co=2000,60,15
def cst(d): n=d.actual/CAP;p=d.q80/CAP; return (Cu*(n-p).clip(lower=0)+Co*(p-n).clip(lower=0)).sum()
NAMES={1:'직전 7일 평균',2:'+서비스수준 보정(k, 12주)',3:'Chronos-2 (과거 관람객만)',4:'+요일·휴관 규칙',5:'+공휴일·명절 연휴',6:'+무료 개방일(명절 연휴 무료, 마지막 수요일)',7:'+임시 무료 개방 행사(공지 반영)'}
def table(lag,kind,method='나눈 것',ci=False):
    x=N[(N.lag==lag)&(N.kind==kind)&(N.method==method)]
    rows=[]; base=cst(x[x.row==1])
    for r in sorted(x.row.unique()):
        y=x[x.row==r]; n=y.actual/CAP;p=y.q80/CAP
        rows.append([r,NAMES[r],len(y),f"{(y.actual-y.q50).abs().sum()/y.actual.sum()*100:.1f}%",f"{cst(y)*1e4:,.0f}",f"{(cst(y)/base-1)*100:+.1f}%",f"{(n<=p).mean():.3f}"])
    return pd.DataFrame(rows,columns=['행','구성','n(개소·일)','WAPE(전체 합)','비용(원)','1행 대비','적중률']).to_markdown(index=False)
def boot(lag,pairs=[(1,6),(3,6),(5,6),(6,7)],B=5000,seed=0):
    rng=np.random.default_rng(seed); x=N[(N.lag==lag)&(N.kind=='격자')&(N.method=='나눈 것')]; orig=sorted(x.origin.unique())
    c={(r,o):cst(x[(x.row==r)&(x.origin==o)]) for r in range(1,8) for o in orig}
    out={}
    for a,b in pairs:
        f=lambda idx: sum(c[(b,orig[i])] for i in idx)/sum(c[(a,orig[i])] for i in idx)-1
        bs=[f(rng.integers(0,len(orig),len(orig))) for _ in range(B)]
        out[(a,b)]=(f(range(len(orig)))*100,*np.percentile(bs,[2.5,97.5])*100)
    return out
L=[]
for lag in 'AB':
    L.append(f'\n### 확정 시점 {lag} | 격자(연속 78개 원점) | 관리소 나눔 (본표)\n\n'+table(lag,'격자'))
    b=boot(lag); L.append('\n구간 추정(원점 78개를 5,000번 다시 뽑는 부트스트랩, 95%): '+', '.join(f'{a}행→{c}행 {v[0]:+.1f}% [{v[1]:+.1f}, {v[2]:+.1f}]' for (a,c),v in b.items()))
    L.append(f'\n### 확정 시점 {lag} | 명절(4개 원점, 격자와 합치지 않음) | 관리소 나눔\n\n'+table(lag,'명절'))
FVA='\n'.join(L)
# A vs B
def c6(lag,row,kind='격자'): return cst(N[(N.lag==lag)&(N.kind==kind)&(N.method=='나눈 것')&(N.row==row)])
AB=pd.DataFrame([[kind,r,f"{c6('A',r,kind)*1e4:,.0f}",f"{c6('B',r,kind)*1e4:,.0f}",f"{(c6('B',r,kind)/c6('A',r,kind)-1)*100:+.1f}%"] for kind in ['격자','명절'] for r in [1,6,7]],columns=['묶음','행','A 비용(원)','B 비용(원)','B가 A보다']).to_markdown(index=False)
open(RES/'fva_final_tables.md','w',encoding='utf-8').write('# 최종 FVA 표 (v7: 학습·입력 모두 2023-01-01 이후 데이터. 7행 = 6행 + 임시 무료 행사(공지 날짜가 확정 시점 이전인 것만 반영) — 관리소 나눔만)\n'+FVA+'\n\n## A vs B\n\n'+AB)
print(FVA); print(AB)
