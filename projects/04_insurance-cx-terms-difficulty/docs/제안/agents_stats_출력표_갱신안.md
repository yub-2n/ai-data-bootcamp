# agents/stats.md "출력" 표 갱신안 (초안, 반영은 정유빈)

준비: 팀원B 쪽 Claude, 2026-11-04. 지시: `docs/지시/팀원몫_정리.md` 3번.
`agents/stats.md`는 고치지 않았다. 아래 1은 지금 표를 그대로 옮긴 것이고, 2가 수정안이다. **바뀐 부분만 굵게** 표시했고, 각 변경에 근거 파일을 붙였다. 열 이름은 지금 `outputs/stats/`의 실제 파일 머리 줄에서 확인했다(2026-11-04 16:44 기준).

## 1. 지금 표 (agents/stats.md 29~48행 그대로)

> # 출력 (2026-11-03 확정, 파일 번호 = 위 분석 순서의 단계 번호)
> writer·dashboard는 아래 파일과 열 이름을 그대로 출처로 쓴다. 이름과 열을 바꾸지 않는다. 모두 `outputs/stats/`에 `utf-8-sig`로 저장한다.
>
> | 단계 | 파일 | 열 |
> |---|---|---|
> | 1 합치기 | `01_합치기점검.csv` | item(합친 수 / 빠진 수 / 빠진 이유), n |
> | 2 기술통계 | `02_기술통계.csv` | issue_type, period, n, n_cited, cited_rate, ci_low, ci_high (전체 합계 행 포함) |
> | 3 집단 비교 | `03_집단비교.csv` | split(median / tertile), group, n, n_cited, cited_rate, ci_low, ci_high, p |
> | 4 층화 | `04_층화.csv` | issue_type(마지막 행 = MH 합산), odds_ratio, ci_low, ci_high, n, breslow_day_p |
> | 5 주 모형 | `05_주모형.csv` | term, coef, odds_ratio, ci_low, ci_high, p, n, n_minority, firth(0/1), exploratory(0/1). 난이도 행의 odds_ratio = 1 표준편차당 |
> | 6 예측 확률 | `06_예측확률.csv` | point(low25 / high25 / diff), difficulty_value, pred, ci_low, ci_high, n, n_boot, seed. **3행**: 모든 사건의 난이도를 바꿔 넣고 평균한 두 값과 그 차이(계획서 7-1). 사건별 예측값은 저장하지 않는다(대시보드가 다시 평균 내지 않도록) |
> | 6-1 곡선 | `pred_curve.csv` | 기준값 18 그대로: difficulty, pred, ci_low, ci_high, n, n_near |
> | 7 필수 민감도 | `07_민감도_필수.csv` | analysis(main / ① 일부인용0 / ② 판단↔주장 / ③ 조 전체 / ④ 2010년 이후), odds_ratio, ci_low, ci_high, n, n_minority, direction_same(0/1) |
> | 8 선택 민감도 | `08_민감도_선택.csv` | 7과 같은 열 + done(0/1). 못 한 것은 done = 0, 나머지 칸은 "수행하지 않음" |
> | 9 시계열 | `09_시계열.csv` | year_bin, n, n_cited, cited_rate, ci_low, ci_high, mean_difficulty, share_<쟁점 유형>(유형마다 한 열) |
> | 10 조항 주제 | `10_조항주제.csv` | topic, n, cited_rate(5건 이상만, 나머지는 빈칸), mean_difficulty |
>
> 함께 저장: `outputs/stats/통계요약.md`, 분석 코드 `outputs/stats/analysis.py`(처음부터 다시 돌리면 같은 결과가 나오게 시드 고정).
>
> writer·dashboard 출처 표기 예: 오즈비 → `05_주모형.csv`, 하위·상위 25% 예측 확률 → `06_예측확률.csv`, 곡선 → `pred_curve.csv`.

## 2. 수정안

# 출력 (2026-11-03 확정, **2026-11-04 갱신**, 파일 번호 = 위 분석 순서의 단계 번호)
writer·dashboard는 아래 파일과 열 이름을 그대로 출처로 쓴다. 이름과 열을 바꾸지 않는다. 모두 `outputs/stats/`에 `utf-8-sig`로 저장한다.

