import argparse
import sys
import time
import os
from scanner import scan_library
from sorter import PlaylistManager
from sync_engine import SyncEngine

def progress_reporter(current, total, message):
    """Callback for progress updates"""
    percent = int((current / total) * 100) if total > 0 else 0
    # Clear line with whitespace padding
    sys.stdout.write(f"\r[{percent}%] {message[:60]:<60}")
    sys.stdout.flush()

def handle_scan(args):
    # No progress callback to avoid noise, user wants minimal output
    try:
        # Determine strict or normal scan
        # We pass None as progress_callback to keep it silent
        result = scan_library(progress_callback=None, force_update=args.force)
        
        if result.get('error') == 'NO_PLAYLISTS_FOUND':
            print("\n❌ Error: No playlists found.")
            print("⚠️  Safety abort triggered to prevent database wipe.")
            print("👉 Please update your 'headers_auth.json' with fresh headers.")
            return

        # Calculate total new songs
        total_new = 0
        if result.get('added_songs'):
            for songs in result['added_songs'].values():
                total_new += len(songs)
                
        # Final minimal output as requested
        found = result.get('found_playlists', [])
        print(f"Playlists Found ({result.get('total_playlists', 0)}):")
        for p in found:
            print(f" - {p}")

        print(f"\nNew Songs ({total_new}):")
        if total_new > 0 and result.get('added_songs'):
            for pl_name, songs in result['added_songs'].items():
                for s in songs:
                    print(f" - {pl_name}: {s}")
        else:
            print(" (None)")
            
    except Exception as e:
        print(f"\nError: {e}")

def handle_sort(args):
    pm = PlaylistManager()
    playlists = pm.get_my_playlists()
    
    # Filter system playlists
    valid_playlists = [p for p in playlists if p['playlistId'] not in ['LM', 'SE'] and not p['title'].endswith('[Sorted]')]
    
    # --- New Song Calculation (From Last Scan) ---
    import json
    import os
    scan_status = {}
    try:
        if os.path.exists('scan_status.json'):
            with open('scan_status.json', 'r', encoding='utf-8') as f:
                scan_status = json.load(f)
    except:
        pass

    for p in valid_playlists:
        # Check if this playlist had new songs in last scan
        # scan_status uses Playlist Names as keys
        if p['title'] in scan_status:
            p['new_count'] = scan_status[p['title']]
        else:
            p['new_count'] = 0
    # ---------------------------

    if args.all:
        print(f"📂 Sorting ALL {len(valid_playlists)} playlists...")
        import time 
        total = len(valid_playlists)
        bar_length = 20

        for i, p in enumerate(valid_playlists):
            # Calculate progress
            percent = (i / total) 
            filled_length = int(bar_length * percent)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            # Print bar with current playlist name
            sys.stdout.write(f"\rSorting: [{bar}] {int(percent * 100)}% - {p['title'][:30]:<30}")
            sys.stdout.flush()

            try:
                # Suppress prints from sorter by capturing stdout if needed, or rely on logic removal
                # Since we cleaned sorter interaction, it should be quiet.
                pm.sort_standard(p['playlistId'], title_hint=p['title'], create_copy=not args.in_place)
                time.sleep(2) 
            except Exception as e:
                # Move to new line to show error, then continue progress bar on next line
                sys.stdout.write(f"\n❌ Failed to sort {p['title']}: {e}\n")
        
        # Final 100% bar
        sys.stdout.write(f"\rSorting: [{'█' * bar_length}] 100% - Done!{' '*30}\n")
        print("✅ Batch Sort Complete.")
        return

    # Interactive selection if no specific arg (or if we add a --name filter later)
    print("\n--- 📂 Available Playlists ---")
    for i, p in enumerate(valid_playlists, 1):
        indicator = ""
        if p.get('new_count', 0) > 0:
            indicator = f" [+{p['new_count']} songs]"
        print(f"{i}. {p['title']}{indicator}")
        
    choice = input("\nSelect playlist number to sort (or 'a' for all): ")
    if choice.lower() in ['a', 'all']:
        # Recursive call with all=True
        args.all = True
        handle_sort(args)
        return
        
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(valid_playlists):
            target = valid_playlists[idx]
            
            # Simple text output as requested
            new_title = f"{target['title']} [Sorted]"
            # print(f"Sorting '{target['title']}'...") # Optional: User wanted minimal
            
            pm.sort_standard(target['playlistId'], title_hint=target['title'], create_copy=not args.in_place)
            
            print(f"Creating new playlist: {new_title}") # Validated confirmation
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

def handle_sync(args):
    engine = SyncEngine()
    print("🔄 YouTube Music -> Spotify Sync")
    
    # 1. Fetch YT Playlists
    yt_pl, _ = engine.get_playlists()
    
    # Filter
    ignored_titles = ["Your Likes", "Liked Songs", "Liked Music", "Watch Later", "Episodes for Later"]
    yt_pl = [p for p in yt_pl if p['title'] not in ignored_titles]
    
    if args.all:
        print(f"🚀 Syncing ALL {len(yt_pl)} playlists to Spotify...")
        for i, p in enumerate(yt_pl):
            msg = f"Syncing {p['title']}..."
            print(f"\n[{i+1}/{len(yt_pl)}] {msg}")
            try:
                engine.sync_to_spotify(p['playlistId'], smart=True, progress_callback=progress_reporter)
            except Exception as e:
                print(f"\n❌ Failed: {e}")
        print("\n\n✅ Batch Sync Complete.")
        return

    # Interactive
    print("\n--- Available YouTube Playlists ---")
    for i, p in enumerate(yt_pl, 1):
        print(f"{i}. {p['title']}")
        
    choice = input("\nSelect playlist number to sync to Spotify (or 'a' for all): ")
    if choice.lower() == 'a':
        args.all = True
        handle_sync(args)
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(yt_pl):
            target = yt_pl[idx]
            print(f"\nSyncing '{target['title']}' to Spotify...")
            engine.sync_to_spotify(target['playlistId'], smart=True, progress_callback=progress_reporter)
            print("\n\n✅ Sync Finished.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

def main():
    parser = argparse.ArgumentParser(description="MusicBridge CLI Tool 🎵")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # SCAN
    parser_scan = subparsers.add_parser('scan', help='Scan library for new tracks')
    parser_scan.add_argument('--force', action='store_true', help='Force full metadata refresh')

    # SORT
    parser_sort = subparsers.add_parser('sort', help='Sort playlists (Artist -> Title)')
    parser_sort.add_argument('--all', action='store_true', help='Sort ALL playlists automatically')
    parser_sort.add_argument('--in-place', action='store_true', help='Sort in-place (DANGEROUS: overwrites original). Default is to create a copy.')

    # SYNC
    parser_sync = subparsers.add_parser('sync', help='Sync YouTube playlists to Spotify')
    parser_sync.add_argument('--all', action='store_true', help='Sync ALL playlists automatically')

    args = parser.parse_args()

    if args.command == 'scan':
        handle_scan(args)
    elif args.command == 'sort':
        handle_sort(args)
    elif args.command == 'sync':
        handle_sync(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
