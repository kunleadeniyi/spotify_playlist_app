# spotify_playlist_app

To setup, follow the steps below:
1. Create and activate virtual env or venv
2. Install pre-requisite packages found in the requirements.txt file

3. Configure airflow to run on heroku as done using this link https://elements.heroku.com/buttons/jsoyland/heroku_airflow

To run on prem, use the following steps instead of step 3

  a. Initialize airflow db using "airflow db init"
  b. Start airflow webserver using "airflow webserver -p 8080"
  c. Start airflow scheduler using "airflow scheduler"

4. DAG name "spotify_dag" should be among dag list
5. Activate DAG


Extra:

1. additinal dags can be added to the dags folder in the project
2. If running on prem dag folder in $AIRFLOW_HOME/airflow.cfg must point to the folder where your dags are running.
