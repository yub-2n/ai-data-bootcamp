-- 이 상품을 본 사람이 함께 본 상품 (리뷰어 기반 연관 추천 시스템)
-- 같은 리뷰어가 리뷰한 상품들은 취향이 이어져 있다고 보고, 상품 상세 페이지에서
-- 함께 볼 만한 상품을 제안합니다. 협업 필터링의 기초 형태입니다.
WITH reviewer_product AS (
  SELECT product_id, product_name,
         TRIM(unnest(string_split(user_id, ','))) AS reviewer
  FROM clean
)
SELECT
  a.product_name             AS 기준상품,
  b.product_name             AS 추천상품,
  COUNT(DISTINCT a.reviewer) AS 공유리뷰어수
FROM reviewer_product a
JOIN reviewer_product b
  ON a.reviewer = b.reviewer
 AND a.product_id <> b.product_id
GROUP BY a.product_name, b.product_name
ORDER BY 공유리뷰어수 DESC, 기준상품
LIMIT 20;