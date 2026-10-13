-- 아직 안 알려진 숨은 명품이에요 (평점 대비 저노출 상품 추천 시스템)
-- 평점은 상위권인데 리뷰 수는 하위권인 상품을 발굴해, 고객이 아직 알려지지 않은
-- 좋은 상품을 발견할 수 있게 합니다.
WITH scored AS (
  SELECT
    product_id,
    product_name,
    rating_num,
    rating_count_num,
    NTILE(4) OVER (ORDER BY rating_num)            AS 평점등급,
    NTILE(4) OVER (ORDER BY rating_count_num DESC) AS 리뷰희소등급  -- 둘 다 4가 제일 높은 등급
  FROM clean
  WHERE rating_num IS NOT NULL
    AND rating_count_num IS NOT NULL   -- 리뷰수 결측 2건이 최상위 등급으로 오분류되는 것 방지
)
SELECT DISTINCT                        -- 원본 중복 등재(114행) 대응
  product_id       AS 상품번호,
  product_name     AS 상품명,
  rating_num       AS 평점,
  rating_count_num AS 리뷰수
FROM scored
WHERE 평점등급 = 4
  AND 리뷰희소등급 = 4
ORDER BY rating_num DESC
LIMIT 20;