### 2-1. 주 분석 (analysis.py)

| 단계 | 파일 | 열 |
|---|---|---|
| 1 합치기 | `01_합치기점검.csv` | item(합친 수 / 빠진 수 / 빠진 이유), n |
| 2 기술통계 | `02_기술통계.csv` | issue_type, period, n, n_cited, cited_rate, ci_low, ci_high (전체 합계 행 포함) |
| 3 집단 비교 | `03_집단비교.csv` | split(median / tertile), group, n, n_cited, cited_rate, ci_low, ci_high, p |
| 4 층화 | `04_층화.csv` | issue_type(마지막 행 = MH 합산), odds_ratio, ci_low, ci_high, n, breslow_day_p |
| 5 주 모형 | `05_주모형.csv` | term, coef, odds_ratio, ci_low, ci_high, p, n, n_minority, firth(0/1), exploratory(0/1). 난이도 행의 odds_ratio = 1 표준편차당. **주 결과는 firth = 0 행이고, firth = 1 행은 참고용 Firth 결과다**(근거: `docs/지시/stats_실행.md` 2~6절, `docs/보고/stats_실행.md` 사람 확인 2) |
| 6 예측 확률 | `06_예측확률.csv` | point(low25 / high25 / diff), difficulty_value, pred, ci_low, ci_high, n, n_boot, seed. **3행**: 모든 사건의 난이도를 바꿔 넣고 평균한 두 값과 그 차이(계획서 7-1). 사건별 예측값은 저장하지 않는다(대시보드가 다시 평균 내지 않도록) |
| 6-1 곡선 | `pred_curve.csv` | 기준값 18 그대로: difficulty, pred, ci_low, ci_high, n, n_near |
| 7 필수 민감도 | `07_민감도_필수.csv` | analysis(main / ① 일부인용0 / ② 판단↔주장 / ③ 조 전체 / ④ 2010년 이후), odds_ratio, ci_low, ci_high, n, n_minority, direction_same(0/1), **firth(0/1), exploratory(0/1)**(맨 뒤 2열. 각 행 모형에서 실제로 쓴 방식, 기준값 9·10. 근거: `docs/지시/마무리_정리.md` 2번, `docs/보고/마무리_정리.md` 2절, `검수_4.md`) |
| 8 선택 민감도 | `08_민감도_선택.csv` | 7의 **처음 7열(analysis ~ direction_same)** + done(0/1). 못 한 것은 done = 0, 나머지 칸은 "수행하지 않음". **08에는 firth·exploratory 열을 두지 않는다**(근거: `docs/보고/마무리_정리.md` 2절 "08의 열은 그대로") |
| 8 (사후 1행) | `08_민감도_선택.csv` 맨 아래 | **analysis = `쟁점 유형 R2(판단 안 면책 조항, 사후)`. 열은 위와 같다. 08에는 exploratory 열이 없으므로, 사후 분석이라는 표시는 통계요약.md 8장에 "사후·탐색적"으로 적는다**(근거: `docs/지시/stats_수정_3.md`, `docs/보고/stats_수정_3.md`, `docs/issue_type_민감도_규칙.md`, 이 표시 방식은 `docs/지시/팀원몫_정리.md` 3번에 결정으로 적힘. 단 `검수_3.md`·`검수_6.md` 기준으로는 "사람 확인 필요 2"가 아직 열린 항목이라 정유빈 확인 필요) |
| 9 시계열 | `09_시계열.csv` | year_bin, n, n_cited, cited_rate, ci_low, ci_high, mean_difficulty, share_<쟁점 유형>(유형마다 한 열) |
| 10 조항 주제 | `10_조항주제.csv` | topic, n, cited_rate(5건 이상만, 나머지는 빈칸), mean_difficulty, **n_cited, ci_low, ci_high**(맨 뒤 3열. Wilson 95% CI, 5건 미만 주제는 n_cited만 채우고 CI는 빈칸. 근거: `docs/지시/stats_수정_2.md` 1번, `docs/보고/stats_수정_2.md` 1절) |
| **10 기준선** | **`10_조항주제_기준선.csv`** | **item, value, 설명. 2행: cited_rate_overall(분석 157건 전체 인용률), n_median_topics(인용률을 표시하는 5건 이상 주제들의 n 중앙값). 우선순위 그림의 기준선 값만 담고, 사분면 판정·순위는 하지 않는다**(근거: `docs/지시/stats_수정_2.md` 2번, `docs/보고/stats_수정_2.md` 2절) |

