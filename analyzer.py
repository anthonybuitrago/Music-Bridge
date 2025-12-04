from db_manager import DBManager
import collections

def analyze_library():
    db = DBManager()
    
    print("Analyzing library...")
    
    # 1. Get all artists
    artists = db.get_all_artists()
    print(f"Total unique artists: {len(artists)}")
    
    # 2. Find Split Artists (Artists in > 1 playlist)
    split_artists = []
    artist_locations = {} # Artist -> List of Playlists
    
    for artist in artists:
        playlists = db.get_artist_playlists(artist)
        # Filter out "Shazam" from the count, as it's the source of chaos
        non_shazam_playlists = [p for p in playlists if "Shazam" not in p and "Liked Music" not in p]
        
        if len(non_shazam_playlists) > 1:
            split_artists.append((artist, non_shazam_playlists))
            
        artist_locations[artist] = playlists

    # 3. Analyze Shazam Content
    # Find artists in Shazam that ALREADY exist in other playlists
    shazam_moves = collections.defaultdict(list) # Target Playlist -> List of Artists
    shazam_new_artists = [] # Artists only in Shazam
    
    # Get tracks in Shazam
    db.cursor.execute('''
        SELECT t.artist, t.title 
        FROM tracks t
        JOIN playlist_tracks pt ON t.video_id = pt.video_id
        JOIN playlists p ON pt.playlist_id = p.id
        WHERE p.title LIKE '%Shazam%'
    ''')
    shazam_tracks = db.cursor.fetchall()
    
    for artist, title in shazam_tracks:
        # Where else does this artist exist?
        playlists = artist_locations.get(artist, [])
        targets = [p for p in playlists if "Shazam" not in p and "Liked Music" not in p]
        
        if targets:
            # Propose move to the first target found (usually the main genre list)
            target = targets[0]
            shazam_moves[target].append((artist, title))
        else:
            shazam_new_artists.append((artist, title))

    # Generate Report
    report_lines = []
    report_lines.append("# Library Analysis Report")
    report_lines.append(f"**Total Artists:** {len(artists)}")
    report_lines.append(f"**Shazam Tracks:** {len(shazam_tracks)}\n")
    
    report_lines.append("## 1. Split Artists (Confusion)")
    report_lines.append("> Artists found in multiple genre playlists. Should we unify them?")
    if split_artists:
        for artist, p_list in split_artists:
            report_lines.append(f"- **{artist}**: Found in {', '.join(p_list)}")
    else:
        report_lines.append("*None found! Your genre lists are very clean.*")
        
    report_lines.append("\n## 2. Shazam Cleanup Proposal")
    report_lines.append("> Based on your existing library, here is where I can move Shazam tracks automatically:")
    
    total_moves = 0
    for target, items in shazam_moves.items():
        unique_artists = len(set(i[0] for i in items))
        count = len(items)
        total_moves += count
        report_lines.append(f"- **Move to '{target}'**: {count} tracks ({unique_artists} artists)")
        # report_lines.append(f"  - Examples: {items[0][0]} - {items[0][1]}, ...")

    report_lines.append(f"\n**Total Automatic Moves:** {total_moves} tracks.")
    
    report_lines.append("\n## 3. The Leftovers (New Artists)")
    report_lines.append(f"> There are **{len(shazam_new_artists)} tracks** in Shazam from artists you don't have anywhere else.")
    report_lines.append("Since I don't know their genre, I propose moving them to a new playlist called **'Inbox / To Sort'** so you can empty Shazam.")
    report_lines.append("\n### Top New Artists in Shazam:")
    
    # Count most frequent new artists
    new_artist_counts = collections.Counter([i[0] for i in shazam_new_artists])
    for artist, count in new_artist_counts.most_common(10):
        report_lines.append(f"- **{artist}**: {count} tracks")

    # Write Report
    with open("library_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    print("Report generated: library_report.md")
    db.close()

if __name__ == "__main__":
    analyze_library()
