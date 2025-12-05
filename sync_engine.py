from spotify_manager import SpotifyManager
from sorter import PlaylistManager
import time
import json

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

class SyncEngine:
    def __init__(self):
        self.config = load_config()
        self.sp_config = self.config['spotify']
        self.sp = None
        self.yt = None
        
    def connect(self):
        if not self.sp:
            self.sp = SpotifyManager(
                self.sp_config['client_id'], 
                self.sp_config['client_secret'],
                self.sp_config['redirect_uri']
            )
        if not self.yt:
            self.yt = PlaylistManager()

    def get_playlists(self):
        self.connect()
        yt_pl = self.yt.get_my_playlists()
        sp_pl = self.sp.get_user_playlists()
        
        # Filter out unwanted playlists
        ignored_titles = ["Your Likes", "Liked Songs", "Liked Music", "Watch Later", "Episodes for Later"]
        
        yt_pl = [p for p in yt_pl if p['title'] not in ignored_titles]
        sp_pl = [p for p in sp_pl if p['name'] not in ignored_titles]
        
        # Sort alphabetically
        yt_pl.sort(key=lambda x: x['title'].lower())
        sp_pl.sort(key=lambda x: x['name'].lower())
        
        return yt_pl, sp_pl

    def sync_to_spotify(self, yt_playlist_id, sp_playlist_name=None, smart=True, progress_callback=None):
        self.connect()
        
        # Get Source Tracks
        yt_tracks = self.yt.get_playlist_tracks(yt_playlist_id)
        
        # Determine Target Name
        if not sp_playlist_name:
            try:
                # Fetch playlist info to get title
                pl_info = self.yt.yt.get_playlist(yt_playlist_id, limit=1) # Limit 1 just to get metadata
                sp_playlist_name = pl_info.get('title', 'Synced Playlist')
            except:
                sp_playlist_name = "Synced Playlist"
            
        if progress_callback: progress_callback(0, 0, f"Preparing to sync to '{sp_playlist_name}'...")
            
        # Create/Get Target
        sp_playlist_id = self.sp.create_playlist(sp_playlist_name)
        
        # Get Existing Target Tracks (for Smart Sync)
        existing_uris = set()
        if smart:
            current_tracks = self.sp.get_playlist_tracks(sp_playlist_id)
            existing_uris = {t['uri'] for t in current_tracks}
            
        # Match Tracks
        to_add = []
        total = len(yt_tracks)
        
        for i, track in enumerate(yt_tracks):
            artist = track['artists'][0]['name'] if track.get('artists') else "Unknown"
            title = track['title']
            
            if progress_callback and i % 5 == 0:
                progress_callback(i+1, total, f"Matching: {title}")
            
            uri = self.sp.search_track(artist, title)
            if uri:
                if not smart or uri not in existing_uris:
                    to_add.append(uri)
            else:
                print(f"Missing on Spotify: {artist} - {title}")
                
        # Execute
        if to_add:
            if progress_callback: progress_callback(total, total, f"Adding {len(to_add)} tracks...")
            self.sp.add_tracks_to_playlist(sp_playlist_id, to_add)
            return f"Added {len(to_add)} tracks."
        else:
            return "No new tracks to add."

    def sync_to_youtube(self, sp_playlist_id, yt_playlist_name=None, smart=True, progress_callback=None):
        self.connect()
        
        # Get Source
        sp_tracks = self.sp.get_playlist_tracks(sp_playlist_id)
        
        if not yt_playlist_name:
            yt_playlist_name = "Imported from Spotify"
            
        if progress_callback: progress_callback(0, 0, f"Preparing import to '{yt_playlist_name}'...")
            
        # Create/Get Target (YT doesn't have easy "get by name", so we usually create new)
        # For now, let's always create new or append if we can find it?
        # Sorter.py has create_playlist.
        
        # We'll just create a new one for safety or append if we implement search.
        # Let's create new for now.
        yt_playlist_id = self.yt.create_playlist(yt_playlist_name, "Imported from Spotify")
        
        # Match Tracks (YT Music Search)
        # YTMusicAPI search is powerful.
        
        video_ids = []
        total = len(sp_tracks)
        
        for i, track in enumerate(sp_tracks):
            query = f"{track['artist']} {track['title']}"
            if progress_callback and i % 5 == 0:
                progress_callback(i+1, total, f"Searching: {track['title']}")
                
            results = self.yt.yt.search(query, filter="songs", limit=1)
            if results:
                video_ids.append(results[0]['videoId'])
            else:
                print(f"Missing on YT: {query}")
                
        # Add
        if video_ids:
            if progress_callback: progress_callback(total, total, f"Importing {len(video_ids)} tracks...")
            self.yt.add_tracks(yt_playlist_id, video_ids)
            return f"Imported {len(video_ids)} tracks."
        else:
            return "No tracks found to import."

