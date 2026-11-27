"""공통 설정: 데이터 위치(패키지 구조).
패키지 폴더/ code(이 파일), data(입력·결과). 원본 파일(heritage_visitors_daily.parquet 등)은 data 안이나 패키지 폴더 위쪽 어딘가에 두면 find()가 찾는다."""
from pathlib import Path
CODE=Path(__file__).resolve().parent; WORK=CODE.parent; ROOT=WORK.parent; OUT=WORK/'data'; OUT.mkdir(exist_ok=True)
def find(name):
    hit=list(OUT.glob(name))
    if not hit: hit=[p for p in ROOT.rglob(name) if p.parent!=OUT and WORK not in p.parents]
    if not hit: raise FileNotFoundError(f'{name} 을(를) {OUT} 또는 {ROOT} 아래에서 찾지 못했습니다')
    return hit[0]
