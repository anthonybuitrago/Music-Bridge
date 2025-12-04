from sorter import PlaylistManager
from db_manager import DBManager
import time

def scan_library():
    pm = PlaylistManager()
    db = DBManager()
    
    print("Fetching playlists...")
    playlists = pm.get_my_playlists()
    
    total_playlists = len(playlists)
    print(f"Found {total_playlists} playlists. Starting scan...")
    
    for i, p in enumerate(playlists):
        pid = p['playlistId']
        title = p['title']
        
        # Skip the "[Sorted]" ones to avoid pollution?
        # Or maybe we want to scan them to compare?
        # Let's skip them for now to get the "Raw" state.
        if "[Sorted]" in title:
            print(f"Skipping {title} (Sorted copy)")
            continue
            
        try:
            print(f"[{i+1}/{total_playlists}] Scanning: {title}...")
        except UnicodeEncodeError:
            print(f"[{i+1}/{total_playlists}] Scanning: {title.encode('ascii', 'ignore').decode('ascii')}...")
        
        # Update Playlist Info in DB
        db.add_playlist(pid, title, p.get('description', ''), p.get('count', 0))
        
        # Fetch Tracks
        try:
            tracks = pm.get_playlist_tracks(pid)
            print(f"  - Found {len(tracks)} tracks.")
            
            for track in tracks:
                db.add_track(track, pid)
                
        except Exception as e:
            print(f"  - Error scanning {title}: {e}")
            
        # Be nice to the API
        time.sleep(1)

    print("Scan complete!")
    db.close()

if __name__ == "__main__":
    scan_library()
