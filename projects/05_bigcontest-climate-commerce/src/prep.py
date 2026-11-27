"""
빅콘테스트 2026 전처리 (전처리_명세서.md 의 P1~P10)

- 원본 파일은 읽기만 합니다. 이 모듈은 아무 파일도 저장하지 않습니다.
- 각 단계마다 명세서의 기대값과 비교해 출력합니다. 다르면 '[다름]'이라고 보여 주며,
  값을 임의로 맞추지 않습니다.
- 난수를 쓰지 않으므로 같은 입력이면 항상 같은 결과가 나옵니다.

사용법 (프로젝트 폴더를 기준으로 실행):
    import sys; sys.path.append('src')
    from prep import *
"""
import glob
from pathlib import Path

import numpy as np
import pandas as pd

# ═══ 경로 (프로젝트 폴더 기준 상대경로) ═══
ROOT = Path('.')
CARD_DIR = ROOT / '2026빅콘테스트_신한카드_데이터_레이아웃'
SK_DIR = ROOT / '2026빅콘테스트_sk통신인구_데이터_레이아웃'
HOLIDAY_FILE = ROOT / 'korea_holiday_calendar_20250701_20260101.csv'
VISITOR_FILE = ROOT / 'visitors_2025H2_all.csv'
ASOS_DIR = ROOT

# ═══ 분석 구간 (P8): 2025-07-01 ~ 2025-12-31, 184일 ═══
DAYS = pd.date_range('2025-07-01', '2025-12-31', freq='D')


def warn(msg):
    """경고 문구 출력."""
    print('[경고]', msg)


def check(name, got, expect):
    """결과(got)와 명세서 기대값(expect)을 비교해 출력합니다. 다르면 [다름]으로 표시."""
    ok = got == expect
    print('[일치]' if ok else '[다름]', name, '| 결과:', got, '| 기대값:', expect)
    return ok


# ═══════════════════════════════════════════════════════════════
# P1. 카드 데이터2 읽기와 기본 확인
# ═══════════════════════════════════════════════════════════════
EXPECT_CARD_ROWS = 1_806_800
EXPECT_CARD_BY_REGION = {'서울 강남구': 1_366_189, '강원 춘천시': 440_611}


def load_card2():
    """카드 데이터2(일별, 거주지 포함, 법인 제외)를 읽고 기본 상태를 확인합니다."""
    df = pd.read_csv(CARD_DIR / '신한카드_빅콘테스트2026_데이터2.txt',
                     sep='\t', encoding='cp949',
                     dtype={'TA_YMD': str})                       # 날짜는 글자로 읽기
    df['date'] = pd.to_datetime(df['TA_YMD'], format='%Y%m%d')    # 날짜 열 만들기
    df['TS_AT'] = pd.to_numeric(df['TS_AT'])                      # 결제액을 숫자로
    df['USE_CNT'] = pd.to_numeric(df['USE_CNT'])                  # 결제건수를 숫자로

    check('P1 전체 행 수', len(df), EXPECT_CARD_ROWS)
    for region, n in df['MCT_SGG_CD'].value_counts().items():     # 지역별 행 수
        check(f'P1 {region} 행 수', n, EXPECT_CARD_BY_REGION.get(region))
    check('P1 날짜 시작', df['date'].min().strftime('%Y-%m-%d'), '2025-07-01')
    check('P1 날짜 끝', df['date'].max().strftime('%Y-%m-%d'), '2025-12-31')
    check('P1 업종 수', df['MCT_RY_CD'].nunique(), 90)
    return df


# ═══════════════════════════════════════════════════════════════
# P2. 제외 업종 7개 (확정)
# ═══════════════════════════════════════════════════════════════
EXCLUDE = ['세금공과금', 'ZZ_나머지', '보험', '결제대행(PG)',
           '학교등록금', '상품권/복권', '통신요금(이동,시내전화)']


def drop_excluded(df):
    """제외 업종 7개를 뺍니다. 먼저 이름이 데이터에 정확히 있는지 확인합니다."""
    present = set(df['MCT_RY_CD'].unique())
    for name in EXCLUDE:
        if name not in present:
            warn(f'제외 업종 이름이 데이터에 없습니다: {name}')
    out = df[~df['MCT_RY_CD'].isin(EXCLUDE)].copy()             # 제외 업종 빼기
    check('P2 제외 후 업종 수', out['MCT_RY_CD'].nunique(), 83)
    return out


