SELECT
  main_category AS 대분류,
  COUNT(*) AS 상품수,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS 비중
FROM clean
GROUP BY main_category
ORDER BY 상품수 DESC;