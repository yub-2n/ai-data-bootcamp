/*
 * todo_data.js — 자세히 보기 3(인용·기각별 난이도)·8(정성)·B(골드 교차표) 실제 값. 2026-11-05 대시보드 수정 때 만듦(예시 데이터 아님).
 * 만든 방법(코드: dashboard/_build/make_todo.py): outputs/stats/analysis.py 0단계와 같은 합치기
 *   (data/interim/cases.csv 분석 포함 행 + difficulty_id_map.csv + data/processed/difficulty.csv, 2009-29는 D204 사용) → 157건(인용 106, 기각 51) 확인.
 *   "02b_난이도분포_인용기각": 통계요약.md 2장 히스토그램과 같은 10구간(np.histogram, bins = 10)을 cited로 나눈 건수. 두 줄 합 = 2장 도수와 같음.
 *   "02b_난이도요약_인용기각": cited별 difficulty_index 분위수(pandas quantile). 기술통계, 검정 안 함.
 *   "08_정성비율": 157건의 ambiguity·explained_duty 값(0/1/2)별 건수, 비율, Wilson 95% CI. 값 뜻 = relabel/isolated/코드북.md Q6·Q7.
 *   "B_골드_교차표": relabel/결과_A셋_비교표.csv의 사람(h_*) × 규칙(m_*) 건수표(행 = 사람, 열 = 규칙). 대각선 합 = 결과_A셋_일치.csv 규칙 행 agree와 같음.
 */
window.DASHBOARD_TODO = {
 "02b_난이도분포_인용기각": [
  {
   "bin_low": -0.92,
   "bin_high": -0.51,
   "n_cited": 17,
   "n_dismissed": 6
  },
  {
   "bin_low": -0.51,
   "bin_high": -0.1,
   "n_cited": 40,
   "n_dismissed": 17
  },
  {
   "bin_low": -0.1,
   "bin_high": 0.31,
   "n_cited": 29,
   "n_dismissed": 18
  },
  {
   "bin_low": 0.31,
   "bin_high": 0.71,
   "n_cited": 13,
   "n_dismissed": 8
  },
  {
   "bin_low": 0.71,
   "bin_high": 1.12,
   "n_cited": 2,
   "n_dismissed": 2
  },
  {
   "bin_low": 1.12,
   "bin_high": 1.53,
   "n_cited": 3,
   "n_dismissed": 0
  },
  {
   "bin_low": 1.53,
   "bin_high": 1.94,
   "n_cited": 1,
   "n_dismissed": 0
  },
  {
   "bin_low": 1.94,
   "bin_high": 2.35,
   "n_cited": 0,
   "n_dismissed": 0
  },
  {
   "bin_low": 2.35,
   "bin_high": 2.76,
   "n_cited": 0,
   "n_dismissed": 0
  },
  {
   "bin_low": 2.76,
   "bin_high": 3.17,
   "n_cited": 1,
   "n_dismissed": 0
  }
 ],
 "02b_난이도요약_인용기각": [
  {
   "group": "인용",
   "n": 106,
   "p5": -0.7193,
   "p25": -0.4138,
   "median": -0.1223,
   "p75": 0.1065,
   "p95": 0.9768,
   "mean": -0.0499
  },
  {
   "group": "기각",
   "n": 51,
   "p5": -0.7117,
   "p25": -0.2166,
   "median": -0.0191,
   "p75": 0.2447,
   "p95": 0.4539,
   "mean": -0.0325
  }
 ],
 "08_정성비율": [
  {
   "label": "ambiguity",
   "value": 0,
   "n": 137,
   "denom": 157,
   "rate": 0.8726,
   "ci_low": 0.8114,
   "ci_high": 0.916
  },
  {
   "label": "ambiguity",
   "value": 1,
   "n": 20,
   "denom": 157,
   "rate": 0.1274,
   "ci_low": 0.084,
   "ci_high": 0.1886
  },
  {
   "label": "ambiguity",
   "value": 2,
   "n": 0,
   "denom": 157,
   "rate": 0.0,
   "ci_low": 0.0,
   "ci_high": 0.0239
  },
  {
   "label": "explained_duty",
   "value": 0,
   "n": 148,
   "denom": 157,
   "rate": 0.9427,
   "ci_low": 0.8947,
   "ci_high": 0.9696
  },
  {
   "label": "explained_duty",
   "value": 1,
   "n": 7,
   "denom": 157,
   "rate": 0.0446,
   "ci_low": 0.0218,
   "ci_high": 0.0892
  },
  {
   "label": "explained_duty",
   "value": 2,
   "n": 2,
   "denom": 157,
   "rate": 0.0127,
   "ci_low": 0.0035,
   "ci_high": 0.0453
  }
 ],
 "B_골드_교차표": [
  {
   "label": "cited",
   "cats": [
    "0",
    "1"
   ],
   "cells": [
    [
     10,
     0
    ],
    [
     0,
     20
    ]
   ]
  },
  {
   "label": "partial",
   "cats": [
    "0",
    "1"
   ],
   "cells": [
    [
     29,
     0
    ],
    [
     0,
     1
    ]
   ]
  },
  {
   "label": "issue_type",
   "cats": [
    "고지·설명",
    "면책",
    "보상범위·정의"
   ],
   "cells": [
    [
     8,
     0,
     0
    ],
    [
     0,
     3,
     4
    ],
    [
     0,
     0,
     15
    ]
   ]
  },
  {
   "label": "explained_duty",
   "cats": [
    "0",
    "1",
    "2"
   ],
   "cells": [
    [
     27,
     0,
     0
    ],
    [
     1,
     1,
     0
    ],
    [
     0,
     0,
     1
    ]
   ]
  },
  {
   "label": "ambiguity",
   "cats": [
    "0",
    "1",
    "2"
   ],
   "cells": [
    [
     21,
     0,
     0
    ],
    [
     4,
     4,
     0
    ],
    [
     1,
     0,
     0
    ]
   ]
  }
 ]
};