# ═══════════════════════════════════════════════════════════════
# P3. 업종 그룹 (명세서 확정안, 83개 전부 한 번씩 배정)
# ═══════════════════════════════════════════════════════════════
GROUPS = {
    '식료품': ['기타식품', '농수산물', '할인점/슈퍼마켓/양판점', '편의점', '정육점', '제과점'],
    '외식': ['한식', '중식', '일식', '양식', '기타요식', '패스트푸드', '커피전문점', '주류판매'],
    '의료·약국': ['약국', '일반병원', '종합병원', '치과병원', '한의원', '기타의료', '보건소', '동물병원'],
    '교통·숙박': ['고속버스/철도/여객선', '택시', '주차장', '주유소', 'LPG가스',
                  '호텔/콘도', '모텔,여관,기타숙박', '여행사/항공사'],
    '여가': ['유흥업소', '노래방', '게임방/오락실', '영화/공연', '스포츠시설',
             '실내/실외골프장', '종합레저타운/놀이동산', '싸우나/목욕탕', '안마/마사지',
             '헬스장', '스포츠/레저용품'],
    '상품쇼핑': ['가구', '가전', '문화용품', '사무기기/문구용품', '생활잡화/수입상품점',
                 '서점', '수제용품점', '시계/귀금속', '악기/음반', '완구/아동용자전거',
                 '의복/의류', '패션잡화', '인테리어/건축자재/주방기구', '화장품', '화원',
                 '애완동물', '백화점', '면세점', '쇼핑몰', '전용매장', '체인점', '기타유통',
                 '중고품판매점', '중고차판매', '수입자동차', '오토바이', '자동차용품',
                 '컴퓨터/소프트웨어'],
    '생활·교육서비스': ['미용서비스', '미용실', '세탁소', '자동차서비스', '학원/학습지',
                        '유치원', '독서실', '장례식장/묘지/장의사', '예식장/결혼서비스',
                        '법률/사무서비스', '연구/번역서비스', '회계/변리서비스',
                        '부동산중개', '방문판매/다단계판매'],
}


def add_group(df):
    """업종마다 그룹 이름을 붙입니다. 중복 배정이나 빠진 업종이 있으면 멈춥니다."""
    all_inds = [i for inds in GROUPS.values() for i in inds]
    n_dup = len(all_inds) - len(set(all_inds))
    if n_dup:
        raise ValueError(f'그룹에 중복 배정된 업종이 {n_dup}개 있습니다.')
    check('P3 그룹에 배정된 업종 수', len(all_inds), 83)

    lookup = {ind: g for g, inds in GROUPS.items() for ind in inds}  # 업종 → 그룹
    out = df.copy()
    out['group'] = out['MCT_RY_CD'].map(lookup)
    missing = sorted(out.loc[out['group'].isna(), 'MCT_RY_CD'].unique())
    if len(missing):
        raise ValueError(f'그룹에 없는 업종이 있습니다: {missing}')
    return out


# ═══════════════════════════════════════════════════════════════
# P4. 현지인 / 외지인 나누기
# ═══════════════════════════════════════════════════════════════
LOCAL_SIDO = {'서울 강남구': '서울', '강원 춘천시': '강원'}   # 가맹점 지역 → 현지인 거주지


def add_segment(df):
    """
    seg 열을 만듭니다.
      loc : 현지인 (거주지 = 가맹점이 있는 시도)
      out : 외지인 (그 밖의 시도)
      unk : 정보없음 (전체(all)에만 들어감)
    """
    local_key = df['MCT_SGG_CD'].map(LOCAL_SIDO)                 # 지역별 현지인 시도
    unk = df['CLN_SGG_CD'] == '정보없음'
    is_loc = (df['CLN_SGG_CD'] == local_key) & ~unk
    out = df.copy()
    out['seg'] = np.select([unk, is_loc], ['unk', 'loc'], default='out')
    # 제외 업종을 뺀 뒤의 값입니다. 전체 원본(제외 전)은 20,244행입니다.
    check('P4 정보없음 행 수 (제외 업종 뺀 뒤)', int((out['seg'] == 'unk').sum()), 16396)
    return out


