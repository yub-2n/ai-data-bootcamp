-- 분야별로 가장 평이 좋은 상품 하나씩 (분야별 1등만 모았어요)
-- 전체 평점 순위는 상품이 많은 카테고리에 편중되므로, 대분류마다 대표 상품을 하나씩 제시해
-- 사용자가 원하는 분야를 쉽게 탐색할 수 있게 합니다.
WITH ranked AS (
  SELECT
    product_name,
    main_category,
    rating_num,
    rating_count_num,
    ROW_NUMBER() OVER (
      PARTITION BY main_category
      ORDER BY rating_num DESC, rating_count_num DESC
    ) AS 카테고리순위
  FROM clean
  WHERE rating_num IS NOT NULL
)
SELECT
  main_category    AS 카테고리,
  product_name     AS 상품명,
  rating_num       AS 평점,
  rating_count_num AS 리뷰수
FROM ranked
WHERE 카테고리순위 = 1
ORDER BY rating_num DESC;