select 'seniority' as dimension, seniority as key, count(*) as postings
from {{ ref('active_postings') }} group by seniority
union all
select 'work_mode', work_mode, count(*)
from {{ ref('active_postings') }} group by work_mode
union all
select 'source', source, count(*)
from {{ ref('active_postings') }} group by source