# ═══════════════════════════════════════════════════════════════
# P5. 일별 집계
# ═══════════════════════════════════════════════════════════════
def daily_table(df, level, seg='all', value='USE_CNT'):
    """
    level='group'    : 지역 × 업종그룹 × 날짜 합계. 184일이 모두 있어야 합니다.
    level='industry' : 지역 × 업종 × 날짜 합계. 거래가 없는 날은 0이 아니라 NaN(결측)입니다.
    seg              : 'all' (전체) | 'loc' (현지인) | 'out' (외지인)
    """
    sub = df if seg == 'all' else df[df['seg'] == seg]
    key = 'group' if level == 'group' else 'MCT_RY_CD'
    daily = sub.groupby(['MCT_SGG_CD', key, 'date'])[value].sum()  # 날짜별 합계
    table = daily.unstack('date').reindex(columns=DAYS)           # 184일 열로 맞추기
    if level == 'group':
        n_nan = int(table.isna().sum().sum())
        check(f'P5 그룹 결측 칸 수 ({seg}, {value})', n_nan, 0)
    return table


# ═══════════════════════════════════════════════════════════════
# P6. 기상 (ASOS 7개 지점)
# ═══════════════════════════════════════════════════════════════
STATION_FILE = {108: '강남구_ASOS.csv', 101: '춘천시_ASOS.csv', 90: '속초_ASOS.csv',
                202: '양평_ASOS.csv', 189: '서귀포_ASOS.csv', 283: '경주_ASOS.csv',
                279: '구미_ASOS.csv'}
STATION_REGION = {108: '서울', 101: '춘천', 90: '속초', 202: '양평',
                  189: '서귀포', 283: '경주', 279: '구미'}
# 파일마다 괄호·공백이 달라서, 이름에 들어 있는 키워드로 짧은 이름을 찾습니다.
ASOS_KEYWORDS = [('일시', 'date'), ('평균기온', 'tavg'), ('최저기온', 'tmin'),
                 ('최고기온', 'tmax'), ('1시간 최다', 'r1h'), ('일강수량', 'rain')]


def load_asos():
    """
    7개 지점 파일을 읽어 184일 행으로 맞춥니다.
    - 일강수량 빈칸(원본) → 0으로 채우고 rain_blank_filled = True 로 표시
    - 파일에 없는 날(구미 2025-09-30) → NaN 행을 추가하고 row_missing = True 로 표시
    - 1시간 최다강수량 빈칸은 NaN 그대로 둠
    """
    rows = []
    for stn, fname in STATION_FILE.items():
        raw = pd.read_csv(ASOS_DIR / fname, encoding='cp949', dtype=str)
        ren = {}
        for col in raw.columns:                                   # 짧은 이름 붙이기
            for key, short in ASOS_KEYWORDS:
                if key in col:
                    ren[col] = short
        d = raw.rename(columns=ren)
        d['date'] = pd.to_datetime(d['date'])
        for c in ['tavg', 'tmin', 'tmax', 'r1h', 'rain']:           # 숫자로 (잘못된 값은 NaN)
            d[c] = pd.to_numeric(d[c], errors='coerce')

        missing_dates = DAYS.difference(pd.DatetimeIndex(d['date']))  # 파일에 없는 날
        d = d.set_index('date').reindex(DAYS)                       # 184일 행으로 맞추기
        d['row_missing'] = d.index.isin(missing_dates)
        d['rain_blank_filled'] = d['rain'].isna() & ~d['row_missing']  # 원본 빈칸
        d['rain'] = d['rain'].mask(d['rain_blank_filled'], 0.0)        # 빈칸만 0으로
        d['station'] = stn
        d['region'] = STATION_REGION[stn]
        rows.append(d.reset_index().rename(columns={'index': 'date'}))

    out = pd.concat(rows, ignore_index=True)
    # 검증 (명세서 P6 기대값)
    n_blank_src = int(out['rain_blank_filled'].sum())
    n_missing = int(out['row_missing'].sum())
    check('P6 일강수량 원본 빈칸 (0으로 채움)', n_blank_src, 685)
    check('P6 누락 행 수 (구미 9/30)', n_missing, 1)
    check('P6 빈칸 합계 (빈칸 + 누락 행)', n_blank_src + n_missing, 686)

    wide = out.pivot(index='date', columns='region', values='rain')
    blank_all = (out.assign(b=out['rain_blank_filled'] | out['row_missing'])
                    .pivot(index='date', columns='region', values='b').all(axis=1))
    check('P6 7개 지점 모두 빈칸인 날', int(blank_all.sum()), 35)
    return out


