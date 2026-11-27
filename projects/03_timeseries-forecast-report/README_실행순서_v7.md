# 코드 실행 순서 (v7) — `code` 폴더 안에서 `python 파일이름.py` 로 실행 (`python -I` 금지)
필요한 것: python3, pandas, numpy, pyarrow, tabulate. (Chronos 실행만 Colab: `05b_run_chronos_colab_v7.py`, 명령은 `colab_v7/Colab_실행순서_v7.txt`)
모든 스크립트가 원점 목록을 `origins_v7.py` 한 곳에서 가져온다(78개 + 명절 4개, 검증 assert 포함).

## A. 이미 실행한 것 (결과는 results_new/ 에 있음). B·C 단계도 모두 실행 완료, 재실행하려면 아래 순서
1. `00_make_origins_v7.py` 원점 78개 검증과 원점표
2. `15_check_readme_values.py`, `00b_validate_data_v7.py` 데이터·공변량 검증
3. `04_baselines3_compare.py` 베이스라인 3개 → `data/baselines3_rows_v7.parquet`
4. `10_partial_rows12_v7.py` 베이스라인 비교표 + FVA 1·2행 부분 결과
5. `25_check_event_files.py` 행사 파일 검증(새 파일 기준)

## B. Colab 결과를 받은 뒤 (data/ 에 4개 parquet 를 넣고)
1. `12_export_eval_rows_v7.py` → `data/eval_rows_v7.parquet` (제외 행은 `results_new/평가집합_제외행_v7.csv`)
2. `최종FVA표_만들기.py` → `fva_final_tables.md` (FVA 1~7행, 부트스트랩 구간)
3. `검증하기_v7.py` 구조·숫자 검증 → "모두 일치" 확인
4. `24_ab_and_direct_tables.py`(A vs B), `23_eval_row7.py`(7행·공지 민감도), `29_block_bootstrap_v7.py`(원점/블록 부트스트랩·집중도)
5. `28_season_tables_v7.py`(계절별, 2025년 1~2월 겨울 포함)
6. `작업1_표_만들기_v7.py`(날짜·개소 유형), `작업2_10건_만들기_v7.py`(오차 상위), `작업3_보정규칙_만들기_v7.py`(보정 규칙), `27_guide_tables.py`
7. `14_make_recommendation_table.py` 2026-01-01~07 권고표 — **17번보다 먼저**
8. `17_savings_split_and_assumptions.py`, `18_main_topic_table.py`, `19_alt_service_levels_backtest.py`(약 1~3분)
9. `16_cause_check_temp_free.py`, `20_check_free_open_file.py`, `21_mistakes_measured.py`
10. `22_seed_check.py` 같은 조건 두 번 실행 비교(서로 다른 시드 실험과 구분해서 보고)
11. `31_overlap_v6_v7.py`(v6와 겹치는 30개 원점 값 대조), `30_compare_v6_v7.py`(v6 대 v7 핵심 지표)
12. (Colab 후속) `32_strict_notice_sensitivity_v7.py` 공지 시점 엄격 기준 민감도: `data/chronos_series_A_v7_strictfh.parquet` 가 있어야 한다
13. (선택) `26_future_seollal_lastwed.py` 추후 방안

## 공용·참고
`07_timing_direct_compare.py`(공용 함수, 지우지 말 것), `03_fva_row1_2_fixed.py`, `02_check_guide.py`, `09_open_expected.py`, `01_build_grid.py`(grid 재생성이 필요할 때만), `13_extend_calendar_2026.py`(2026 달력, 필요할 때만)
v6 회귀 시험으로 `ORIGINS_SET=v6` 를 쓸 수 있다(원점 26개). 분석에는 쓰지 않는다.
