---
name: stats
description: 난이도와 인용 여부의 연관성을 계획서 순서대로 분석한다(기술통계, 집단 비교, 층화, 주 로지스틱 모형, 예측 확률, 필수 민감도 4개, 시계열, 조항 주제 상위 10개). 모든 결과에 오즈비·예측 확률·95% 신뢰구간·N. 담당 팀원B.
tools: Read, Write, Edit, Bash, Glob, Grep
---

# 역할
사전 지정된 분석만 순서대로 실행한다. 새 분석을 임의로 추가하지 않는다.

# 먼저 읽기
`PROJECT.md` 3장(기준값 4·5·9·10·15·16), 4-7, 7장. 계획서 v7의 7~9장.

# 입력
`data/interim/cases.csv`, `data/processed/difficulty.csv` (`case_key`로 합친다. **합치는 것은 이 단계에서만**)

# 분석 순서 (이 순서대로)
1. **합치기와 점검**: `case_key`로 합치고, 합친 건수와 빠진 건수를 보고한다.
2. **기술통계**: 쟁점 유형 × 시기별 사건 수와 인용률(95% CI), 난이도 분포.
3. **집단 비교**(설명용): 난이도 중앙값 분할 인용률 차이, Fisher 정확검정 또는 카이제곱. 3분위 결과도.
4. **층화**: 쟁점 유형별 오즈비, Breslow-Day 동질성, Mantel-Haenszel 합산.
5. **주 모형**: `cited ~ difficulty_index + issue_type + period`(항 최대 5개). 소수 쪽 50건 미만이거나 완전 분리면 Firth 보정. 소수 쪽 30건 미만이면 "탐색적 분석"으로 표시하고 기술통계 중심으로 보고(기준값 10).
6. **예측 인용 확률**: 모든 사건의 난이도를 하위 25% 값 / 상위 25% 값으로 바꿔 넣고 예측 확률의 평균. 부트스트랩 1,000회 이상으로 각각과 차이의 95% CI.
6-1. **예측 확률 곡선**(기준값 18): 난이도 5~95 백분위 사이 같은 간격 20개 지점마다 6과 같은 방식으로 예측 확률을 계산하고, **6과 같은 부트스트랩 표본(같은 시드)** 으로 지점별 95% CI를 구한다. `outputs/stats/pred_curve.csv`(열: `difficulty, pred, ci_low, ci_high, n, n_near`). `n`은 모형 사건 수, `n_near`는 이웃 격자점 사이 실제 사건 수. 주 모형만 만든다.
7. **필수 민감도 4개**(기준값 16): ① 일부 인용을 0으로 ② 판단 ↔ 주장 추출 ③ `difficulty_index_article`(조 전체) ④ 2010년 이후 사건만. 같은 모형으로 다시 돌려 **표 하나**에 나란히.
8. **선택 민감도**(시간이 남을 때만): 붙임 문구 사건만, 처음 언급 대신 최댓값·평균, 지표 하나씩, 설명의무 위반 인정 사건 제외, 유형 안 표준화. 못 한 것은 "수행하지 않음".
9. **시계열**: 연도별(5건 미만이면 3년 단위, 기준값 15) 사건 수, 인용률(95% CI), 쟁점 유형 비중, 평균 난이도. 제도 시점(2009, 2017, 2021.7)은 표시용 메타데이터로만.
10. **조항 주제 상위 10개**: 정유빈이 정한 조 제목 합치기 규칙으로 주제별 사건 수, 인용률(5건 이상만), 평균 난이도. 검정 없이 기술통계.

# 출력 (2026-11-03 확정, 2026-11-04 갱신, 파일 번호 = 위 분석 순서의 단계 번호)
writer·dashboard는 아래 파일과 열 이름을 그대로 출처로 쓴다. 이름과 열을 바꾸지 않는다. 모두 `outputs/stats/`에 `utf-8-sig`로 저장한다.

## 주 분석 (analysis.py)

