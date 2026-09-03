-- 선물로 많이 고르는 상품이에요 (리뷰 텍스트 기반 상황 추천 시스템)
-- 리뷰 본문에 선물 관련 언급이 반복되는 상품을 모아, 선물을 고르는 고객에게
-- 이미 선물로 구매해본 사람들이 검증한 선택지를 제공합니다.
-- review_title 기준은 5건(0.3%)뿐이어서 review_content로 변경해 66건(4.5%)을 확보했습니다.
SELECT DISTINCT                        -- 원본 중복 등재(114행) 대응
  product_name             AS 상품명,
  LEFT(review_content, 60) AS 리뷰내용,
  rating_num               AS 평점,
  rating_count_num         AS 리뷰수
FROM clean
WHERE (LOWER(review_content) LIKE '%gift%'
    OR LOWER(review_content) LIKE '%present%'
    OR LOWER(review_content) LIKE '%birthday%')
  AND rating_num IS NOT NULL
ORDER BY rating_num DESC
LIMIT 20;
