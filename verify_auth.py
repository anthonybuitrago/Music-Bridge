from ytmusicapi import YTMusic
import json
import os
import traceback

def verify_auth():
    print(f"CWD: {os.getcwd()}")
    file_path = 'headers_auth.json'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            headers = json.load(f)
            
        print("JSON load successful. Initializing YTMusic...")
        yt = YTMusic(auth=headers)
        
        print("YTMusic initialized. Attempting search...")
        # Try search first, it's usually more robust
        results = yt.search("test")
        print(f"Search successful! Found {len(results)} results.")
        
        print("Attempting to fetch library playlists...")
        playlists = yt.get_library_playlists(limit=5)
        print("Authentication Successful!")
        print(f"Found {len(playlists)} playlists.")
        for p in playlists:
            print(f"- {p['title']} (ID: {p['playlistId']})")
            
    except Exception:
        print("Authentication Failed!")
        traceback.print_exc()

if __name__ == "__main__":
    verify_auth()