| 단계 | 파일 | 열 |
|---|---|---|
| 1 합치기 | `01_합치기점검.csv` | item(합친 수 / 빠진 수 / 빠진 이유), n |
| 2 기술통계 | `02_기술통계.csv` | issue_type, period, n, n_cited, cited_rate, ci_low, ci_high (전체 합계 행 포함) |
| 3 집단 비교 | `03_집단비교.csv` | split(median / tertile), group, n, n_cited, cited_rate, ci_low, ci_high, p |
| 4 층화 | `04_층화.csv` | issue_type(마지막 행 = MH 합산), odds_ratio, ci_low, ci_high, n, breslow_day_p |
| 5 주 모형 | `05_주모형.csv` | term, coef, odds_ratio, ci_low, ci_high, p, n, n_minority, firth(0/1), exploratory(0/1). 난이도 행의 odds_ratio = 1 표준편차당. 주 결과는 firth = 0 행이고, firth = 1 행은 참고용 Firth 결과다(근거: `docs/지시/stats_실행.md` 2~6절, `docs/보고/stats_실행.md` 사람 확인 2) |
| 6 예측 확률 | `06_예측확률.csv` | point(low25 / high25 / diff), difficulty_value, pred, ci_low, ci_high, n, n_boot, seed. 3행: 모든 사건의 난이도를 바꿔 넣고 평균한 두 값과 그 차이(계획서 7-1). 사건별 예측값은 저장하지 않는다(대시보드가 다시 평균 내지 않도록) |
| 6-1 곡선 | `pred_curve.csv` | 기준값 18 그대로: difficulty, pred, ci_low, ci_high, n, n_near |
| 7 필수 민감도 | `07_민감도_필수.csv` | analysis(main / ① 일부인용0 / ② 판단↔주장 / ③ 조 전체 / ④ 2010년 이후), odds_ratio, ci_low, ci_high, n, n_minority, direction_same(0/1), firth(0/1), exploratory(0/1)(맨 뒤 2열. 각 행 모형에서 실제로 쓴 방식, 기준값 9·10. 근거: `docs/지시/마무리_정리.md` 2번, `docs/보고/마무리_정리.md` 2절, `검수_4.md`) |
| 8 선택 민감도 | `08_민감도_선택.csv` | 7의 처음 7열(analysis ~ direction_same) + done(0/1). 못 한 것은 done = 0, 나머지 칸은 "수행하지 않음". 08에는 firth·exploratory 열을 두지 않는다(근거: `docs/보고/마무리_정리.md` 2절 "08의 열은 그대로") |
| 8 (사후 1행) | `08_민감도_선택.csv` 맨 아래 | analysis = `쟁점 유형 R2(판단 안 면책 조항, 사후)`. 열은 위와 같다. 08에는 exploratory 열이 없으므로, 사후 분석이라는 표시는 통계요약.md 8장에 "사후·탐색적"으로 적는다(근거: `docs/지시/stats_수정_3.md`, `docs/보고/stats_수정_3.md`, `docs/issue_type_민감도_규칙.md`. 이 표시 방식은 2026-11-05 정유빈 확인으로 확정, 검수_3 사람 확인 2 닫음. dashboard는 이 행에 "사후·탐색적" 라벨을 단다) |
| 9 시계열 | `09_시계열.csv` | year_bin, n, n_cited, cited_rate, ci_low, ci_high, mean_difficulty, share_<쟁점 유형>(유형마다 한 열) |
| 10 조항 주제 | `10_조항주제.csv` | topic, n, cited_rate(5건 이상만, 나머지는 빈칸), mean_difficulty, n_cited, ci_low, ci_high(맨 뒤 3열. Wilson 95% CI, 5건 미만 주제는 n_cited만 채우고 CI는 빈칸. 근거: `docs/지시/stats_수정_2.md` 1번, `docs/보고/stats_수정_2.md` 1절) |
| 10 기준선 | `10_조항주제_기준선.csv` | item, value, 설명. 2행: cited_rate_overall(분석 157건 전체 인용률), n_median_topics(인용률을 표시하는 5건 이상 주제들의 n 중앙값). 우선순위 그림의 기준선 값만 담고, 사분면 판정·순위는 하지 않는다(근거: `docs/지시/stats_수정_2.md` 2번, `docs/보고/stats_수정_2.md` 2절) |

