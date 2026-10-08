with active as (select * from {{ ref('active_postings') }}),
total as (select count(*) as n from active)
select
    s.skill,
    count(*) as postings,
    count(distinct a.company) as companies,
    count(*) / any_value(total.n) as share,
    coalesce(any_value(c.category), 'Other') as category
from {{ ref('stg_posting_skills') }} s
join active a using (posting_id)
cross join total
left join {{ ref('skill_categories') }} c on c.skill = s.skill
group by s.skill
order by postings desc, s.skill
