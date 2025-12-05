from sorter import PlaylistManager
from db_manager import DBManager
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger_setup import setup_logger

logger = setup_logger()

def fetch_tracks(pm, pid):
    """Helper to fetch tracks in a thread."""
    return pid, pm.get_playlist_tracks(pid)

def scan_library(progress_callback=None, force_update=False):
    pm = PlaylistManager()
    db = DBManager()
    
    # logger.info("Fetching playlists from YouTube Music...")
    if progress_callback:
        progress_callback(0, 0, "Fetching playlists...")
        
    playlists = pm.get_my_playlists()
    
    skipped_count = 0
    result = {'scanned': 0, 'skipped': 0, 'orphans_removed': 0, 'added_songs': {}}
    
    # Filter out system playlists
    ignored_ids = ['LM', 'SE']
    valid_playlists = [p for p in playlists if p['playlistId'] not in ignored_ids]
    
    total = len(valid_playlists)
    # logger.info(f"Found {total} user playlists (filtered system lists).")
    
    # --- SYNC DELETIONS ---
    # (Keep existing deletion logic)
    db.cursor.execute("SELECT id, track_count FROM playlists")
    local_data = {row[0]: row[1] for row in db.cursor.fetchall()}
    local_ids = set(local_data.keys())
    remote_ids = {p['playlistId'] for p in valid_playlists}
    
    to_delete = local_ids - remote_ids
    if to_delete:
        # logger.info(f"Found {len(to_delete)} stale playlists to remove.")
        for pid in to_delete:
            # logger.info(f"Removing stale playlist: {pid}")
            db.cursor.execute("DELETE FROM playlists WHERE id = ?", (pid,))
            db.cursor.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (pid,))
        db.commit()
    # ----------------------

    # Identify playlists to scan vs skip
    to_scan = []
    skipped_count = 0
    
    for i, p in enumerate(valid_playlists):
        title = p['title']
        pid = p['playlistId']
        remote_count = int(p.get('count', 0) if p.get('count') else 0)
        local_count = int(local_data.get(pid, -1))
        
        # Always update metadata
        db.add_playlist(pid, title, p.get('description', ''), remote_count)
        
        if not force_update and local_count == remote_count:
            skipped_count += 1
            msg = f"Skipping: {title} (No changes)"
            # logger.info(f"[{i+1}/{total}] {msg}")
            if progress_callback:
                progress_callback(i+1, total, msg)
        else:
            to_scan.append((i, p))

    # Parallel Scan for the rest
    if to_scan:
        # logger.info(f"Scanning {len(to_scan)} playlists in parallel...")
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            future_to_meta = {
                executor.submit(fetch_tracks, pm, p['playlistId']): (i, p) 
                for i, p in to_scan
            }
            for future in as_completed(future_to_meta):
                i, p = future_to_meta[future]
                title = p['title']
                pid = p['playlistId']
                
                msg = f"📂 {title}"
                # logger.info(msg) # Removed per user request
                
                if progress_callback:
                    progress_callback(i+1, total, msg)
                
                try:
                    _, tracks = future.result()
                    new_tracks_count = 0
                    added_titles = []
                    for t in tracks:
                        if db.add_track(t, pid):
                            new_tracks_count += 1
                            added_titles.append(t.get('title', 'Unknown'))
                    db.commit() # Commit this playlist
                    
                    if new_tracks_count > 0:
                        logger.info(f"✨ Added {new_tracks_count} new tracks to {title}")
                        if 'added_songs' not in result: result['added_songs'] = {}
                        result['added_songs'][title] = added_titles
                        
                except Exception as e:
                    logger.error(f"Error scanning {title}: {e}")

    # --- CLEANUP & EXPORT ---
    # logger.info("Running database cleanup...")
    dt, da = db.cleanup_orphans()
    if dt > 0 or da > 0:
        logger.info(f"Cleaned {dt} orphan tracks and {da} orphan artists.")
        
    # logger.info("Exporting library backup...")
    try:
        import json
        playlists = db.get_all_playlists()
        library_data = {'playlists': []}
        
        for p in playlists:
            tracks = db.get_playlist_tracks(p['id'])
            p['tracks'] = tracks
            library_data['playlists'].append(p)
            
        with open('library_backup.json', 'w', encoding='utf-8') as f:
            json.dump(library_data, f, indent=2, ensure_ascii=False)
        # logger.info("Backup saved to library_backup.json")
    except Exception as e:
        logger.error(f"Backup failed: {e}")
    # ------------------------

    # logger.info("Scan complete.")
    if progress_callback:
        progress_callback(total, total, "Library Scan Completed.")
        
    # Get final stats for report
    db.cursor.execute("SELECT COUNT(*) FROM tracks")
    final_tracks = db.cursor.fetchone()[0]
    
    # Simple heuristic for "new" tracks in this session
    # Ideally we'd sum up new_tracks_count from threads, but threading makes it tricky to share a counter without a lock.
    # For now, let's just return a generic success message.
    # Actually, we can return the skipped count.
    
    result.update({
        'total_playlists': total,
        'skipped': skipped_count,
        'scanned': len(to_scan),
        'orphans_removed': dt
    })
    
    db.close()
    return result

if __name__ == "__main__":
    scan_library()
