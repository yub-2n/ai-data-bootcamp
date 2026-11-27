# 가이드 「자주 하는 실수」 중 이 분석에서 확인한 것의 크기를 측정한다 → results_new/자주하는실수_측정.md
import importlib.util, numpy as np, pandas as pd
from common import OUT, CODE
spec=importlib.util.spec_from_file_location('m07',CODE/'07_timing_direct_compare.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
RES=OUT.parent/'results_new'
L=['# 자주 하는 실수: 측정한 크기와 막은 방법 (격자 78개 원점, 확정 시점 A, 평가는 문 연 개소·일)\n']
# ---- 실수 1·2: 휴관일의 0, 빠진 날짜를 수요로 쓰기 (직전 7일 평균 1행으로 측정) ----
rows=[]
for o in m.GRID:
    last=o-pd.Timedelta(days=1)
    for s,y in m.Y.items():
        if y.index.min()>o-pd.Timedelta(days=14): continue
        days=pd.date_range(last-pd.Timedelta(days=6),last)
        zero=np.mean([y.get(d,0.0) if not np.isnan(y.get(d,0.0)) else 0.0 for d in days])   # 휴관 0·빠진 날도 0으로 평균
        ours=m.prev7(y,last)                                                                  # 문 연 날만 평균(우리 규칙)
        for d in pd.date_range(o,o+pd.Timedelta(days=6)):
            a=y.get(d,np.nan)
            if np.isnan(a) or a==0 or np.isnan(ours): continue
            rows.append((s,a,zero,ours))
r=pd.DataFrame(rows,columns=['site','a','zero','ours'])
w=lambda c:(r.a-r[c]).abs().sum()/r.a.sum()
def cost(c):
    n=r.a/2000; p=r[c]/2000; return (60*(n-p).clip(lower=0)+15*(p-n).clip(lower=0)).sum()*1e4
L.append('## 실수 1·2. 휴관일의 0(그리고 빠진 날)을 수요로 평균에 넣기\n')
L.append(pd.DataFrame([['0·빠진 날을 넣고 7일 평균',f'{w("zero")*100:.1f}%',f'{cost("zero"):,.0f}'],['문 연 날만 평균(우리 규칙, 1행)',f'{w("ours")*100:.1f}%',f'{cost("ours"):,.0f}']],columns=['직전 7일 평균 계산','WAPE(전체 합)','비용(원, 보정 없음 q=평균)']).to_markdown(index=False))
L.append(f'\n해석: WAPE는 0을 넣은 쪽이 오히려 {(w("ours")-w("zero"))*100:.1f}%p 낮지만(추정: 1행 예측이 무료 개방일 때문에 전반적으로 높아, 평균을 낮추면 오차 합이 줄어듦), 비용은 {(cost("zero")/cost("ours")-1)*100:+.1f}% 더 크다. WAPE 한 지표로는 이 실수가 드러나지 않고 비용(모자란 인원의 단가)으로 드러난다.\n\n측정 개소·일 {len(r):,}개. 막은 방법: 휴관일(total=0)과 기록 없는 날은 평균·학습·평가에서 NaN으로 빼고(방법 1), 직전 7일 평균은 문 연 날만 쓴다. Chronos 입력도 휴관일은 NaN(행은 유지).\n')
# ---- 실수 4: 합계로 평가 ----
d=pd.read_parquet(OUT/'eval_rows_v7.parquet'); d=d[(d.method=='나눈 것')&(d.lag=='A')&(d.kind=='격자')]
out=[]
for row in (1,7):
    x=d[d.row==row]; ws=(x.actual-x.q50).abs().sum()/x.actual.sum()
    t=x.groupby(['origin','date']).agg(a=('actual','sum'),p=('q50','sum')); wt=(t.a-t.p).abs().sum()/t.a.sum()
    out.append([row,f'{ws*100:.1f}%',f'{wt*100:.1f}%'])
L.append('## 실수 4. 합계로 평가\n'); L.append(pd.DataFrame(out,columns=['FVA 행','개소·일 단위 WAPE(우리 방식)','그날 23개소를 합친 뒤 WAPE(잘못된 방식)']).to_markdown(index=False))
L.append('\n막은 방법: 모든 지표를 개소 × 날짜 단위로 계산하고 합쳐서 계산하지 않았다.\n')
# ---- 실수 5: 유료 0(또는 낮은 유료 비중)을 무료 개방일로 봄 ----
h=pd.read_parquet(OUT/'heritage_visitors_daily.parquet'); h=h[(h.date>='2023-01-01')&(h.total>0)].copy(); h['ps']=h.paid/h.total
cv=pd.read_csv(OUT/'covariates_free_open.csv',parse_dates=['timestamp']).rename(columns={'item_id':'site','timestamp':'date'})
mm=h.merge(cv,on=['site','date']); mm['file']=((mm.free_holiday==1)|(mm.free_last_wed==1)).astype(int); mm['rule']=(mm.ps<0.15).astype(int)
mm['grp']=mm.site.map(lambda s:'궁' if s in['경복궁','덕수궁','창경궁','창덕궁'] else '종묘' if s=='종묘' else '왕릉')
t=mm.groupby('grp').apply(lambda g:pd.Series({'개소·일':len(g),'파일이 무료로 표시':int(g.file.sum()),'유료 비중 15% 미만 규칙이 무료로 판정':int(g.rule.sum()),'규칙만 무료(오분류)':int(((g.rule==1)&(g.file==0)).sum()),'파일만 무료(놓침)':int(((g.rule==0)&(g.file==1)).sum())}),include_groups=False)
L.append('## 실수 5. 유료 비중이 낮은 날을 무료 개방일로 판정 (2023-01-01~2025-12-31, 문 연 개소·일)\n'); L.append(t.to_markdown())
L.append('\n막은 방법: 무료 개방일은 유료 비중이 아니라 달력 규칙(설·추석 연휴, 매월 마지막 수요일)과 공지로 정한 파일을 쓴다. 이 규칙이 만든 표시와 새 파일의 차이는 free_holiday 기준 0/1,096일(Colab 확인, 2023-01-01~2025-12-31).\n')
L.append('## 실수 3. 미래 정보 누수\n\n- 날씨는 모형에 쓰지 않았다(「완벽한 예보 가정」 행 없음). 모형에 들어간 공변량은 달력으로 미리 알 수 있는 값(요일, 정기 휴관, 공휴일, 명절 연휴, 무료 개방 표시, 이웃 개소 휴관)뿐이다.\n- 서비스수준 보정의 k는 확정 시점(A: 원점 전날, B: 원점 7일 전)까지 끝난 주의 실적으로만 계산한다(`07_timing_direct_compare.py`의 `kfac`).\n- 개소 나누기 비중도 확정 시점 이전 4주 기록만 쓴다.\n')
(RES/'자주하는실수_측정.md').write_text('\n'.join(L),encoding='utf-8'); print('\n'.join(L))
