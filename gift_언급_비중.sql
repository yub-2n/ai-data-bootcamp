SELECT
  COUNT(*) AS 전체상품,
  COUNT(CASE WHEN LOWER(review_title) LIKE '%gift%' THEN 1 END) AS gift언급상품,
  ROUND(COUNT(CASE WHEN LOWER(review_title) LIKE '%gift%' THEN 1 END) * 100.0 / COUNT(*), 1) AS 비중
FROM clean;