def hot_days(asos, threshold=33):
    """폭염일 수: 최고기온 33℃ 이상 (지점별)."""
    return asos[asos['tmax'] >= threshold].groupby('region').size()


# ═══════════════════════════════════════════════════════════════
# P8. 공휴일 달력 (P7에서 쓰므로 먼저 정의)
# ═══════════════════════════════════════════════════════════════
def load_calendar():
    """공휴일 달력을 읽고, 분석 구간(184일)만 남깁니다. 6/30과 2026-01-01은 뺍니다."""
    raw = pd.read_csv(HOLIDAY_FILE, encoding='utf-8-sig')
    raw['date'] = pd.to_datetime(raw['date'])
    check('P8 원본 in_analysis_period=1 행 수 (잘못 표시 포함)',
          int((raw['in_analysis_period'] == 1).sum()), 185)
    cal = raw[raw['date'].isin(DAYS)].reset_index(drop=True)
    check('P8 분석 구간 달력 행 수', len(cal), 184)
    return cal


def holiday_days(cal):
    """연휴 날: off_block_len >= 3 인 날 (명세서 P7). 집합으로 돌려줍니다."""
    return set(cal.loc[cal['off_block_len'] >= 3, 'date'])


# ═══════════════════════════════════════════════════════════════
# P7. 호우 사건 정의와 제외 규칙
# ═══════════════════════════════════════════════════════════════
RAIN_EVENT_MM = 30    # 호우일 기준 (일강수량 30mm 이상)
AFTER_DAYS = 7        # 사건 뒤 몇 날까지 보는지 (P1~P7)


def rain_events(rain):
    """
    rain: 날짜 인덱스의 일강수량 (지점 하나).
    30mm 이상인 날을 이어진 날끼리 묶어 (시작일, 끝일) 목록을 돌려줍니다.
    """
    wet = rain.index[rain >= RAIN_EVENT_MM]
    events = []
    for d in wet:
        if events and (d - events[-1][1]).days == 1:   # 바로 전날에 이어지면 같은 사건
            events[-1] = (events[-1][0], d)
        else:                                          # 아니면 새 사건
            events.append((d, d))
    return events


def keep_events(events, holidays):
    """
    사건 구간 [시작일, 끝일 + 7일] 안에 연휴가 하나라도 있으면 그 사건을 뺍니다.
    반환: (남는 사건, 뺀 사건)
    """
    kept, dropped = [], []
    for s, e in events:
        window = pd.date_range(s, e + pd.Timedelta(days=AFTER_DAYS))
        if any(d in holidays for d in window):
            dropped.append((s, e))
        else:
            kept.append((s, e))
    return kept, dropped


def event_dummies(events_all, events_kept, rain):
    """
    사건 전후 더미 (명세서 P7). 날짜 인덱스 DataFrame을 돌려줍니다.
      D0 : 호우일 (남는 사건의 30mm 이상 날)
      L1 : 사건 시작 하루 전
      P1~P7 : 사건 끝 이후 1~7일. 다음 호우일이 나오면 그 앞에서 멈춤.
    """
    cols = ['D0', 'L1'] + [f'P{k}' for k in range(1, AFTER_DAYS + 1)]
    D = pd.DataFrame(0, index=rain.index, columns=cols)
    wet_all = sorted(d for s, e in events_all for d in pd.date_range(s, e))

    for s, e in events_kept:
        for d in pd.date_range(s, e):
            D.loc[d, 'D0'] = 1
        before = s - pd.Timedelta(days=1)
        if before in D.index:
            D.loc[before, 'L1'] = 1
        later = [w for w in wet_all if w > e]                  # 이 사건 뒤의 다음 호우일
        next_wet = later[0] if later else None
        for k in range(1, AFTER_DAYS + 1):
            d = e + pd.Timedelta(days=k)
            if next_wet is not None and d >= next_wet:          # 다음 호우일 앞에서 멈춤
                break
            if d in D.index:
                D.loc[d, f'P{k}'] = 1
    return D


