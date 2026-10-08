{% test exactly_one_row(model) %}
select n from (select count(*) as n from {{ model }}) where n != 1
{% endtest %}
