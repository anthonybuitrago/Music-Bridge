from db_manager import DBManager
from sorter import PlaylistManager
import time

def restore_library(progress_callback=None):
    print("=== STARTING LIBRARY RESTORATION ===")
    print("WARNING: This will create new playlists in your YouTube Music account based on the local database.")
    print("You have 5 seconds to cancel (Ctrl+C)...")
    
    if progress_callback:
        progress_callback(0, 0, "Waiting 5s (Safety Delay)...")
    
    time.sleep(5)

    db = DBManager()
    pm = PlaylistManager()

    # 1. Get all playlists from DB
    playlists = db.get_all_playlists()
    total_playlists = len(playlists)
    print(f"Found {total_playlists} playlists in backup.")

    for i, p in enumerate(playlists):
        original_id = p['id']
        title = p['title']
        description = p['description']
        
        # Add a tag to indicate it's a restored playlist
        new_title = f"{title} [Restored]"
        
        msg = f"Restoring: {title}..."
        print(f"\n[{i+1}/{total_playlists}] {msg}")
        
        if progress_callback:
            progress_callback(i+1, total_playlists, msg)
        
        # 2. Get tracks for this playlist
        video_ids = db.get_playlist_tracks(original_id)
        if not video_ids:
            print("  - No tracks found in backup. Skipping.")
            continue
            
        print(f"  - Found {len(video_ids)} tracks.")
        
        # 3. Create new playlist on YouTube
        try:
            new_pid = pm.create_playlist(new_title, description if description else "Restored from backup")
            print(f"  - Created new playlist: {new_title} ({new_pid})")
            
            # 4. Add tracks
            # YTMusic API can handle lists of video IDs
            # But let's do it in chunks if it's too big? 
            # add_playlist_items usually handles it, but let's be safe with chunks of 50 if needed.
            # Actually, the library handles it pretty well.
            
            status = pm.add_tracks(new_pid, video_ids)
            print(f"  - Added tracks. Status: {status}")
            
        except Exception as e:
            print(f"  - FAILED to restore {title}: {e}")
            
        time.sleep(2) # Rate limiting

    print("\n=== RESTORATION COMPLETE ===")
    if progress_callback:
        progress_callback(total_playlists, total_playlists, "Restoration Complete!")
    db.close()

if __name__ == "__main__":
    restore_library()
