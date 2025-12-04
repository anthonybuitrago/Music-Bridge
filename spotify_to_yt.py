from spotify_manager import SpotifyManager
from sorter import PlaylistManager
import json
import time

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def sync_spotify_to_yt(spotify_playlist_url, progress_callback=None):
    print("=== STARTING REVERSE SYNC (Spotify -> YouTube) ===")
    
    config = load_config()
    spotify_config = config['spotify']
    
    try:
        sp_manager = SpotifyManager(
            spotify_config['client_id'], 
            spotify_config['client_secret'],
            spotify_config['redirect_uri']
        )
        yt_manager = PlaylistManager()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return

    # Extract Playlist ID from URL
    # URL format: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=...
    try:
        sp_pid = spotify_playlist_url.split("/playlist/")[1].split("?")[0]
    except:
        print("Invalid Spotify URL")
        return

    # Get Spotify Tracks
    print(f"Fetching Spotify playlist: {sp_pid}")
    if progress_callback:
        progress_callback(0, 0, "Fetching Spotify tracks...")
        
    sp_tracks = sp_manager.sp.playlist_items(sp_pid)
    sp_info = sp_manager.sp.playlist(sp_pid)
    playlist_name = sp_info['name']
    
    tracks_to_find = []
    for item in sp_tracks['items']:
        track = item['track']
        if track:
            name = track['name']
            artist = track['artists'][0]['name']
            tracks_to_find.append((artist, name))
            
    total_tracks = len(tracks_to_find)
    print(f"Found {total_tracks} tracks in '{playlist_name}'.")
    
    # Create YT Playlist
    yt_title = f"{playlist_name} [From Spotify]"
    print(f"Creating YouTube playlist: {yt_title}")
    yt_pid = yt_manager.create_playlist(yt_title, f"Imported from Spotify: {spotify_playlist_url}")
    
    found_video_ids = []
    
    for i, (artist, title) in enumerate(tracks_to_find):
        query = f"{artist} - {title}"
        msg = f"Searching: {query}..."
        print(f"[{i+1}/{total_tracks}] {msg}")
        if progress_callback:
            progress_callback(i+1, total_tracks, msg)
            
        # Search on YT Music
        results = yt_manager.yt.search(query, filter="songs", limit=1)
        if results:
            video_id = results[0]['videoId']
            found_video_ids.append(video_id)
        else:
            print(f"  - NOT FOUND: {query}")
            
        time.sleep(0.5) # Rate limit
        
    # Add to YT
    if found_video_ids:
        print(f"Adding {len(found_video_ids)} tracks to YouTube...")
        if progress_callback:
            progress_callback(total_tracks, total_tracks, "Adding tracks to YouTube...")
        yt_manager.add_tracks(yt_pid, found_video_ids)
        print("Done!")
    else:
        print("No tracks found to add.")
        
    if progress_callback:
        progress_callback(total_tracks, total_tracks, "Reverse Sync Complete!")
