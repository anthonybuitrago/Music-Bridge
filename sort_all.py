from sorter import PlaylistManager
import time

def sort_all():
    pm = PlaylistManager()
    
    print("Fetching playlists...")
    playlists = pm.get_my_playlists()
    
    print(f"Found {len(playlists)} playlists. Starting sort...")
    
    for p in playlists:
        title = p['title']
        pid = p['playlistId']
        
        # Skip system lists
        if title == "Liked Music" or title == "Episodes for Later":
            continue
            
        # Skip if it's already a sorted copy (just in case)
        if "[Sorted]" in title:
            print(f"Skipping {title} (Already a sorted copy)")
            continue
            
        try:
            print(f"Sorting '{title}'...")
        except UnicodeEncodeError:
            print(f"Sorting '{title.encode('ascii', 'ignore').decode('ascii')}'...")
            
        try:
            pm.sort_standard(pid, create_copy=True)
            # Sleep to avoid rate limits
            time.sleep(2)
        except Exception as e:
            print(f"Failed to sort {title}: {e}")

    print("\n=== SORTING COMPLETE ===")

if __name__ == "__main__":
    sort_all()
