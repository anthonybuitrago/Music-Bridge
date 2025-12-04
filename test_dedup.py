from sorter import PlaylistManager
import time
import json

def test_deduplication():
    pm = PlaylistManager()
    
    print("Searching for a valid song...")
    search_results = pm.yt.search("Never Gonna Give You Up", filter="songs")
    if not search_results:
        print("Error: Could not find any songs.")
        return
    
    video_id = search_results[0]['videoId']
    print(f"Found song: {search_results[0]['title']} ({video_id})")
    
    print("Creating test playlist with tracks...")
    try:
        # Create with duplicates initially
        playlist_id = pm.yt.create_playlist("Test Deduplication Atomic", "Temporary playlist", video_ids=[video_id, video_id])
        print(f"Created playlist: {playlist_id}")
    except Exception as e:
        print(f"Failed to create playlist: {e}")
        return
    
    print("Waiting 5 seconds for propagation...")
    time.sleep(5)
    
    # Verify count
    print("Fetching tracks...")
    try:
        tracks = pm.get_playlist_tracks(playlist_id)
        print(f"Tracks before dedup: {len(tracks)}")
    except Exception as e:
        print(f"Failed to get tracks: {e}")
        return

    if len(tracks) != 2:
        print("Error: Failed to add duplicates (count mismatch).")
        # Continue anyway

    # Run deduplication
    print("Running deduplication...")
    try:
        pm.deduplicate_playlist(playlist_id)
    except Exception as e:
        print(f"Deduplication failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Verify count
    time.sleep(5)
    
    try:
        tracks = pm.get_playlist_tracks(playlist_id)
        print(f"Tracks after dedup: {len(tracks)}")
        
        if len(tracks) == 1:
            print("SUCCESS: Deduplication worked!")
        else:
            print("FAILURE: Duplicates still exist.")
    except Exception as e:
        print(f"Failed to verify: {e}")
        
    # Cleanup
    print("Cleaning up...")
    try:
        pm.yt.delete_playlist(playlist_id)
        print("Playlist deleted.")
    except Exception as e:
        print(f"Failed to delete playlist: {e}")

if __name__ == "__main__":
    test_deduplication()
