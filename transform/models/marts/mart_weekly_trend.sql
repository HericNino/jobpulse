-- Weekly share of new postings that mention each of the top skills.
-- Only complete weeks (Monday to Sunday) are included.
with postings as (select * from {{ ref('stg_postings') }}),
as_of as (select max(last_seen) as as_of from postings),
weekly as (
    select date_trunc('week', first_seen) as week, posting_id
    from postings, as_of
    where first_seen > as_of.as_of - interval {{ (var('trend_weeks') + 1) * 7 }} day
),
weeks as (
    select week, count(*) as total
    from weekly, as_of
    where week + interval 6 day <= as_of.as_of
    group by week
),
top_skills as (
    select skill, row_number() over (order by postings desc, skill) as rank
    from {{ ref('mart_top_skills') }}
    qualify rank <= {{ var('trend_skills') }}
)
select
    cast(w.week as date) as week,
    w.total,
    t.skill,
    t.rank,
    count(s.posting_id) / w.total as share
from weeks w
cross join top_skills t
left join weekly p on p.week = w.week
left join {{ ref('stg_posting_skills') }} s on s.posting_id = p.posting_id and s.skill = t.skill
group by w.week, w.total, t.skill, t.rank
order by t.rank, week
