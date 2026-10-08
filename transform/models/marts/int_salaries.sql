-- Yearly pay per posting: midpoint of the stated range, monthly figures x12.
-- Hourly pay and implausible values (likely extraction mistakes) are left out.
with pay as (
    select
        posting_id,
        salary_currency as currency,
        (coalesce(salary_min, salary_max) + coalesce(salary_max, salary_min)) / 2
            * case salary_period when 'month' then 12 else 1 end as yearly
    from {{ ref('active_postings') }}
    where salary_currency is not null
      and salary_period in ('year', 'month')
      and coalesce(salary_min, salary_max) is not null
)
select * from pay where yearly between 5000 and 1000000