### 2-2. **난이도 프로필 (difficulty_profile.py, 탐색적 보조 분석)**

**근거: `docs/지시/난이도프로필_실행.md` 출력 표, `docs/지시/난이도프로필_수정_1.md`, `docs/보고/난이도프로필_수정_1.md`, `프로필검수_1.md`·`프로필검수_2.md` 1번(추가 열 확인). 새 지표·차원 점수는 cited와 검정하지 않는다.**

| 파일 | 열 |
|---|---|
| **`11_표준약관기준.csv`** | **std_type(생명보험 / 질병·상해보험 / 실손의료보험 / 전체), unit(조 / 항 / 문장), n_units, usable_n50, used_as_benchmark, 지표 10개 × (\_median, \_p90)**. usable_n50·used_as_benchmark는 지시 표 밖에 실행이 더한 열 |
| **`12_조항프로필.csv`** | **diff_id, case_key, in_analysis, topic, issue_type, period, clause_level, bench_note, 지표 10개(조 단위), pct_<지표> 10개, dim_vocab, dim_sentence, dim_logic, dim_ref, high_<차원> 4개, top_dim, dim_<차원>_orig 4개(보조), top_dim_rel**(top_dim_rel은 수정 1-4에서 맨 뒤에 더함, 그림 A4 점 색 표시용) |
| **`13_주제별프로필.csv`** | **topic, n, cited_rate(10번 값 그대로), dim_<차원>_median 4개, high_<차원>_rate 4개, top_dim_mode** |
| **`13b_유형시기별프로필.csv`** | **group_var(issue_type / period), group, n, cited_rate(02번 '전체' 행 값), 나머지는 13과 같음** |
| **`14_문장핫스팟.csv`** | **diff_id, case_key, topic, n_sents, sent_no, hotspot_text, hotspot_dim, dim 점수 4개**(n_sents는 실행이 더한 열) |
| **`15_평가타당성.csv`** | **measure, role(기본(조 단위) / 부록(원래 단위) / 참고), spearman, ci_low, ci_high, n, note**(role은 수정 1-6, note는 실행이 더한 열. 마지막 행 = 두 평가자 가중 카파) |
| **`16_고쳐쓰기.csv`** | **rewrite_id, diff_id, topic, clause_level, bench_unit, 차원 점수 4개 전/후, 지표 10개 전/후, human_answer, status**(clause_level·bench_unit은 실행이 더한 열, human_answer·status는 수정 1-5) |
| **`난이도프로필_요약.md`** | **결과 요약과 한계** |
| **그림 A** | **`figs/fig_A1_주제별차원.png`, `fig_A2_표준약관대비.png`, `fig_A3_고쳐쓰기전후.png`, `fig_A4_우선순위.png`(png 200dpi)** |
| **코드** | **`outputs/stats/difficulty_profile.py`**(**이전 이름 `profile.py`. 파이썬 내장 모듈 `profile`과 이름이 겹쳐 2026-11-04 이름을 바꿈.** 근거: `docs/지시/마무리_정리.md` 3번, `docs/보고/마무리_정리.md` 3절) |

### 2-3. **BERTopic (topic.py, 탐색적 보조 분석)**

**근거: `docs/지시/버토픽_실행.md` 출력 표, `docs/보고/버토픽_실행.md`, `토픽검수_1.md` 1번. 토픽은 cited와 검정하지 않는다.**