def build_event_table(asos):
    """
    지점(지역)별로 사건, 남긴 사건, 더미, 표본 여부(sample)를 만듭니다.
    sample = 0 : 연휴 날이거나, 뺀 사건의 구간 [시작일, 끝일+7] 안의 날
    """
    cal = load_calendar()
    hol = holiday_days(cal)
    result = {}
    for region, g in asos.groupby('region'):
        rain = g.set_index('date')['rain'].reindex(DAYS)
        events = rain_events(rain)
        kept, dropped = keep_events(events, hol)
        D = event_dummies(events, kept, rain)

        bad = pd.Series(False, index=DAYS)
        bad[bad.index.isin(list(hol))] = True                    # 연휴 날 제외
        for s, e in dropped:                                     # 뺀 사건 구간 제외
            win = pd.date_range(s, e + pd.Timedelta(days=AFTER_DAYS))
            bad[bad.index.isin(win)] = True
        D['sample'] = (~bad).astype(int)
        result[region] = {'events': events, 'kept': kept, 'dropped': dropped, 'D': D}

        check(f'P7 {region} 호우 사건 수 (30mm)', len(events), EXPECT_EVENTS_RAW[region])
        check(f'P7 {region} 남는 사건 수', len(kept), EXPECT_EVENTS_KEPT[region])
    return result


EXPECT_EVENTS_RAW = {'서울': 13, '춘천': 14, '양평': 12, '속초': 10,
                     '서귀포': 6, '구미': 6, '경주': 5}
EXPECT_EVENTS_KEPT = {'서울': 10, '춘천': 12, '속초': 9, '양평': 9,
                      '서귀포': 4, '경주': 4, '구미': 6}


# ═══════════════════════════════════════════════════════════════
# P9. 관광공사 방문자
# ═══════════════════════════════════════════════════════════════
def load_visitors():
    """방문자 데이터를 읽고 행 수·키 중복을 확인합니다. 지역은 이름이 아니라 코드로 구분합니다."""
    v = pd.read_csv(VISITOR_FILE, encoding='utf-8-sig',
                    dtype={'signguCode': str, 'baseYmd': str})
    v['date'] = pd.to_datetime(v['baseYmd'], format='%Y%m%d')
    check('P9 행 수', len(v), 145_728)
    check('P9 시군구 코드 수', v['signguCode'].nunique(), 264)
    check('P9 날짜 수', v['date'].nunique(), 184)
    check('P9 (시군구, 구분, 날짜) 중복 행', int(v.duplicated(['signguCode', 'touDivCd', 'baseYmd']).sum()), 0)
    return v


# ═══════════════════════════════════════════════════════════════
# P10. SK 통신 유동인구
# ═══════════════════════════════════════════════════════════════
SK_PREFIX = {'age': 'flow_age_pop', 'time': 'flow_time_pop', 'wkdy': 'flow_wkdy_pop'}
EXPECT_SK_DUP = {'age': 0, 'time': 92_545, 'wkdy': 121_267}   # 12월 파일의 완전 중복 행 수


def load_sk(kind):
    """
    kind: 'age' | 'time' | 'wkdy'
    월별 파일 6개를 읽고, 파일마다 완전 중복 행을 뺀 뒤 합칩니다.
    반환: (합친 데이터, 파일별 행 수 표)
    """
    files = sorted(glob.glob(str(SK_DIR / f'{SK_PREFIX[kind]}_2025*.csv')))
    check(f'P10 {kind} 파일 수', len(files), 6)
    parts, log = [], []
    for f in files:
        raw = pd.read_csv(f, sep='|', encoding='utf-8-sig', dtype=str)  # 구분자는 |
        dd = raw.drop_duplicates()                                       # 완전 중복 행 제거
        log.append({'파일': Path(f).name, '원본 행': len(raw),
                    '중복 제거 후': len(dd), '중복 행': len(raw) - len(dd)})
        parts.append(dd)
    log = pd.DataFrame(log)
    print(log.to_string(index=False))
    check(f'P10 {kind} 중복 행 합계', int(log['중복 행'].sum()), EXPECT_SK_DUP[kind])
    return pd.concat(parts, ignore_index=True), log
