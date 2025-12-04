from db_manager import DBManager
from sorter import PlaylistManager
import time

def create_smart_playlist(name, rule_type, rule_value, progress_callback=None):
    """
    rule_type: 'artist', 'title_contains', 'duration_lt', 'duration_gt'
    """
    print(f"=== CREATING SMART PLAYLIST: {name} ===")
    
    db = DBManager()
    pm = PlaylistManager()
    
    if progress_callback:
        progress_callback(0, 0, "Querying Database...")
        
    # 1. Find Tracks
    tracks = []
    
    if rule_type == 'artist':
        # Exact match or contains? Let's do case-insensitive contains for friendliness
        db.cursor.execute("SELECT video_id, title, artist FROM tracks WHERE artist LIKE ?", (f"%{rule_value}%",))
        tracks = db.cursor.fetchall()
        
    elif rule_type == 'title_contains':
        db.cursor.execute("SELECT video_id, title, artist FROM tracks WHERE title LIKE ?", (f"%{rule_value}%",))
        tracks = db.cursor.fetchall()
        
    # Add more rules as needed
    
    total_tracks = len(tracks)
    print(f"Found {total_tracks} tracks matching rule: {rule_type}='{rule_value}'")
    
    if not tracks:
        print("No tracks found. Aborting.")
        if progress_callback:
            progress_callback(0, 0, "No tracks found matching criteria.")
        return

    # 2. Create Playlist
    if progress_callback:
        progress_callback(0, total_tracks, f"Creating Playlist '{name}'...")
        
    try:
        pid = pm.create_playlist(name, f"Smart Playlist: {rule_type} = {rule_value}")
        print(f"Created playlist {pid}")
        
        # 3. Add Tracks
        video_ids = [t[0] for t in tracks]
        # Remove duplicates from list just in case
        video_ids = list(set(video_ids))
        
        print(f"Adding {len(video_ids)} unique tracks...")
        if progress_callback:
            progress_callback(50, 100, "Adding tracks...")
            
        pm.add_tracks(pid, video_ids)
        print("Done!")
        
        if progress_callback:
            progress_callback(100, 100, "Smart Playlist Created!")
            
    except Exception as e:
        print(f"Error: {e}")
        
    db.close()
