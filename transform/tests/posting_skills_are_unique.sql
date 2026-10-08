-- each skill appears at most once per posting
select posting_id, skill, count(*) as n
from {{ ref('stg_posting_skills') }}
group by posting_id, skill
having count(*) > 1
