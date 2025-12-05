from ytmusicapi import YTMusic
from ytmusicapi.auth.oauth import OAuthCredentials
import time

import json
import os
import requests

class PlaylistManager:
    def __init__(self, auth_file='headers_auth.json'):
        # Prioritize OAuth if available
        if os.path.exists('oauth.json'):
            print("Using OAuth credentials (oauth.json)")
            try:
                with open('client_secrets.json', 'r') as f:
                    secrets = json.load(f)
                    # Handle both "installed" and "web" formats, or direct keys
                    if 'installed' in secrets:
                        creds_data = secrets['installed']
                    elif 'web' in secrets:
                        creds_data = secrets['web']
                    else:
                        creds_data = secrets
                        
                creds = OAuthCredentials(client_id=creds_data['client_id'], client_secret=creds_data['client_secret'])
                self.yt = YTMusic(auth='oauth.json', oauth_credentials=creds)
            except Exception as e:
                print(f"Error loading OAuth credentials: {e}")
                self.yt = YTMusic(auth_file) # Fallback
        else:
            print(f"Using legacy headers auth ({auth_file})")
            self.yt = YTMusic(auth_file)
        
        # Load config for user filter
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.user_name = config['youtube'].get('user_filter', "Anthony Buitrago")
        except:
            self.user_name = "Anthony Buitrago" # Fallback

    def _get_access_token(self):
        """Helper to get fresh access token from ytmusicapi instance."""
        try:
            # If using OAuth, the token is in self.yt._token.access_token
            # But we should ensure it's fresh. calling .headers triggers refresh if needed.
            _ = self.yt.headers 
            if hasattr(self.yt, '_token'):
                return self.yt._token.access_token
        except Exception as e:
            print(f"Error getting access token: {e}")
        return None

    def get_my_playlists(self):
        """Returns a list of playlists using YouTube Data API."""
        print("Fetching playlists via Data API...")
        token = self._get_access_token()
        if not token:
            print("No OAuth token available, falling back to legacy method (likely to fail if headers invalid)")
            return self.yt.get_library_playlists(limit=100)

        import requests
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        playlists = []
        
        try:
            # 1. Fetch 'Liked Music' (LM) - DISABLED by user request
            # try:
            #     channel_url = "https://www.googleapis.com/youtube/v3/channels?part=contentDetails&mine=true"
            #     c_resp = requests.get(channel_url, headers=headers)
            #     if c_resp.status_code == 200:
            #         items = c_resp.json().get('items', [])
            #         if items:
            #             likes_id = items[0]['contentDetails']['relatedPlaylists']['likes']
            #             playlists.append({
            #                 'playlistId': likes_id,
            #                 'title': 'Liked Music',
            #                 'count': 0 
            #             })
            # except Exception as e:
            #     print(f"Error fetching Liked Music ID: {e}")

            # 2. Fetch standard playlists
            ignored_titles = ["Liked Videos", "Watch Later", "Ver más tarde", "Videos que me gustan"]
            
            next_page_token = None
            while True:
                url = "https://www.googleapis.com/youtube/v3/playlists?part=snippet,contentDetails&mine=true&maxResults=50"
                if next_page_token:
                    url += f"&pageToken={next_page_token}"
                    
                resp = requests.get(url, headers=headers)
                if resp.status_code != 200:
                    print(f"Data API Error (Playlists): {resp.status_code} {resp.text}")
                    break
                    
                data = resp.json()
                for item in data.get('items', []):
                    title = item['snippet']['title']
                    pid = item['id']
                    
                    # Filter out ignored playlists
                    if pid == 'WL' or title in ignored_titles:
                        continue
                        
                    playlists.append({
                        'playlistId': pid,
                        'title': title,
                        'count': item['contentDetails']['itemCount']
                    })
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
            
        except Exception as e:
            print(f"Error fetching playlists via Data API: {e}")
            
        return playlists

    def get_playlist_tracks(self, playlist_id):
        """Fetches all tracks from a playlist using YouTube Data API."""
        print(f"Fetching tracks for {playlist_id} via Data API...")
        token = self._get_access_token()
        if not token:
             return self.yt.get_playlist(playlist_id, limit=None)['tracks']

        import requests
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        tracks = []
        
        try:
            next_page_token = None
            while True:
                url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={playlist_id}&maxResults=50"
                if next_page_token:
                    url += f"&pageToken={next_page_token}"
                
                resp = requests.get(url, headers=headers)
                if resp.status_code != 200:
                    print(f"Data API Error (Tracks): {resp.status_code} {resp.text}")
                    break
                
                data = resp.json()
                for item in data.get('items', []):
                    snippet = item['snippet']
                    # Map Data API format to ytmusicapi format expected by DBManager
                    track = {
                        'videoId': snippet['resourceId']['videoId'],
                        'title': snippet['title'],
                        'artists': [{'name': snippet.get('videoOwnerChannelTitle', 'Unknown')}],
                        'album': {'name': 'Unknown'}, # Data API doesn't give album info easily
                        'duration': '0:00', # Data API snippet doesn't have duration (contentDetails does, but requires extra call or different part)
                        'setVideoId': item['id'] # Important for deduplication
                    }
                    tracks.append(track)
                    
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
                    
        except Exception as e:
            print(f"Error fetching tracks via Data API: {e}")
            
        return tracks

    def deduplicate_playlist(self, playlist_id):
        """Removes duplicate songs from a playlist."""
        print(f"Scanning playlist {playlist_id} for duplicates...")
        tracks = self.get_playlist_tracks(playlist_id)
        
        seen_ids = set()
        seen_signatures = set() # Artist - Title
        duplicates = []

        for track in tracks:
            # Track ID (videoId) is the most reliable
            video_id = track.get('videoId')
            
            # Signature fallback (Artist - Title)
            title = track.get('title', '').lower()
            artists = " ".join([a['name'] for a in track.get('artists', [])]).lower()
            signature = f"{artists} - {title}"
            
            is_duplicate = False
            
            if video_id and video_id in seen_ids:
                is_duplicate = True
            elif signature in seen_signatures:
                is_duplicate = True
            
            if is_duplicate:
                duplicates.append(track)
            else:
                if video_id:
                    seen_ids.add(video_id)
                seen_signatures.add(signature)

        if not duplicates:
            print("No duplicates found.")
            return

        print(f"Found {len(duplicates)} duplicates. Removing...")
        # ytmusicapi remove_playlist_items requires setVideoId (the unique ID of the item in the playlist)
        # NOT the videoId of the song.
        # Wait, get_playlist returns 'setVideoId' for each track?
        # Yes, it should. Let's verify.
        
        items_to_remove = []
        for track in duplicates:
            if 'setVideoId' in track:
                items_to_remove.append(track)
            else:
                print(f"Warning: Could not find setVideoId for duplicate {track.get('title')}")

        if items_to_remove:
            self.yt.remove_playlist_items(playlist_id, items_to_remove)
            print(f"Successfully removed {len(items_to_remove)} duplicates.")
            
            # Update Local DB
            try:
                from db_manager import DBManager
                db = DBManager()
                for track in items_to_remove:
                    # We need to remove specific setVideoId entries
                    svid = track.get('setVideoId')
                    if svid:
                        db.cursor.execute("DELETE FROM playlist_tracks WHERE set_video_id = ?", (svid,))
                db.conn.commit()
                db.close()
            except Exception as e:
                print(f"Error updating DB after deduplication: {e}")
        else:
            print("Could not remove duplicates (missing setVideoId).")

    def create_playlist(self, title, description=""):
        return self.yt.create_playlist(title, description)

    def add_tracks(self, playlist_id, video_ids):
        return self.yt.add_playlist_items(playlist_id, video_ids)

    def smart_organize(self, source_playlist_id, target_playlist_ids):
        """
        Moves tracks from source playlist to target playlists based on artist matching.
        target_playlist_ids: List of playlist IDs to check against.
        """
        print(f"Starting Smart Organization from {source_playlist_id}...")
        
        # 1. Build Artist Map from Target Playlists
        artist_map = {} # Artist Name -> Playlist ID
        print("Building artist map from target playlists...")
        for pid in target_playlist_ids:
            try:
                tracks = self.get_playlist_tracks(pid)
                for track in tracks:
                    artists = track.get('artists', [])
                    if artists:
                        # Map primary artist
                        primary_artist = artists[0]['name'].lower()
                        artist_map[primary_artist] = pid
                        # Also map all artists? Maybe just primary for safety.
            except Exception as e:
                print(f"Error reading playlist {pid}: {e}")

        print(f"Mapped {len(artist_map)} artists.")

        # 2. Scan Source Playlist
        source_tracks = self.get_playlist_tracks(source_playlist_id)
        moves = {} # Target PID -> List of Video IDs to add
        removals = [] # List of setVideoIds to remove from source

        for track in source_tracks:
            artists = track.get('artists', [])
            if not artists:
                continue
                
            primary_artist = artists[0]['name'].lower()
            target_pid = artist_map.get(primary_artist)
            
            if target_pid:
                # Check if it's already in target? 
                # For now, just assume we add it. Deduplication can run later on target.
                if target_pid not in moves:
                    moves[target_pid] = []
                
                moves[target_pid].append(track['videoId'])
                
                if 'setVideoId' in track:
                    removals.append(track) # Store full track object for removal
                
                print(f"Match: {primary_artist} -> {target_pid} ({track['title']})")

        # 3. Execute Moves
        if not moves:
            print("No matches found.")
            return

        print(f"Moving {len(removals)} tracks...")
        
        # Add to targets
        for pid, video_ids in moves.items():
            print(f"Adding {len(video_ids)} tracks to {pid}...")
            try:
                self.yt.add_playlist_items(pid, video_ids)
            except Exception as e:
                print(f"Failed to add to {pid}: {e}")

        # Remove from source
        if removals:
            print(f"Removing {len(removals)} tracks from source...")
            try:
                self.yt.remove_playlist_items(source_playlist_id, removals)
            except Exception as e:
                print(f"Failed to remove from source: {e}")

    def sort_standard(self, playlist_id, create_copy=True):
        """
        Sorts a playlist by Artist -> Title.
        If create_copy is True, creates a new playlist "[Sorted] Original Name".
        """
        print(f"Sorting playlist {playlist_id}...")
        playlist_info = self.yt.get_playlist(playlist_id, limit=None)
        tracks = playlist_info['tracks']
        title = playlist_info['title']
        
        # Sort logic
        # Key: Artist (lowercase) -> Title (lowercase)
        def sort_key(track):
            artist = track['artists'][0]['name'].lower() if track.get('artists') else ""
            title = track.get('title', '').lower()
            return (artist, title)

        sorted_tracks = sorted(tracks, key=sort_key)
        sorted_video_ids = [t['videoId'] for t in sorted_tracks if t.get('videoId')]

        if create_copy:
            new_title = f"{title} [Sorted]"
            try:
                print(f"Creating new playlist: {new_title}")
            except UnicodeEncodeError:
                print(f"Creating new playlist: {new_title.encode('ascii', 'ignore').decode('ascii')}")
            
            try:
                new_pid = self.yt.create_playlist(new_title, f"Sorted version of {title}", video_ids=sorted_video_ids)
                print(f"Success! Created {new_title.encode('ascii', 'ignore').decode('ascii')} ({new_pid})")
                return new_pid
            except Exception as e:
                print(f"Failed to create playlist: {e}")
        else:
            # In-place sort (Dangerous / Slow)
            # We would need to clear and re-add.
            # Or use edit_playlist to move items? No, too many moves.
            # Clear and add is best for in-place.
            print("In-place sort not fully implemented for safety. Please use create_copy=True.")

if __name__ == "__main__":
    pm = PlaylistManager()
    playlists = pm.get_my_playlists()
    print("Available Playlists:")
    for p in playlists:
        try:
            print(f"- {p['title']} ({p['playlistId']})")
        except UnicodeEncodeError:
            safe_title = p['title'].encode('ascii', 'ignore').decode('ascii')
            print(f"- {safe_title} ({p['playlistId']})")
