SELECT
  CASE WHEN img_link IS NULL OR TRIM(img_link) = '' THEN '이미지 없음'
       ELSE '이미지 있음' END AS 이미지여부,
  COUNT(*) AS 상품수,
  ROUND(AVG(TRY_CAST(rating AS DOUBLE)), 2) AS 평균평점,
  ROUND(AVG(TRY_CAST(REPLACE(rating_count, ',', '') AS BIGINT))) AS 평균리뷰수
FROM amazon
GROUP BY 이미지여부;