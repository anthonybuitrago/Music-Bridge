import customtkinter as ctk
import sys
import threading
import io
from datetime import datetime

# Import our tools
# We might need to adjust them to be importable without running immediately
# (Most have if __name__ == "__main__", so we are good)
import scanner
import sorter
import sync_engine
import restore_library

class TextRedirector(io.StringIO):
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, str):
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", str)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass

class MusicBridgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MusicBridge v2.0")
        self.geometry("1000x700")

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MusicBridge", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Navigation Buttons
        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="📊 Dashboard", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("dashboard"))
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10)

        self.btn_library = ctk.CTkButton(self.sidebar_frame, text="📚 Library", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("library"))
        self.btn_library.grid(row=2, column=0, padx=20, pady=10)

        self.btn_sync = ctk.CTkButton(self.sidebar_frame, text="🔄 Sync", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("sync"))
        self.btn_sync.grid(row=3, column=0, padx=20, pady=10)
        
        self.btn_tools = ctk.CTkButton(self.sidebar_frame, text="🛠️ Tools", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("tools"))
        self.btn_tools.grid(row=4, column=0, padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="⚙️ Settings", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("settings"))
        self.btn_settings.grid(row=5, column=0, padx=20, pady=10)

        # Main Content Area
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.create_frames()
        
        self.show_frame("dashboard")
        self.center_window()

    def create_frames(self):
        # --- Dashboard Frame ---
        dash = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["dashboard"] = dash
        
        ctk.CTkLabel(dash, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        stats_frame = ctk.CTkFrame(dash)
        stats_frame.pack(pady=10, padx=20, fill="x")
        
        self.lbl_total_tracks = ctk.CTkLabel(stats_frame, text="Total Tracks: Loading...", font=ctk.CTkFont(size=16))
        self.lbl_total_tracks.pack(side="left", padx=20, pady=20)
        
        self.lbl_total_playlists = ctk.CTkLabel(stats_frame, text="Playlists: Loading...", font=ctk.CTkFont(size=16))
        self.lbl_total_playlists.pack(side="left", padx=20, pady=20)
        
        ctk.CTkButton(dash, text="🔄 Refresh Stats", command=self.refresh_stats).pack(pady=10)

        # --- Library Frame (Existing Functionality) ---
        lib = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["library"] = lib
        
        ctk.CTkLabel(lib, text="Library Management", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        # Actions Frame
        btn_frame = ctk.CTkFrame(lib)
        btn_frame.pack(pady=10, fill="x", padx=20)
        
        ctk.CTkLabel(btn_frame, text="Global Actions", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        action_btns = ctk.CTkFrame(btn_frame, fg_color="transparent")
        action_btns.pack(pady=5)
        
        ctk.CTkButton(action_btns, text="🔍 Scan Library", command=self.run_scan).pack(side="left", padx=10)
        ctk.CTkButton(action_btns, text="📂 Sort All", command=self.run_sort).pack(side="left", padx=10)
        ctk.CTkButton(action_btns, text="↩️ Restore Backup", command=self.run_restore, fg_color="transparent", border_width=2).pack(side="left", padx=10)

        # Duplicate Cleaner Section
        cleaner_frame = ctk.CTkFrame(lib)
        cleaner_frame.pack(pady=20, fill="x", padx=20)
        
        ctk.CTkLabel(cleaner_frame, text="Duplicate Cleaner", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.playlist_combo = ctk.CTkComboBox(cleaner_frame, values=["Loading..."], width=300)
        self.playlist_combo.pack(pady=5)
        
        ctk.CTkButton(cleaner_frame, text="🧹 Remove Duplicates", command=self.run_cleaner).pack(pady=5)
        
        # Refresh playlists for combo
        self.after(1000, self.load_playlists_to_combo)

        # Console for Library
        self.console_box = ctk.CTkTextbox(lib, width=700, height=200)
        self.console_box.pack(pady=20, padx=20, fill="both", expand=True)
        self.console_box.configure(state="disabled")
        
        # Progress Bar (Shared)
        self.progress_bar = ctk.CTkProgressBar(lib)
        self.progress_bar.pack(pady=(0, 10), padx=20, fill="x")
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(lib, text="Ready")
        self.status_label.pack(pady=(0, 20))

        # --- Sync Frame ---
        sync = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["sync"] = sync
        ctk.CTkLabel(sync, text="Synchronization", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        # Export
        export_frame = ctk.CTkFrame(sync)
        export_frame.pack(pady=10, fill="x", padx=20)
        ctk.CTkLabel(export_frame, text="Export to Spotify", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        ctk.CTkLabel(export_frame, text="Syncs all [Sorted] playlists to Spotify.").pack(pady=5)
        ctk.CTkButton(export_frame, text="🟢 Start Export", command=self.run_sync).pack(pady=10)
        
        # Import
        import_frame = ctk.CTkFrame(sync)
        import_frame.pack(pady=20, fill="x", padx=20)
        ctk.CTkLabel(import_frame, text="Import from Spotify", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.spotify_url_entry = ctk.CTkEntry(import_frame, placeholder_text="Spotify Playlist URL", width=400)
        self.spotify_url_entry.pack(pady=5)
        
        ctk.CTkButton(import_frame, text="⬇️ Import to YouTube", command=self.run_reverse_sync).pack(pady=10)

        # --- Tools Frame ---
        tools = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["tools"] = tools
        ctk.CTkLabel(tools, text="Tools", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        # Smart Playlist Builder
        sp_frame = ctk.CTkFrame(tools)
        sp_frame.pack(pady=10, fill="x", padx=20)
        ctk.CTkLabel(sp_frame, text="Smart Playlist Builder", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.sp_name = ctk.CTkEntry(sp_frame, placeholder_text="Playlist Name (e.g. 'Rock Mix')")
        self.sp_name.pack(pady=5)
        
        self.sp_type = ctk.CTkComboBox(sp_frame, values=["Artist Name", "Title Contains"])
        self.sp_type.pack(pady=5)
        
        self.sp_value = ctk.CTkEntry(sp_frame, placeholder_text="Value (e.g. 'Linkin Park')")
        self.sp_value.pack(pady=5)
        
        ctk.CTkButton(sp_frame, text="✨ Create Smart Playlist", command=self.run_smart_playlist).pack(pady=10)

        # --- Settings Frame ---
        settings = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["settings"] = settings
        ctk.CTkLabel(settings, text="Settings", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        # Config Editor
        self.config_text = ctk.CTkTextbox(settings, width=600, height=300)
        self.config_text.pack(pady=10)
        try:
            with open("config.json", "r") as f:
                self.config_text.insert("0.0", f.read())
        except:
            self.config_text.insert("0.0", "Error loading config.json")
            
        ctk.CTkButton(settings, text="💾 Save Config", command=self.save_config).pack(pady=10)

        # Redirect stdout (Default to Library console for now)
        sys.stdout = TextRedirector(self.console_box)
        sys.stderr = TextRedirector(self.console_box)

    def show_frame(self, name):
        # Hide all
        for frame in self.frames.values():
            frame.grid_forget()
        # Show selected
        self.frames[name].grid(row=0, column=0, sticky="nsew")
        
        if name == "dashboard":
            self.refresh_stats()

    def refresh_stats(self):
        # Simple stats fetching
        try:
            from db_manager import DBManager
            db = DBManager()
            # We need to add count methods to DBManager or run raw queries
            # For now, raw queries via cursor if possible, or add methods.
            # Let's assume we can add methods later.
            # Hacky way for now:
            db.cursor.execute("SELECT COUNT(*) FROM tracks")
            count_tracks = db.cursor.fetchone()[0]
            db.cursor.execute("SELECT COUNT(*) FROM playlists")
            count_playlists = db.cursor.fetchone()[0]
            db.close()
            
            self.lbl_total_tracks.configure(text=f"Total Tracks: {count_tracks}")
            self.lbl_total_playlists.configure(text=f"Playlists: {count_playlists}")
        except Exception as e:
            print(f"Stats Error: {e}")

    def save_config(self):
        content = self.config_text.get("0.0", "end").strip()
        try:
            import json
            # Validate JSON
            json.loads(content)
            with open("config.json", "w") as f:
                f.write(content)
            print("Config saved!")
        except Exception as e:
            print(f"Invalid JSON: {e}")

    def center_window(self):
        self.update_idletasks()
        width = 1000
        height = 700
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def update_progress(self, current, total, message):
        def _update():
            if total > 0:
                progress = current / total
                self.progress_bar.set(progress)
                self.status_label.configure(text=f"{message} ({current}/{total})")
            else:
                self.progress_bar.set(0)
                self.status_label.configure(text=message)
        self.after(0, _update)

    def run_in_thread(self, target, name):
        # Switch to library tab to show output
        self.show_frame("library")
        
        self.status_label.configure(text=f"Running: {name}...")
        self.progress_bar.set(0)
        self.console_box.configure(state="normal")
        self.console_box.delete("0.0", "end")
        self.console_box.configure(state="disabled")
        
        def wrapper():
            try:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Starting {name}...")
                target()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {name} Completed.")
                self.after(0, lambda: self.progress_bar.set(1))
            except Exception as e:
                print(f"❌ ERROR: {e}")
            finally:
                self.after(0, lambda: self.status_label.configure(text="Ready"))

        threading.Thread(target=wrapper, daemon=True).start()

    def run_scan(self):
        self.run_in_thread(lambda: scanner.scan_library(progress_callback=self.update_progress), "🔍 Library Scan")

    def run_sort(self):
        def sort_wrapper():
            pm = sorter.PlaylistManager()
            playlists = pm.get_my_playlists()
            to_sort = [p for p in playlists if "[Sorted]" not in p['title']]
            total = len(to_sort)
            print(f"Found {total} playlists to sort.")
            self.update_progress(0, total, "Starting Sort...")
            for i, p in enumerate(to_sort):
                msg = f"📂 Sorting {p['title']}..."
                print(msg)
                self.update_progress(i+1, total, msg)
                pm.sort_standard(p['playlistId'])
        self.run_in_thread(sort_wrapper, "📂 Playlist Sort")

    def run_sync(self):
        self.run_in_thread(lambda: sync_engine.sync_to_spotify(progress_callback=self.update_progress), "🟢 Spotify Sync")

    def run_restore(self):
        self.run_in_thread(lambda: restore_library.restore_library(progress_callback=self.update_progress), "↩️ Library Restore")

    def load_playlists_to_combo(self):
        try:
            from db_manager import DBManager
            db = DBManager()
            # We need to get track counts too.
            # Let's do a join or just a separate query for now.
            # Actually, the 'playlists' table has a 'track_count' column!
            # Let's check db_manager.py init_db. Yes: track_count INTEGER.
            
            db.cursor.execute('SELECT id, title, track_count FROM playlists ORDER BY title')
            playlists = [{'id': r[0], 'title': r[1], 'count': r[2]} for r in db.cursor.fetchall()]
            db.close()
            
            # Format: "Title (Count tracks) [ID]"
            values = [f"{p['title']} ({p['count']} tracks) [{p['id']}]" for p in playlists]
            self.playlist_combo.configure(values=values)
            if values:
                self.playlist_combo.set(values[0])
        except Exception as e:
            print(f"Error loading playlists: {e}")

    def run_cleaner(self):
        selection = self.playlist_combo.get()
        if not selection or "[" not in selection:
            return
            
        # Extract ID from [ID]
        pid = selection.split("[")[-1].replace("]", "")
        title = selection.split(" (")[0]
        
        def clean_wrapper():
            pm = sorter.PlaylistManager()
            print(f"🧹 Cleaning duplicates in '{title}'...")
            pm.deduplicate_playlist(pid)
            print("✅ Cleaning complete.")
            
    def run_reverse_sync(self):
        url = self.spotify_url_entry.get()
        if not url:
            print("Please enter a Spotify Playlist URL.")
            return
            
        # Import here to avoid circular imports if any
        import spotify_to_yt
        
        self.run_in_thread(lambda: spotify_to_yt.sync_spotify_to_yt(url, progress_callback=self.update_progress), "⬇️ Spotify Import")
        
    def run_smart_playlist(self):
        name = self.sp_name.get()
        rule_type_raw = self.sp_type.get()
        value = self.sp_value.get()
        
        if not name or not value:
            print("Please fill in all fields.")
            return
            
        # Map readable type to internal key
        rule_map = {
            "Artist Name": "artist",
            "Title Contains": "title_contains"
        }
        rule_type = rule_map.get(rule_type_raw, "artist")
        
        import smart_playlists
        self.run_in_thread(lambda: smart_playlists.create_smart_playlist(name, rule_type, value, progress_callback=self.update_progress), f"✨ Creating {name}")

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = MusicBridgeApp()
    app.mainloop()
