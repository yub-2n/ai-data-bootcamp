WITH r AS (
  SELECT product_id, unnest(string_split(user_id, ',')) AS reviewer
  FROM clean
)
SELECT COUNT(*) AS 겹치는리뷰어수
FROM (SELECT reviewer FROM r GROUP BY reviewer HAVING COUNT(DISTINCT product_id) >= 2);