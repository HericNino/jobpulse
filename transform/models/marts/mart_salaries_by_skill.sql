select
    p.currency,
    s.skill,
    count(*) as postings,
    round(median(p.yearly)) as median
from {{ ref('int_salaries') }} p
join {{ ref('stg_posting_skills') }} s using (posting_id)
group by p.currency, s.skill
having count(*) >= 3
order by p.currency, median desc, s.skill
