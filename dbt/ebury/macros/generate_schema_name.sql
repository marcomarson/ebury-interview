{#
  Use the custom schema name AS-IS (e.g. `staging`, `analytics`) instead of dbt's
  default `<target_schema>_<custom>` concatenation. Keeps warehouse schema names clean
  and matches the plan-04 schema layout (staging vs analytics).
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