| 파일 | 열 |
|---|---|
| **`17_토픽목록.csv`** | **corpus(title / clause), topic, label, n, keywords, rep_docs** |
| **`18_토픽배정.csv`** | **case_key, corpus, text_clean, topic, prob, topic_reduced, rule_topic, issue_type, in_analysis, exemption_cue(0/1)** |
| **`19_토픽비교.csv`** | **table(rule_topic / issue_type / metric), row, col, n**(긴 형식 교차표. 맨 아래 table = metric 6행이 ARI·NMI) |
| **`20_토픽안정성.csv`** | **corpus, seed_a, seed_b, ari** |
| **`21_면책단서.csv`** | **issue_type, n, n_cue, share_cue** |
| **`22_토픽인용률.csv`** | **topic, label, n, n_cited, cited_rate, ci_low, ci_high**(분석 포함 5건 이상 토픽만, Wilson CI, 검정 없음) |
| **`토픽_요약.md`** | **결과 요약과 한계**(topic.py가 만드는 파일이 아니라 에이전트가 쓴 문서) |
| **그림 B** | **`figs/fig_B1_토픽지도.png`, `fig_B2_토픽키워드.png`, `fig_B3_규칙주제대비.png`, `fig_B4_면책단서.png`** |
| **코드** | **`outputs/stats/topic.py`, 임베딩 캐시 `outputs/stats/topic_cache/`** |

함께 저장: `outputs/stats/통계요약.md`, 분석 코드 `outputs/stats/analysis.py`(처음부터 다시 돌리면 같은 결과가 나오게 시드 고정). **난이도 프로필은 `difficulty_profile.py`, BERTopic은 `topic.py`(둘 다 시드 고정).**

writer·dashboard 출처 표기 예: 오즈비 → `05_주모형.csv`(**firth = 0 행**), 하위·상위 25% 예측 확률 → `06_예측확률.csv`, 곡선 → `pred_curve.csv`, **우선순위 그림 기준선 → `10_조항주제_기준선.csv`, 주제별 인용률 CI → `10_조항주제.csv`**.

## 3. 바뀐 점 목록 (근거 파일)

| # | 바뀐 점 | 근거 |
|---|---|---|
| 1 | 07 맨 뒤 `firth`, `exploratory` | `docs/지시/마무리_정리.md` 2번, `docs/보고/마무리_정리.md`, `검수_4.md` |
| 2 | 10 맨 뒤 `n_cited`, `ci_low`, `ci_high` | `docs/지시/stats_수정_2.md` 1번, `docs/보고/stats_수정_2.md` |
| 3 | `10_조항주제_기준선.csv` 새 파일(item, value, 설명) | `docs/지시/stats_수정_2.md` 2번, `docs/보고/stats_수정_2.md` |
| 4 | 08 맨 아래 `쟁점 유형 R2(판단 안 면책 조항, 사후)` 행. 08에는 exploratory 열이 없고 통계요약에 "사후·탐색적"으로 적음 | `docs/지시/stats_수정_3.md`, `docs/보고/stats_수정_3.md`, `docs/issue_type_민감도_규칙.md`, `docs/지시/팀원몫_정리.md` 3번(표시 방식). `검수_3.md` 사람 확인 2는 아직 열림 |
| 5 | 11~16, 13b, 난이도프로필_요약.md, 그림 A1~A4 | `docs/지시/난이도프로필_실행.md` 출력 표, `docs/지시/난이도프로필_수정_1.md`, `프로필검수_2.md` |
| 6 | 17~22, 토픽_요약.md, 그림 B1~B4 | `docs/지시/버토픽_실행.md` 출력 표, `토픽검수_1.md` |
| 7 | `profile.py` → `difficulty_profile.py` | `docs/지시/마무리_정리.md` 3번, `docs/보고/마무리_정리.md` 3절 |
| 8 | 05 "주 결과는 firth = 0 행" 문구 | `docs/보고/stats_실행.md` 사람 확인 2, `통계요약.md` 5장(표 열은 그대로, 설명만 더함) |

- 8번은 지시 3번 목록에 없는 문구 보탬이다. 열은 바뀌지 않는다. 필요 없으면 빼도 된다(정유빈 판단).
- 참고: `.claude/agents/profile-reviewer.md`에 옛 이름 `profile.py`가 남아 있다(`검수_4.md` 사람 확인 3, `다음에_바꿀_점.md` 5-3). 이 갱신안의 범위 밖이다.
