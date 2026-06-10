{% macro log_model_run(model_name) %}
    -- Record model execution in the pipeline_runs audit table
    INSERT INTO public.pipeline_runs (started_at, status, records_extracted)
    VALUES (NOW(), 'dbt_{{ model_name }}', (
        SELECT COUNT(*) FROM {{ this }}
    ));
{% endmacro %}