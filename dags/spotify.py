import random
import spotipy
import os

from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()


class SpotifyObject:
    scope = "user-library-read user-read-recently-played user-top-read playlist-read-private playlist-modify-public playlist-modify-private"
    client_id = os.environ.get('CLIENT_ID')
    client_secret = os.environ.get('CLIENT_SECRET')

    @staticmethod
    def get_spotify_object():
        sp_object = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                scope=SpotifyObject.scope,
                client_id=SpotifyObject.client_id,
                client_secret=SpotifyObject.client_secret,
                redirect_uri='http://localhost:4000/callback')
        )
        return sp_object


class WeeklyPlaylist(object):
    def __init__(self, spotify_object):
        self.sp = spotify_object

    def get_current_user_id(self):
        me = self.sp.current_user()
        return me['id']

    def get_saved_tracks(self):
        my_saved_tracks = self.sp.current_user_saved_tracks()
        saved_track_list = [track['id'] for track in my_saved_tracks['items']]
        return saved_track_list

    def get_recently_played(self):
        my_recently_played = self.sp.current_user_recently_played()
        rec_played_track_list = [track['track']['id'] for track in my_recently_played['items']]
        return rec_played_track_list

    def get_my_top_tracks(self):
        """ Will return a list of top tracks listened too"""
        my_top_tracks = self.sp.current_user_top_tracks(limit=10)
        top_track_list = [track['id'] for track in my_top_tracks['items']]
        return top_track_list

    def get_my_top_artists(self):
        """ Will return a list of top artists listened too"""
        my_top_artist = self.sp.current_user_top_artists(limit=10)
        top_artist_list = [artist['id'] for artist in my_top_artist['items']]
        return top_artist_list

    def get_seed_artists(self, top_artists):
        return self.get_random_seeds(top_artists)

    def get_seed_tracks(self, saved_tracks):
        """will return a list of 5 tracks to be passed as seed tracks in sp.recommendations"""
        if len(saved_tracks) == 0:
            return self.get_seed_tracks(self.get_my_top_tracks())
        if len(saved_tracks) <= 3:
            return saved_tracks
        if len(saved_tracks) > 3:
            return self.get_random_seeds(saved_tracks, 4)

    def get_seed_genres(self):
        seed_genres = self.sp.recommendation_genre_seeds()
        return self.get_random_seeds(seed_genres['genres'])

    def get_random_seeds(self, seed_list, number_of_seeds=5):
        """
        helper function
        For the recommendation function. It needs a seed of at most 5 items
        It will used in
        """
        seed_list = seed_list
        if len(seed_list) < number_of_seeds:
            number_of_seeds = len(seed_list)
            return self.get_random_seeds(seed_list, number_of_seeds)
        return random.sample(seed_list, number_of_seeds)

    def get_recommendations(self, seed_tracks, seed_genres=None, seed_artists=None, limit=None):
        limit = 25 if limit is None else limit
        if seed_genres and seed_artists:
            seed_genres = self.get_random_seeds(seed_genres, 1)
            seed_tracks = self.get_random_seeds(seed_tracks, 2)
            seed_artists = self.get_random_seeds(seed_artists, 2)
            track_recommendations = self.sp.recommendations(
                seed_tracks=seed_tracks,
                seed_genres=seed_genres,
                seed_artists=seed_artists,
                limit=limit
            )
            return [track['id'] for track in track_recommendations['tracks']]
        if seed_genres and seed_artists is None:
            seed_genres = self.get_random_seeds(seed_genres, 2)
            seed_tracks = self.get_random_seeds(seed_tracks, 3)
            # print(seed_tracks, seed_genres)
            track_recommendations = self.sp.recommendations(
                seed_tracks=seed_tracks,
                seed_genres=seed_genres,
                limit=limit
            )
            return [track['id'] for track in track_recommendations['tracks']]
        if seed_genres is None and seed_artists:
            seed_artists = self.get_random_seeds(seed_artists, 3)
            seed_tracks = self.get_random_seeds(seed_tracks, 2)
            track_recommendations = self.sp.recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                limit=limit
            )
            return [track['id'] for track in track_recommendations['tracks']]
        track_recommendations = self.sp.recommendations(
            seed_tracks=seed_tracks,
            limit=limit
        )
        return [track['id'] for track in track_recommendations['tracks']]

    def unpack_recommended_track_ids(self,
                                     rec_from_saved_tracks=None,
                                     rec_from_recently_played=None,
                                     rec_from_top_tracks=None
                                     ):
        if rec_from_top_tracks is None:
            rec_from_top_tracks = []
        if rec_from_recently_played is None:
            rec_from_recently_played = []
        if rec_from_saved_tracks is None:
            rec_from_saved_tracks = []
        unpacked_track_ids = [*rec_from_saved_tracks, *rec_from_recently_played, *rec_from_top_tracks]

        # get unique track ids
        unique_track_ids = list(set(unpacked_track_ids))
        return unique_track_ids

    def get_my_playlists(self):
        """
        get a list of my playlist
        :return: a list of tuples. each tuple containing the playlist id and the playlist name
        """
        my_playlists = self.sp.current_user_playlists()
        if len(my_playlists['items']) == 0:
            return []
        if len(my_playlists['items']) > 0:
            playlist_ids = [playlist['id'] for playlist in my_playlists['items']]
            playlist_names = [playlist['name'] for playlist in my_playlists['items']]

            print(playlist_ids, playlist_names)
            my_playlists_info = zip(playlist_ids, playlist_names)
            return list(my_playlists_info)

    def check_if_playlists_exist(self, my_playlist_info, new_playlist_name):
        """

        :list my_playlist_info: a list of tuples. each tuple containing (playlist_id, playlist_name)
        :str new_playlist_name: name of playlist to be created or replaced
        :return: dictionary  if playlist already exists or None if playlist does not exist
        """
        if len(my_playlist_info) == 0:
            return None
        for playlist_id, playlist_name in my_playlist_info:
            if playlist_name == new_playlist_name:
                return {'playlist_id': playlist_id, 'playlist_name': playlist_name}
            else:
                return None

    def create_or_replace_playlist(self, user_id, track_ids_list, playlist_name, playlist_desc="Made for you by you"):
        """
        creates or replaces a playlist if it already exists with the list of tracks passed
        :str user_id: should be current user's id
        :list track_ids_list: list of track_ids
        :str playlist_name: name of playlist
        :str playlist_desc: description of the playlist

        :return: created playlist in my spotify using api call
        """
        # get my playlists
        my_playlists = self.get_my_playlists()
        playlist_exists = self.check_if_playlists_exist(my_playlists, playlist_name)
        if playlist_exists:
            rebuilt_playlist = self.sp.playlist_replace_items(playlist_exists['playlist_id'], track_ids_list)
            return rebuilt_playlist
        else:
            new_playlist = self.sp.user_playlist_create(user=user_id, name=playlist_name, description=playlist_desc)
            new_playlist_id = new_playlist['id']
            built_playlist = self.sp.playlist_add_items(playlist_id=new_playlist_id, items=track_ids_list)
            return built_playlist
