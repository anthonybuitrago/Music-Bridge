from spotify_manager import SpotifyManager
from sorter import PlaylistManager
import time

import json

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def sync_to_spotify(progress_callback=None):
    print("=== STARTING SPOTIFY SYNC ===")
    
    config = load_config()
    spotify_config = config['spotify']
    
    # 1. Init Managers
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

    # 2. Get YT Playlists
    yt_playlists = yt_manager.get_my_playlists()
    
    # Filter first to get accurate count
    playlists_to_sync = [p for p in yt_playlists if "[Sorted]" in p['title']]
    total_playlists = len(playlists_to_sync)
    
    print(f"Found {total_playlists} sorted playlists to sync.")
    
    missing_tracks = [] # (Playlist, Artist, Title)

    for i, p in enumerate(playlists_to_sync):
        title = p['title']
        pid = p['playlistId']
        
        # Clean name for Spotify (Remove [Sorted] tag for cleaner look?)
        spotify_title = title.replace(" [Sorted]", "")
        
        msg = f"Syncing '{spotify_title}'..."
        try:
            print(f"\n[{i+1}/{total_playlists}] {msg}")
        except UnicodeEncodeError:
            safe_title = spotify_title.encode('ascii', 'ignore').decode('ascii')
            msg = f"Syncing '{safe_title}'..."
            print(f"\n[{i+1}/{total_playlists}] {msg}")

        if progress_callback:
            progress_callback(i+1, total_playlists, msg)

        # Create/Get Spotify Playlist
        sp_playlist_id = sp_manager.create_playlist(spotify_title)
        
        # Get YT Tracks
        yt_tracks = yt_manager.get_playlist_tracks(pid)
        print(f"  - Found {len(yt_tracks)} tracks on YT.")
        
        spotify_uris = []
        
        for track in yt_tracks:
            artist = track['artists'][0]['name'] if track.get('artists') else "Unknown"
            track_title = track['title']
            
            uri = sp_manager.search_track(artist, track_title)
            if uri:
                spotify_uris.append(uri)
                # print(f"    + Found: {artist} - {track_title}")
            else:
                try:
                    print(f"    - MISSING: {artist} - {track_title}")
                except UnicodeEncodeError:
                    safe_artist = artist.encode('ascii', 'ignore').decode('ascii')
                    safe_title = track_title.encode('ascii', 'ignore').decode('ascii')
                    print(f"    - MISSING: {safe_artist} - {safe_title}")
                missing_tracks.append((spotify_title, artist, track_title))
        
        # Add to Spotify (Clean Sync)
        if spotify_uris:
            print(f"  - Syncing {len(spotify_uris)} tracks to Spotify (Overwriting)...")
            sp_manager.replace_tracks_in_playlist(sp_playlist_id, spotify_uris)
        
        time.sleep(1)

    # Report Missing
    if missing_tracks:
        print(f"\n=== SYNC COMPLETE. {len(missing_tracks)} MISSING TRACKS ===")
        with open("missing_on_spotify.md", "w", encoding="utf-8") as f:
            f.write("# Missing Tracks Report\n\n")
            f.write("| Playlist | Artist | Title |\n")
            f.write("| --- | --- | --- |\n")
            for pl, art, tit in missing_tracks:
                f.write(f"| {pl} | {art} | {tit} |\n")
        print("Report saved to missing_on_spotify.md")
    else:
        print("\n=== SYNC COMPLETE. PERFECT MATCH! ===")
    
    if progress_callback:
        progress_callback(total_playlists, total_playlists, "Sync Complete!")

if __name__ == "__main__":
    sync_to_spotify()
