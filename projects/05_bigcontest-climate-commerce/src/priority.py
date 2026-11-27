"""
빅콘테스트 2026 — 지원 우선순위 점수 (src/priority.py)

단위: 지역(춘천·강남) × 업종 그룹(7개) = 14칸.  "상권 = 시·군·구 × 업종" (팀 가정, 확정 전)

지표 4개 → 순위 백분위(1등 1.0, 꼴찌 0) → 가중합(0~100점)
  ① 점포당 기대 손실 (40) : 사건당 사라진 결제액(방법1, 택시 제외) × 시즌당 호우 사건 수(30년 평균) ÷ 점포 수
                            단, 사건당 손실의 90% 구간이 0을 포함하면 0 ("손실이 확인되지 않음", 2026-10-21 기본안)
  ② 순손실률 N5      (20) : 주 모형의 외지인 결제건수 N5
  ③ 외지인 의존도    (20) : 결제건수 중 외지인 비중 — 뜻이 지역마다 달라 "지역 안에서만" 순위
  ④ 확실성           (20) : N5 90% 구간 아래쪽 끝(5%)이 0보다 크면 1, 아니면 0
등급: 70점 이상 "지원 1순위", 40~70점 "지원 2순위", 40점 미만 "관찰"

- 업종 연결표: data/processed/업종연결표.csv (상가정보 소분류 → 카드 업종 그룹). 팀이 고치면 그 내용이 그대로 반영됩니다.
  연결표를 처음 만들 때만:  python -B src/priority.py --write-mapping
- 파일을 저장하지 않습니다(위 옵션 제외). 금액 구간의 난수 시드는 event_study.py와 같은 2026입니다.
- 프로젝트 폴더에서 실행:  python -B src/priority.py
"""
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, 'src')
from prep import GROUPS
from event_study import REGION_CARD, load_all, main_model
from rain_followup import money_table

GROUP_NAMES = list(GROUPS)
REGIONS = ['춘천', '강남']
STORE_DIR = Path('data/external/상가정보_2025')
STORE_VERSIONS = {'2025-06': '20250630', '2025-10': '20251030', '2025-12': '20251231'}
STORE_MAIN = '2025-10'
STORE_SGG = {'춘천': ('강원', '춘천시'), '강남': ('서울', '강남구')}
MAPPING_FILE = Path('data/processed/업종연결표.csv')
RAIN30_FILE = Path('data/external/asos_rain_30yr/asos_108_101_daily_rain_19950701_20250630.csv')
RAIN30_NAME = {'춘천': '춘천', '강남': '서울'}
WEIGHTS = {'점포당기대손실': 40, 'N5': 20, '외지인비중': 20, '확실성': 20}
WITHIN_REGION = {'외지인비중'}                  # 지역 안에서만 순위를 매기는 지표
GRADES = [(70, '지원 1순위'), (40, '지원 2순위'), (-np.inf, '관찰')]


