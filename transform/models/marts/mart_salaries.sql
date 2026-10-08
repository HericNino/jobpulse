select
    currency,
    count(*) as postings,
    round(quantile_cont(yearly, 0.25)) as p25,
    round(median(yearly)) as median,
    round(quantile_cont(yearly, 0.75)) as p75
from {{ ref('int_salaries') }}
group by currency
having count(*) >= 3
