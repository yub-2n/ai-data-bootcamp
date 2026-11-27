# stats 전체 자동 실행 지시 (2026-11-04, 담당 팀원B)

이 지시를 받은 메인 Claude Code 세션은 **지휘만** 한다. 분석은 `stats` 에이전트가, 검수는 `stats-reviewer` 에이전트가 한다. 메인 세션은 분석 파일을 직접 고치지 않는다.

**PROJECT.md, agents/, docs/코드북.md는 어느 에이전트도 수정하지 않는다.**

## 0. 시작 전 점검 (메인 세션이 직접)

아래가 하나라도 안 맞으면 **멈추고** 무엇이 안 맞는지 보고한다. 대신 만들거나 추측하지 않는다.

- 파일: `data/processed/difficulty.csv`, `data/interim/cases.csv`, `data/interim/difficulty_id_map.csv`, `agents/stats.md`, `docs/지시/stats_실행.md`, `.claude/agents/stats.md`, `.claude/agents/stats-reviewer.md`
- 파이썬: 이 컴퓨터에서는 `python`이 아니라 **`py -3.10`** 으로 실행한다(firthlogist가 파이썬 3.11 미만만 지원). `py -3.10 -c "import pandas, numpy, scipy, statsmodels, sklearn, firthlogist"`가 에러 없이 끝나야 한다.
- 패키지가 없으면 **설치하지 말고** 없는 패키지 이름을 보고하고 멈춘다(`docs/지시/stats_실행.md` 0단계: 설치는 사람이 한다).
- 행 수 확인은 `docs/지시/stats_실행.md` 0단계 표대로 stats 에이전트가 한다.

## 1. 분석 (stats 에이전트)

stats 에이전트에게 보낸다:

> agents/stats.md와 docs/지시/stats_실행.md를 읽고 그대로 실행해. PROJECT.md는 수정하지 마. 파이썬은 `py -3.10`으로 실행해. 끝나면 docs/보고/stats_실행.md에 보고를 저장하고 멈춰.

stats 에이전트가 0단계 확인에서 멈추면, 메인 세션도 그 보고를 그대로 전하고 멈춘다.

## 2. 검수 (stats-reviewer 에이전트)

stats-reviewer 에이전트에게 보낸다:

> 가장 최근 stats 보고와 outputs/stats/를 체크리스트로 검수하고 docs/보고/검수_<회차>.md를 써.

## 3. 반복 규칙

- 판정이 **통과**면 4로 간다.
- **수정 필요**면 메인 세션이 검수 보고의 "수정 지시" 부분만 그대로 옮겨 `docs/지시/stats_수정_<n>.md`로 저장한다(내용을 더하거나 빼지 않는다). 그다음 stats 에이전트에게 "docs/지시/stats_수정_<n>.md를 읽고 해. 끝나면 docs/보고/stats_수정_<n>.md에 보고를 저장하고 멈춰."라고 보내고 2로 돌아간다(검수 회차 + 1).
- **최대 3회** 반복한다. 3회 뒤에도 통과가 아니면 멈추고 남은 항목을 보고한다.
- 판정이 **사람 확인 필요**면 반복하지 않고 **즉시 멈춘다.**

## 4. 마무리 보고 (메인 세션)

`docs/보고/stats_최종.md`에 저장하고 화면에도 출력한다.

```
한 일:
처리 건수:
제외한 것:
불확실한 점:
결과 문장 판정: (통계요약.md 맨 위 문장 그대로)
검수 회차와 최종 판정:
사람이 할 일: 정유빈 코드 재실행 대조(analysis.py), 결과 파일을 팀원C(writer·dashboard)에게 전달
```

## 절대 하지 않을 것 (모든 에이전트 공통)

- `PROJECT.md`, `agents/`, `docs/코드북.md`, `data/processed/difficulty.csv`, `data/interim/`의 파일 수정
- 파일 삭제, 패키지 설치, git commit/push, GitHub 업로드
- 원문(`data/interim/texts/`, `data/raw/`) 읽기
- 결과를 보고 변수·모형·표본·난이도 규칙을 바꾸는 것
- 검수에서 통과시키려고 기준을 느슨하게 해석하는 것

## 사람 검수는 대체하지 않는다

이 자동 검수는 보조다. PROJECT.md의 "stats 후 코드 재실행과 결과 대조"는 그대로 정유빈이 한다.
