with postings as (select * from {{ ref('stg_postings') }}),
active as (select * from {{ ref('active_postings') }}),
as_of as (select max(last_seen) as as_of from postings)
select
    as_of.as_of,
    (select count(*) from active) as active,
    (select count(*) from postings where first_seen > as_of.as_of - interval 7 day) as new_this_week,
    (select count(distinct company) from active) as companies,
    (select coalesce(avg(case when work_mode = 'remote' then 1 else 0 end), 0) from active) as remote_share,
    (select coalesce(avg(case when salary_min is not null then 1 else 0 end), 0) from active) as salary_share,
    (select count(*) from postings) as all_time
from as_of
