# stats 실행 지시 (2026-11-04, 담당 팀원B)

이 파일과 `agents/stats.md`, `PROJECT.md`를 먼저 읽고, `agents/stats.md`의 분석 순서 1~10을 그대로 실행한다.
**PROJECT.md, agents/, docs/코드북.md는 수정하지 않는다.** 규칙을 바꾸고 싶으면 "규칙 변경 제안"으로 보고만 한다.

## 0. 시작 전 확인 (하나라도 안 맞으면 멈추고 보고)

| 파일 | 확인 |
|---|---|
| `data/interim/cases.csv` | 449행. `exclude_reason`이 비어 있는 행 = 분석 포함 **157건**(cited 1 = 106, 0 = 51, partial 1 = 6). 시기 ~2009 75 / 2010-2016 42 / 2017-2026 40 |
| `data/interim/difficulty_id_map.csv` | 261행(diff_id ↔ case_key) |
| `data/processed/difficulty.csv` | 261행(diff_id 기준). 팀원B 컴퓨터에 있던 파일을 이 위치에 둔다 |
| `requirements.txt` | 패키지가 없으면 설치하지 말고 무엇이 없는지 보고한다(설치는 사람이 한다) |

## 1. 합치기 (분석 1단계)

- `difficulty.csv` → `difficulty_id_map.csv`(diff_id) → `cases.csv`(case_key) 순서로 합친다. **합치는 것은 이 단계가 처음이다.**
- 분석 표본 = `cases.csv`에서 `exclude_reason`이 빈 157건.
- `difficulty_id_map.csv`에 case_key **2009-29가 두 번**(D204, D246) 있다. `cases.csv`의 2009-29도 두 행(nttId 64488 = 분석 포함, 64502 = "중복" 제외)이다. **분석 포함 행의 `clause_text`와 같은 문구를 가진 diff_id 하나만** 쓰고, 어느 것을 골랐는지 `01_합치기점검.csv`와 보고에 적는다.
- 157건 모두 difficulty가 붙었는지, 빠진 건과 이유를 `01_합치기점검.csv`에 적는다.

## 2~6. 기술통계 · 집단 비교 · 층화 · 주 모형 · 예측 확률

`agents/stats.md` 그대로. 아래만 분명히 한다.
- **주 모형**: `cited ~ difficulty_index + issue_type + period`. 소수 쪽(기각) 51건 ≥ 50이라 **일반 로지스틱 회귀**(기준값 9). 완전 분리가 생기면 Firth. 50에 가까우므로 **Firth 결과도 참고로** `05_주모형.csv` 아래(또는 `통계요약.md`)에 함께 적는다(PROJECT.md 4-8).
- 난이도 오즈비는 **분석 표본(157건)의 difficulty_index 표준편차 1당**이다. 쓴 표준편차 값을 보고에 적는다.
- 참조 범주: issue_type = 보상범위·정의, period = ~2009. 보고에 적는다.
- 부트스트랩: 1,000회 이상, 시드 42. 6(하위·상위 25%)과 6-1(곡선)은 **같은 부트스트랩 표본**.

## 7. 필수 민감도 4개 (기준값 16)

1. **① 일부 인용을 0으로**: partial = 1인 6건의 cited를 0으로 바꿔 같은 모형.
2. **② 판단 ↔ 주장**: `cases.csv`의 `arg_clause_text`가 있는 분석 사건(약 20건)은 그 문구로 난이도를 다시 계산해 바꿔 넣고, 나머지는 그대로 둔다.
   - 계산은 `outputs/stats/difficulty_colab.py`의 같은 함수(`compute`, 전문용어 사전 `outputs/stats/term_dict.csv`, 예외 = expanded, 참조 = each)로 4개 원지표를 구한다.
   - z점수는 **`difficulty.csv` 261행의 각 원지표 평균·표준편차**로 만들어 평균한다(같은 척도 유지).
   - 바꾼 사건 수를 보고에 적는다. 계산할 수 없으면 멈추지 말고 "수행하지 못함 + 이유"로 표에 남긴다.
3. **③ 조 전체**: `difficulty_index_article`로 같은 모형.
4. **④ 2010년 이후**: period ≠ ~2009인 사건만(82건). 소수 쪽 수를 적고, 30건 미만이면 exploratory = 1.

## 8. 선택 민감도

- **"풀어 쓴 서술 포함"은 반드시 한다**(PROJECT.md 4-8): `exclude_reason = "풀어 쓴 서술"`인 사건(difficulty가 있는 것)을 더해 같은 모형. 더한 건수를 적는다.
- 나머지는 `agents/stats.md` 8번. 못 한 것은 done = 0.

## 9~10. 시계열 · 조항 주제

`agents/stats.md` 그대로. 조항 주제는 `cases.csv`의 `topic` 열을 쓴다.

## 결과 문장

`agents/stats.md` "결과 문장 판정" 표 그대로. 판정 결과(양의 연관 / 뚜렷하지 않음 / 음의 연관)와 덧붙일 말("탐색적으로", "조건에 따라 달라진다")을 `통계요약.md` 맨 위에 적는다.

## 출력

- `outputs/stats/01_합치기점검.csv` ~ `10_조항주제.csv`, `pred_curve.csv`, `통계요약.md`, `analysis.py`(처음부터 다시 돌리면 같은 결과).
- **보고 파일**: `docs/보고/stats_실행.md`에 저장한다. 내용: 4줄 요약(한 일 / 처리 건수 / 제외한 것 / 불확실한 점) + 핵심 결과 3줄 + 한계 3줄 + 위에서 "보고에 적는다"고 한 항목 전부 + 사람이 확인할 점.
- 끝나면 멈춘다. 검수는 정유빈(같은 코드 재실행).

## 금지

- 원문(`data/interim/texts/`)은 읽지 않는다(필요 없음).
- 결과가 기대와 달라도 변수·모형·표본을 바꾸지 않는다.
- 인과 표현, "가능성이 ~배" 표현을 쓰지 않는다.
