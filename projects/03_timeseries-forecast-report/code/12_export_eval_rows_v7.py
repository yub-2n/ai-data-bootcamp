# [v7] eval_rows_v7.parquet : 최종 평가 표. 학습·입력 모두 2023-01-01 이후 데이터, Colab 결과(원점 82개 = 정기 78 + 명절 4).
# 입력: chronos_series_A_v7.parquet, chronos_series_B_v7.parquet (05b_run_chronos_colab_v7.py --rows 3,4,5,6,7), grid_site_day.parquet, covariates_free_open.csv, 달력
# 방식은 '나눈 것'(관리소 단위 예측 -> 개소 배분) 하나뿐. 열: lag, method, row, kind, origin, site, group, date, actual, q50, q80, date_type
# v7에서 추가된 규칙(v6에는 해당 사례가 없었다): 직전 7일 평균이 없는 (lag, 원점, 개소, 날짜)는 FVA 1~7행 모두에서 제외해 모든 행이 같은 개소·날짜를 평가하게 한다.
#   제외 목록은 results_new/평가집합_제외행_v7.csv 에 남긴다. 대체값을 새로 만들지는 않는다.
import importlib.util, numpy as np, pandas as pd
from common import OUT, CODE, find
from origins_v7 import ORIGINS
spec=importlib.util.spec_from_file_location('m07',CODE/'07_timing_direct_compare.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
RES=OUT.parent/'results_new'; RES.mkdir(exist_ok=True)
g=pd.read_parquet(OUT/'grid_site_day.parquet'); GRP=g.groupby('site').group.first().to_dict()
cal=pd.read_csv(find('calendar_kr_2015_2025.csv'),parse_dates=['date']).set_index('date')
cv=pd.read_csv(OUT/'covariates_free_open.csv',parse_dates=['timestamp']); fo=cv[cv.item_id=='경복궁'].set_index('timestamp')
def date_type(site,d):
    r=fo.loc[d] if d in fo.index else None
    if r is not None:
        if site=='종묘' and cv[(cv.item_id=='종묘')&(cv.timestamp==d)].free_jongmyo_daeje.eq(1).any(): return '종묘대제'
        if r.free_holiday==1: return '명절 연휴 무료'
        if r.free_last_wed==1: return '마지막 수요일'
    if cal.loc[d,'is_holiday']==1: return '그 외 공휴일'
    return '주말' if d.dayofweek>=5 else '평일'
out=[]
for L in 'AB':
    b=m.baseline(1 if L=='A' else 7)
    out+=[b.assign(q80=b.q50,row=1,lag=L), b.assign(row=2,lag=L)]            # 1행: 직전7일 평균 그대로 / 2행: ×보정 k
    c=m.chronos_rows('series',L,'_v7'); assert sorted(c.row.unique())==[3,4,5,6,7] and c.origin.nunique()==len(ORIGINS), (L,c.origin.nunique(),len(ORIGINS))
    out.append(c.assign(lag=L))
R=pd.concat(out,ignore_index=True); R['method']='나눈 것'; R['group']=R.site.map(GRP)
# ---- 공통 평가 집합 ----
key=['lag','origin','site','date']
badmask=R.q50.isna()|R.q80.isna()
if badmask.any():
    bad=R[badmask].groupby(key).agg(actual=('actual','first'),행=('row',lambda s:','.join(map(str,sorted(set(s)))))).reset_index()
    bad.to_csv(RES/'평가집합_제외행_v7.csv',index=False,encoding='utf-8-sig')
    R=R.merge(bad[key].assign(_x=1),on=key,how='left'); R=R[R._x.isna()].drop(columns='_x')
    print('직전 7일 평균이 없어 모든 행에서 제외한 (lag,원점,개소,날짜):',len(bad),'-> results_new/평가집합_제외행_v7.csv')
else:
    pd.DataFrame(columns=key+['actual','행']).to_csv(RES/'평가집합_제외행_v7.csv',index=False,encoding='utf-8-sig'); print('제외한 행 없음')
cnt=R.groupby(['lag','kind','row']).size().unstack('row'); assert (cnt.nunique(axis=1)==1).all(), '행마다 평가 개소·일 수가 다르다:\n'+cnt.to_string()
dt={(s,d):date_type(s,d) for s,d in R[['site','date']].drop_duplicates().itertuples(index=False)}
R['date_type']=[dt[(s,d)] for s,d in zip(R.site,R.date)]
R=R[['lag','method','row','kind','origin','site','group','date','actual','q50','q80','date_type']].sort_values(['lag','row','origin','site','date']).reset_index(drop=True)
R.to_parquet(OUT/'eval_rows_v7.parquet'); print(R.shape); print(cnt.to_string())
CAP,Cu,Co=2000,60,15
def cost(d): need=d.actual/CAP; plan=d.q80/CAP; return (Cu*(need-plan).clip(lower=0)+Co*(plan-need).clip(lower=0)).sum()
print('\n비용(억원) 격자/명절')
for l in 'AB': print(l,{r:(round(cost(R[(R.lag==l)&(R.row==r)&(R.kind=="격자")])/1e4,2),round(cost(R[(R.lag==l)&(R.row==r)&(R.kind=="명절")])/1e4,2)) for r in range(1,8)})
