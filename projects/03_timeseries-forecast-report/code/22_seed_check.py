# Chronos-2 반복 실행 확인: 같은 입력으로 Colab을 두 번 돌린 결과가 같은지 비교한다.
# 사용: python 22_seed_check.py   (data/ 에 chronos_series_A_v7_o2026-01-01.parquet(1회차) 와 ..._rerun.parquet(2회차) 가 있어야 함)
import pandas as pd, numpy as np, sys
from common import OUT, OUT as D
RES=OUT.parent/'results_new'; Q=[f'0.{i}' for i in range(1,10)]; L=['# Chronos-2 반복 실행 확인 (최종 모형 7행 · 확정 시점 A · 원점 2026-01-01, 계열 9개 × 7일 × 분위수 9개, 2023-01-01 이후 데이터)\n']; rows=[]
for lag in 'A':
    a=pd.read_parquet(D/f'chronos_series_{lag}_v7_o2026-01-01.parquet').sort_values(['key','date']).reset_index(drop=True)
    b=pd.read_parquet(D/f'chronos_series_{lag}_v7_o2026-01-01_rerun.parquet').sort_values(['key','date']).reset_index(drop=True)
    assert (a[['key','date']].values==b[['key','date']].values).all(), '행 순서/키가 다름'
    d=(a[Q].astype(float)-b[Q].astype(float)).abs(); rel=(d/a[Q].astype(float).abs().clip(lower=1)).max().max()
    rows.append([lag,len(a),f'{d.max().max():.6g}',f'{rel:.3g}',bool((a[Q].values==b[Q].values).all())])
L.append(pd.DataFrame(rows,columns=['확정 시점','행 수','최대 절대 차이(명)','최대 상대 차이','완전히 같음']).to_markdown(index=False))
L.append('\n해석: 완전히 같으면 같은 입력에서 결과가 반복된다. 다르면 차이의 크기를 보고, 그 차이가 인원 수(÷2,000)에서 얼마인지 따져 본다.')
(RES/'시드확인.md').write_text('\n'.join(L),encoding='utf-8'); print('\n'.join(L))
