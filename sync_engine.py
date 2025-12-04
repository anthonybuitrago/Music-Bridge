from spotify_manager import SpotifyManager
from sorter import PlaylistManager
import time

import json

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

def sync_to_spotify():
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
    
    missing_tracks = [] # (Playlist, Artist, Title)

    for p in yt_playlists:
        title = p['title']
        pid = p['playlistId']
        
        # Only sync the [Sorted] versions to keep it clean?
        # Or sync everything? Let's sync the [Sorted] ones as they are the "Master" lists now.
        if "[Sorted]" not in title:
            continue
            
        # Clean name for Spotify (Remove [Sorted] tag for cleaner look?)
        spotify_title = title.replace(" [Sorted]", "")
        
        try:
            print(f"\nSyncing '{spotify_title}'...")
        except UnicodeEncodeError:
            print(f"\nSyncing '{spotify_title.encode('ascii', 'ignore').decode('ascii')}'...")

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

if __name__ == "__main__":
    sync_to_spotify()
