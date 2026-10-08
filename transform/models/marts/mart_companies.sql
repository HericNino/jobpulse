select company, count(*) as postings
from {{ ref('active_postings') }}
where company is not null
group by company
order by postings desc, company
