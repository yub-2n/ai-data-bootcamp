-- 쓸만한 상품중에서 할인금액이 높은것들
-- 정가와 할인가, 할인금액, 리뷰점수를 결합해 추천을 제공합니다.
select product_name as 상품명, actual_price_num as 정가, discounted_price_num as 할인가, saving_amount as 할인금액, rating_num as 리뷰점수
from clean
where rating_num>=4 and
rating_count_num>=5 and
saving_amount IS NOT NULL
order by saving_amount DESC
limit 20;