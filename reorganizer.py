from sorter import PlaylistManager
from db_manager import DBManager
import time

def reorganize_library():
    pm = PlaylistManager()
    db = DBManager()
    
    print("=== STARTING REORGANIZATION ===")
    
    # 1. Identify Playlists
    playlists = pm.get_my_playlists()
    shazam_playlist = next((p for p in playlists if "Shazam" in p['title']), None)
    
    if not shazam_playlist:
        print("Shazam playlist not found! Aborting.")
        return

    shazam_id = shazam_playlist['playlistId']
    print(f"Found Shazam: {shazam_id}")

    # 2. Calculate Moves (Same logic as Analyzer)
    print("Calculating moves...")
    artists = db.get_all_artists()
    artist_locations = {}
    for artist in artists:
        p_list = db.get_artist_playlists(artist)
        # Filter out Shazam and Liked Music for targets
        targets = [p for p in p_list if "Shazam" not in p and "Liked Music" not in p]
        if targets:
            artist_locations[artist] = targets[0] # Pick first valid target

    # Get Shazam Tracks from DB
    db.cursor.execute('''
        SELECT t.video_id, t.artist, t.title 
        FROM tracks t
        JOIN playlist_tracks pt ON t.video_id = pt.video_id
        WHERE pt.playlist_id = ?
    ''', (shazam_id,))
    shazam_tracks = db.cursor.fetchall()
    
    moves = {} # Target Playlist Name -> List of Video IDs
    inbox_tracks = [] # List of Video IDs for Inbox
    
    print(f"Processing {len(shazam_tracks)} tracks from Shazam...")
    
    for video_id, artist, title in shazam_tracks:
        target_playlist_name = artist_locations.get(artist)
        
        if target_playlist_name:
            if target_playlist_name not in moves:
                moves[target_playlist_name] = []
            moves[target_playlist_name].append(video_id)
        else:
            inbox_tracks.append(video_id)

    # 3. Execute Moves to Existing Playlists
    # We need a map of Name -> ID for targets
    playlist_map = {p['title']: p['playlistId'] for p in playlists}
    
    for target_name, video_ids in moves.items():
        target_id = playlist_map.get(target_name)
        if target_id:
            try:
                print(f"Moving {len(video_ids)} tracks to '{target_name}'...")
            except UnicodeEncodeError:
                print(f"Moving {len(video_ids)} tracks to '{target_name.encode('ascii', 'ignore').decode('ascii')}'...")
            
            try:
                # Add in batches of 50 just to be safe
                for i in range(0, len(video_ids), 50):
                    batch = video_ids[i:i+50]
                    pm.add_tracks(target_id, batch)
                    time.sleep(0.5)
            except Exception as e:
                print(f"Failed to move to {target_name}: {e}")
        else:
            print(f"Warning: Target playlist '{target_name}' not found in current library.")

    # 4. Create Inbox and Move Leftovers
    if inbox_tracks:
        print(f"Moving {len(inbox_tracks)} tracks to 'Inbox / Por Clasificar'...")
        try:
            inbox_id = pm.create_playlist("Inbox / Por Clasificar", "Canciones de Shazam sin clasificar")
            print(f"Created Inbox: {inbox_id}")
            
            for i in range(0, len(inbox_tracks), 50):
                batch = inbox_tracks[i:i+50]
                pm.add_tracks(inbox_id, batch)
                time.sleep(0.5)
        except Exception as e:
            print(f"Failed to create/fill Inbox: {e}")

    # 5. Delete Shazam
    print("Deleting original Shazam playlist...")
    try:
        pm.yt.delete_playlist(shazam_id)
        print("Shazam deleted.")
    except Exception as e:
        print(f"Failed to delete Shazam: {e}")

    # 6. Create Sorted Copies of EVERYTHING
    print("\n=== CREATING SORTED COPIES ===")
    # Refresh playlist list because we added Inbox and deleted Shazam
    time.sleep(2)
    current_playlists = pm.get_my_playlists()
    
    for p in current_playlists:
        title = p['title']
        pid = p['playlistId']
        
        # Skip Liked Music (Read-only usually) and already sorted ones
        if title == "Liked Music" or "[Sorted]" in title:
            continue
            
        try:
            print(f"Sorting '{title}'...")
        except UnicodeEncodeError:
            print(f"Sorting '{title.encode('ascii', 'ignore').decode('ascii')}'...")
            
        try:
            pm.sort_standard(pid, create_copy=True)
        except Exception as e:
            print(f"Failed to sort {title}: {e}")

    print("\n=== REORGANIZATION COMPLETE ===")
    db.close()

if __name__ == "__main__":
    reorganize_library()
