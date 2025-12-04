from sorter import PlaylistManager
from db_manager import DBManager
import time

def scan_library(progress_callback=None):
    pm = PlaylistManager()
    db = DBManager()
    
    print("Fetching playlists from YouTube Music...")
    if progress_callback:
        progress_callback(0, 0, "Fetching playlists...")
        
    playlists = pm.get_my_playlists()
    
    # Filter out system playlists (Liked Music, Episodes for Later)
    # IDs: LM = Liked Music, SE = Episodes for Later
    ignored_ids = ['LM', 'SE']
    valid_playlists = [p for p in playlists if p['playlistId'] not in ignored_ids]
    
    total = len(valid_playlists)
    print(f"Found {total} user playlists (filtered system lists).")
    
    # --- SYNC DELETIONS ---
    # Get all local IDs
    db.cursor.execute("SELECT id FROM playlists")
    local_ids = {row[0] for row in db.cursor.fetchall()}
    remote_ids = {p['playlistId'] for p in valid_playlists}
    
    # Find IDs to delete (Local - Remote)
    to_delete = local_ids - remote_ids
    if to_delete:
        print(f"Found {len(to_delete)} stale playlists to remove.")
        for pid in to_delete:
            print(f"Removing stale playlist: {pid}")
            db.cursor.execute("DELETE FROM playlists WHERE id = ?", (pid,))
            db.cursor.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pid,))
        db.conn.commit()
    # ----------------------

    for i, p in enumerate(valid_playlists):
        title = p['title']
        pid = p['playlistId']
        count = p.get('count', 0) # Track count from YT metadata
        
        msg = f"Scanning: {title}..."
        try:
            print(f"[{i+1}/{total}] {msg}")
        except UnicodeEncodeError:
            safe_title = title.encode('ascii', 'ignore').decode('ascii')
            print(f"[{i+1}/{total}] Scanning: {safe_title}...")
        if progress_callback:
            progress_callback(i+1, total, msg)
            
        # Add/Update Playlist Info
        # We pass 'count' to store it in DB
        db.add_playlist(pid, title, p.get('description', ''), count)
        
        # Fetch Tracks
        try:
            tracks = pm.get_playlist_tracks(pid)
            
            # Add Tracks to DB
            # Add Tracks to DB
            for t in tracks:
                # DBManager.add_track(track_data, playlist_id)
                db.add_track(t, pid)
        except Exception as e:
            try:
                print(f"Error scanning tracks for {title}: {e}")
            except UnicodeEncodeError:
                safe_title = title.encode('ascii', 'ignore').decode('ascii')
                print(f"Error scanning tracks for {safe_title}: {e}")
            
        time.sleep(0.5) # Be nice to API
            
    print("Scan complete.")
    if progress_callback:
        progress_callback(total, total, "Library Scan Completed.")
        
    db.close()

if __name__ == "__main__":
    scan_library()
