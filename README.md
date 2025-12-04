# 🎵 YT Music Architect

**Organize, Sort, and Sync your YouTube Music library with Spotify.**

This tool allows you to take control of your music library by applying advanced sorting logic, deduplication, and cross-platform synchronization.

## 🚀 Features

*   **Smart Sorter**: Automatically moves songs from a "Catch-all" playlist (like Shazam) to specific Genre playlists based on your existing artist library.
*   **Inbox System**: Moves unidentified songs to an "Inbox" for manual review, keeping your main library clean.
*   **Alphabetical Sort**: Sorts all your playlists by **Artist -> Title**.
*   **Spotify Sync**: Clones your organized YouTube Music playlists to Spotify, ensuring your library is identical on both platforms.
*   **Deduplication**: Removes duplicate tracks to save space and sanity.

## 🛠️ Installation

1.  **Clone the repo**
    ```bash
    git clone https://github.com/yourusername/yt-music-architect.git
    cd yt-music-architect
    ```

2.  **Install Dependencies**
    ```bash
    pip install ytmusicapi spotipy
    ```

3.  **Setup Authentication**
    *   **YouTube Music**: Follow the `ytmusicapi` instructions to get your headers.
    *   **Spotify**: Create an App in the Spotify Developer Dashboard and get your Client ID/Secret.

4.  **Configuration**
    *   Copy `config.json.example` to `config.json`.
    *   Fill in your Spotify credentials and YouTube user name.
    *   Customize playlist names if desired.

## 📖 Usage

1.  **Scan your Library**
    ```bash
    python scanner.py
    ```
2.  **Analyze & Reorganize**
    ```bash
    python reorganizer.py
    ```
3.  **Sync to Spotify**
    ```bash
    python sync_engine.py
    ```

## ⚠️ Disclaimer
This tool performs **destructive actions** (deleting playlists, moving songs). Always back up your library or run in a test environment first.
