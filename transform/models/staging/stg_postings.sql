-- Read the JSON Lines file with explicit column types, so an empty file or a
-- missing optional field still produces the right schema.
select
    id as posting_id,
    source,
    title,
    nullif(url, '') as url,
    nullif(company, '') as company,
    nullif(country, '') as country,
    remote as work_mode,
    seniority,
    cast(posted_at as date) as posted_at,
    cast(first_seen as date) as first_seen,
    cast(last_seen as date) as last_seen,
    salary_min,
    salary_max,
    upper(salary_currency) as salary_currency,
    salary_period,
    analyzed_by,
    skills
from read_json(
    '{{ var("postings_path") }}',
    format = 'newline_delimited',
    columns = {
        id: 'varchar', source: 'varchar', url: 'varchar', title: 'varchar', company: 'varchar',
        location: 'varchar', country: 'varchar', posted_at: 'varchar', first_seen: 'varchar',
        last_seen: 'varchar', remote: 'varchar', seniority: 'varchar', skills: 'varchar[]',
        salary_min: 'bigint', salary_max: 'bigint', salary_currency: 'varchar',
        salary_period: 'varchar', analyzed_by: 'varchar'
    }
)
