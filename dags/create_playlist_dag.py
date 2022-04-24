from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.models import XCom
from airflow.utils.timezone import make_aware
from datetime import datetime, timedelta

from spotify import SpotifyObject, WeeklyPlaylist

sp = SpotifyObject.get_spotify_object()
weekly_playlist = WeeklyPlaylist(sp)

# weekly_playlist.get_my_playlists()

dag_default_args = {
    'owner': 'airflow',
    'start_date': datetime(2020, 2, 20),
    'sla': timedelta(minutes=30)
}

with DAG('spotify_dag',
         description='Spotify DAG',
         default_args=dag_default_args,
         schedule_interval='@daily',
         catchup=False) as spotify_dag:

    get_user_id = PythonOperator(
        task_id="get_my_id",
        python_callable=weekly_playlist.get_current_user_id
    )

    get_rec_played_songs = PythonOperator(
        task_id="get_rec_played_songs",
        python_callable=weekly_playlist.get_recently_played
    )

    get_saved_songs = PythonOperator(
        task_id="get_saved_songs",
        python_callable=weekly_playlist.get_saved_tracks
    )

    get_top_tracks = PythonOperator(
        task_id="get_top_tracks",
        python_callable=weekly_playlist.get_my_top_tracks
    )

    get_top_artists = PythonOperator(
        task_id="get_top_artists",
        python_callable=weekly_playlist.get_my_top_artists
    )

    def get_xcom(task_id):
        """
        Get XCom of a certain task.
        :str task_id:
        :return: the xcom value
        """
        xcom = XCom.get_one(
            execution_date=make_aware(datetime.now()),
            task_id=task_id,
            include_prior_dates=True
        )
        return xcom

    get_seed_top_artists = PythonOperator(
        task_id="get_seed_top_artists",
        python_callable=weekly_playlist.get_seed_artists,
        op_kwargs={"top_artists": get_xcom("get_top_artists")}
    )

    get_seed_top_tracks = PythonOperator(
        task_id="get_seed_top_tracks",
        python_callable=weekly_playlist.get_seed_tracks,
        op_kwargs={"saved_tracks": get_xcom("get_top_tracks")}
    )

    get_seed_saved_songs = PythonOperator(
        task_id="get_seed_saved_songs",
        python_callable=weekly_playlist.get_seed_tracks,
        op_kwargs={"saved_tracks": get_xcom("get_saved_songs")}
    )

    get_seed_rec_played = PythonOperator(
        task_id="get_seed_rec_played",
        python_callable=weekly_playlist.get_seed_tracks,
        op_kwargs={"saved_tracks": get_xcom("get_rec_played_songs")}
    )

    rec_from_saved_songs = PythonOperator(
        task_id="rec_from_saved_songs",
        python_callable=weekly_playlist.get_recommendations,
        op_kwargs={
            "seed_tracks": get_xcom("get_seed_saved_songs"),
            "limit": 10
        }
    )

    rec_from_top_songs = PythonOperator(
        task_id="rec_from_top_songs",
        python_callable=weekly_playlist.get_recommendations,
        op_kwargs={
            "seed_tracks": get_xcom("get_seed_top_tracks"),
            "seed_artists": get_xcom("get_seed_top_artists"),
            "limit": 20
        }
    )

    rec_from_rec_played = PythonOperator(
        task_id="rec_from_rec_played",
        python_callable=weekly_playlist.get_recommendations,
        op_kwargs={
            "seed_tracks": get_xcom("get_seed_rec_played"),
            "limit": 10
        }
    )

    get_playlist_tracks = PythonOperator(
        task_id="get_playlist_tracks",
        python_callable=weekly_playlist.unpack_recommended_track_ids,
        op_kwargs={
            "rec_from_saved_tracks": get_xcom("rec_from_saved_songs"),
            "rec_from_recently_played": get_xcom("rec_from_rec_played"),
            "rec_from_top_tracks": get_xcom("rec_from_top_songs")
        }
    )

    create_playlist = PythonOperator(
        task_id="create_playlist",
        python_callable=weekly_playlist.create_or_replace_playlist,
        op_kwargs={
            "user_id": get_xcom("get_my_id"),
            "track_ids_list": get_xcom("get_playlist_tracks"),
            "playlist_name": "Made for you",
            "playlist_desc": "Made for you by you. Powered by Airflow"
        }
    )

    # workflow
    """
    get user id - no args
    
    get recently played songs - get_user_id['id']
    get saved songs - no args
    get top tracks - no args
    get top artists - no args
    
    get seed_tracks - get saved songs
    
    get seed_top_tracks - get top tracks
    get seed_top_artists - get top artists
    
    get seed_recently_played -  get_recently_played_songs
    
    get recommendation using saved tracks - seed_saved_tracks, seed_genres
    get recommendation using top tracks - seed_top_artists, seed_top_tracks 
    get recommendation using recently played tracks - seed_recently_played, limit=5
    
    unpack track_ids - rec_from_saved_tracks, rec_from_recently_played, rec_from_top_tracks
    
    create or replace playlist - user_id, unpacked_track_ids, playlist_name
    """

    get_user_id >> [get_top_artists, get_top_tracks, get_saved_songs, get_rec_played_songs]
    get_top_artists >> get_seed_top_artists
    get_top_tracks >> get_seed_top_tracks

    get_saved_songs >> get_seed_saved_songs
    get_rec_played_songs >> get_seed_rec_played

    get_seed_saved_songs >> rec_from_saved_songs
    [get_seed_top_artists, get_seed_top_tracks] >> rec_from_top_songs
    get_seed_rec_played >> rec_from_rec_played

    [rec_from_rec_played, rec_from_top_songs, rec_from_saved_songs] >> get_playlist_tracks

    get_playlist_tracks >> create_playlist

    # The top is the correct one -- make it work
    
    """
    get_user_id >> [get_top_artists, get_top_tracks, get_rec_played_songs]
    get_top_artists >> get_seed_top_artists
    get_top_tracks >> get_seed_top_tracks

    # get_saved_songs >> get_seed_saved_songs
    get_rec_played_songs >> get_seed_rec_played

    # get_seed_saved_songs >> rec_from_saved_songs
    [get_seed_top_artists, get_seed_top_tracks] >> rec_from_top_songs
    get_seed_rec_played >> rec_from_rec_played

    [rec_from_rec_played, rec_from_top_songs] >> get_playlist_tracks

    get_playlist_tracks >> create_playlist
    """