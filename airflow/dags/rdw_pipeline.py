from datetime import datetime, timedelta
from airflow.decorators import dag, task

DBT = "/usr/local/airflow/dbt_venv/bin/dbt"
DBT_DIR = "/usr/local/airflow/rdw_project/dbt"
PROFILES_DIR = "/usr/local/airflow/rdw_project/dbt"

default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
}

@dag(
    dag_id="rdw_pipeline",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["rdw", "production"],
)
def rdw_pipeline():

    @task.bash
    def dbt_deps():
        return f"cd {DBT_DIR} && {DBT} deps --profiles-dir {PROFILES_DIR}"

    @task.bash
    def dbt_snapshot():
        return f"cd {DBT_DIR} && {DBT} snapshot --profiles-dir {PROFILES_DIR}"

    @task.bash
    def dbt_run():
        return f"cd {DBT_DIR} && {DBT} run --profiles-dir {PROFILES_DIR}"

    @task.bash
    def dbt_test():
        return f"cd {DBT_DIR} && {DBT} test --profiles-dir {PROFILES_DIR}"

    @task.bash
    def dbt_source_freshness():
        return f"cd {DBT_DIR} && {DBT} source freshness --profiles-dir {PROFILES_DIR}"

    deps = dbt_deps()
    snapshot = dbt_snapshot()
    run = dbt_run()
    test = dbt_test()
    freshness = dbt_source_freshness()

    deps >> snapshot >> run >> test >> freshness

rdw_pipeline()
