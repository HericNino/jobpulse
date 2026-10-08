select posting_id
from {{ ref('stg_postings') }}
where last_seen < first_seen
