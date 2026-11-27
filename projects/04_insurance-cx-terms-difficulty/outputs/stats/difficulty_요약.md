# 본 분석 난이도 요약 (difficulty_colab.py full)

- 처리 건수: 261 (diff_id 기준, 결과·사건 정보 없음). 문구가 빈 행은 계산하지 않음
- 전문용어 사전: 36개, 예외 표현: expanded, 참조: each

## 지표별 분포

| 지표 | 평균 | 표준편차 | 최소 | 최대 | 0 비율 |
|---|---|---|---|---|---|
| words_per_sentence | 29.525 | 15.029 | 4.000 | 99.000 | 0.000 |
| exception_count | 0.655 | 1.210 | 0.000 | 10.000 | 0.625 |
| term_ratio | 0.101 | 0.086 | 0.000 | 0.500 | 0.130 |
| ref_count | 1.410 | 1.801 | 0.000 | 12.000 | 0.364 |
| difficulty_index | 0.000 | 0.541 | -0.970 | 3.165 | 0.000 |
| difficulty_index_article | -0.000 | 0.544 | -1.000 | 2.824 | 0.000 |

## 기준값 12

- term_ratio 0 비율: 0.130 → 50% 미만이라 종합 지수에 포함
- 예외 표현 0 비율: 0.625 → 50% 이상이라 한계에 적는다(4-8)

## 상관행렬

| index | words_per_sentence | exception_count | term_ratio | ref_count |
|---|---|---|---|---|
| words_per_sentence | 1.000 | 0.138 | -0.179 | 0.438 |
| exception_count | 0.138 | 1.000 | -0.082 | 0.162 |
| term_ratio | -0.179 | -0.082 | 1.000 | -0.145 |
| ref_count | 0.438 | 0.162 | -0.145 | 1.000 |

- |r| ≥ 0.7인 쌍: 없음

## 종합 지수

- 사용 지표: words_per_sentence, exception_count, ref_count, term_ratio (각 z점수의 평균). `difficulty_index_article`은 조 전체 문구로 같은 방식 계산