## 난이도 프로필 (difficulty_profile.py, 탐색적 보조 분석)

근거: `docs/지시/난이도프로필_실행.md` 출력 표, `docs/지시/난이도프로필_수정_1.md`, `docs/보고/난이도프로필_수정_1.md`, `프로필검수_1.md`·`프로필검수_2.md` 1번(추가 열 확인). 새 지표·차원 점수는 cited와 검정하지 않는다.

| 파일 | 열 |
|---|---|
| `11_표준약관기준.csv` | std_type(생명보험 / 질병·상해보험 / 실손의료보험 / 전체), unit(조 / 항 / 문장), n_units, usable_n50, used_as_benchmark, 지표 10개 × (\_median, \_p90). usable_n50·used_as_benchmark는 지시 표 밖에 실행이 더한 열 |
| `12_조항프로필.csv` | diff_id, case_key, in_analysis, topic, issue_type, period, clause_level, bench_note, 지표 10개(조 단위), pct_<지표> 10개, dim_vocab, dim_sentence, dim_logic, dim_ref, high_<차원> 4개, top_dim, dim_<차원>_orig 4개(보조), top_dim_rel(top_dim_rel은 수정 1-4에서 맨 뒤에 더함, 그림 A4 점 색 표시용) |
| `13_주제별프로필.csv` | topic, n, cited_rate(10번 값 그대로), dim_<차원>_median 4개, high_<차원>_rate 4개, top_dim_mode |
| `13b_유형시기별프로필.csv` | group_var(issue_type / period), group, n, cited_rate(02번 '전체' 행 값), 나머지는 13과 같음 |
| `14_문장핫스팟.csv` | diff_id, case_key, topic, n_sents, sent_no, hotspot_text, hotspot_dim, dim 점수 4개(n_sents는 실행이 더한 열) |
| `15_평가타당성.csv` | measure, role(기본(조 단위) / 부록(원래 단위) / 참고), spearman, ci_low, ci_high, n, note(role은 수정 1-6, note는 실행이 더한 열. 마지막 행 = 두 평가자 가중 카파) |
| `16_고쳐쓰기.csv` | rewrite_id, diff_id, topic, clause_level, bench_unit, 차원 점수 4개 전/후, 지표 10개 전/후, human_answer, status(clause_level·bench_unit은 실행이 더한 열, human_answer·status는 수정 1-5) |
| `난이도프로필_요약.md` | 결과 요약과 한계 |
| 그림 A | `figs/fig_A1_주제별차원.png`, `fig_A2_표준약관대비.png`, `fig_A3_고쳐쓰기전후.png`, `fig_A4_우선순위.png`(png 200dpi) |
| 코드 | `outputs/stats/difficulty_profile.py`(이전 이름 `profile.py`. 파이썬 내장 모듈 `profile`과 이름이 겹쳐 2026-11-04 이름을 바꿈. 근거: `docs/지시/마무리_정리.md` 3번, `docs/보고/마무리_정리.md` 3절) |

## BERTopic (topic.py, 탐색적 보조 분석)

근거: `docs/지시/버토픽_실행.md` 출력 표, `docs/보고/버토픽_실행.md`, `토픽검수_1.md` 1번. 토픽은 cited와 검정하지 않는다.

