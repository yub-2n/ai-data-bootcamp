SELECT
  MIN(rating_count_num)      AS 최소리뷰수,
  MAX(rating_count_num)      AS 최대리뷰수,
  ROUND(AVG(rating_count_num)) AS 평균,
  MEDIAN(rating_count_num)   AS 중앙값
FROM clean;