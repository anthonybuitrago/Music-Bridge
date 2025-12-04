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

        # Playlists table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                track_count INTEGER
            )
        ''')
        self.conn.commit()

    def add_playlist(self, pid, title, description, count):
        self.cursor.execute('''
            INSERT OR REPLACE INTO playlists (id, title, description, track_count)
            VALUES (?, ?, ?, ?)
        ''', (pid, title, description, count))
        self.conn.commit()

    def add_track(self, track_data, playlist_id):
        """
        track_data: dict from ytmusicapi
        """
        video_id = track_data.get('videoId')
        if not video_id:
            return # Skip tracks without ID (uploads/local files might be tricky)

        title = track_data.get('title', '')
        artists = track_data.get('artists', [])
        # Join all artists
        if isinstance(artists, list):
            artist_name = ", ".join([a['name'] for a in artists])
        else:
            artist_name = str(artists) if artists else "Unknown"
            
        album = track_data.get('album', {}).get('name') if track_data.get('album') else None
        duration = track_data.get('duration')
        is_explicit = track_data.get('isExplicit', False)
        set_video_id = track_data.get('setVideoId')

        # Insert Track (Ignore if exists, maybe update?)
        self.cursor.execute('''
            INSERT OR IGNORE INTO tracks (video_id, title, artist, album, duration, is_explicit)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (video_id, title, artist_name, album, duration, is_explicit))

        # Link to Playlist
        self.cursor.execute('''
            INSERT OR REPLACE INTO playlist_tracks (playlist_id, video_id, set_video_id, added_by)
            VALUES (?, ?, ?, ?)
        ''', (playlist_id, video_id, set_video_id, "User"))
        
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

    def close(self):
        if self.conn:
            self.conn.close()
