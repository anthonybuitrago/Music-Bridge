import sqlite3
import os

class DBManager:
    def __init__(self, db_path='music_library.db'):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.connect()
        self.init_db()

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def init_db(self):
        # Tracks table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracks (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                artist TEXT,
                album TEXT,
                duration TEXT,
                is_explicit BOOLEAN
            )
        ''')
        
        # Playlist_Tracks table (Many-to-Many relationship)
        # Because a track can be in multiple playlists
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id TEXT,
                video_id TEXT,
                set_video_id TEXT, -- Unique ID in the playlist
                added_by TEXT,
                FOREIGN KEY(video_id) REFERENCES tracks(video_id)
            )
        ''')
        
        # Ensure Unique Constraint (Prevent Duplicates)
        try:
            self.cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_playlist_tracks_unique 
                ON playlist_tracks(playlist_id, video_id)
            ''')
        except sqlite3.Error:
            # This might fail if duplicates already exist. 
            # We'll ignore it here; the user must run the "Fix Issues" tool to clean up first.
            pass

        # Playlists table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                track_count INTEGER
            )
        ''')
        # Artists table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
            )
        ''')

        # Track_Artists table (Many-to-Many)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS track_artists (
                track_id TEXT,
                artist_id INTEGER,
                FOREIGN KEY(track_id) REFERENCES tracks(video_id),
                FOREIGN KEY(artist_id) REFERENCES artists(id),
                UNIQUE(track_id, artist_id)
            )
        ''')

        # FTS5 Virtual Table for Fast Search
        self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts USING fts5(
                title, 
                artist, 
                album, 
                content='tracks', 
                content_rowid='rowid'
            )
        ''')

        # Triggers to keep FTS in sync
        self.cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS tracks_ai AFTER INSERT ON tracks BEGIN
                INSERT INTO tracks_fts(rowid, title, artist, album) VALUES (new.rowid, new.title, new.artist, new.album);
            END;
        ''')
        self.cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS tracks_ad AFTER DELETE ON tracks BEGIN
                INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album) VALUES('delete', old.rowid, old.title, old.artist, old.album);
            END;
        ''')
        self.cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS tracks_au AFTER UPDATE ON tracks BEGIN
                INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album) VALUES('delete', old.rowid, old.title, old.artist, old.album);
                INSERT INTO tracks_fts(rowid, title, artist, album) VALUES (new.rowid, new.title, new.artist, new.album);
            END;
        ''')
        
        self.conn.commit()

    def add_playlist(self, pid, title, description, count):
        self.cursor.execute('''
            INSERT OR REPLACE INTO playlists (id, title, description, track_count)
            VALUES (?, ?, ?, ?)
        ''', (pid, title, description, count))
        # Commit is now handled manually for batch performance

    def add_track(self, track_data, playlist_id):
        """
        track_data: dict from ytmusicapi
        """
        video_id = track_data.get('videoId')
        if not video_id:
            return # Skip tracks without ID (uploads/local files might be tricky)

        title = track_data.get('title', '')
        artists_list = track_data.get('artists', [])
        
        # Join all artists for the denormalized column (Compatibility)
        if isinstance(artists_list, list):
            artist_name = ", ".join([a['name'] for a in artists_list])
        else:
            artist_name = str(artists_list) if artists_list else "Unknown"
            # If artists is not a list, try to make it one for normalization
            if artists_list:
                artists_list = [{'name': str(artists_list)}]
            
        album = track_data.get('album', {}).get('name') if track_data.get('album') else None
        duration = track_data.get('duration')
        is_explicit = track_data.get('isExplicit', False)
        set_video_id = track_data.get('setVideoId')

        # Insert Track (Ignore if exists, maybe update?)
        self.cursor.execute('''
            INSERT OR IGNORE INTO tracks (video_id, title, artist, album, duration, is_explicit)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (video_id, title, artist_name, album, duration, is_explicit))
        
        is_new = self.cursor.rowcount > 0

        # Link to Playlist
        self.cursor.execute('''
            INSERT OR REPLACE INTO playlist_tracks (playlist_id, video_id, set_video_id, added_by)
            VALUES (?, ?, ?, ?)
        ''', (playlist_id, video_id, set_video_id, "User"))
        
        # --- Artist Normalization ---
        for artist in artists_list:
            name = artist.get('name')
            if not name: continue
            
            # Insert Artist
            self.cursor.execute('INSERT OR IGNORE INTO artists (name) VALUES (?)', (name,))
            
            # Get Artist ID
            self.cursor.execute('SELECT id FROM artists WHERE name = ?', (name,))
            artist_id = self.cursor.fetchone()[0]
            
            # Link Track to Artist
            self.cursor.execute('''
                INSERT OR IGNORE INTO track_artists (track_id, artist_id)
                VALUES (?, ?)
            ''', (video_id, artist_id))
        # ----------------------------
        
        return is_new
        
    def commit(self):
        """Explicitly commit changes to the database."""
        if self.conn:
            self.conn.commit()

    def get_all_artists(self):
        self.cursor.execute('SELECT DISTINCT artist FROM tracks ORDER BY artist')
        return [r[0] for r in self.cursor.fetchall()]

    def get_artist_playlists(self, artist):
        """Returns which playlists an artist appears in."""
        self.cursor.execute('''
            SELECT DISTINCT p.title 
            FROM playlists p
            JOIN playlist_tracks pt ON p.id = pt.playlist_id
            JOIN tracks t ON pt.video_id = t.video_id
            WHERE t.artist = ?
        ''', (artist,))
        return [r[0] for r in self.cursor.fetchall()]

    def get_all_playlists(self):
        """Returns all playlists stored in the DB."""
        self.cursor.execute('SELECT id, title, description FROM playlists')
        return [{'id': r[0], 'title': r[1], 'description': r[2]} for r in self.cursor.fetchall()]

    def get_playlist_tracks(self, playlist_id):
        """Returns all video_ids for a playlist, ordered by insertion (rowid)."""
        self.cursor.execute('''
            SELECT video_id 
            FROM playlist_tracks 
            WHERE playlist_id = ? 
            ORDER BY rowid
        ''', (playlist_id,))
        return [r[0] for r in self.cursor.fetchall()]

    def search_tracks(self, query):
        """Fast full-text search using FTS5."""
        # Escape double quotes to prevent syntax errors
        safe_query = query.replace('"', '""')
        # FTS5 query syntax: match full phrase or prefix
        fts_query = f'"{safe_query}"*' 
        
        self.cursor.execute('''
            SELECT rowid, title, artist, album 
            FROM tracks_fts 
            WHERE tracks_fts MATCH ? 
            ORDER BY rank 
            LIMIT 50
        ''', (fts_query,))
        return [{'id': r[0], 'title': r[1], 'artist': r[2], 'album': r[3]} for r in self.cursor.fetchall()]

    def cleanup_orphans(self):
        """Removes tracks and artists not linked to anything."""
        # Delete orphan tracks (not in any playlist)
        self.cursor.execute('''
            DELETE FROM tracks 
            WHERE video_id NOT IN (SELECT DISTINCT video_id FROM playlist_tracks)
        ''')
        deleted_tracks = self.cursor.rowcount
        
        # Delete orphan artists (not linked to any track)
        self.cursor.execute('''
            DELETE FROM artists 
            WHERE id NOT IN (SELECT DISTINCT artist_id FROM track_artists)
        ''')
        deleted_artists = self.cursor.rowcount
        
        self.conn.commit()
        return deleted_tracks, deleted_artists

    def get_global_duplicates(self):
        """
        Finds tracks that exist in more than one playlist.
        Returns a list of dicts:
        [{
            'video_id': '...',
            'title': '...',
            'artist': '...',
            'playlists': [{'id': '...', 'title': '...'}, ...]
        }, ...]
        """
        # Find video_ids with > 1 playlist
        self.cursor.execute('''
            SELECT video_id, COUNT(DISTINCT playlist_id) as cnt
            FROM playlist_tracks
            GROUP BY video_id
            HAVING cnt > 1
        ''')
        duplicate_ids = [row[0] for row in self.cursor.fetchall()]
        
        results = []
        for vid in duplicate_ids:
            # Get track info
            self.cursor.execute("SELECT title, artist FROM tracks WHERE video_id = ?", (vid,))
            track_info = self.cursor.fetchone()
            if not track_info: continue
            
            # Get playlists (Unique)
            self.cursor.execute('''
                SELECT DISTINCT p.id, p.title 
                FROM playlists p
                JOIN playlist_tracks pt ON p.id = pt.playlist_id
                WHERE pt.video_id = ?
            ''', (vid,))
            playlists = [{'id': r[0], 'title': r[1]} for r in self.cursor.fetchall()]
            
            results.append({
                'video_id': vid,
                'title': track_info[0],
                'artist': track_info[1],
                'playlists': playlists
            })
            
        return results

    def remove_local_duplicates(self):
        """
        Removes duplicate entries from playlist_tracks table.
        Keeps only the instance with the lowest rowid (first added).
        """
        self.cursor.execute('''
            DELETE FROM playlist_tracks 
            WHERE rowid NOT IN (
                SELECT MIN(rowid) 
                FROM playlist_tracks 
                GROUP BY playlist_id, video_id
            )
        ''')
        removed = self.cursor.rowcount
        
        # Now that duplicates are gone, enforce the constraint permanently
        try:
            self.cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_playlist_tracks_unique 
                ON playlist_tracks(playlist_id, video_id)
            ''')
        except Exception as e:
            print(f"Warning: Could not create unique index: {e}")
            
        self.conn.commit()
        return removed


    def close(self):
        if self.conn:
            self.conn.close()
