{% macro rdw_date(column_name) %}
    try_strptime(nullif(trim({{ column_name }}), ''), '%Y%m%d')::date
{% endmacro %}