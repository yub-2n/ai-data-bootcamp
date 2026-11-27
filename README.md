# 데이터 인텔리전스 부트캠프 — 주차별 과제 저장소

데이터 인텔리전스 부트캠프에서 수행한 주차별 과제(노트북, 보고서)를 모아 둔 저장소입니다.

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
├── D001 ~ D021/     주차별 과제 노트북 (D017은 D017_ABtest/)
├── 대시보드/         할인 정책 수익성 진단 대시보드 과제
├── amazon_task/     Amazon 판매 데이터 기반 추천 시스템 설계 (SQL)
├── .gitignore
└── README.md
```

## 올리는 것과 올리지 않는 것

- 데이터셋(CSV·XLSX·ZIP)은 원칙적으로 저장소에 올리지 않습니다 (.gitignore). 예외로 amazon_task/에는 과제 결과 CSV가 포함되어 있습니다.
- 강의 제공 자료(이론 노트북 등)는 올리지 않습니다.
- D006 노트북은 d006_work/orders_raw.csv(주문 원본 데이터)를 읽어서 orders_clean.csv를 만듭니다. 이 두 파일은 저장소에 올리지 않았으니, 실행하려면 원본 파일을 D006/d006_work/ 폴더에 넣어 주세요.

## 주차별 과제

| 주차 | 폴더 | 내용 (사용 기술) | 상태 |
|---|---|---|---|
| D001 | [D001](D001/) | 저장소 소개 | main 반영됨 |
| D002 | [D002](D002/) | 따릉이 대여 데이터 기초 EDA — `따릉이_기초EDA_리포트.ipynb` (pandas, seaborn) | main 반영됨 |
| D003 | [D003](D003/) | 옷장패션 데이터 정제 보고서 — `옷장패션_데이터정제_보고서.ipynb` (pandas, missingno) | main 반영됨 |
| D004 | [D004](D004/) | 데이터 병합·집계 보고서 (pandas merge·groupby) | main 반영됨 |
| D005 | [D005](D005/) | 모두마켓 웹 로그 파싱·트래픽 리포트 (pandas, seaborn) | main 반영됨 |
| D006 | [D006](D006/) | 전처리 파이프라인 (pandas, scikit-learn) | main 반영됨 |
| D007 | [D007](D007/) | 대용량 데이터 처리 — `모두마켓_대용량데이터_처리.ipynb` (pandas, Polars, psutil) | main 반영됨 |
| D008 | [D008](D008/) | 시각화로 검증·탐색·전달 보고서 (matplotlib, seaborn, Plotly) | main 반영됨 |
| D009 | [D009](D009/) | 건강기능식품 데이터 품질 진단 및 EDA 보고서 (pandas, matplotlib) | main 반영됨 |
| D010 | [D010](D010/) | 웹 스크래핑 입문 (requests, BeautifulSoup, Selenium) | main 반영됨 |
| D011 | [D011](D011/) | 웹 스크래핑 종합 과제: 동남아 날씨 비교 (requests, BeautifulSoup, seaborn) | main 반영됨 |
| D012 | [D012](D012/) | 기술통계와 모집단 (pandas, seaborn) | main 반영됨 |
| D013 | [D013](D013/) | 추론통계와 신뢰구간, 문제 3 표준오차 — `문제3_표준오차.ipynb` (SciPy) | main 반영됨 |
| D014 | [D014](D014/) | 가설검정 (SciPy, statsmodels) | main 반영됨 |
| D015 | [D015](D015/) | 상관과 회귀 (SciPy, statsmodels) | main 반영됨 |
| D016 | [D016](D016/) | 가설검정의 주의점, 인과와 상관 (statsmodels, scikit-learn) | main 반영됨 |
| D017 | [D017_ABtest](D017_ABtest/) | A/B 테스트 종합 과제 (SciPy, statsmodels) | main 반영됨 |
| D018 | [D018](D018/) | 선형·로지스틱 회귀 (scikit-learn) | main 반영됨 |
| D019 | [D019](D019/) | 의사결정나무와 앙상블 (scikit-learn, XGBoost) | main 반영됨 |
| D020 | [D020](D020/) | 과적합과 교차검증 (scikit-learn, XGBoost) | main 반영됨 |
| D021 | [D021](D021/) | 분류 지표와 데이터 불균형 (scikit-learn) | main 반영됨 |
| D022 | D022 | 피처 선택과 데이터 누수 | 작업 폴더에만 있음 (실습 미완료) |
| D023 | D023 | 군집화와 차원축소 | 작업 폴더에만 있음 (실습 미완료) |
| D024 | D024 | 모델 해석과 SHAP | 작업 폴더에만 있음 (실습 미완료) |
| 대시보드 | [대시보드](대시보드/) | 할인 정책 수익성 진단 (Superstore 샘플 데이터, pandas, HTML) | main 반영됨 |

기타 과제: [Amazon 판매 데이터 기반 추천 시스템 설계 (SQL)](amazon_task/)
