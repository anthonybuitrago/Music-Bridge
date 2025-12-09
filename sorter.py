from ytmusicapi import YTMusic
from ytmusicapi.auth.oauth import OAuthCredentials
import time

import json
import os
import requests
import logging

logger = logging.getLogger("MusicBridge")

class PlaylistManager:
    def __init__(self, auth_file='headers_auth.json', db_path='music_library.db'):
        self.db_path = db_path
        self.yt = None      # Internal API (Cookies preferred)
        self.yt_oauth = None # Data API (Token provider)

        # 1. Setup OAuth (for Data API Access Token)
        if os.path.exists('oauth.json'):
            try:
                # print("Loading OAuth for Data API...")
                with open('client_secrets.json', 'r') as f:
                    secrets = json.load(f)
                    if 'installed' in secrets: creds_data = secrets['installed']
                    elif 'web' in secrets: creds_data = secrets['web']
                    else: creds_data = secrets
                        
                creds = OAuthCredentials(client_id=creds_data['client_id'], client_secret=creds_data['client_secret'])
                self.yt_oauth = YTMusic(auth='oauth.json', oauth_credentials=creds)
                # Use OAuth for main interface too if available
                self.yt = self.yt_oauth
                self.yt = self.yt_oauth
                logger.info("Using OAuth credentials (oauth.json).")
            except Exception as e:
                print(f"Error loading OAuth: {e}")

        # 2. Setup Internal API (Cookies - Legacy/Fallback)
        if self.yt is None and os.path.exists(auth_file):
            logger.debug(f"Using headers auth ({auth_file}) as fallback.")
            try:
                # Manual load to bypass YTMusic's file detection quirks
                with open(auth_file, 'r') as f:
                    headers_dict = json.load(f)
                
                # --- AUTO-FIX: Generate missing Authorization header ---
                if 'Cookie' in headers_dict and 'Authorization' not in headers_dict:
                    import hashlib
                    import re
                    import time
                    
                    try:
                        cookie = headers_dict['Cookie']
                        sapisid_match = re.search(r'SAPISID=([^;]+)', cookie)
                        if sapisid_match:
                            sapisid = sapisid_match.group(1)
                            origin = headers_dict.get('x-origin', 'https://music.youtube.com')
                            timestamp = str(int(time.time()))
                            
                            payload = f"{timestamp} {sapisid} {origin}"
                            sha = hashlib.sha1(payload.encode('utf-8')).hexdigest()
                            
                            headers_dict['Authorization'] = f"SAPISIDHASH {timestamp}_{sha}"
                            # print(f"Generated Authorization header for SAPISID.")
                    except Exception as e:
                        print(f"Failed to generate auth header: {e}")
                # -----------------------------------------------------

                self.yt = YTMusic(auth=headers_dict)
            except Exception as e:
                print(f"Error loading headers auth: {e}")

        # If manual load failed, or self.yt is still None, try standard init as backup/fallback
        if self.yt is None and os.path.exists(auth_file):
             try:
                 self.yt = YTMusic(auth_file)
             except Exception: pass
        
        # Fallback: If no headers auth, try to use OAuth for Internal API too (though prone to 400s)
        if self.yt is None and self.yt_oauth is not None:
             print("⚠️ headers_auth.json not found. Using OAuth for Internal API (Write operations might fail).")
             self.yt = self.yt_oauth
        
        if self.yt is None:
            print("⛔ No authentication method found (headers_auth.json or oauth.json)!")

        # Load config for user filter
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                self.user_name = config['youtube'].get('user_filter', "Anthony Buitrago")
        except:
            self.user_name = "Anthony Buitrago"

    # _get_access_token removed: No longer needed for Internal API via OAuth

    def get_my_playlists(self):
        """Returns a list of playlists using YouTube Internal API (OAuth or Cookies)."""
        logger.debug("ℹ️ Fetching playlists via Internal API...")
        
        if not self.yt:
            logger.error("❌ API instance is None. Cannot fetch playlists.")
            return []

        try:
            # Native ytmusicapi method (works with OAuth now)
            data = self.yt.get_library_playlists(limit=None)
            
            # --- AUTO-FIX: Brand Account / Channel Switcher ---
            # If default channel (0) has no playlists, user likely has a "Brand Account".
            # We assume "no playlists" = wrong channel, because active users usually have at least "Your Likes".
            if not data or len(data) == 0:
                if hasattr(self.yt, 'headers'):
                    # print("ℹ️ Default channel empty. Checking Brand Accounts...")
                    current_auth_user = self.yt.headers.get('X-Goog-AuthUser', '0')
                    
                    # Only try if we are on default 0
                    if current_auth_user == '0':
                        for i in range(1, 5):
                            self.yt.headers['X-Goog-AuthUser'] = str(i)
                            try:
                                # Quick check with small limit first? No, get_library is fast enough.
                                check_data = self.yt.get_library_playlists(limit=None)
                                if check_data and len(check_data) > 0:
                                    print(f"✅ Found playlists on Channel Index {i}. Switching channel.")
                                    data = check_data
                                    break
                            except Exception:
                                continue
                        else:
                            # Reset if none found (optional, but good for cleanup)
                            self.yt.headers['X-Goog-AuthUser'] = '0'
            # --------------------------------------------------
            
            # Format to match our app's structure
            playlists = []
            params_blacklist = ["LM", "SE"] # Liked Music, Episodes for Later (system ids)
            
            for item in data:
                pid = item['playlistId']
                if pid in params_blacklist: 
                    continue
                    
                playlists.append({
                    'playlistId': pid,
                    'title': item['title'],
                    'count': item.get('count', 0) # Count might be missing or different
                })
            return playlists
            
        except Exception as e:
            print(f"Internal API failed: {e}. Falling back to Local Database...")
            try:
                from db_manager import DBManager
                db = DBManager(self.db_path)
                db_playlists = db.get_all_playlists()
                db.close()
                params_blacklist = ["LM", "SE"]
                return [{
                    'playlistId': p['id'],
                    'title': p['title'],
                    'count': 0 
                } for p in db_playlists if p['id'] not in params_blacklist]
            except Exception as db_e:
                print(f"Database fallback failed: {db_e}")
                return []

    def _fetch_db_tracks(self, playlist_id):
        # print(f"Using Local Database for tracks (API Fallback) for {playlist_id}...") 
        try:
            from db_manager import DBManager
            db = DBManager(self.db_path)
            tracks = db.get_playlist_tracks_details(playlist_id)
            db.close()
            return tracks
        except Exception as e:
            print(f"Database track fetch failed: {e}")
            return []

    def _fetch_internal_tracks_logic(self, playlist_id):
        # print("Falling back to Internal API (get_playlist)...")
        if not self.yt:
             return self._fetch_db_tracks(playlist_id)
        
        try:
            # Internal API get_playlist returns dict with 'tracks' key
            # limit=None is important to get all tracks
            data = self.yt.get_playlist(playlist_id, limit=None)
            
            # Logger context
            t_count = len(data.get('tracks', [])) if data else 0
            # logger.debug(f"Internal API 'get_playlist' for {playlist_id}: Found {t_count} tracks.")
            
            if not data or 'tracks' not in data:
                logger.warning(f"Internal API returned invalid data for {playlist_id}. Falling back to DB.")
                return self._fetch_db_tracks(playlist_id)
            
            formatted_tracks = []
            for t in data['tracks']:
                # Map Internal API fields to Data API structure
                artists = []
                if 'artists' in t and t['artists']:
                    artists = [{'name': a['name']} for a in t['artists']]
                else:
                    artists = [{'name': 'Unknown'}]

                if not t.get('videoId'):
                    logger.warning(f"Track missing videoId: {t.get('title', 'Unknown')}")

                formatted_tracks.append({
                    'videoId': t.get('videoId'),
                    'title': t.get('title'),
                    'artists': artists,
                    'album': {'name': (t.get('album') or {}).get('name', 'Unknown')},
                    'duration': t.get('duration', '0:00'),
                    'setVideoId': t.get('setVideoId', t.get('videoId'))
                })
            return formatted_tracks
        except Exception as e:
            logger.error(f"Internal API track fetch failed: {e}")
            return self._fetch_db_tracks(playlist_id)

    def get_playlist_tracks(self, playlist_id):
        """Fetches all tracks from a playlist using YouTube Data API. Fallbacks to DB."""
        
        # PRIORITIZE INTERNAL API (Cookie Auth)
        if self.yt:
             return self._fetch_internal_tracks_logic(playlist_id)
        
        # Only try token if we don't have self.yt (Internal)
        token = None
        if hasattr(self, '_get_access_token'):
            token = self._get_access_token()

        if not token:
             return self._fetch_internal_tracks_logic(playlist_id)

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
                    if resp.status_code == 403:
                         raise Exception(f"Quota exceeded.")
                    print(f"Data API Error (Tracks): {resp.status_code} {resp.text}")
                    break
                
                data = resp.json()
                for item in data.get('items', []):
                    snippet = item['snippet']
                    try:
                         vid = snippet['resourceId']['videoId']
                    except KeyError:
                         continue 

                    track = {
                        'videoId': vid,
                        'title': snippet['title'],
                        'artists': [{'name': snippet.get('videoOwnerChannelTitle', 'Unknown')}],
                        'album': {'name': 'Unknown'},
                        'duration': '0:00',
                        'setVideoId': item['id']
                    }
                    tracks.append(track)
                
                next_page_token = data.get('nextPageToken')
                if not next_page_token:
                    break
            
        except Exception as e:
            # print(f"Error fetching tracks via Data API: {e}") 
            is_quota = "quota" in str(e).lower() or "403" in str(e)
            
            if is_quota:
                if not getattr(self, '_quota_warned', False):
                    print("⚠️ Data API Quota Limit Reached. Switching to Internal API / Local Database.")
                    self._quota_warned = True
                return self._fetch_internal_tracks_logic(playlist_id)
            
            print(f" [WARN] Data API Error: {e}. Falling back to DB.")
            return self._fetch_db_tracks(playlist_id)
            
        return tracks

    def deduplicate_playlist(self, playlist_id):
        """Removes duplicate songs from a playlist."""
        print(f"Scanning playlist {playlist_id} for duplicates...")
        tracks = self.get_playlist_tracks(playlist_id)
        
        seen_ids = set()
        seen_signatures = set()
        duplicates = []

        for track in tracks:
            video_id = track.get('videoId')
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
                if video_id: seen_ids.add(video_id)
                seen_signatures.add(signature)

        if not duplicates:
            print("No duplicates found.")
            return

        print(f"Found {len(duplicates)} duplicates. Removing...")
        items_to_remove = []
        for track in duplicates:
            if 'setVideoId' in track:
                items_to_remove.append(track)
            else:
                print(f"Warning: Could not find setVideoId for duplicate {track.get('title')}")

        if items_to_remove:
            try:
                self.yt.remove_playlist_items(playlist_id, items_to_remove)
                print(f"Successfully removed {len(items_to_remove)} duplicates.")
                
                # Update Local DB
                try:
                    from db_manager import DBManager
                    db = DBManager(self.db_path)
                    for track in items_to_remove:
                        svid = track.get('setVideoId')
                        if svid:
                            db.cursor.execute("DELETE FROM playlist_tracks WHERE set_video_id = ?", (svid,))
                    db.commit()
                    db.close()
                except Exception as e:
                    print(f"Error updating DB after deduplication: {e}")

            except Exception as e:
                print(f"Error removing items: {e}")
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

    # create_playlist_v3 removed: Replaced by self.yt.create_playlist (Internal API)

    def add_items_internal_robust(self, playlist_id, video_ids, batch_size=50):
        """
        Adds tracks using the Internal API (Quota-Free).
        Strategy:
        1. Try adding in batches.
        2. If a batch fails (HTTP 400), retry items individually to isolate bad tracks.
        """
        import time
        
    def add_items_internal_robust(self, playlist_id, video_ids, batch_size=50):
        """
        Adds tracks using the Internal API (Quota-Free).
        Strategy:
        1. Try adding in batches.
        2. If a batch fails (HTTP 400), retry items individually to isolate bad tracks.
        """
        import time
        
        total = len(video_ids)
        # print(f"Adding {total} tracks via Internal API (Quota-Free)...")
        
        for i in range(0, total, batch_size):
            batch = video_ids[i:i+batch_size]
            current_batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            # print(f"Processing batch {current_batch_num}/{total_batches} ({len(batch)} songs)...")
            
            try:
                # Try adding the whole batch
                resp = self.yt.add_playlist_items(playlist_id, batch)
                logger.debug(f"Batch response: {resp}")
            except Exception as e:
                # If batch fails, fallback to individual
                logger.debug(f"Batch failed ({e}). Retrying individually...")
                for vid in batch:
                    try:
                        self.yt.add_playlist_items(playlist_id, [vid])
                    except Exception as inner_e:
                        logger.debug(f"Skipping bad track {vid}: {inner_e}")
                logger.debug(f"Recovered from batch error.")
            
            # Small sleep to be nice to the server
            time.sleep(0.5)
            
        # print("Done adding tracks.")



    def sort_standard(self, playlist_id, title_hint=None, create_copy=True):
        """
        Sorts a playlist by Artist -> Title.
        If create_copy is True, creates a new playlist "[Sorted] Original Name".
        """
        # print(f"Sorting playlist {playlist_id}...")
        
        # Use Data API method (reliable) instead of internal API (fragile for some users)
        tracks = self.get_playlist_tracks(playlist_id)
        
        if title_hint:
            title = title_hint
        else:
            # Fallback if no title provided (inefficient but safe)
            try:
                playlist_info = self.yt.get_playlist(playlist_id, limit=5)
                title = playlist_info['title']
            except:
                title = f"Playlist_{playlist_id}"

        
        # Sort logic
        # Key: Artist (lowercase) -> Title (lowercase)
        def sort_key(track):
            artist_list = track.get('artists', [])
            artist = artist_list[0]['name'].lower() if artist_list else ""
            title = track.get('title', '').lower()
            return (artist, title)

        sorted_tracks = sorted(tracks, key=sort_key)
        sorted_video_ids = [t['videoId'] for t in sorted_tracks if t.get('videoId')]
        
        # logger.info(f"Preparing to add {len(sorted_video_ids)} tracks to sorted playlist.")

        if create_copy:
            new_title = f"{title} [Sorted]"
            try:
                # print(f"Creating new playlist: {new_title}")
                pass
            except UnicodeEncodeError:
                # print(f"Creating new playlist: {new_title.encode('ascii', 'ignore').decode('ascii')}")
                pass
            
            try:
                new_pid = self.yt.create_playlist(new_title, f"Sorted version of {title}")
                # print(f"Success! Created {new_title} ({new_pid})")
                
                # Internal API for adding items
                self.add_items_internal_robust(new_pid, sorted_video_ids)
                

                
                return new_pid
            except Exception as e:
                print(f"Failed to create/populate playlist: {e}")
        else:
            # In-place sort (Dangerous / Slow)
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