# ═══════════════════════════════════════════════════════════════
# 1. 업종 연결표 (상가정보 소분류 → 카드 업종 그룹)
# ═══════════════════════════════════════════════════════════════
# (대분류, 중분류) → 그룹. 소분류 예외는 아래 SUB_RULE이 먼저 적용됩니다.  '제외' = 개인 카드 결제와 맞지 않음
MID_RULE = {
    ('음식', None): ('외식', '높음'),
    ('소매', '식료품 소매'): ('식료품', '높음'), ('소매', '종합 소매'): ('식료품', '높음'),
    ('소매', '음료 소매'): ('식료품', '보통'), ('소매', '담배 소매'): ('식료품', '낮음'),
    ('소매', '연료 소매'): ('교통·숙박', '보통'),
    ('소매', None): ('상품쇼핑', '보통'),
    ('보건의료', None): ('의료·약국', '높음'),
    ('과학·기술', '수의'): ('의료·약국', '높음'),
    ('과학·기술', '법무관련'): ('생활·교육서비스', '보통'), ('과학·기술', '회계·세무'): ('생활·교육서비스', '보통'),
    ('과학·기술', None): ('제외', '높음'),
    ('숙박', None): ('교통·숙박', '높음'),
    ('시설관리·임대', '여행사·보조'): ('교통·숙박', '보통'), ('시설관리·임대', '운송장비 대여'): ('교통·숙박', '낮음'),
    ('시설관리·임대', None): ('제외', '높음'),
    ('예술·스포츠', None): ('여가', '높음'),
    ('수리·개인', '욕탕·신체관리'): ('여가', '보통'),
    ('수리·개인', None): ('생활·교육서비스', '보통'),
    ('교육', None): ('생활·교육서비스', '높음'),
    ('부동산', None): ('생활·교육서비스', '보통'),
}
SUB_RULE = {
    '빵/도넛': ('식료품', '보통', '카드에서는 제과점=식료품'),
    '떡/한과': ('식료품', '낮음', '카드에서는 제과점·기타식품에 가까움'),
    '약국': ('의료·약국', '높음', ''),
    '의료기기 소매업': ('의료·약국', '낮음', ''),
    '화장품 소매업': ('상품쇼핑', '높음', '카드에서는 화장품=상품쇼핑'),
    '운동용품 소매업': ('여가', '보통', '카드에서는 스포츠/레저용품=여가'),
    '자전거 소매업': ('여가', '낮음', ''),
    '복권 발행/판매업': ('제외', '높음', '카드에서 상품권/복권은 제외 업종'),
    '무도 유흥 주점': ('여가', '보통', '카드에서는 유흥업소=여가'),
    '일반 유흥 주점': ('여가', '보통', '카드에서는 유흥업소=여가'),
}
MEMO = {
    '주점': '카드의 주류판매=외식 (유흥 주점 2개 소분류만 여가로 나눔)',
    '연료 소매': '주유소·LPG (카드 교통·숙박). 택시·버스·주차장은 점포가 없어 상가정보에 없음',
}


def load_stores(version, reg):
    """상가정보 CSV에서 지역(시군구)의 점포를 읽습니다 (업종 열만)."""
    sido, sgg = STORE_SGG[reg]
    f = glob.glob(str(STORE_DIR / f'소상공인시장진흥공단_상가(상권)정보_{STORE_VERSIONS[version]}' / f'*_{sido}_*.csv'))[0]
    d = pd.read_csv(f, usecols=['시군구명', '상권업종대분류명', '상권업종중분류명', '상권업종소분류명'], dtype=str)
    d = d.apply(lambda c: c.str.strip())          # 업종 이름 끝에 공백이 붙은 경우가 있음 (예: '법무관련 ')
    return d[d['시군구명'] == sgg]


def mapping_from_rules():
    """규칙(MID_RULE, SUB_RULE)으로 연결표를 만듭니다. 2025년 파일 3개의 춘천·강남에 있는 소분류 전체."""
    s = pd.concat([load_stores(v, r) for v in STORE_VERSIONS for r in REGIONS])
    cats = s[['상권업종대분류명', '상권업종중분류명', '상권업종소분류명']].drop_duplicates()
    rows = []
    for big, mid, sub in cats.itertuples(index=False):
        if sub in SUB_RULE:
            grp, conf, memo = SUB_RULE[sub]
        else:
            grp, conf = MID_RULE.get((big, mid)) or MID_RULE[(big, None)]
            memo = MEMO.get(mid, '')
        rows.append({'대분류': big, '중분류': mid, '소분류': sub, '카드그룹': grp, '확실도': conf, '메모': memo})
    return pd.DataFrame(rows).sort_values(['대분류', '중분류', '소분류']).reset_index(drop=True)


def load_mapping():
    """연결표 CSV를 읽습니다. 카드그룹 값이 7그룹 또는 '제외'인지 확인합니다."""
    m = pd.read_csv(MAPPING_FILE, encoding='utf-8-sig', dtype=str)
    bad = set(m['카드그룹']) - set(GROUP_NAMES) - {'제외'}
    if bad:
        raise ValueError(f'연결표에 알 수 없는 카드그룹이 있습니다: {bad}')
    return m


def store_counts(mapping, version=STORE_MAIN):
    """지역 × 카드그룹 점포 수. 연결표에 없는 소분류가 있으면 알려 줍니다."""
    lookup = mapping.set_index('소분류')['카드그룹']
    out = {}
    for reg in REGIONS:
        s = load_stores(version, reg)
        g = s['상권업종소분류명'].map(lookup)
        if g.isna().any():
            print(f'[경고] {version} {reg}: 연결표에 없는 소분류 {sorted(s.loc[g.isna(), "상권업종소분류명"].unique())} '
                  f'({int(g.isna().sum())}곳) → 계산에서 빠짐')
        out[reg] = g.value_counts()
    return pd.DataFrame(out).reindex(GROUP_NAMES).fillna(0).astype(int)


