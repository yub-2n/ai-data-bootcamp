WITH rp AS (
  SELECT product_name, TRIM(unnest(string_split(user_id, ','))) AS reviewer
  FROM clean
)
SELECT reviewer, COUNT(DISTINCT product_name) AS 등장상품수
FROM rp
GROUP BY reviewer
ORDER BY 등장상품수 DESC
LIMIT 10;