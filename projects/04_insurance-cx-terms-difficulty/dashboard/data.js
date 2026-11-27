/*
 * data.js — 대시보드 실제 결과(예시 데이터 아님). dashboard/_build/make_data.py가 만듦(2026-11-05 12:04).
 * 키 = 결과 파일 이름(확장자 뺌), 행의 키 = 그 CSV 첫 줄의 열 이름. 빈칸 = null. 숫자는 고치거나 계산하지 않음.
 * 08의 "수행하지 않음"은 글자 그대로 둠(숫자로 쓰지 않음). 17의 rep_docs, 18 전체는 넣지 않음(안건명).
 * 원본: outputs/stats/*.csv, outputs/stats/통계요약.md, outputs/qual/사례_담보집계_표1.csv, docs/제외사유_비교표.csv,
 *       relabel/결과_*.csv, (글 숫자) relabel/결과.md, docs/issue_type_민감도_규칙.md, docs/수집근거표.md
 * 통계요약_2장_난이도분포·통계요약_2장_히스토그램 = outputs/stats/통계요약.md 2장 표·도수를 옮겨 적은 것(계산 없음)
 */
window.DASHBOARD_DATA = {
 "is_sample": false,
 "meta": {
  "title": "약관 난이도와 보험금 분쟁 결과",
  "client": "보험사 소비자보호·상품(약관) 담당 부서장(가상의 의뢰인)",
  "decision": "분쟁이 몰리는 약관 조항 중 어디부터 쉬운 말로 고치고 설명을 강화할지 우선순위를 정한다",
  "question": "분쟁에서 쟁점이 된 약관 조항이 어려울수록 고객 주장이 받아들여지는(인용되는) 경향이 있는가?",
  "scope": "공개된 금감원 분쟁조정결정례(보험, 자동차보험 제외, 결정 연도 1996~2026, 분석 포함은 1998~2026) 안에서의 경향. 1996년 제96-23호 1건은 tif 형식이라 제외, 1997년 결정 23건은 모두 자동차보험이라 제외",
  "analysis_basis": "판단 기반(위원회 판단 부분에서 처음 언급된 약관 조항)",
  "model_formula": "cited ~ difficulty_index + issue_type + period (일반 로지스틱, 참조 범주 보상범위·정의, ~2009)",
  "conclusion": "연관이 뚜렷하지 않다(불확실)",
  "conclusion_source": "outputs/stats/통계요약.md '결과 문장 판정'",
  "common_note": null,
  "priority_hypothesis": [],
  "collected": {
   "decisions": "2026-10-30 (결정례 목록·상세 페이지·첨부 결정문 수집)",
   "cases_list": "2026-10-30 확인 (분쟁조정 사례 목록, 사람이 복사)",
   "standard_terms": "2026-11-03 확인 (표준약관 3종, 2026. 9. 10. 시행본)",
   "source": "docs/수집근거표.md"
  },
  "generated_at": "2026-11-05 12:04",
  "limits_stats": [
   "표본: 분석 157건, 기각 51건으로 작아 CI가 넓다. 분쟁조정을 신청하고 결정문이 공개된 사건뿐이다.",
   "선택 편향: 풀어 쓴 서술 91건이 빠졌고 인용률이 14.2%p 낮다(기준값 11 초과, PROJECT.md 4-8 수치). 선택 민감도 \"풀어 쓴 서술 포함\" 결과는 8장. 조항을 뽑을 수 있었던 사건만 들어 있다.",
   "시대 차이: 결정문 양식·약관 문구가 시기마다 다르다(옛 결정 75건). 전문용어 사전은 현행 표준약관 기준이다.",
   "지수 타당성: 평가 일치도 카파 0.059(기준값 13 미달), 예외 표현 0 비율 62.5%(PROJECT.md 4-8·인계 문서 수치).",
   "R2는 A셋에서 R1이 틀린 사건의 모양을 알고 만든 규칙이라 A셋 29/30도 완전히 독립된 검증이 아니다.",
   "조항 주제(10번, 우선순위 그림)도 처음 언급 조항 기준이라 같은 문제가 있다."
  ],
  "method_08": {
   "풀어 쓴 서술 포함": {
    "method": "일반 로지스틱",
    "exploratory": 0
   },
   "붙임 문구 사건만": {
    "method": "Firth",
    "exploratory": 1
   },
   "지표 하나씩: words_per_sentence": {
    "method": "일반 로지스틱",
    "exploratory": 0
   },
   "지표 하나씩: exception_count": {
    "method": "일반 로지스틱",
    "exploratory": 0
   },
   "지표 하나씩: term_ratio": {
    "method": "일반 로지스틱",
    "exploratory": 0
   },
   "지표 하나씩: ref_count": {
    "method": "일반 로지스틱",
    "exploratory": 0
   },
   "설명의무 위반 인정 사건 제외": {
    "method": "일반 로지스틱",
    "exploratory": 0
   },
   "유형 안 표준화": {
    "method": "일반 로지스틱",
    "exploratory": 0
   },
   "쟁점 유형 R2(판단 안 면책 조항, 사후)": {
    "method": "일반 로지스틱",
    "exploratory": 0
   }
  },
  "reason_08": {
   "처음 언급 대신 최댓값": "여러 조항의 난이도가 입력에 없음(difficulty.csv는 사건당 처음 언급 조항 1개)",
   "처음 언급 대신 평균": "여러 조항의 난이도가 입력에 없음(difficulty.csv는 사건당 처음 언급 조항 1개)",
   "쟁점 판단 문장 한정(계획서 7-3)": "쟁점 정리 문장 안의 조항을 따로 뽑은 열이 입력에 없음",
   "쟁점 문장에 가장 가까운 조항(PROJECT.md 4-8 ④)": "가장 가까운 조항을 뽑은 열이 입력에 없음"
  }
 },
 "rules": {
  "small_n_minority": 30,
  "firth_minority": 50,
  "small_cell": 5,
  "max_quote_sentences": 3,
  "n_near_faint": 5
 },
 "01_합치기점검": [
  {
   "item": "합친 수",
   "n": 157
  },
  {
   "item": "빠진 수",
   "n": 0
  },
  {
   "item": "빠진 이유: 없음(분석 포함 157건 모두 difficulty 붙음)",
   "n": 0
  },
  {
   "item": "입력: cases.csv 행",
   "n": 449
  },
  {
   "item": "입력: cases.csv 분석 포함(exclude_reason 빈 행)",
   "n": 157
  },
  {
   "item": "입력: difficulty_id_map.csv 행",
   "n": 261
  },
  {
   "item": "입력: difficulty.csv 행",
   "n": 261
  },
  {
   "item": "중복 처리: case_key 2009-29의 diff_id D204/D246 중 D204 사용, D246 제외(cases.csv 두 행 문구 같음=1, 두 diff_id 지표 모두 같음=1)",
   "n": 1
  },
  {
   "item": "점검: issue_type이 cases.csv와 difficulty.csv에서 다른 사건",
   "n": 0
  },
  {
   "item": "점검: cases.csv case_key 2012-14 두 행(분석 포함 1, 제외 배포용 문서), difficulty_id_map에 1번 → 분석 포함 행에만 사용",
   "n": 1
  }
 ],
 "02_기술통계": [
  {
   "issue_type": "보상범위·정의",
   "period": "~2009",
   "n": 59,
   "n_cited": 34,
   "cited_rate": 0.5763,
   "ci_low": 0.4493,
   "ci_high": 0.6939
  },
  {
   "issue_type": "보상범위·정의",
   "period": "2010-2016",
   "n": 31,
   "n_cited": 21,
   "cited_rate": 0.6774,
   "ci_low": 0.5014,
   "ci_high": 0.8143
  },
  {
   "issue_type": "보상범위·정의",
   "period": "2017-2026",
   "n": 26,
   "n_cited": 24,
   "cited_rate": 0.9231,
   "ci_low": 0.7586,
   "ci_high": 0.9786
  },
  {
   "issue_type": "보상범위·정의",
   "period": "전체",
   "n": 116,
   "n_cited": 79,
   "cited_rate": 0.681,
   "ci_low": 0.5916,
   "ci_high": 0.7589
  },
  {
   "issue_type": "면책",
   "period": "~2009",
   "n": 6,
   "n_cited": 5,
   "cited_rate": 0.8333,
   "ci_low": 0.4365,
   "ci_high": 0.9699
  },
  {
   "issue_type": "면책",
   "period": "2010-2016",
   "n": 3,
   "n_cited": 1,
   "cited_rate": 0.3333,
   "ci_low": 0.0615,
   "ci_high": 0.7923
  },
  {
   "issue_type": "면책",
   "period": "2017-2026",
   "n": 8,
   "n_cited": 6,
   "cited_rate": 0.75,
   "ci_low": 0.4093,
   "ci_high": 0.9285
  },
  {
   "issue_type": "면책",
   "period": "전체",
   "n": 17,
   "n_cited": 12,
   "cited_rate": 0.7059,
   "ci_low": 0.4687,
   "ci_high": 0.8672
  },
  {
   "issue_type": "고지·설명",
   "period": "~2009",
   "n": 10,
   "n_cited": 4,
   "cited_rate": 0.4,
   "ci_low": 0.1682,
   "ci_high": 0.6873
  },
  {
   "issue_type": "고지·설명",
   "period": "2010-2016",
   "n": 8,
   "n_cited": 6,
   "cited_rate": 0.75,
   "ci_low": 0.4093,
   "ci_high": 0.9285
  },
  {
   "issue_type": "고지·설명",
   "period": "2017-2026",
   "n": 6,
   "n_cited": 5,
   "cited_rate": 0.8333,
   "ci_low": 0.4365,
   "ci_high": 0.9699
  },
  {
   "issue_type": "고지·설명",
   "period": "전체",
   "n": 24,
   "n_cited": 15,
   "cited_rate": 0.625,
   "ci_low": 0.4271,
   "ci_high": 0.7884
  },
  {
   "issue_type": "전체",
   "period": "~2009",
   "n": 75,
   "n_cited": 43,
   "cited_rate": 0.5733,
   "ci_low": 0.4605,
   "ci_high": 0.679
  },
  {
   "issue_type": "전체",
   "period": "2010-2016",
   "n": 42,
   "n_cited": 28,
   "cited_rate": 0.6667,
   "ci_low": 0.5155,
   "ci_high": 0.7899
  },
  {
   "issue_type": "전체",
   "period": "2017-2026",
   "n": 40,
   "n_cited": 35,
   "cited_rate": 0.875,
   "ci_low": 0.7389,
   "ci_high": 0.9454
  },
  {
   "issue_type": "전체",
   "period": "전체",
   "n": 157,
   "n_cited": 106,
   "cited_rate": 0.6752,
   "ci_low": 0.5985,
   "ci_high": 0.7435
  }
 ],
 "03_집단비교": [
  {
   "split": "median",
   "group": "하위(중앙값 이하)",
   "n": 79,
   "n_cited": 56,
   "cited_rate": 0.7089,
   "ci_low": 0.6009,
   "ci_high": 0.7975,
   "p": 0.3974
  },
  {
   "split": "median",
   "group": "상위(중앙값 초과)",
   "n": 78,
   "n_cited": 50,
   "cited_rate": 0.641,
   "ci_low": 0.5303,
   "ci_high": 0.7385,
   "p": 0.3974
  },
  {
   "split": "tertile",
   "group": "하위 1/3",
   "n": 52,
   "n_cited": 40,
   "cited_rate": 0.7692,
   "ci_low": 0.6387,
   "ci_high": 0.8628,
   "p": 0.08024
  },
  {
   "split": "tertile",
   "group": "중위 1/3",
   "n": 52,
   "n_cited": 36,
   "cited_rate": 0.6923,
   "ci_low": 0.5573,
   "ci_high": 0.8009,
   "p": 0.08024
  },
  {
   "split": "tertile",
   "group": "상위 1/3",
   "n": 53,
   "n_cited": 30,
   "cited_rate": 0.566,
   "ci_low": 0.4327,
   "ci_high": 0.6905,
   "p": 0.08024
  }
 ],
 "04_층화": [
  {
   "issue_type": "보상범위·정의",
   "odds_ratio": 0.691,
   "ci_low": 0.3111,
   "ci_high": 1.5346,
   "n": 116,
   "breslow_day_p": null
  },
  {
   "issue_type": "면책",
   "odds_ratio": 0.3333,
   "ci_low": 0.0387,
   "ci_high": 2.8745,
   "n": 17,
   "breslow_day_p": null
  },
  {
   "issue_type": "고지·설명",
   "odds_ratio": 1.2727,
   "ci_low": 0.1822,
   "ci_high": 8.892,
   "n": 24,
   "breslow_day_p": null
  },
  {
   "issue_type": "MH 합산",
   "odds_ratio": 0.6939,
   "ci_low": 0.3473,
   "ci_high": 1.3864,
   "n": 157,
   "breslow_day_p": 0.6598
  }
 ],
 "05_주모형": [
  {
   "term": "const",
   "coef": 0.3185,
   "odds_ratio": 1.375,
   "ci_low": 0.8376,
   "ci_high": 2.2572,
   "p": 0.2079,
   "n": 157,
   "n_minority": 51,
   "firth": 0,
   "exploratory": 0
  },
  {
   "term": "difficulty_index",
   "coef": -0.2619,
   "odds_ratio": 0.7696,
   "ci_low": 0.524,
   "ci_high": 1.1303,
   "p": 0.1817,
   "n": 157,
   "n_minority": 51,
   "firth": 0,
   "exploratory": 0
  },
  {
   "term": "issue_type[면책]",
   "coef": -0.3106,
   "odds_ratio": 0.733,
   "ci_low": 0.2208,
   "ci_high": 2.4338,
   "p": 0.612,
   "n": 157,
   "n_minority": 51,
   "firth": 0,
   "exploratory": 0
  },
  {
   "term": "issue_type[고지·설명]",
   "coef": -0.4021,
   "odds_ratio": 0.6689,
   "ci_low": 0.2545,
   "ci_high": 1.7584,
   "p": 0.4148,
   "n": 157,
   "n_minority": 51,
   "firth": 0,
   "exploratory": 0
  },
  {
   "term": "period[2010-2016]",
   "coef": 0.4089,
   "odds_ratio": 1.5051,
   "ci_low": 0.6795,
   "ci_high": 3.334,
   "p": 0.3136,
   "n": 157,
   "n_minority": 51,
   "firth": 0,
   "exploratory": 0
  },
  {
   "term": "period[2017-2026]",
   "coef": 1.9171,
   "odds_ratio": 6.8015,
   "ci_low": 2.1534,
   "ci_high": 21.4824,
   "p": 0.001086,
   "n": 157,
   "n_minority": 51,
   "firth": 0,
   "exploratory": 0
  },
  {
   "term": "const",
   "coef": 0.3138,
   "odds_ratio": 1.3687,
   "ci_low": 0.8422,
   "ci_high": 2.2479,
   "p": 0.2058,
   "n": 157,
   "n_minority": 51,
   "firth": 1,
   "exploratory": 0
  },
  {
   "term": "difficulty_index",
   "coef": -0.2563,
   "odds_ratio": 0.7739,
   "ci_low": 0.535,
   "ci_high": 1.1316,
   "p": 0.1794,
   "n": 157,
   "n_minority": 51,
   "firth": 1,
   "exploratory": 0
  },
  {
   "term": "issue_type[면책]",
   "coef": -0.3267,
   "odds_ratio": 0.7213,
   "ci_low": 0.2328,
   "ci_high": 2.4091,
   "p": 0.58,
   "n": 157,
   "n_minority": 51,
   "firth": 1,
   "exploratory": 0
  },
  {
   "term": "issue_type[고지·설명]",
   "coef": -0.3987,
   "odds_ratio": 0.6712,
   "ci_low": 0.2629,
   "ci_high": 1.7554,
   "p": 0.4086,
   "n": 157,
   "n_minority": 51,
   "firth": 1,
   "exploratory": 0
  },
  {
   "term": "period[2010-2016]",
   "coef": 0.3879,
   "odds_ratio": 1.4739,
   "ci_low": 0.6829,
   "ci_high": 3.2663,
   "p": 0.3251,
   "n": 157,
   "n_minority": 51,
   "firth": 1,
   "exploratory": 0
  },
  {
   "term": "period[2017-2026]",
   "coef": 1.7845,
   "odds_ratio": 5.9563,
   "ci_low": 2.1504,
   "ci_high": 19.9134,
   "p": 0.0003283,
   "n": 157,
   "n_minority": 51,
   "firth": 1,
   "exploratory": 0
  }
 ],
 "06_예측확률": [
  {
   "point": "low25",
   "difficulty_value": -0.3617,
   "pred": 0.7035,
   "ci_low": 0.6279,
   "ci_high": 0.7847,
   "n": 157,
   "n_boot": 1000,
   "seed": 42
  },
  {
   "point": "high25",
   "difficulty_value": 0.1866,
   "pred": 0.6498,
   "ci_low": 0.5582,
   "ci_high": 0.7279,
   "n": 157,
   "n_boot": 1000,
   "seed": 42
  },
  {
   "point": "diff",
   "difficulty_value": null,
   "pred": -0.0536,
   "ci_low": -0.1534,
   "ci_high": 0.0193,
   "n": 157,
   "n_boot": 1000,
   "seed": 42
  }
 ],
 "pred_curve": [
  {
   "difficulty": -0.7375,
   "pred": 0.7377,
   "ci_low": 0.628,
   "ci_high": 0.8508,
   "n": 157,
   "n_near": 2
  },
  {
   "difficulty": -0.6514,
   "pred": 0.7301,
   "ci_low": 0.6287,
   "ci_high": 0.8362,
   "n": 157,
   "n_near": 6
  },
  {
   "difficulty": -0.5652,
   "pred": 0.7223,
   "ci_low": 0.6286,
   "ci_high": 0.8233,
   "n": 157,
   "n_near": 7
  },
  {
   "difficulty": -0.4791,
   "pred": 0.7144,
   "ci_low": 0.6272,
   "ci_high": 0.8089,
   "n": 157,
   "n_near": 10
  },
  {
   "difficulty": -0.3929,
   "pred": 0.7064,
   "ci_low": 0.6281,
   "ci_high": 0.7898,
   "n": 157,
   "n_near": 10
  },
  {
   "difficulty": -0.3068,
   "pred": 0.6983,
   "ci_low": 0.6233,
   "ci_high": 0.7766,
   "n": 157,
   "n_near": 9
  },
  {
   "difficulty": -0.2207,
   "pred": 0.6901,
   "ci_low": 0.6187,
   "ci_high": 0.763,
   "n": 157,
   "n_near": 12
  },
  {
   "difficulty": -0.1345,
   "pred": 0.6817,
   "ci_low": 0.6108,
   "ci_high": 0.7511,
   "n": 157,
   "n_near": 18
  },
  {
   "difficulty": -0.0484,
   "pred": 0.6733,
   "ci_low": 0.6024,
   "ci_high": 0.7433,
   "n": 157,
   "n_near": 13
  },
  {
   "difficulty": 0.0378,
   "pred": 0.6648,
   "ci_low": 0.5874,
   "ci_high": 0.7366,
   "n": 157,
   "n_near": 13
  },
  {
   "difficulty": 0.1239,
   "pred": 0.6562,
   "ci_low": 0.5726,
   "ci_high": 0.7306,
   "n": 157,
   "n_near": 8
  },
  {
   "difficulty": 0.21,
   "pred": 0.6475,
   "ci_low": 0.5523,
   "ci_high": 0.7276,
   "n": 157,
   "n_near": 8
  },
  {
   "difficulty": 0.2962,
   "pred": 0.6387,
   "ci_low": 0.536,
   "ci_high": 0.7242,
   "n": 157,
   "n_near": 8
  },
  {
   "difficulty": 0.3823,
   "pred": 0.6299,
   "ci_low": 0.5179,
   "ci_high": 0.7254,
   "n": 157,
   "n_near": 7
  },
  {
   "difficulty": 0.4684,
   "pred": 0.6209,
   "ci_low": 0.4985,
   "ci_high": 0.7249,
   "n": 157,
   "n_near": 5
  },
  {
   "difficulty": 0.5546,
   "pred": 0.612,
   "ci_low": 0.4758,
   "ci_high": 0.7213,
   "n": 157,
   "n_near": 0
  },
  {
   "difficulty": 0.6407,
   "pred": 0.6029,
   "ci_low": 0.4453,
   "ci_high": 0.7232,
   "n": 157,
   "n_near": 2
  },
  {
   "difficulty": 0.7269,
   "pred": 0.5939,
   "ci_low": 0.4229,
   "ci_high": 0.7244,
   "n": 157,
   "n_near": 2
  },
  {
   "difficulty": 0.813,
   "pred": 0.5847,
   "ci_low": 0.4026,
   "ci_high": 0.7265,
   "n": 157,
   "n_near": 0
  },
  {
   "difficulty": 0.8991,
   "pred": 0.5756,
   "ci_low": 0.377,
   "ci_high": 0.7289,
   "n": 157,
   "n_near": 2
  }
 ],
 "07_민감도_필수": [
  {
   "analysis": "main",
   "odds_ratio": 0.7696,
   "ci_low": 0.524,
   "ci_high": 1.1303,
   "n": 157,
   "n_minority": 51,
   "direction_same": 1,
   "firth": 0,
   "exploratory": 0
  },
  {
   "analysis": "① 일부인용0",
   "odds_ratio": 0.8148,
   "ci_low": 0.567,
   "ci_high": 1.1707,
   "n": 157,
   "n_minority": 57,
   "direction_same": 1,
   "firth": 0,
   "exploratory": 0
  },
  {
   "analysis": "② 판단↔주장",
   "odds_ratio": 0.685,
   "ci_low": 0.4431,
   "ci_high": 1.0588,
   "n": 157,
   "n_minority": 51,
   "direction_same": 1,
   "firth": 0,
   "exploratory": 0
  },
  {
   "analysis": "③ 조 전체",
   "odds_ratio": 0.7362,
   "ci_low": 0.4853,
   "ci_high": 1.1168,
   "n": 157,
   "n_minority": 51,
   "direction_same": 1,
   "firth": 0,
   "exploratory": 0
  },
  {
   "analysis": "④ 2010년 이후",
   "odds_ratio": 0.7859,
   "ci_low": 0.4964,
   "ci_high": 1.3113,
   "n": 82,
   "n_minority": 19,
   "direction_same": 1,
   "firth": 1,
   "exploratory": 1
  }
 ],
 "08_민감도_선택": [
  {
   "analysis": "풀어 쓴 서술 포함",
   "odds_ratio": 0.8011,
   "ci_low": 0.6083,
   "ci_high": 1.0549,
   "n": 247,
   "n_minority": 93,
   "direction_same": 1,
   "done": 1
  },
  {
   "analysis": "붙임 문구 사건만",
   "odds_ratio": 1.111,
   "ci_low": 0.6445,
   "ci_high": 2.5141,
   "n": 26,
   "n_minority": 5,
   "direction_same": 0,
   "done": 1
  },
  {
   "analysis": "처음 언급 대신 최댓값",
   "odds_ratio": "수행하지 않음",
   "ci_low": "수행하지 않음",
   "ci_high": "수행하지 않음",
   "n": "수행하지 않음",
   "n_minority": "수행하지 않음",
   "direction_same": "수행하지 않음",
   "done": 0
  },
  {
   "analysis": "처음 언급 대신 평균",
   "odds_ratio": "수행하지 않음",
   "ci_low": "수행하지 않음",
   "ci_high": "수행하지 않음",
   "n": "수행하지 않음",
   "n_minority": "수행하지 않음",
   "direction_same": "수행하지 않음",
   "done": 0
  },
  {
   "analysis": "지표 하나씩: words_per_sentence",
   "odds_ratio": 0.9117,
   "ci_low": 0.6416,
   "ci_high": 1.2954,
   "n": 157,
   "n_minority": 51,
   "direction_same": 1,
   "done": 1
  },
  {
   "analysis": "지표 하나씩: exception_count",
   "odds_ratio": 0.9548,
   "ci_low": 0.5983,
   "ci_high": 1.5236,
   "n": 157,
   "n_minority": 51,
   "direction_same": 1,
   "done": 1
  },
  {
   "analysis": "지표 하나씩: term_ratio",
   "odds_ratio": 0.7119,
   "ci_low": 0.506,
   "ci_high": 1.0017,
   "n": 157,
   "n_minority": 51,
   "direction_same": 1,
   "done": 1
  },
  {
   "analysis": "지표 하나씩: ref_count",
   "odds_ratio": 1.0447,
   "ci_low": 0.7121,
   "ci_high": 1.5328,
   "n": 157,
   "n_minority": 51,
   "direction_same": 0,
   "done": 1
  },
  {
   "analysis": "설명의무 위반 인정 사건 제외",
   "odds_ratio": 0.7794,
   "ci_low": 0.5312,
   "ci_high": 1.1437,
   "n": 150,
   "n_minority": 51,
   "direction_same": 1,
   "done": 1
  },
  {
   "analysis": "유형 안 표준화",
   "odds_ratio": 0.7512,
   "ci_low": 0.5084,
   "ci_high": 1.11,
   "n": 157,
   "n_minority": 51,
   "direction_same": 1,
   "done": 1
  },
  {
   "analysis": "쟁점 판단 문장 한정(계획서 7-3)",
   "odds_ratio": "수행하지 않음",
   "ci_low": "수행하지 않음",
   "ci_high": "수행하지 않음",
   "n": "수행하지 않음",
   "n_minority": "수행하지 않음",
   "direction_same": "수행하지 않음",
   "done": 0
  },
  {
   "analysis": "쟁점 문장에 가장 가까운 조항(PROJECT.md 4-8 ④)",
   "odds_ratio": "수행하지 않음",
   "ci_low": "수행하지 않음",
   "ci_high": "수행하지 않음",
   "n": "수행하지 않음",
   "n_minority": "수행하지 않음",
   "direction_same": "수행하지 않음",
   "done": 0
  },
  {
   "analysis": "쟁점 유형 R2(판단 안 면책 조항, 사후)",
   "odds_ratio": 0.8028,
   "ci_low": 0.5496,
   "ci_high": 1.1727,
   "n": 157,
   "n_minority": 51,
   "direction_same": 1,
   "done": 1
  }
 ],
 "09_시계열": [
  {
   "year_bin": "1998-2000",
   "n": 13,
   "n_cited": 8,
   "cited_rate": 0.6154,
   "ci_low": 0.3552,
   "ci_high": 0.8229,
   "mean_difficulty": -0.052,
   "share_보상범위·정의": 0.7692,
   "share_면책": 0.1538,
   "share_고지·설명": 0.0769
  },
  {
   "year_bin": "2001-2003",
   "n": 12,
   "n_cited": 10,
   "cited_rate": 0.8333,
   "ci_low": 0.552,
   "ci_high": 0.953,
   "mean_difficulty": -0.2764,
   "share_보상범위·정의": 0.5833,
   "share_면책": 0.25,
   "share_고지·설명": 0.1667
  },
  {
   "year_bin": "2004-2006",
   "n": 18,
   "n_cited": 7,
   "cited_rate": 0.3889,
   "ci_low": 0.2031,
   "ci_high": 0.6138,
   "mean_difficulty": -0.1404,
   "share_보상범위·정의": 0.8889,
   "share_면책": 0.0556,
   "share_고지·설명": 0.0556
  },
  {
   "year_bin": "2007-2009",
   "n": 32,
   "n_cited": 18,
   "cited_rate": 0.5625,
   "ci_low": 0.3933,
   "ci_high": 0.7183,
   "mean_difficulty": -0.08,
   "share_보상범위·정의": 0.8125,
   "share_면책": 0.0,
   "share_고지·설명": 0.1875
  },
  {
   "year_bin": "2010-2012",
   "n": 22,
   "n_cited": 12,
   "cited_rate": 0.5455,
   "ci_low": 0.3466,
   "ci_high": 0.7308,
   "mean_difficulty": -0.2078,
   "share_보상범위·정의": 0.6364,
   "share_면책": 0.1364,
   "share_고지·설명": 0.2273
  },
  {
   "year_bin": "2013-2015",
   "n": 11,
   "n_cited": 10,
   "cited_rate": 0.9091,
   "ci_low": 0.6226,
   "ci_high": 0.9838,
   "mean_difficulty": -0.0473,
   "share_보상범위·정의": 0.9091,
   "share_면책": 0.0,
   "share_고지·설명": 0.0909
  },
  {
   "year_bin": "2016-2018",
   "n": 26,
   "n_cited": 22,
   "cited_rate": 0.8462,
   "ci_low": 0.6647,
   "ci_high": 0.9385,
   "mean_difficulty": 0.0695,
   "share_보상범위·정의": 0.7692,
   "share_면책": 0.0769,
   "share_고지·설명": 0.1538
  },
  {
   "year_bin": "2019-2021",
   "n": 16,
   "n_cited": 13,
   "cited_rate": 0.8125,
   "ci_low": 0.5699,
   "ci_high": 0.9341,
   "mean_difficulty": 0.2541,
   "share_보상범위·정의": 0.5,
   "share_면책": 0.3125,
   "share_고지·설명": 0.1875
  },
  {
   "year_bin": "2022-2024",
   "n": 4,
   "n_cited": 3,
   "cited_rate": 0.75,
   "ci_low": 0.3006,
   "ci_high": 0.9544,
   "mean_difficulty": 0.2342,
   "share_보상범위·정의": 0.5,
   "share_면책": 0.25,
   "share_고지·설명": 0.25
  },
  {
   "year_bin": "2025-2026",
   "n": 3,
   "n_cited": 3,
   "cited_rate": 1.0,
   "ci_low": 0.4385,
   "ci_high": 1.0,
   "mean_difficulty": 0.1367,
   "share_보상범위·정의": 1.0,
   "share_면책": 0.0,
   "share_고지·설명": 0.0
  }
 ],
 "10_조항주제": [
  {
   "topic": "보험금 지급사유",
   "n": 73,
   "cited_rate": 0.726,
   "mean_difficulty": 0.0479,
   "n_cited": 53,
   "ci_low": 0.6144,
   "ci_high": 0.8151
  },
  {
   "topic": "기타",
   "n": 24,
   "cited_rate": 0.6667,
   "mean_difficulty": -0.1344,
   "n_cited": 16,
   "ci_low": 0.4671,
   "ci_high": 0.8203
  },
  {
   "topic": "계약 전 알릴 의무",
   "n": 17,
   "cited_rate": 0.5882,
   "mean_difficulty": -0.1132,
   "n_cited": 10,
   "ci_low": 0.3601,
   "ci_high": 0.7839
  },
  {
   "topic": "면책",
   "n": 14,
   "cited_rate": 0.7143,
   "mean_difficulty": 0.0021,
   "n_cited": 10,
   "ci_low": 0.4535,
   "ci_high": 0.8828
  },
  {
   "topic": "재해·상해 정의",
   "n": 9,
   "cited_rate": 0.4444,
   "mean_difficulty": 0.2408,
   "n_cited": 4,
   "ci_low": 0.1888,
   "ci_high": 0.7333
  },
  {
   "topic": "질병 정의",
   "n": 8,
   "cited_rate": 0.75,
   "mean_difficulty": -0.4168,
   "n_cited": 6,
   "ci_low": 0.4093,
   "ci_high": 0.9285
  },
  {
   "topic": "계약 해지·부활",
   "n": 6,
   "cited_rate": 0.6667,
   "mean_difficulty": -0.371,
   "n_cited": 4,
   "ci_low": 0.3,
   "ci_high": 0.9032
  },
  {
   "topic": "수술·입원 정의",
   "n": 3,
   "cited_rate": null,
   "mean_difficulty": -0.33,
   "n_cited": 1,
   "ci_low": null,
   "ci_high": null
  },
  {
   "topic": "장해",
   "n": 2,
   "cited_rate": null,
   "mean_difficulty": -0.3151,
   "n_cited": 1,
   "ci_low": null,
   "ci_high": null
  },
  {
   "topic": "보험기간·갱신",
   "n": 1,
   "cited_rate": null,
   "mean_difficulty": -0.3146,
   "n_cited": 1,
   "ci_low": null,
   "ci_high": null
  }
 ],
 "10_조항주제_기준선": [
  {
   "item": "cited_rate_overall",
   "value": 0.6752,
   "설명": "분석 포함 157건 전체 인용률(= 106/157)"
  },
  {
   "item": "n_median_topics",
   "value": 14.0,
   "설명": "인용률을 표시하는 주제(5건 이상) 7개의 건수 n 중앙값"
  }
 ],
 "통계요약_2장_난이도분포": [
  {
   "group": "전체",
   "n": 157,
   "mean": -0.0443,
   "sd": 0.5346,
   "min": -0.9197,
   "p5": -0.7375,
   "p25": -0.3617,
   "median": -0.109,
   "p75": 0.1866,
   "p95": 0.8991,
   "max": 3.165,
   "group_var": "전체",
   "group_value": "전체"
  },
  {
   "group": "issue_type=보상범위·정의",
   "n": 116,
   "mean": -0.0303,
   "sd": 0.5695,
   "min": -0.9197,
   "p5": -0.8221,
   "p25": -0.3947,
   "median": -0.059,
   "p75": 0.2088,
   "p95": 0.9002,
   "max": 3.165,
   "group_var": "issue_type",
   "group_value": "보상범위·정의"
  },
  {
   "group": "issue_type=면책",
   "n": 17,
   "mean": -0.0184,
   "sd": 0.6046,
   "min": -0.803,
   "p5": -0.5645,
   "p25": -0.443,
   "median": -0.2284,
   "p75": 0.249,
   "p95": 1.264,
   "max": 1.411,
   "group_var": "issue_type",
   "group_value": "면책"
  },
  {
   "group": "issue_type=고지·설명",
   "n": 24,
   "mean": -0.1301,
   "sd": 0.2311,
   "min": -0.462,
   "p5": -0.4309,
   "p25": -0.2369,
   "median": -0.1766,
   "p75": -0.1042,
   "p95": 0.3552,
   "max": 0.4306,
   "group_var": "issue_type",
   "group_value": "고지·설명"
  },
  {
   "group": "period=~2009",
   "n": 75,
   "mean": -0.1211,
   "sd": 0.4069,
   "min": -0.9114,
   "p5": -0.808,
   "p25": -0.3584,
   "median": -0.1223,
   "p75": 0.1019,
   "p95": 0.5358,
   "max": 0.9823,
   "group_var": "period",
   "group_value": "~2009"
  },
  {
   "group": "period=2010-2016",
   "n": 42,
   "mean": -0.1485,
   "sd": 0.3769,
   "min": -0.8294,
   "p5": -0.6793,
   "p25": -0.4375,
   "median": -0.1577,
   "p75": -0.0158,
   "p95": 0.649,
   "max": 0.895,
   "group_var": "period",
   "group_value": "2010-2016"
  },
  {
   "group": "period=2017-2026",
   "n": 40,
   "mean": 0.2091,
   "sd": 0.7685,
   "min": -0.9197,
   "p5": -0.7285,
   "p25": -0.2456,
   "median": 0.0755,
   "p75": 0.4183,
   "p95": 1.437,
   "max": 3.165,
   "group_var": "period",
   "group_value": "2017-2026"
  }
 ],
 "통계요약_2장_히스토그램": [
  {
   "bin_low": -0.92,
   "bin_high": -0.51,
   "n": 23
  },
  {
   "bin_low": -0.51,
   "bin_high": -0.1,
   "n": 57
  },
  {
   "bin_low": -0.1,
   "bin_high": 0.31,
   "n": 47
  },
  {
   "bin_low": 0.31,
   "bin_high": 0.71,
   "n": 21
  },
  {
   "bin_low": 0.71,
   "bin_high": 1.12,
   "n": 4
  },
  {
   "bin_low": 1.12,
   "bin_high": 1.53,
   "n": 3
  },
  {
   "bin_low": 1.53,
   "bin_high": 1.94,
   "n": 1
  },
  {
   "bin_low": 1.94,
   "bin_high": 2.35,
   "n": 0
  },
  {
   "bin_low": 2.35,
   "bin_high": 2.76,
   "n": 0
  },
  {
   "bin_low": 2.76,
   "bin_high": 3.17,
   "n": 1
  }
 ],
 "사례_담보집계_표1": [
  {
   "product_group": "질병·상해·간병보험",
   "coverage": "진단",
   "건수": 15,
   "비율(%)": 11.6
  },
  {
   "product_group": "질병·상해·간병보험",
   "coverage": "기타",
   "건수": 13,
   "비율(%)": 10.1
  },
  {
   "product_group": "질병·상해·간병보험",
   "coverage": "수술",
   "건수": 10,
   "비율(%)": 7.8
  },
  {
   "product_group": "질병·상해·간병보험",
   "coverage": "입원",
   "건수": 5,
   "비율(%)": 3.9
  },
  {
   "product_group": "손해보험",
   "coverage": "책임보험",
   "건수": 14,
   "비율(%)": 10.9
  },
  {
   "product_group": "손해보험",
   "coverage": "운전자",
   "건수": 8,
   "비율(%)": 6.2
  },
  {
   "product_group": "손해보험",
   "coverage": "재물보험",
   "건수": 6,
   "비율(%)": 4.7
  },
  {
   "product_group": "손해보험",
   "coverage": "자동차성능·상태점검",
   "건수": 3,
   "비율(%)": 2.3
  },
  {
   "product_group": "손해보험",
   "coverage": "비용",
   "건수": 1,
   "비율(%)": 0.8
  },
  {
   "product_group": "실손보험",
   "coverage": "치료비",
   "건수": 18,
   "비율(%)": 14.0
  },
  {
   "product_group": "실손보험",
   "coverage": "기타",
   "건수": 6,
   "비율(%)": 4.7
  },
  {
   "product_group": "실손보험",
   "coverage": "수술비",
   "건수": 3,
   "비율(%)": 2.3
  },
  {
   "product_group": "실손보험",
   "coverage": "약제비",
   "건수": 2,
   "비율(%)": 1.6
  },
  {
   "product_group": "보험",
   "coverage": "일반",
   "건수": 16,
   "비율(%)": 12.4
  },
  {
   "product_group": "생명보험",
   "coverage": "사망",
   "건수": 5,
   "비율(%)": 3.9
  },
  {
   "product_group": "생명보험",
   "coverage": "연금",
   "건수": 4,
   "비율(%)": 3.1
  }
 ],
 "15_평가타당성_카파": [
  {
   "measure": "참고: 두 평가자 가중 카파(quadratic)",
   "role": "참고",
   "spearman": 0.059,
   "ci_low": -0.209,
   "ci_high": 0.328,
   "n": 24,
   "note": "평가일치도.md 값. 일치도 낮음(0.4 미만) → 위 상관은 해석 제한"
  }
 ],
 "제외사유_비교표": [
  {
   "구분": "분석 포함",
   "건수 N": 157,
   "결과 판정된 건": 157,
   "인용·일부 인용 수": 106,
   "인용률": 0.675,
   "분석 포함과 차이(%p)": null,
   "10%p 이상": null,
   "~2009": 75,
   "2010-2016": 42,
   "2017-2026": 40
  },
  {
   "구분": "자동차보험",
   "건수 N": 99,
   "결과 판정된 건": 18,
   "인용·일부 인용 수": 10,
   "인용률": 0.556,
   "분석 포함과 차이(%p)": 12.0,
   "10%p 이상": "예",
   "~2009": 80,
   "2010-2016": 14,
   "2017-2026": 5
  },
  {
   "구분": "풀어 쓴 서술",
   "건수 N": 91,
   "결과 판정된 건": 90,
   "인용·일부 인용 수": 48,
   "인용률": 0.533,
   "분석 포함과 차이(%p)": 14.2,
   "10%p 이상": "예",
   "~2009": 54,
   "2010-2016": 36,
   "2017-2026": 1
  },
  {
   "구분": "조항 미추출",
   "건수 N": 64,
   "결과 판정된 건": 64,
   "인용·일부 인용 수": 40,
   "인용률": 0.625,
   "분석 포함과 차이(%p)": 5.0,
   "10%p 이상": "아니오",
   "~2009": 50,
   "2010-2016": 4,
   "2017-2026": 10
  },
  {
   "구분": "배포용 문서",
   "건수 N": 19,
   "결과 판정된 건": 0,
   "인용·일부 인용 수": 0,
   "인용률": "미확인",
   "분석 포함과 차이(%p)": null,
   "10%p 이상": null,
   "~2009": 0,
   "2010-2016": 19,
   "2017-2026": 0
  },
  {
   "구분": "조항 문구 없음",
   "건수 N": 11,
   "결과 판정된 건": 11,
   "인용·일부 인용 수": 10,
   "인용률": 0.909,
   "분석 포함과 차이(%p)": 23.4,
   "10%p 이상": "예",
   "~2009": 7,
   "2010-2016": 3,
   "2017-2026": 1
  },
  {
   "구분": "본안 아님(각하)",
   "건수 N": 3,
   "결과 판정된 건": 0,
   "인용·일부 인용 수": 0,
   "인용률": "미확인",
   "분석 포함과 차이(%p)": null,
   "10%p 이상": null,
   "~2009": 2,
   "2010-2016": 1,
   "2017-2026": 0
  },
  {
   "구분": "지원하지 않는 형식",
   "건수 N": 2,
   "결과 판정된 건": 0,
   "인용·일부 인용 수": 0,
   "인용률": "미확인",
   "분석 포함과 차이(%p)": null,
   "10%p 이상": null,
   "~2009": 2,
   "2010-2016": 0,
   "2017-2026": 0
  },
  {
   "구분": "결정례 아님",
   "건수 N": 2,
   "결과 판정된 건": 0,
   "인용·일부 인용 수": 0,
   "인용률": "미확인",
   "분석 포함과 차이(%p)": null,
   "10%p 이상": null,
   "~2009": 0,
   "2010-2016": 1,
   "2017-2026": 1
  },
  {
   "구분": "중복",
   "건수 N": 1,
   "결과 판정된 건": 1,
   "인용·일부 인용 수": 0,
   "인용률": 0.0,
   "분석 포함과 차이(%p)": 67.5,
   "10%p 이상": "예",
   "~2009": 1,
   "2010-2016": 0,
   "2017-2026": 0
  },
  {
   "구분": "(묶음) 조항 관련 제외: 조항 미추출 + 조항 문구 없음 + 풀어 쓴 서술",
   "건수 N": 166,
   "결과 판정된 건": 165,
   "인용·일부 인용 수": 98,
   "인용률": 0.594,
   "분석 포함과 차이(%p)": 8.1,
   "10%p 이상": "아니오",
   "~2009": 111,
   "2010-2016": 43,
   "2017-2026": 12
  },
  {
   "구분": "(합계) 전체",
   "건수 N": 449,
   "결과 판정된 건": 341,
   "인용·일부 인용 수": 214,
   "인용률": 0.628,
   "분석 포함과 차이(%p)": 4.8,
   "10%p 이상": "아니오",
   "~2009": 271,
   "2010-2016": 120,
   "2017-2026": 58
  }
 ],
 "12_조항프로필": [
  {
   "diff_id": "D016",
   "case_key": "2018-13",
   "in_analysis": 1,
   "topic": "기타",
   "clause_level": "조",
   "dim_vocab": 43.9542,
   "dim_sentence": 33.7691,
   "dim_logic": 14.7059,
   "dim_ref": 49.183,
   "top_dim": "없음",
   "top_dim_rel": "참조 구조"
  },
  {
   "diff_id": "D055",
   "case_key": "2010-23",
   "in_analysis": 1,
   "topic": "보험금 지급사유",
   "clause_level": "호",
   "dim_vocab": 57.0261,
   "dim_sentence": 50.1089,
   "dim_logic": 14.7059,
   "dim_ref": 38.5621,
   "top_dim": "없음",
   "top_dim_rel": "어휘"
  },
  {
   "diff_id": "D118",
   "case_key": "2005-73",
   "in_analysis": 1,
   "topic": "보험금 지급사유",
   "clause_level": "호",
   "dim_vocab": 67.1569,
   "dim_sentence": 12.3094,
   "dim_logic": 25.0545,
   "dim_ref": 15.3595,
   "top_dim": "없음",
   "top_dim_rel": "어휘"
  },
  {
   "diff_id": "D121",
   "case_key": "2010-103",
   "in_analysis": 1,
   "topic": "면책",
   "clause_level": "항",
   "dim_vocab": 29.5752,
   "dim_sentence": 61.0022,
   "dim_logic": 56.6449,
   "dim_ref": 15.3595,
   "top_dim": "없음",
   "top_dim_rel": "문장 구조"
  },
  {
   "diff_id": "D184",
   "case_key": "2009-32",
   "in_analysis": 1,
   "topic": "질병 정의",
   "clause_level": "조",
   "dim_vocab": 7.3529,
   "dim_sentence": 81.9172,
   "dim_logic": 35.6209,
   "dim_ref": 67.1569,
   "top_dim": "없음",
   "top_dim_rel": "문장 구조"
  },
  {
   "diff_id": "D189",
   "case_key": "2007-79",
   "in_analysis": 1,
   "topic": "보험금 지급사유",
   "clause_level": "조",
   "dim_vocab": 75.0,
   "dim_sentence": 12.0915,
   "dim_logic": 14.7059,
   "dim_ref": 15.3595,
   "top_dim": "없음",
   "top_dim_rel": "어휘"
  },
  {
   "diff_id": "D211",
   "case_key": "2016-8",
   "in_analysis": 1,
   "topic": "기타",
   "clause_level": "조",
   "dim_vocab": 73.8562,
   "dim_sentence": 45.6427,
   "dim_logic": 14.7059,
   "dim_ref": 38.5621,
   "top_dim": "없음",
   "top_dim_rel": "어휘"
  },
  {
   "diff_id": "D221",
   "case_key": "2021-23",
   "in_analysis": 1,
   "topic": "보험금 지급사유",
   "clause_level": "항",
   "dim_vocab": 40.8497,
   "dim_sentence": 62.3094,
   "dim_logic": 44.2266,
   "dim_ref": 49.183,
   "top_dim": "없음",
   "top_dim_rel": "문장 구조"
  },
  {
   "diff_id": "D238",
   "case_key": "2005-34",
   "in_analysis": 1,
   "topic": "보험금 지급사유",
   "clause_level": "조",
   "dim_vocab": 36.2745,
   "dim_sentence": 36.8192,
   "dim_logic": 14.7059,
   "dim_ref": 15.3595,
   "top_dim": "없음",
   "top_dim_rel": "문장 구조"
  },
  {
   "diff_id": "D257",
   "case_key": "2021-19",
   "in_analysis": 1,
   "topic": "면책",
   "clause_level": "조",
   "dim_vocab": 59.9673,
   "dim_sentence": 21.6776,
   "dim_logic": 70.4793,
   "dim_ref": 38.5621,
   "top_dim": "없음",
   "top_dim_rel": "논리 구조"
  },
  {
   "diff_id": "D271",
   "case_key": "2021-18",
   "in_analysis": 1,
   "topic": "면책",
   "clause_level": "조",
   "dim_vocab": 57.1895,
   "dim_sentence": 77.5599,
   "dim_logic": 94.2266,
   "dim_ref": 38.5621,
   "top_dim": "논리 구조",
   "top_dim_rel": "논리 구조"
  },
  {
   "diff_id": "D272",
   "case_key": "1998-36",
   "in_analysis": 1,
   "topic": "재해·상해 정의",
   "clause_level": "조",
   "dim_vocab": 15.8497,
   "dim_sentence": 99.7821,
   "dim_logic": 14.7059,
   "dim_ref": 76.634,
   "top_dim": "문장 구조",
   "top_dim_rel": "문장 구조"
  }
 ],
 "17_토픽목록": [
  {
   "corpus": "title",
   "topic": -1,
   "label": "바깥값",
   "n": 31,
   "keywords": null
  },
  {
   "corpus": "title",
   "topic": 0,
   "label": "계약 해지·의무 위반·청구",
   "n": 92,
   "keywords": "계약, 해지, 의무, 위반, 보증, 청구, 보험료, 손해, 소멸, 설명"
  },
  {
   "corpus": "title",
   "topic": 1,
   "label": "재해사망·장해 급여금 지급분쟁",
   "n": 33,
   "keywords": "분쟁, 재해, 사망, 급여금, 장해, 일반, 자금, 응급, 소득, 성인병"
  },
  {
   "corpus": "title",
   "topic": 2,
   "label": "실손 의료비·입원 비용",
   "n": 33,
   "keywords": "의료비, 유무, 실손, 입원, 비용, 수술, 의료, 급여, 자금, 뇌졸중"
  },
  {
   "corpus": "title",
   "topic": 3,
   "label": "재해·상해로 인한 사망",
   "n": 30,
   "keywords": "사망, 재해, 상해, 발생, 피보험자, 원인, 추정, 뇌출혈, 놀이, 활동"
  },
  {
   "corpus": "title",
   "topic": 4,
   "label": "암 진단 확정·검사",
   "n": 30,
   "keywords": "진단, 검사, 확정, 약관, 흡인, 개시일, 세침, 치료, 입원, 목적"
  },
  {
   "corpus": "title",
   "topic": 5,
   "label": "수술 해당·수술급여금",
   "n": 30,
   "keywords": "수술, 치료, 관절, 급여금, 제거, 체외, 정맥, 충격파, 신경, 대상"
  },
  {
   "corpus": "title",
   "topic": 6,
   "label": "교통재해·차량 운전",
   "n": 28,
   "keywords": "교통, 차량, 재해, 발생, 작업, 운전, 정비, 사망, 탑승, 분쟁"
  },
  {
   "corpus": "title",
   "topic": 7,
   "label": "계약전 알릴의무 위반·자필서명",
   "n": 16,
   "keywords": "계약, 의무, 위반, 가능, 서명, 해지, 고지, 사실, 본인, 자필"
  },
  {
   "corpus": "title",
   "topic": 8,
   "label": "알리지 않은 사실·알릴의무 위반",
   "n": 12,
   "keywords": "계약, 사실, 의무, 위반, 체결, 투약, 갑상선, 건강, 가능, 가입"
  },
  {
   "corpus": "title",
   "topic": 9,
   "label": "정신질환 상태 자살·재해사망",
   "n": 11,
   "keywords": "자살, 정신, 사망, 질환, 재해, 상태, 피보험자, 수익자, 약관, 사실"
  },
  {
   "corpus": "clause",
   "topic": -1,
   "label": "바깥값",
   "n": 24,
   "keywords": null
  },
  {
   "corpus": "clause",
   "topic": 0,
   "label": "보상하는 손해·배상책임",
   "n": 41,
   "keywords": "손해, 신체, 상해, 이하, 약관, 우연, 보상, 피보험자, 배상, 기재"
  },
  {
   "corpus": "clause",
   "topic": 1,
   "label": "계약전 알릴의무·청약 질문",
   "n": 21,
   "keywords": "청약, 계약, 건강, 의무, 사실, 계약자, 진단, 질문, 변경, 내용"
  },
  {
   "corpus": "clause",
   "topic": 2,
   "label": "보험금을 지급하지 않는 사유",
   "n": 15,
   "keywords": "사망, 사유, 특정, 발생, 부위, 계약, 손해, 자신, 고의, 이외"
  },
  {
   "corpus": "clause",
   "topic": 3,
   "label": "재해장해급여금·농업 작업",
   "n": 14,
   "keywords": "장해, 재해, 연금, 안전, 농업, 작업, 기간, 보험자, 계약, 사망"
  },
  {
   "corpus": "clause",
   "topic": 4,
   "label": "책임개시일 이후 진단확정·상피내암",
   "n": 11,
   "keywords": "확정, 진단, 개시일, 이후, 상피내암, 상피, 장애, 피보험자, 수술, 목적"
  },
  {
   "corpus": "clause",
   "topic": 5,
   "label": "재해사망·장해 분류",
   "n": 9,
   "keywords": "재해, 사망, 장해, 분류, 기간, 산업, 직접, 교통, 상태, 원인"
  },
  {
   "corpus": "clause",
   "topic": 6,
   "label": "입원의료비 보상 한도",
   "n": 9,
   "keywords": "입원, 급여, 한도, 병실, 금액, 질병, 치료, 의료비, 보상, 병원"
  },
  {
   "corpus": "clause",
   "topic": 7,
   "label": "의사·의료기관 진단 소견",
   "n": 7,
   "keywords": "소견, 의사, 의료, 검사, 기초, 진단, 수술, 국외, 동등, 국내"
  },
  {
   "corpus": "clause",
   "topic": 8,
   "label": "우발적 외래 사고·관절",
   "n": 6,
   "keywords": "요인, 외부, 관절, 우발, 완전, 행위, 외래, 증상, 악화, 발병"
  }
 ],
 "19_토픽비교_지표": [
  {
   "table": "metric",
   "row": "ARI",
   "col": "title(157) vs rule_topic",
   "n": 0.0454
  },
  {
   "table": "metric",
   "row": "NMI",
   "col": "title(157) vs rule_topic",
   "n": 0.3144
  },
  {
   "table": "metric",
   "row": "ARI",
   "col": "title_reduced(157) vs rule_topic",
   "n": 0.0524
  },
  {
   "table": "metric",
   "row": "NMI",
   "col": "title_reduced(157) vs rule_topic",
   "n": 0.3154
  },
  {
   "table": "metric",
   "row": "ARI",
   "col": "clause(157) vs rule_topic",
   "n": 0.2632
  },
  {
   "table": "metric",
   "row": "NMI",
   "col": "clause(157) vs rule_topic",
   "n": 0.4417
  }
 ],
 "22_토픽인용률": [
  {
   "topic": -1,
   "label": "바깥값",
   "n": 18,
   "n_cited": 13,
   "cited_rate": 0.7222,
   "ci_low": 0.4913,
   "ci_high": 0.875
  },
  {
   "topic": 0,
   "label": "계약 해지·의무 위반·청구",
   "n": 48,
   "n_cited": 34,
   "cited_rate": 0.7083,
   "ci_low": 0.5682,
   "ci_high": 0.8176
  },
  {
   "topic": 2,
   "label": "실손 의료비·입원 비용",
   "n": 18,
   "n_cited": 12,
   "cited_rate": 0.6667,
   "ci_low": 0.4375,
   "ci_high": 0.8372
  },
  {
   "topic": 3,
   "label": "재해·상해로 인한 사망",
   "n": 17,
   "n_cited": 10,
   "cited_rate": 0.5882,
   "ci_low": 0.3601,
   "ci_high": 0.7839
  },
  {
   "topic": 4,
   "label": "암 진단 확정·검사",
   "n": 13,
   "n_cited": 10,
   "cited_rate": 0.7692,
   "ci_low": 0.4974,
   "ci_high": 0.9182
  },
  {
   "topic": 5,
   "label": "수술 해당·수술급여금",
   "n": 8,
   "n_cited": 4,
   "cited_rate": 0.5,
   "ci_low": 0.2152,
   "ci_high": 0.7848
  },
  {
   "topic": 6,
   "label": "교통재해·차량 운전",
   "n": 13,
   "n_cited": 9,
   "cited_rate": 0.6923,
   "ci_low": 0.4237,
   "ci_high": 0.8732
  },
  {
   "topic": 7,
   "label": "계약전 알릴의무 위반·자필서명",
   "n": 7,
   "n_cited": 5,
   "cited_rate": 0.7143,
   "ci_low": 0.3589,
   "ci_high": 0.9178
  },
  {
   "topic": 8,
   "label": "알리지 않은 사실·알릴의무 위반",
   "n": 7,
   "n_cited": 4,
   "cited_rate": 0.5714,
   "ci_low": 0.2505,
   "ci_high": 0.8418
  },
  {
   "topic": 9,
   "label": "정신질환 상태 자살·재해사망",
   "n": 6,
   "n_cited": 4,
   "cited_rate": 0.6667,
   "ci_low": 0.3,
   "ci_high": 0.9032
  }
 ],
 "결과_A셋_일치": [
  {
   "label": "cited",
   "method": "규칙",
   "agree": 30,
   "n": 30,
   "kappa": 1.0
  },
  {
   "label": "cited",
   "method": "LLM 전체",
   "agree": 30,
   "n": 30,
   "kappa": 1.0
  },
  {
   "label": "partial",
   "method": "규칙",
   "agree": 30,
   "n": 30,
   "kappa": 1.0
  },
  {
   "label": "partial",
   "method": "LLM 전체",
   "agree": 28,
   "n": 30,
   "kappa": 0.47
  },
  {
   "label": "issue_type",
   "method": "규칙",
   "agree": 26,
   "n": 30,
   "kappa": 0.77
  },
  {
   "label": "issue_type",
   "method": "LLM 전체",
   "agree": 26,
   "n": 30,
   "kappa": 0.77
  },
  {
   "label": "issue_type",
   "method": "LLM 조각",
   "agree": 27,
   "n": 30,
   "kappa": 0.83
  },
  {
   "label": "explained_duty",
   "method": "규칙",
   "agree": 29,
   "n": 30,
   "kappa": 0.79
  },
  {
   "label": "explained_duty",
   "method": "LLM 전체",
   "agree": 30,
   "n": 30,
   "kappa": 1.0
  },
  {
   "label": "ambiguity",
   "method": "규칙",
   "agree": 25,
   "n": 30,
   "kappa": 0.53
  },
  {
   "label": "ambiguity",
   "method": "LLM 전체",
   "agree": 27,
   "n": 30,
   "kappa": 0.74
  },
  {
   "label": "ambiguity",
   "method": "LLM 조각",
   "agree": 24,
   "n": 30,
   "kappa": 0.48
  }
 ],
 "결과_B셋_일치": [
  {
   "label": "cited",
   "method": "규칙",
   "agree": 22,
   "n": 22,
   "kappa": 1.0
  },
  {
   "label": "cited",
   "method": "LLM 전체",
   "agree": 22,
   "n": 22,
   "kappa": 1.0
  },
  {
   "label": "partial",
   "method": "규칙",
   "agree": 20,
   "n": 22,
   "kappa": 0.46
  },
  {
   "label": "partial",
   "method": "LLM 전체",
   "agree": 21,
   "n": 22,
   "kappa": 0.78
  },
  {
   "label": "issue_type",
   "method": "규칙",
   "agree": 10,
   "n": 22,
   "kappa": 0.23
  },
  {
   "label": "issue_type",
   "method": "LLM 전체",
   "agree": 11,
   "n": 22,
   "kappa": 0.28
  },
  {
   "label": "issue_type",
   "method": "LLM 조각",
   "agree": 11,
   "n": 22,
   "kappa": 0.28
  },
  {
   "label": "explained_duty",
   "method": "규칙",
   "agree": 21,
   "n": 22,
   "kappa": 0.65
  },
  {
   "label": "explained_duty",
   "method": "LLM 전체",
   "agree": 22,
   "n": 22,
   "kappa": 1.0
  },
  {
   "label": "ambiguity",
   "method": "규칙",
   "agree": 17,
   "n": 22,
   "kappa": 0.61
  },
  {
   "label": "ambiguity",
   "method": "LLM 전체",
   "agree": 16,
   "n": 22,
   "kappa": 0.55
  },
  {
   "label": "ambiguity",
   "method": "LLM 조각",
   "agree": 16,
   "n": 22,
   "kappa": 0.54
  }
 ],
 "결과_B셋_빈틈유형별": [
  {
   "gap": "G1",
   "label": "ambiguity",
   "n": 7,
   "규칙": 6,
   "LLM전체": 6,
   "LLM조각": 5.0
  },
  {
   "gap": "G4",
   "label": "ambiguity",
   "n": 3,
   "규칙": 3,
   "LLM전체": 2,
   "LLM조각": 3.0
  },
  {
   "gap": "G2",
   "label": "issue_type",
   "n": 8,
   "규칙": 1,
   "LLM전체": 1,
   "LLM조각": 1.0
  },
  {
   "gap": "G5",
   "label": "issue_type",
   "n": 2,
   "규칙": 1,
   "LLM전체": 1,
   "LLM조각": 1.0
  },
  {
   "gap": "G3",
   "label": "explained_duty",
   "n": 2,
   "규칙": 1,
   "LLM전체": 2,
   "LLM조각": null
  }
 ],
 "결과_조항확인_비교": [
  {
   "no": 14,
   "key": "2016-5",
   "h_cc": "맞음",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "그대로",
   "근거": "첫 조항 보통약관 제13조 ①과 일치",
   "구분": "무작위 확인"
  },
  {
   "no": 18,
   "key": "2021-14",
   "h_cc": "다른 조항",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "다른 조항",
   "clause_text_ok": "그대로",
   "근거": "판단에서 별표2(농업작업의 범위)가 먼저, 제9조는 뒤",
   "구분": "LLM 지적"
  },
  {
   "no": 5,
   "key": "1999-44",
   "h_cc": "법령",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "다른 문구 섞임",
   "근거": "첫 약관조항은 제4조이나 뽑힌 문구는 상법 제659조 문장",
   "구분": "LLM 지적"
  },
  {
   "no": 10,
   "key": "2012-14",
   "h_cc": "맞음",
   "h_tx": "잘림",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "잘림",
   "근거": "제14조 ①은 맞으나 별표4 이름 일부만 뽑힘",
   "구분": "LLM 지적"
  },
  {
   "no": 7,
   "key": "2002-7",
   "h_cc": "맞음",
   "h_tx": "잘림",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "잘림",
   "근거": "특약 제2조 제11항 본문만 있고 '다만' 단서 누락",
   "구분": "LLM 지적"
  },
  {
   "no": 24,
   "key": "2006-65",
   "h_cc": "맞음",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "그대로",
   "근거": "첫 조항 제4조 제6항 인용문과 일치",
   "구분": "무작위 확인"
  },
  {
   "no": 22,
   "key": "2008-15",
   "h_cc": "맞음",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "그대로",
   "근거": "첫 조항 제16조 ① 3호 인용문과 일치",
   "구분": "무작위 확인"
  },
  {
   "no": 15,
   "key": "2026-4",
   "h_cc": "맞음",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "다른 문구 섞임",
   "근거": "조항은 맞으나 원문 '별표5'가 '별표6'으로, 끝에 ')' 추가",
   "구분": "LLM 지적"
  },
  {
   "no": 1,
   "key": "2009-17",
   "h_cc": "맞음",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "그대로",
   "근거": "판단의 첫 약관조항 제3조, 본문 ① 문구와 일치",
   "구분": "무작위 확인"
  },
  {
   "no": 2,
   "key": "2009-76",
   "h_cc": "맞음",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "맞음",
   "clause_text_ok": "그대로",
   "근거": "판단 첫 조항 보통약관 제14조, 제목줄 포함 본문과 일치",
   "구분": "무작위 확인"
  },
  {
   "no": 16,
   "key": "2019-5",
   "h_cc": "다른 조항",
   "h_tx": "그대로",
   "memo": null,
   "clause_correct": "다른 조항",
   "clause_text_ok": "다른 문구 섞임",
   "근거": "뽑힌 제2조는 일본 보험사 약관 인용, 이 사건은 붙임 제11조",
   "구분": "LLM 지적"
  }
 ],
 "text_facts": {
  "auto_confirmed": {
   "text": "규칙 = LLM조각 1회 = 2회로 자동 확정된 79개 라벨 중 20개(25%)가 사람과 달랐다(issue_type 14개, ambiguity 6개).",
   "source": "relabel/결과.md 3절"
  },
  "clause_check": {
   "text": "LLM이 28행을 판정해 6행을 문제로 지적했고, 팀원C이 지적된 6행과 무작위 5행(11행)을 확인했다. 지적된 6행 중 5행은 사람도 문제(법령 1, 잘림 2, 다른 조항 2)로 봤다. 분석 포함 사건 28건 중 약 5건(18%)은 난이도를 계산한 문구가 실제 쟁점 약관 문구와 다르다.",
   "source": "relabel/결과.md 6절"
  },
  "r2_gold": {
   "A_R1": "26/30 (κ 0.77)",
   "A_R2": "29/30 (κ 0.95)",
   "B_R1": "10/22 (κ 0.23)",
   "B_R2": "22/22 (κ 1.00)",
   "changed": "157건 중 26건(17%)이 바뀌었고, 면책이 17 → 41건이 됐다.",
   "source": "docs/issue_type_민감도_규칙.md '골드 확인 결과', '157건 적용'"
  },
  "gold_criteria": {
   "cited": "29/30",
   "issue_type": "26/30",
   "explained_duty": "26/30",
   "ambiguity": "26/30",
   "source": "PROJECT.md 3장 기준값 14"
  },
  "gold_split": {
   "text": "팀원C 20건: cited 20, partial 20, issue_type 16, explained_duty 19, ambiguity 17 / 정유빈 10건: cited 10, partial 10, issue_type 10, explained_duty 10, ambiguity 8",
   "source": "PROJECT.md 4-8 '골드 표본 30건 최종 결과'"
  },
  "topic_stability": {
   "text": "시드 5개 모두 기준(평균 ARI 0.5)을 넘었고, 다른 컴퓨터에서 다시 돌려도 묶음은 거의 같았지만(ARI 0.94) 토픽 번호와 크기는 조금 달라졌다.",
   "source": "docs/제안/대시보드_데이터사전.md 20번(PROJECT.md 10장 2026-11-05 'BERTopic 결과 표현')"
  },
  "flow": {
   "posts": 445,
   "posts_note": "게시물 445건(사이트 분류 자동차보험 81건·사례집 2건은 받지 않음, 첨부 366개)",
   "source": "docs/수집근거표.md, PROJECT.md 1장"
  },
  "median_split": {
   "text": "상위 − 하위 인용률 차이 -0.068 [-0.210, 0.078](Newcombe), Fisher 정확검정 p = 0.397",
   "source": "outputs/stats/통계요약.md 3장"
  },
  "excluded_total": {
   "value": 292,
   "source": "outputs/stats/통계요약.md 4줄 요약(cases.csv에서 exclude_reason이 있는 행 292)"
  }
 }
};
