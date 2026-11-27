# 파일럿 난이도 지표 요약 (difficulty_colab.py pilot)

- 처리 건수: 21 (blind_id 기준, 결과·사건 정보 없음)
- 전문용어 사전: 41개 (`outputs/stats/term_dict.csv`)
- 예외 표현 사전 기본값: v7, 참조 세기 기본값: each (회의에서 확정)

## 지표별 분포

| 지표 | 평균 | 표준편차 | 최소 | 최대 | 0 비율 |
|---|---|---|---|---|---|
| words_per_sentence | 29.909 | 14.810 | 13.000 | 80.000 | 0.000 |
| exception_count_v7 | 0.571 | 0.978 | 0.000 | 3.000 | 0.667 |
| exception_count_expanded | 0.762 | 1.044 | 0.000 | 3.000 | 0.571 |
| term_ratio | 0.172 | 0.088 | 0.016 | 0.381 | 0.000 |
| ref_count_each | 1.143 | 1.153 | 0.000 | 3.000 | 0.429 |
| ref_count_chain | 1.048 | 1.024 | 0.000 | 3.000 | 0.429 |

## 기준값 12

- term_ratio가 0인 조항 비율: 0.000 → 50% 미만이라 **종합 지수에 포함**

## 상관행렬 (지수에 쓰는 버전)

| index | words_per_sentence | exception_count | term_ratio | ref_count |
|---|---|---|---|---|
| words_per_sentence | 1.000 | -0.073 | -0.141 | 0.551 |
| exception_count | -0.073 | 1.000 | -0.599 | 0.101 |
| term_ratio | -0.141 | -0.599 | 1.000 | -0.227 |
| ref_count | 0.551 | 0.101 | -0.227 | 1.000 |

- |r| ≥ 0.7인 쌍: 없음

## 종합 지수

- 사용 지표: words_per_sentence, exception_count, ref_count, term_ratio (각 z점수의 평균)

## 문장 나누기 점검 (원문은 적지 않음)

- words_per_sentence 최대: P11 — 80.0 (문장 1개, 어절 80개, 가장 긴 문장 80어절, 문구 형태 풀어 쓴 서술)
- words_per_sentence 최소: P21 — 13.0 (문장 1개, 어절 13개, 가장 긴 문장 13어절, 문구 형태 따옴표 인용)