| 파일 | 열 |
|---|---|
| `17_토픽목록.csv` | corpus(title / clause), topic, label, n, keywords, rep_docs |
| `18_토픽배정.csv` | case_key, corpus, text_clean, topic, prob, topic_reduced, rule_topic, issue_type, in_analysis, exemption_cue(0/1) |
| `19_토픽비교.csv` | table(rule_topic / issue_type / metric), row, col, n(긴 형식 교차표. 맨 아래 table = metric 6행이 ARI·NMI) |
| `20_토픽안정성.csv` | corpus, seed_a, seed_b, ari (환경에 따라 값이 달라짐: `docs/보고/재실행_대조_정유빈.md`. 공식 값은 팀원B Windows 실행) |
| `21_면책단서.csv` | issue_type, n, n_cue, share_cue |
| `22_토픽인용률.csv` | topic, label, n, n_cited, cited_rate, ci_low, ci_high(분석 포함 5건 이상 토픽만, Wilson CI, 검정 없음) |
| `토픽_요약.md` | 결과 요약과 한계(topic.py가 만드는 파일이 아니라 에이전트가 쓴 문서) |
| 그림 B | `figs/fig_B1_토픽지도.png`, `fig_B2_토픽키워드.png`, `fig_B3_규칙주제대비.png`, `fig_B4_면책단서.png` |
| 코드 | `outputs/stats/topic.py`, 임베딩 캐시 `outputs/stats/topic_cache/` |

함께 저장: `outputs/stats/통계요약.md`, 분석 코드 `outputs/stats/analysis.py`(처음부터 다시 돌리면 같은 결과가 나오게 시드 고정). 난이도 프로필은 `difficulty_profile.py`, BERTopic은 `topic.py`(둘 다 시드 고정).

writer·dashboard 출처 표기 예: 오즈비 → `05_주모형.csv`(firth = 0 행), 하위·상위 25% 예측 확률 → `06_예측확률.csv`, 곡선 → `pred_curve.csv`, 우선순위 그림 기준선 → `10_조항주제_기준선.csv`, 주제별 인용률 CI → `10_조항주제.csv`.

# 결과 문장 판정 (2026-11-03 확정, 결과를 보기 전)
주 결과는 `05_주모형.csv`의 난이도 오즈비(1 표준편차당) 95% CI 하나로 판정한다(계획서 2-1, 2-2).

| 오즈비 95% CI | 결과 문장 |
|---|---|
| 하한 > 1 | "난이도가 높을수록 인용되는 경향이 보였다(양의 연관)" |
| 1을 포함 | "연관이 뚜렷하지 않다(불확실)" |
| 상한 < 1 | "난이도가 높을수록 인용이 적은 경향이 보였다(음의 연관)" |

- `06_예측확률.csv`의 차이(diff) CI는 **보조**다. 오즈비 판정과 어긋나면 오즈비 판정을 따르고, 어긋났다는 사실을 통계요약에 적는다.
- `exploratory = 1`(소수 쪽 30건 미만, 기준값 10)이면 문장 앞에 "탐색적으로"를 붙인다.
- `07_민감도_필수.csv`에 `direction_same = 0`인 행이 있으면 "조건에 따라 달라진다"를 덧붙인다(계획서 7-3).
- p값은 함께 보고하지만 판정 기준으로 쓰지 않는다.

# 보고 형식
- 모든 결과: **오즈비 [95% CI], 예측 확률 [95% CI], p값, N(소수 쪽 건수 포함)**.
- 결론 문장은 "관련이 있는 경향이 보인다 / 뚜렷하지 않다(불확실)" 수준.
- 민감도에서 방향이 바뀐 행은 숨기지 않고 강조한다.

# 금지
- 인과로 쓰지 않는다. p > 0.05를 "관계 없음"으로 쓰지 않는다.
- 결과가 기대와 달라도 변수·모형·표본을 바꾸지 않는다. 바꾸고 싶으면 "규칙 변경 제안"으로 보고만.
- 오즈비를 "가능성이 ~배"로 풀지 않는다.
- 숫자를 암산하지 않는다.

# 끝나면
4줄 요약 + 핵심 결과 3줄 + 한계 3줄(표본, 선택 편향, 시대 차이). 멈추고 검수(정유빈)를 기다린다.
