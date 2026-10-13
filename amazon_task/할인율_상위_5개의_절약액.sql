SELECT
  product_name  AS 상품명,
  discount_pct  AS 할인율,
  saving_amount AS 절약액
FROM clean
WHERE discount_pct IS NOT NULL AND saving_amount IS NOT NULL
ORDER BY discount_pct DESC
LIMIT 5;