# ═══════════════════════════════════════════════════════════════
# 2. 지표 계산
# ═══════════════════════════════════════════════════════════════
def season_events():
    """30년(1995~2024) 7~12월 시즌당 호우 사건 수 평균. 사건 = 30mm 이상 날이 이어진 묶음 (prep.py와 같은 규칙)."""
    d = pd.read_csv(RAIN30_FILE, encoding='utf-8-sig', parse_dates=['일시'])
    d = d[(d['일시'].dt.month >= 7) & (d['일시'].dt.year <= 2024)]
    out = {}
    for reg, name in RAIN30_NAME.items():
        g = d[d['지점명'] == name]
        counts = []
        for _, s in g.groupby(g['일시'].dt.year):
            wet = s.loc[s['일강수량(mm)'] >= 30, '일시'].sort_values()
            counts.append(int((wet.diff().dt.days.fillna(99) > 1).sum()))
        out[reg] = float(np.mean(counts))
    return out


def outsider_share(data):
    """지역 × 그룹의 외지인 결제건수 비중(%). 거주지 '정보없음'은 뺍니다."""
    c = data['card']
    c = c[c['seg'] != 'unk']
    out = {}
    for reg in REGIONS:
        s = c[c['MCT_SGG_CD'] == REGION_CARD[reg]].groupby(['group', 'seg'])['USE_CNT'].sum().unstack()
        out[reg] = 100 * s['out'] / (s['out'] + s['loc'])
    return pd.DataFrame(out).reindex(GROUP_NAMES)


def indicators(data, stores, events):
    """14칸의 지표 표."""
    share = outsider_share(data)
    rows = []
    for reg in REGIONS:
        money, _, _ = money_table(data, reg)
        for grp in GROUP_NAMES:
            n5 = main_model(data, reg, grp)['N5']                 # (점추정, 5%, 95%)
            loss = money.loc[grp, '방법1(만원/사건)'] * 1e4        # 원/사건
            n_store = int(stores.loc[grp, reg])
            rows.append({'지역': reg, '그룹': grp,
                         '사건당손실(만원)': loss / 1e4, '사건당손실_5%(만원)': money.loc[grp, '방법1_5%'],
                         '시즌당사건': events[reg], '점포수': n_store,
                         '점포당기대손실_원값': loss * events[reg] / n_store if n_store else np.nan,  # 원/점포/시즌
                         'N5': n5[0], 'N5_5%': n5[1], 'N5_95%': n5[2],
                         '외지인비중': share.loc[grp, reg],
                         '확실성': float(n5[1] > 0)})
    return apply_zero_rule(pd.DataFrame(rows))


def apply_zero_rule(ind):
    """
    기본안 규칙: 사건당 손실의 90% 구간 아래쪽 끝(5%)이 0 이하이면 "손실이 확인되지 않음"으로 보고
    ① 점포당 기대 손실을 0으로 둡니다. (11번 호우 후속 결정: 구간이 0을 포함하는 금액은 쓰지 않음)
    원래 값은 '점포당기대손실_원값'에 남깁니다.
    """
    ind = ind.copy()
    ind['금액확인'] = ind['사건당손실_5%(만원)'] > 0
    ind['점포당기대손실'] = ind['점포당기대손실_원값'].where(ind['금액확인'], 0.0)
    return ind


# ═══════════════════════════════════════════════════════════════
# 3. 점수
# ═══════════════════════════════════════════════════════════════
def pct_rank(s):
    """순위 백분위: 가장 큰 값 1.0, 가장 작은 값 0.0 (같은 값은 평균 순위)."""
    r = s.rank(method='average')
    return (r - 1) / (len(s) - 1) if len(s) > 1 else r * 0 + 1


