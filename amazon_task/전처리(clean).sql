CREATE OR REPLACE TABLE clean AS
SELECT
  product_id,
  product_name,
  category,                                    -- 원본도 남겨둠

  -- 카테고리 계층 쪼개기
  string_split(category, '|')[1]  AS main_category,   -- 대분류
  string_split(category, '|')[2]  AS sub_category,    -- 중분류
  string_split(category, '|')[-1] AS leaf_category,   -- 가장 세부

  -- 숫자로 변환
  TRY_CAST(rating AS DOUBLE) AS rating_num,
  TRY_CAST(REPLACE(rating_count, ',', '') AS BIGINT) AS rating_count_num,
  TRY_CAST(REPLACE(REPLACE(actual_price,     '₹',''), ',','') AS DOUBLE) AS actual_price_num,
  TRY_CAST(REPLACE(REPLACE(discounted_price, '₹',''), ',','') AS DOUBLE) AS discounted_price_num,
  TRY_CAST(REPLACE(discount_percentage, '%','') AS DOUBLE) AS discount_pct,

  -- 파생 컬럼
  actual_price_num - discounted_price_num       AS saving_amount,   -- 실제로 아낀 금액
  len(string_split(user_id, ','))               AS reviewer_count,  -- 리뷰어 수

  -- 텍스트는 그대로
  user_id,
  review_title,
  review_content,
  about_product
FROM amazon;

SELECT
  COUNT(*)                  AS 전체,
  COUNT(rating_num)         AS 평점정상,
  COUNT(sub_category)       AS 중분류있음,
  ROUND(AVG(saving_amount)) AS 평균절약액
FROM clean;
