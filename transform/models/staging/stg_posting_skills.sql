select distinct
    posting_id,
    unnest(skills) as skill
from {{ ref('stg_postings') }}
