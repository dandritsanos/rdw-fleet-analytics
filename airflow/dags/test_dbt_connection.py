from airflow.decorators import dag, task
from datetime import datetime

@dag(
    dag_id="test_dbt_connection",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["test"],
)
def test_dbt_connection():

    @task.bash
    def check_dbt_version():
        return "cd /usr/local/airflow/rdw_project/dbt && dbt --version"

    @task.bash
    def check_project_files():
        return "ls -la /usr/local/airflow/rdw_project/scripts/"

    check_dbt_version() >> check_project_files()

test_dbt_connection()
