# relabel 1~4단계 보고 (2026-11-04, 라벨 v2 실험, 탐색적)

- **한 일**: A셋(골드 30건)·B셋(빈틈 챌린지 22건) 대상 확정 → 판단 부분에서 판례·판결문을 **그대로 옮긴 인용은 지우고** 조각 추출 → 격리 폴더(코드북·조각·지시만) 생성 → 규칙 v1 값 붙임.
- **처리 건수**: 사건 52건(A 30, B 22), 조각 100개(ambiguity 48, issue_type 52). 판례 원문 인용을 지운 사건 13건.
- **제외한 것**: 판례·판결문 원문 인용(따옴표 안 법원 문장, "○○법원 … 선고 … 판결: “…”" 각주형). ambiguity 키워드가 없는 사건 19건은 ambiguity 조각이 없다(규칙·LLM 모두 0으로 보고 사람 확인 대상에서 뺄지 팀 결정 필요). explained_duty는 이번에 하지 않음.
- **불확실한 점**: 인용 제거는 정규식이라 일부 원문 인용이 남거나(따옴표 없는 인용), 위원회 문장 일부가 같이 지워졌을 수 있다. B셋은 기존 챌린지 셋 22건을 그대로 썼다(빈틈 유형별 최대 10개 규칙이면 G2만 2건 늘어남). B셋 유형별 건수: {'G2': 8, 'G1': 7, 'G4': 3, 'G3': 2, 'G5': 2}.

## 산출물
- `relabel/snippets.csv`: snippet_id, case_key, set, gap_type, label_name, part, snippet_text (팀 내부용, 병명 포함 가능 → 밖으로 내보내지 않음)
- `relabel/rule_v1.csv`: snippet_id별 규칙 v1 값(cases.csv)
- `relabel/추출통계.csv`: 사건별 ambiguity 조각 수, 지운 인용 글자 수
- `relabel/isolated/`: 코드북.md, snippets_for_llm.csv(snippet_id·label_name·snippet_text만, 번호는 섞음), LABELER.md(=CLAUDE.md)

## 다음(5단계, 격리 라벨링 뒤)
llm_run1.csv, llm_run2.csv가 오면: 규칙·LLM1·LLM2 모두 같으면 auto, 하나라도 다르면 human. auto 중 무작위 10%(시드 42)와 ambiguity = 1인 auto 전부도 human. 사람 시트 3개로 나눔(답 숨김, 시작·끝 시각 기록).
