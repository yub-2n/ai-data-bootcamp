# 데이터 인텔리전스 부트캠프 — 프로젝트·과제 포트폴리오

데이터로 문제를 정의하고, 통계로 검증하고, 의사결정에 쓸 수 있는 형태(보고서·대시보드)로 전달한 작업을 모은 저장소입니다.

## 대표 프로젝트

| 프로젝트 | 질문 | 핵심 결과 | 결과물 |
|---|---|---|---|
| [약관 난이도와 보험금 분쟁 결과](projects/04_insurance-cx-terms-difficulty/)<br>보험 CX · 3인 팀 | 어떤 약관 조항부터 쉽게 고쳐 쓸까? | 분쟁의 46%가 '보험금 지급사유' 조항에 집중, 난이도와 결과의 연관은 불확실 → 해당 조항부터 시험 개선 권고 | [▶ 대시보드](https://yub-2n.github.io/ai-data-bootcamp/projects/04_insurance-cx-terms-difficulty/dashboard/) |
| [비 한 번에 놓치는 외지인 매출](projects/05_bigcontest-climate-commerce/)<br>빅콘테스트 · 3인 팀 | 큰비가 오면 관광 상권 매출은 얼마나 줄고, 다시 돌아올까? | 30mm 호우일 춘천 외지인 결제 **−21.5%**, 5일 뒤에도 하루치의 48.3% 미회복(비 한 번에 약 7억 원, 최소 추정) → 30mm 날씨지수 보험 제안 | [보고서 PDF](projects/05_bigcontest-climate-commerce/bigcontest_final_report.pdf)·코드 |
| [궁·능 관람객 예측과 인력 배치](projects/03_timeseries-forecast-report/)<br>시계열 · 4인 팀 | 관람객을 예측해 인력 배치 비용을 줄일 수 있을까? | Chronos-2 + 운영 정보로 인력 배치 비용 **−42.8%** (백테스트) | [보고서](projects/03_timeseries-forecast-report/timeseries_report_summary.pdf)·[발표 자료](projects/03_timeseries-forecast-report/timeseries_final_presentation.pdf) |
| [Olist 셀러 유치 전략](projects/02_olist-seller-acquisition-dashboard/)<br>대시보드 · 4인 팀 | 어떤 셀러를 유치해야 실제 판매로 이어질까? | 유통×중대형 온라인 셀러 활성화율 54.9% (평균 44.1%) → 같은 계약으로 활성 셀러 **+24.6%** | [▶ 대시보드](https://yub-2n.github.io/ai-data-bootcamp/projects/02_olist-seller-acquisition-dashboard/step7_dashboard.html) |
| [Olist 배송 지연과 리뷰](projects/01_olist-delivery-review/)<br>ML · 4인 팀 | 배송 지연은 리뷰를 얼마나 깎고, 어디서 생길까? | 지연 시 평균 리뷰 4.29 → **2.57점**, 지연의 81%가 운송사 구간 → 정시율·운송사 관리 권고 | 분석 노트북·발표 자료 |

## 개인 과제 하이라이트

- [할인 정책 수익성 대시보드](대시보드/) (Superstore) — 할인 20% 초과 구간에서 이익이 적자로 뒤집히는 지점을 찾아 **할인 상한 20%**를 권고 · [▶ 대시보드](https://yub-2n.github.io/ai-data-bootcamp/%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C/superstore_discount_dashboard.html)
- [Amazon 판매 데이터 기반 추천 시스템 설계](amazon_task/) (SQL) — 상품 1,465건으로 관점이 다른 추천 로직 5종 설계
- [A/B 테스트 종합 과제](D017_ABtest/) — 랜딩 페이지 전환율: SRM 점검 → 카이제곱 검정 → 검정력·MDE → 의사결정

## 사용 기술

- Python, Jupyter Notebook
- 데이터 처리: pandas, NumPy, Polars
- 시각화: matplotlib, seaborn, Plotly, missingno
- 웹 스크래핑: requests, BeautifulSoup, Selenium
- 통계: SciPy, statsmodels
- 머신러닝: scikit-learn, XGBoost
- SQL (amazon_task)

## 폴더 구조

```
ai-data-bootcamp/
├── projects/        팀 프로젝트 5개 (ML, 대시보드, 시계열, 보험 CX, 빅콘테스트)
├── D001 ~ D021/     주차별 과제 노트북 (D017은 D017_ABtest/)
├── 대시보드/         할인 정책 수익성 진단 대시보드 (개인 과제)
├── amazon_task/     Amazon 판매 데이터 기반 추천 시스템 설계 (SQL)
├── index.html       대시보드 모음 (GitHub Pages 첫 화면)
├── .gitignore
└── README.md
```

## 올리는 것과 올리지 않는 것

- 데이터셋(CSV·XLSX·ZIP)은 원칙적으로 저장소에 올리지 않습니다 (.gitignore). 예외로 amazon_task/에는 과제 결과 CSV가 포함되어 있습니다.
- 강의 제공 자료(이론 노트북 등)는 올리지 않습니다.
- D006 노트북은 d006_work/orders_raw.csv(주문 원본 데이터)를 읽어서 orders_clean.csv를 만듭니다. 이 두 파일은 저장소에 올리지 않았으니, 실행하려면 원본 파일을 D006/d006_work/ 폴더에 넣어 주세요.

## 주차별 과제

| 주차 | 폴더 | 내용 (사용 기술) |
|---|---|---|
| D001 | [D001](D001/) | 저장소 소개 |
| D002 | [D002](D002/) | 따릉이 대여 데이터 기초 EDA — `따릉이_기초EDA_리포트.ipynb` (pandas, seaborn) |
| D003 | [D003](D003/) | 옷장패션 데이터 정제 보고서 — `옷장패션_데이터정제_보고서.ipynb` (pandas, missingno) |
| D004 | [D004](D004/) | 데이터 병합·집계 보고서 (pandas merge·groupby) |
| D005 | [D005](D005/) | 모두마켓 웹 로그 파싱·트래픽 리포트 (pandas, seaborn) |
| D006 | [D006](D006/) | 전처리 파이프라인 (pandas, scikit-learn) |
| D007 | [D007](D007/) | 대용량 데이터 처리 — `모두마켓_대용량데이터_처리.ipynb` (pandas, Polars, psutil) |
| D008 | [D008](D008/) | 시각화로 검증·탐색·전달 보고서 (matplotlib, seaborn, Plotly) |
| D009 | [D009](D009/) | 건강기능식품 데이터 품질 진단 및 EDA 보고서 (pandas, matplotlib) |
| D010 | [D010](D010/) | 웹 스크래핑 입문 (requests, BeautifulSoup, Selenium) |
| D011 | [D011](D011/) | 웹 스크래핑 종합 과제: 동남아 날씨 비교 (requests, BeautifulSoup, seaborn) |
| D012 | [D012](D012/) | 기술통계와 모집단 (pandas, seaborn) |
| D013 | [D013](D013/) | 추론통계와 신뢰구간, 문제 3 표준오차 — `문제3_표준오차.ipynb` (SciPy) |
| D014 | [D014](D014/) | 가설검정 (SciPy, statsmodels) |
| D015 | [D015](D015/) | 상관과 회귀 (SciPy, statsmodels) |
| D016 | [D016](D016/) | 가설검정의 주의점, 인과와 상관 (statsmodels, scikit-learn) |
| D017 | [D017_ABtest](D017_ABtest/) | A/B 테스트 종합 과제 (SciPy, statsmodels) |
| D018 | [D018](D018/) | 선형·로지스틱 회귀 (scikit-learn) |
| D019 | [D019](D019/) | 의사결정나무와 앙상블 (scikit-learn, XGBoost) |
| D020 | [D020](D020/) | 과적합과 교차검증 (scikit-learn, XGBoost) |
| D021 | [D021](D021/) | 분류 지표와 데이터 불균형 (scikit-learn) |
| D022 | D022 | 피처 선택과 데이터 누수 (실습 미완료) |
| D023 | D023 | 군집화와 차원축소 (실습 미완료) |
| D024 | D024 | 모델 해석과 SHAP (실습 미완료) |

