import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time

class SpotifyManager:
    def __init__(self, client_id, client_secret, redirect_uri="http://127.0.0.1:8888/callback"):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public playlist-modify-private",
            open_browser=True
        ))
        self.user_id = self.sp.current_user()['id']
        print(f"Connected to Spotify as: {self.user_id}")

    def get_user_playlists(self):
        playlists = []
        results = self.sp.current_user_playlists(limit=50)
        playlists.extend(results['items'])
        while results['next']:
            results = self.sp.next(results)
            playlists.extend(results['items'])
        return {p['name']: p['id'] for p in playlists}

    def create_playlist(self, name, description="Synced from YouTube Music"):
        # Check if exists first
        current_playlists = self.get_user_playlists()
        if name in current_playlists:
            try:
                print(f"Playlist '{name}' already exists on Spotify.")
            except UnicodeEncodeError:
                print(f"Playlist '{name.encode('ascii', 'ignore').decode('ascii')}' already exists on Spotify.")
            return current_playlists[name]
        
        try:
            print(f"Creating Spotify playlist: {name}")
        except UnicodeEncodeError:
            print(f"Creating Spotify playlist: {name.encode('ascii', 'ignore').decode('ascii')}")
        playlist = self.sp.user_playlist_create(self.user_id, name, public=False, description=description)
        return playlist['id']

    def search_track(self, artist, title):
        # Clean title (remove [Official Video], etc)
        clean_title = title.split('(')[0].split('[')[0].strip()
        query = f"artist:{artist} track:{clean_title}"
        
        try:
            results = self.sp.search(q=query, type='track', limit=1)
            items = results['tracks']['items']
            if items:
                return items[0]['uri']
            
            # Retry with just title if artist + title fails (looser search)
            # query = f"track:{clean_title} artist:{artist}"
            # results = self.sp.search(q=query, type='track', limit=1)
            # items = results['tracks']['items']
            # if items:
            #     return items[0]['uri']
                
        except Exception as e:
            print(f"Error searching {artist} - {title}: {e}")
            
        return None

    def add_tracks_to_playlist(self, playlist_id, track_uris):
        # Spotify allows max 100 tracks per request
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            try:
                self.sp.playlist_add_items(playlist_id, batch)
                time.sleep(0.5)
            except Exception as e:
                print(f"Error adding tracks: {e}")

    def replace_tracks_in_playlist(self, playlist_id, track_uris):
        # First batch uses 'replace' to clear and set (max 100)
        if not track_uris:
            self.sp.playlist_replace_items(playlist_id, [])
            return

        first_batch = track_uris[:100]
        try:
            self.sp.playlist_replace_items(playlist_id, first_batch)
            time.sleep(0.5)
        except Exception as e:
            print(f"Error replacing tracks: {e}")
            return

        # Subsequent batches use 'add'
        if len(track_uris) > 100:
            self.add_tracks_to_playlist(playlist_id, track_uris[100:])
