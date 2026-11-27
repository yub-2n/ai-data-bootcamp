# stats 수정 3: issue_type 사후 민감도(R2) 1줄 추가 (2026-11-04)

`stats_수정_2.md`가 끝난 뒤 실행한다. **PROJECT.md, agents/, cases.csv, difficulty.csv는 수정하지 않는다.** 주 모형·필수 민감도·다른 선택 민감도 숫자는 바뀌면 안 된다.

배경: `docs/issue_type_민감도_규칙.md`(규칙을 결과 보기 전에 기록, 골드 A셋 29/30으로 통과). 팀 결정 "사전 규칙 유지 + 사후 민감도 추가".

## 할 일

1. `data/processed/issue_type_r2.csv`(case_key, issue_type_r2, r2_source, 157행)를 `case_key`로 분석 표본에 합친다. 빠지는 사건이 있으면 멈추고 보고한다.
2. 주 모형과 똑같은 식(난이도 + issue_type + period, 같은 참조 범주)에서 issue_type만 issue_type_r2로 바꿔 로지스틱을 돌린다.
3. `08_민감도_선택.csv`의 맨 아래에 한 줄 추가한다.
   - analysis = `쟁점 유형 R2(판단 안 면책 조항, 사후)`
   - 나머지 열은 다른 행과 같은 방식(odds_ratio, ci_low, ci_high, n, n_minority, direction_same, done)
   - 칸이 0인 범주 때문에 Firth가 필요하면 기존 규칙대로 하고 보고에 적는다.
4. `통계요약.md` 선택 민감도 부분에 이 줄을 "사후 추가(2026-11-04, 탐색적)"로 적는다. **판정 문구("연관이 뚜렷하지 않다")는 바꾸지 않는다.**
5. `analysis.py`에 반영해 처음부터 다시 돌려도 같은 결과가 나오게 한다. 다른 csv가 바이트 단위로 그대로인지 확인한다.

## 보고

`docs/보고/stats_수정_3.md`: R2 행 숫자, 주 결과와 방향이 같은지, 합친 건수, 다른 파일이 그대로인지. 끝나면 멈춘다.