def score(ind, weights=None):
    """지표 → 백분위 → 가중합 점수(0~100)와 등급. weights에서 0이거나 빠진 지표는 쓰지 않습니다."""
    weights = {k: v for k, v in (weights or WEIGHTS).items() if v}
    t = ind[['지역', '그룹']].copy()
    for k in weights:
        if k in WITHIN_REGION:
            t[f'p_{k}'] = ind.groupby('지역')[k].transform(pct_rank)
        else:
            t[f'p_{k}'] = pct_rank(ind[k])
    total = sum(weights.values())
    t['점수'] = 100 * sum(t[f'p_{k}'] * w for k, w in weights.items()) / total
    t['순위'] = t['점수'].rank(ascending=False, method='min').astype(int)
    t['등급'] = t['점수'].map(lambda v: next(lab for cut, lab in GRADES if v >= cut))
    return t.sort_values('순위').reset_index(drop=True)


def sensitivity(data, mapping, events, ind_main):
    """가중치·점포 기준 시점을 바꿔도 순위가 유지되는지: 시나리오별 순위 표와 기본안과의 비교."""
    scen = {'기본안 (40/20/20/20)': (WEIGHTS, ind_main),
            '같은 가중치 (25×4)': ({k: 25 for k in WEIGHTS}, ind_main)}
    for k in WEIGHTS:
        scen[f'{k} 빼기'] = ({j: w for j, w in WEIGHTS.items() if j != k}, ind_main)
    ind_raw = ind_main.copy()                                # 옛 기본안: 구간이 0을 포함해도 금액 점추정을 그대로 씀
    ind_raw['점포당기대손실'] = ind_raw['점포당기대손실_원값']
    scen['불확실한 금액도 그대로 (옛 기본안)'] = (WEIGHTS, ind_raw)
    for ver in ['2025-06', '2025-12']:
        ind_v = ind_main.copy()
        st = store_counts(mapping, ver)
        ind_v['점포수'] = [int(st.loc[g, r]) for r, g in zip(ind_v['지역'], ind_v['그룹'])]
        ind_v['점포당기대손실_원값'] = ind_v['사건당손실(만원)'] * 1e4 * ind_v['시즌당사건'] / ind_v['점포수']
        scen[f'점포 수 {ver} 기준'] = (WEIGHTS, apply_zero_rule(ind_v))
    w0, i0 = scen['기본안 (40/20/20/20)']
    base = score(i0, w0).set_index(['지역', '그룹'])['순위']
    top4 = set(base[base <= 4].index)
    ranks, summ = {}, []
    for name, (w, ind) in scen.items():
        r = score(ind, w).set_index(['지역', '그룹'])['순위']
        ranks[name] = r
        summ.append({'시나리오': name,
                     '기본안 상위4와 겹침': f'{len(top4 & set(r[r <= 4].index))}/4',
                     '순위 상관(스피어만)': float(base.corr(r.reindex(base.index), method='spearman'))})
    return pd.DataFrame(ranks).reindex(base.sort_values().index), pd.DataFrame(summ)


def run(data=None):
    """전체 실행: (지표, 점수, 시나리오별 순위, 시나리오 요약, 점포 수, 시즌당 사건)."""
    data = data or load_all()
    mapping = load_mapping()
    stores = store_counts(mapping)
    events = season_events()
    ind = indicators(data, stores, events)
    sc = score(ind)
    ranks, summ = sensitivity(data, mapping, events, ind)
    return ind, sc, ranks, summ, stores, events


def main():
    if '--write-mapping' in sys.argv:
        MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
        m = mapping_from_rules()
        m.to_csv(MAPPING_FILE, index=False, encoding='utf-8-sig')
        print('연결표 저장:', MAPPING_FILE, len(m), '행')
        print(m['카드그룹'].value_counts().to_string())
        return
    pd.set_option('display.width', 250)
    pd.set_option('display.float_format', lambda v: f'{v:,.2f}')
    ind, sc, ranks, summ, stores, events = run()
    print('시즌당 호우 사건(30년 평균):', events)
    print('\n== 점포 수 (2025-10) ==\n', stores.to_string())
    print('\n== 지표 ==\n', ind.to_string(index=False))
    print('\n== 점수와 등급 (기본안) ==\n', sc.to_string(index=False))
    print('\n== 민감도: 시나리오별 순위 ==\n', ranks.to_string())
    print('\n', summ.to_string(index=False))


if __name__ == '__main__':
    main()
