select posting_id
from {{ ref('stg_postings') }}
where salary_min is not null and salary_max is not null and salary_min > salary_max
