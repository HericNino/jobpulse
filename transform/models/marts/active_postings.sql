-- Postings still listed within the last `active_days` of the most recent run.
with as_of as (
    select max(last_seen) as as_of from {{ ref('stg_postings') }}
)
select p.*
from {{ ref('stg_postings') }} p, as_of
where p.last_seen >= as_of.as_of - interval {{ var('active_days') }} day
