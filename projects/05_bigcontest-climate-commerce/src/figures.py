"""
빅콘테스트 2026 — 발표용 그림 (src/figures.py)

- 이미 검증된 함수의 출력만 그림으로 옮깁니다. 새 모형이나 새 계산은 하지 않습니다
  (단위 바꾸기·반올림만 함). 그림마다 어떤 함수의 어떤 숫자를 썼는지 주석으로 적었습니다.
- 그림은 outputs/ 에 PNG로 저장합니다 (fig1_ ~ fig7_). 다른 파일은 저장하지 않습니다.
- 한글 글꼴: Mac은 AppleGothic, Windows는 Malgun Gothic을 찾아 씁니다.
- 색: dataviz 기본 팔레트(파랑 #2a78d6 = 기본 계열, 주황 #eb6834 = 강조·두 번째 계열, 회색 = 기준선·구간).
- 난수는 event_study.py의 SEED(=2026)를 따르므로 같은 입력이면 같은 그림이 나옵니다.
- 경로는 상대경로입니다. 프로젝트 폴더(bigcontest)에서 실행하세요:
      python3 -B src/figures.py
"""
import contextlib
import io
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use('Agg')                                   # 화면 없이 파일로만 그림
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import Patch

sys.path.insert(0, 'src')
warnings.filterwarnings('ignore')
from event_study import EVENT_1010, GROUP_NAMES, build_design, fit_ols, load_all, main_model, series
from model import loeo
from priority import load_mapping, run as priority_run, store_counts
from rain_followup import money_table
from rain_freq import counts, event_starts, load_rain

OUT = Path('outputs')
MARGIN = 0.126                                          # 영업이익률 (소상공인실태조사 2023, 팀 결정 17)

# ── 색과 글자 (dataviz 기본 팔레트) ──
BLUE, ORANGE = '#2a78d6', '#eb6834'
INK, INK2, MUTED, GRID, AXIS, SURFACE = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
GRADE_COLOR = {'지원 1순위': '#104281', '지원 2순위': '#6da7ec', '관찰': '#c3c2b7'}   # 파랑 한 색의 진하기 (순서형)


