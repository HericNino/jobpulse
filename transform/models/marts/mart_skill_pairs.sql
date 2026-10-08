-- How often two skills are asked for in the same posting.
with s as (
    select s.*
    from {{ ref('stg_posting_skills') }} s
    join {{ ref('active_postings') }} using (posting_id)
)
select a.skill as a, b.skill as b, count(*) as postings
from s a
join s b on a.posting_id = b.posting_id and a.skill < b.skill
group by a.skill, b.skill
having count(*) >= 2
order by postings desc, a, b
