"""[v7] 백테스트 원점 목록: 이 파일 한 곳에서만 정의한다 (다른 스크립트는 여기서 import).
정기 격자 78개 = 2024-07-02(화)부터 7일 간격, 마지막 2025-12-23(마지막 평가일 2025-12-29). 명절 4개는 v6와 같다.
환경변수 ORIGINS_SET=v6 이면 v6의 26개 격자를 쓴다(회귀 시험 전용, 분석에는 쓰지 않는다)."""
import os, pandas as pd
_SET=os.environ.get('ORIGINS_SET','v7')
if _SET=='v7':
    GRID=[pd.Timestamp('2024-07-02')+pd.Timedelta(days=7*i) for i in range(78)]
    assert len(GRID)==78 and GRID[0]==pd.Timestamp('2024-07-02') and GRID[-1]==pd.Timestamp('2025-12-23'), '정기 원점 78개 검증 실패'
    assert GRID[-1]+pd.Timedelta(days=6)==pd.Timestamp('2025-12-29'), '마지막 평가일 검증 실패'
elif _SET=='v6':
    GRID=[pd.Timestamp('2025-07-01')+pd.Timedelta(days=7*i) for i in range(26)]
else: raise ValueError(_SET)
HOL=[pd.Timestamp(x) for x in ['2024-02-07','2024-09-14','2025-01-25','2025-10-02']]
ORIGINS=GRID+HOL
assert len(set(ORIGINS))==len(ORIGINS), '격자와 명절 원점 날짜가 겹침'
