# -*- coding: utf-8 -*-
"""대시보드 사례 탭 12건 뽑기 (기준: docs/사례뷰어_선정기준.md)

실행: insurance-cx 폴더에서  python outputs/qual/사례뷰어_선정.py
필요한 파일: data/interim/cases.csv, data/interim/difficulty_id_map.csv, data/processed/difficulty.csv
결과: outputs/qual/사례뷰어_선정.csv

- 칸: 쟁점 유형 R1(cases.csv의 issue_type) 3개 x cited(1/0) 2개 = 6칸
- 칸마다 sample(frac=1, random_state=42)로 섞은 순서대로 앞 2건
- 바꾸기(신청인 정보 / 약관 아님 / 잘림)는 사람이 문구 상태만 보고 정한다.
  2026-11-04 실행에서는 바꾼 사건이 없었다(REPLACE가 비어 있음).
  바꿔야 하면 REPLACE에 {'바꿀 case_key': '이유'}를 적고 다시 돌린다.
"""
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
REPLACE = {}          # 예: {'2009-32': '잘림'}
ISSUES = ['보상범위·정의', '면책', '고지·설명']

cs = pd.read_csv(BASE / 'data/interim/cases.csv', dtype={'case_key': str}, encoding='utf-8-sig')
a = cs[cs['exclude_reason'].isna()].copy()
idm = pd.read_csv(BASE / 'data/interim/difficulty_id_map.csv', encoding='utf-8-sig')
idm = idm[~((idm['case_key'] == '2009-29') & (idm['diff_id'] != 'D204'))]   # stats와 같이 D204 사용
dif = pd.read_csv(BASE / 'data/processed/difficulty.csv', encoding='utf-8-sig')[['diff_id', 'difficulty_index']]
a = a.merge(idm, on='case_key', how='left').merge(dif, on='diff_id', how='left')
assert len(a) == 157, len(a)
assert a['difficulty_index'].notna().all()

rows = []
for it in ISSUES:
    for c in [1, 0]:
        cell = a[(a['issue_type'] == it) & (a['cited'] == c)].sample(frac=1, random_state=42)
        picked, pending = [], []
        for _, r in cell.iterrows():
            if len(picked) == 2:
                break
            if r['case_key'] in REPLACE:
                pending.append((r['case_key'], REPLACE[r['case_key']]))
                continue
            frm = pending.pop(0) if pending else ('', '')
            picked.append(dict(case_key=r['case_key'], issue_type_R1=it, cited=c,
                               clause_text=r['clause_text'], difficulty_index=r['difficulty_index'],
                               replaced=1 if frm[0] else 0, replace_reason=frm[1], replaced_from=frm[0]))
        if len(picked) < 2:
            print(f'{it}/{c}: 후보 {len(cell)}건, {len(picked)}건만 채움')
        rows += picked

out = pd.DataFrame(rows)
out.to_csv(BASE / 'outputs/qual/사례뷰어_선정.csv', index=False, encoding='utf-8-sig')
print(out[['case_key', 'issue_type_R1', 'cited', 'replaced']].to_string(index=False))
