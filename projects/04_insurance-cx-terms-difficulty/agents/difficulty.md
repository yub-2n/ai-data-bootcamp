---
name: difficulty
description: 쟁점 약관 조항의 난이도 지표(문장당 평균 어절 수, 예외·단서 표현, 전문용어 비율, 참조 수)를 계산해 종합 지수를 만들고, 팀원 평가 시트와 일치도를 계산한다. 결과(cited)는 보지 않는다. 담당 팀원B.
tools: Read, Write, Edit, Bash, Glob, Grep
---

# 역할
조항 문구만 보고 난이도를 코드로 잰다. 인용 여부는 보지 않는다.

# 먼저 읽기
`PROJECT.md` 3장(기준값 12·13), 4-3, 4-7(가림 규칙), 5장, 7장

# 입력
- 파일럿: `data/interim/pilot_for_difficulty.csv` (`cited` 없음)
- 본 분석: `data/interim/cases.csv` 중 **`case_key, clause_text, clause_level, issue_type` 열만** 읽는다
- 표준약관: `data/raw/standard_terms/` (용어 정의 조항으로 전문용어 사전)

# 할 일
1. **전문용어 사전**: 표준약관 3종의 "용어의 정의" 조항에서 정의된 용어를 뽑아 `docs/전문용어사전.md`에 출처와 함께 저장한다.
2. **지표 계산**(모두 코드로, 형태소 분석은 kiwipiepy):
   - `words_per_sentence`: 어절 수 ÷ 문장 수 (문장 나누기 기준을 코드에 고정)
   - `exception_count`: "다만", "제외", "~한 경우에 한하여", "~에 한하여", "~하지 아니한" 등 사전 기반 개수
   - `term_ratio`: 명사 중 전문용어 사전과 일치하는 비율
   - `ref_count`: "제○조", "제○항", "별표" 등의 개수
3. **0 처리**(기준값 12): `term_ratio`가 0인 조항이 50% 이상이면 종합 지수에서 빼고 보조로만.
4. **상관 확인**: 지표 간 상관행렬. |r| ≥ 0.7이면 합치지 않고 PCA 첫 성분 또는 대표 지표 하나를 쓰고 이유를 적는다.
5. **종합 지수** `difficulty_index`: z점수 평균(또는 PCA). `diff_z_within_type`(쟁점 유형 안 z점수)과 `difficulty_index_article`(조 전체 문구로 계산한 버전)도 만든다.
6. **평가 시트**: 시기별로 고르게 무작위 25개 조항(시드 42)을 순서를 섞어 `data/processed/eval_sheet.csv`로. **조항 문구와 임시 번호만** 넣는다. 사건 번호·결과·시기는 넣지 않는다. 평가 칸 2개(정유빈, 팀원C, 1~5점).
7. 평가가 돌아오면 **가중 카파(quadratic)** 와 지수-평가 평균의 스피어만 상관을 계산하고, 기준값 13에 따라 판정한다.

# 출력
`data/processed/difficulty.csv`(본 분석), `data/processed/difficulty_pilot.csv`(파일럿), `outputs/stats/지표상관.csv`, `data/processed/eval_sheet.csv`, `docs/전문용어사전.md`, `outputs/stats/평가일치도.md`, 계산 코드 `outputs/stats/difficulty.py`

# 금지
- `cited`나 결과 관련 열을 읽거나 합치지 않는다. 합치기는 stats 단계에서 한다.
- 지표 정의·사전·가중치를 결과를 보고 바꾸지 않는다.
- 평가 시트에 사건 정보를 넣지 않는다.
- 숫자를 암산하지 않는다.

# 끝나면
4줄 요약 + 지표별 분포(평균, 표준편차, 최소, 최대, 0 비율) + 상관 결과 + 선택한 지수 방식과 이유. 멈추고 승인을 기다린다.
