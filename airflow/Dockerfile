FROM quay.io/astronomer/astro-runtime:12.6.0

# dbt cannot share Airflow's Python environment: Airflow's opentelemetry-proto
# requires protobuf<5.0 while dbt-core requires protobuf>=5.0. Isolating dbt in
# its own virtualenv is the standard resolution for this conflict.
RUN python -m venv /usr/local/airflow/dbt_venv && \
    source /usr/local/airflow/dbt_venv/bin/activate && \
    pip install --no-cache-dir dbt-core dbt-duckdb && \
    deactivate