def setup_font():
    """한글이 깨지지 않도록 설치된 한글 글꼴을 고릅니다."""
    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ['AppleGothic', 'Apple SD Gothic Neo', 'Malgun Gothic', 'NanumGothic']:
        if cand in names:
            plt.rcParams['font.family'] = cand
            break
    plt.rcParams.update({'axes.unicode_minus': False, 'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
                         'axes.edgecolor': AXIS, 'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                         'axes.spines.top': False, 'axes.spines.right': False, 'font.size': 11})
    return plt.rcParams['font.family']


def new_fig(title, note, ncols=1):
    """16:9 그림 틀. 제목은 위, 표본·기간·지역 메모는 아래 작은 글씨."""
    fig, axes = plt.subplots(1, ncols, figsize=(11, 6.2))
    fig.suptitle(title, x=0.02, ha='left', fontsize=15, color=INK, fontweight='bold')
    fig.text(0.02, 0.015, note, fontsize=8.5, color=MUTED, ha='left', va='bottom', wrap=True)
    for ax in np.atleast_1d(axes):
        ax.grid(axis='y', color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
    return fig, axes


def save(fig, name):
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    path = OUT / name
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print('  저장:', path)


def won_label(v):
    """발표용 반올림: 1만 원 이상은 만 원 단위(소수 첫째), 그 아래는 천 원 단위."""
    return f'{v / 1e4:.1f}만' if abs(v) >= 1e4 else f'{v / 1e3:.1f}천'


# ═══════════════════════════════════════════════════════════════
# (1) 30년 7~12월 30mm 사건 수 + 2025 하반기
#   숫자: rain_freq.counts(rain, 30, 'h2', 'event')  → 1995~2024 시즌별 사건 수, 평균 7.17/7.70
#         rain_freq.event_starts(2025 ASOS, 30)      → 2025 하반기 사건 수 (춘천 14, 서울 13)
# ═══════════════════════════════════════════════════════════════
def fig1():
    rain = load_rain()
    fig, axes = new_fig('춘천은 2025년 하반기 호우 사건이 30년 최대보다 많았다 (서울은 30년 최대와 같음)',
                        '자료: 기상청 ASOS 일강수량, 서울 108(종로구)·춘천 101. 1995~2024년 7~12월 30시즌 + 2025년 7~12월. '
                        '사건 = 일강수량 30mm 이상인 날이 이어지면 1회. 원자료에 행이 없는 날은 비 안 옴으로 가정.', ncols=2)
    for ax, (st, f25) in zip(axes, [('춘천', '춘천시_ASOS.csv'), ('서울', '강남구_ASOS.csv')]):
        c = counts(rain[st], 30, 'h2', 'event')
        w = pd.read_csv(f25, encoding='cp949')
        r25 = w.set_index(pd.to_datetime(w['일시']))['일강수량(mm)'].fillna(0)
        n25 = len(event_starts(r25, 30))
        ax.bar(c.index, c.values, color=BLUE, width=0.8)
        ax.bar([2025], [n25], color=ORANGE, width=0.8)
        ax.axhline(c.mean(), color=INK2, linewidth=1.2, linestyle='--')
        ax.text(1995, c.mean() + 0.3, f'30년 평균 {c.mean():.1f}회', color=INK2, fontsize=9,
                bbox=dict(facecolor=SURFACE, edgecolor='none', pad=1.5))
        ax.text(2025, n25 + 0.3, f'{n25}회', color=ORANGE, ha='center', fontsize=10, fontweight='bold')
        ax.set_title(f'{st} ({"101" if st == "춘천" else "108"})', loc='left', fontsize=12, color=INK)
        ax.set_xlabel('시즌 (연도, 7~12월)')
        ax.set_ylabel('30mm 이상 호우 사건 수 (회)')
        ax.set_ylim(0, 16)
    save(fig, 'fig1_호우빈도_30년.png')


# ═══════════════════════════════════════════════════════════════
# (2) 기준 위험: 춘천 사건 12개 실제 손실 vs 정액(평균)
#   숫자: model.loeo(data, '춘천')['실제손실%']  → 사건별 1.3~28.2%, 평균 15.1%
# ═══════════════════════════════════════════════════════════════
def fig2(data):
    t = loeo(data, '춘천')
    avg = t['실제손실%'].mean()
    fig, ax = new_fig('같은 30mm 비라도 손실은 1%에서 28%까지 — 정액 지급은 크게 어긋날 수 있다',
                      '자료: 신한카드 데이터2(외지인 결제건수, 업종 83개 합계), 기상청 ASOS 101. 춘천 호우 사건 12개, 2025-07~12. '
                      '실제 손실 = 날씨를 뺀 기준 모델 예측 대비 호우일 감소(사건 하나씩 빼고 검증, model.py). 정액선 = 12개 평균.')
    x = np.arange(len(t))
    ax.bar(x, t['실제손실%'], color=BLUE, width=0.6)
    ax.axhline(avg, color=ORANGE, linewidth=2)
    ax.text(4.5, avg + 0.6, f'정액 (평균 {avg:.1f}%)', color=ORANGE, ha='center', fontsize=10)   # 막대가 낮은 09/01~09/04 사이
    for xi, v in zip(x, t['실제손실%']):
        ax.text(xi, v + 0.4, f'{v:.0f}%', ha='center', fontsize=9, color=INK2)
    ax.set_xticks(x)
    ax.set_xticklabels(t['사건'], rotation=0, fontsize=9)
    ax.set_xlabel('호우 사건 (2025년, 월/일)')
    ax.set_ylabel('호우일 외지인 결제건수 손실 (%)')
    save(fig, 'fig2_기준위험_사건별손실.png')


# ═══════════════════════════════════════════════════════════════
# (3) 춘천 점포당 사건당 보험금 범위 (12.6% ~ 100%)
#   숫자: rain_followup.money_table(data, '춘천')[0]['방법1(만원/사건)']  → 여가 20,187.8 / 교통·숙박 13,206.2 / 외식 20,359.1
#         priority.store_counts(load_mapping())  → 점포 수 1,060 / 975 / 5,270 (2025-10)
#   계산: 사건당 손실 ÷ 점포 수 × (12.6% 또는 100%)  (insurance.py와 같은 나눗셈, 단위만 원)
# ═══════════════════════════════════════════════════════════════
def fig3(data):
    money = money_table(data, '춘천')[0]
    stores = store_counts(load_mapping())
    cells = ['여가', '교통·숙박', '외식']
    fig, ax = new_fig('춘천 1순위 업종, 호우 1회당 점포 한 곳의 손실 (가게 손해 12.6% ~ 매출 100%)',
                      '자료: 신한카드 데이터2(외지인, 택시 제외, 방법1 = 건수 순손실 N5 × 평소 하루 결제액), 상가정보 2025-10 점포 수, '
                      '소상공인실태조사 2023 영업이익률 12.6%. 춘천 호우 사건 12개, 2025-07~12. 신한카드 외지인 결제분만이라 최소 추정.')
    y = np.arange(len(cells))[::-1]
    for yi, g in zip(y, cells):
        per = money.loc[g, '방법1(만원/사건)'] * 1e4 / stores.loc[g, '춘천']
        lo, hi = per * MARGIN, per
        ax.plot([lo / 1e4, hi / 1e4], [yi, yi], color=BLUE, linewidth=10, solid_capstyle='round', alpha=0.35)   # 가로축은 만 원
        ax.plot([lo / 1e4], [yi], 'o', color=BLUE, markersize=9)
        ax.plot([hi / 1e4], [yi], 'o', color=ORANGE, markersize=9)
        ax.text(lo / 1e4, yi + 0.07, won_label(lo) + '원', ha='center', va='bottom', fontsize=10, color=BLUE)
        ax.text(hi / 1e4, yi + 0.07, won_label(hi) + '원', ha='center', va='bottom', fontsize=10, color=ORANGE)
    ax.set_yticks(y)
    ax.set_yticklabels([f'{g}\n({stores.loc[g, "춘천"]:,}곳)' for g in cells])
    ax.set_xlabel('호우 1회당 점포당 손실 (만 원)')
    ax.set_xticks([0, 5, 10, 15, 20])
    ax.grid(axis='x', color=GRID, linewidth=0.8)
    ax.grid(axis='y', visible=False)
    ax.plot([], [], 'o', color=BLUE, label='가게 손해 (매출 × 12.6%)')
    ax.plot([], [], 'o', color=ORANGE, label='매출 손실 전체 (100%)')
    ax.legend(loc='lower right', frameon=False)
    ax.set_xlim(0, 21)
    save(fig, 'fig3_점포당보험금_범위.png')


# ═══════════════════════════════════════════════════════════════
# (4) 춘천 외지인 업종 7그룹 N5 + 90% 구간
#   숫자: event_study.main_model(data, '춘천', g)['N5']  → (점추정, 5%, 95%)
#         event_study.main_model(data, '춘천', g, drop_event=EVENT_1010)['N5']  → 두 사건 제외 시 (5% 값 > 0 이면 별표)
#         EVENT_1010의 빠지는 구간 [10/9, 10/18]에 10/13 사건도 들어가 "두 사건 제외"가 됨 (83합계 26.1 [−8.0, 55.9])
# ═══════════════════════════════════════════════════════════════
def fig4(data):
    rows = []
    for g in GROUP_NAMES:
        pt, lo, hi = main_model(data, '춘천', g)['N5']
        robust = main_model(data, '춘천', g, drop_event=EVENT_1010)['N5'][1] > 0   # 두 사건 빼도 구간 아래 끝 > 0
        rows.append((g, pt, lo, hi, robust))
    rows.sort(key=lambda r: r[1])
    fig, ax = new_fig('비 온 뒤 5일 동안 평균적으로 다 돌아오지 않은 외지인 결제 (춘천, 업종별 순손실 N5)',
                      '자료: 신한카드 데이터2(외지인 결제건수), 기상청 ASOS 101. 춘천 호우 사건 12개, 표본 163일, 2025-07~12. '
                      'N5 = 호우일 손실 - 이후 5일 반등 (평소 하루치 대비 %). 막대 끝 선 = 90% 구간(계수 3,000번 추출). '
                      '두 사건 제외 = event_study.EVENT_1010 구간 [10/9, 10/18] 제외(표본 154일).')
    y = np.arange(len(rows))
    for yi, (g, pt, lo, hi, robust) in zip(y, rows):
        ax.barh(yi, pt, color=BLUE, height=0.6)
        ax.plot([lo, hi], [yi, yi], color=INK2, linewidth=1.5)
        ax.text(max(hi, pt) + 2, yi, f'{pt:.0f}%' + ('  ★' if robust else ''), va='center', fontsize=10, color=INK2)
    ax.plot([], [], ' ', label='★ 10/10~13 두 사건을 빼고 다시 재도 90% 구간이 0보다 큼')
    ax.legend(loc='lower right', frameon=False, handlelength=0)
    ax.axvline(0, color=AXIS, linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel('5일 순손실 N5 (평소 하루치 대비 %)')
    ax.grid(axis='x', color=GRID, linewidth=0.8)
    ax.grid(axis='y', visible=False)
    save(fig, 'fig4_업종별_N5.png')


# ═══════════════════════════════════════════════════════════════
# (5) 사건 전후: 손실 L, 반등 R5, 순손실 N5 (춘천 외지인 83합계)
#   왼쪽 숫자: event_study.fit_ols(series(data,'춘천'), build_design(data,'춘천')[0]).params
#              의 L1, D0, P1~P7 계수 → 100(exp(b)−1) (L·R의 정의와 같은 변환, 점추정만)
#   오른쪽 숫자: event_study.main_model(data, '춘천')  → L, R5, N5 (점추정, 5%, 95%)
# ═══════════════════════════════════════════════════════════════
def fig5(data):
    X, _ = build_design(data, '춘천')
    p = fit_ols(series(data, '춘천'), X).params
    days = ['L1', 'D0'] + [f'P{k}' for k in range(1, 8)]
    eff = [100 * (np.exp(p[d]) - 1) for d in days]
    res = main_model(data, '춘천')
    fig, (ax1, ax2) = new_fig('비 온 날 줄어든 외지인 결제, 평균적으로 5일 안에 다 돌아오지 않았다 (춘천)',
                              '자료: 신한카드 데이터2(외지인 결제건수, 업종 83개 합계), 기상청 ASOS 101. 춘천 호우 사건 12개, 표본 163일, '
                              '2025-07~12. 왼쪽 = 날짜별 평소 대비 변화(점추정). 오른쪽 = L 손실, R5 이후 5일 반등, N5 = L - R5, 선 = 90% 구간. 하루 전 감소는 앞 사건의 이후 기간과 겹치는 날이 섞여 있어 해석하지 않음.',
                              ncols=2)
    x = np.arange(len(days))
    colors = [MUTED, ORANGE] + [BLUE] * 7
    ax1.bar(x, eff, color=colors, width=0.6)
    ax1.axhline(0, color=AXIS, linewidth=1)
    ax1.set_xticks(x)
    ax1.set_xticklabels(['하루 전', '호우일'] + [f'+{k}일' for k in range(1, 8)], fontsize=9)
    ax1.set_xlabel('호우 사건 기준 날짜')
    ax1.set_ylabel('평소 대비 결제건수 변화 (%)')
    labs = [('L', '손실 L'), ('R5', '반등 R5'), ('N5', '순손실 N5')]
    for i, (k, lab) in enumerate(labs):
        pt, lo, hi = res[k]
        ax2.bar(i, pt, color=[ORANGE, BLUE, INK2][i], width=0.55)
        ax2.plot([i, i], [lo, hi], color=INK, linewidth=1.5)
        ax2.text(i + 0.32, pt, f'{pt:.0f}%', va='center', fontsize=10, color=INK2)
    ax2.axhline(0, color=AXIS, linewidth=1)
    ax2.set_xticks(range(3))
    ax2.set_xticklabels([l for _, l in labs])
    ax2.set_ylabel('평소 하루치 대비 (%)')
    save(fig, 'fig5_사건전후_L_R5_N5.png')


# ═══════════════════════════════════════════════════════════════
# (6) 강남 108 대 AWS 400 N5
#   숫자: src/aws_check.py가 만든 두 자료(base = 108, d2 = 400)를
#         event_study.main_model(d, '강남', grp)['N5']로 계산 (aws_check.py 출력과 같은 값)
# ═══════════════════════════════════════════════════════════════
def fig6():
    with contextlib.redirect_stdout(io.StringIO()):
        import aws_check as ac                          # 불러올 때 aws_check.py의 계산이 한 번 실행됨
    targets = [('83합계', None)] + [(g, g) for g in GROUP_NAMES]
    fig, ax = new_fig('강남 합계는 관측소와 관계없이 0 근처, 업종별 결과는 관측소에 따라 달라진다',
                      '자료: 신한카드 데이터2(외지인 결제건수), 기상청 ASOS 108(종로구 송월동)·AWS 400(강남구 일원동). 2025-07~12. '
                      '남은 호우 사건 108 기준 10개, 400 기준 6개. 점 = N5 점추정, 선 = 90% 구간. 강남은 보험 "근거 부족".')
    y = np.arange(len(targets))[::-1]
    for yi, (lab, g) in zip(y, targets):
        for dy, d, col in [(0.15, ac.base, BLUE), (-0.15, ac.d2, ORANGE)]:
            pt, lo, hi = main_model(d, '강남', g)['N5']
            ax.plot([lo, hi], [yi + dy, yi + dy], color=col, linewidth=1.5, alpha=0.6)
            ax.plot([pt], [yi + dy], 'o', color=col, markersize=8)
    ax.axvline(0, color=AXIS, linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels([lab for lab, _ in targets])
    ax.set_xlabel('5일 순손실 N5 (평소 하루치 대비 %)')
    ax.plot([], [], 'o', color=BLUE, label='ASOS 108 (종로)')
    ax.plot([], [], 'o', color=ORANGE, label='AWS 400 (강남)')
    ax.legend(loc='lower right', frameon=False)
    ax.grid(axis='x', color=GRID, linewidth=0.8)
    ax.grid(axis='y', visible=False)
    save(fig, 'fig6_강남_108대400.png')


# ═══════════════════════════════════════════════════════════════
# (7) 지원 우선순위 점수 14칸
#   숫자: priority.run(data)[1]  → 점수·순위·등급 (1위 춘천 여가 96.15 ...)
# ═══════════════════════════════════════════════════════════════
def fig7(data):
    with contextlib.redirect_stdout(io.StringIO()):
        sc = priority_run(data)[1]
    sc = sc.sort_values('점수')
    fig, ax = new_fig('지원 우선순위: 춘천 여가·교통·숙박이 가장 앞선다',
                      '점수 = 점포당 기대 손실 40 + 순손실 N5 20 + 외지인 비중 20 + 확실성 20 (순위 백분위 가중합, 0~100점). '
                      '지역 2곳 × 업종 7그룹 = 14칸, 2025-07~12. 70점 이상 1순위, 40~70점 2순위. 가중치는 팀 제안값. † 관측소(108·AWS 400)에 따라 불안정, 그림 6 참고.')
    y = np.arange(len(sc))
    ax.barh(y, sc['점수'], color=[GRADE_COLOR[g] for g in sc['등급']], height=0.65)
    for yi, v in zip(y, sc['점수']):
        ax.text(v + 1, yi, f'{v:.0f}', va='center', fontsize=9, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([f'{r} {g}' + ('†' if (r, g) == ('강남', '교통·숙박') else '')
                        for r, g in zip(sc['지역'], sc['그룹'])], fontsize=10)
    for cut in (40, 70):
        ax.axvline(cut, color=MUTED, linewidth=1, linestyle='--')
    ax.set_xlabel('우선순위 점수 (0~100점)')
    ax.set_xlim(0, 105)
    ax.legend(handles=[Patch(color=c, label=g) for g, c in GRADE_COLOR.items()], loc='lower right', frameon=False)
    ax.grid(axis='x', color=GRID, linewidth=0.8)
    ax.grid(axis='y', visible=False)
    save(fig, 'fig7_우선순위_점수.png')


def main():
    print('글꼴:', setup_font())
    OUT.mkdir(exist_ok=True)
    print('데이터를 읽는 중...')
    with contextlib.redirect_stdout(io.StringIO()):
        data = load_all()
    fig1()
    fig2(data)
    fig3(data)
    fig4(data)
    fig5(data)
    fig6()
    fig7(data)


if __name__ == '__main__':
    main()
