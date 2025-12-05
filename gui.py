import customtkinter as ctk
import sys
import threading
import io
import logging
from datetime import datetime

# Import our tools
import scanner
import sorter
import sync_engine
import restore_library
import smart_playlists
import tools_manager
import tkinter.messagebox

class TextRedirector(io.StringIO):
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, str):
        self.text_widget.configure(state="normal")
        
        # Determine tag based on content
        tags = "info"
        if "ERROR" in str or "❌" in str: tags = "error"
        elif "WARNING" in str or "⚠️" in str: tags = "warning"
        elif "✅" in str or "Success" in str: tags = "success"
        elif "[" in str and "]" in str: tags = "dim" # Timestamps
        
        # Use underlying tk widget for tags
        self.text_widget._textbox.insert("end", str, tags)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")
        
    def flush(self):
        pass

class GuiHandler(logging.Handler):
    def __init__(self, text_widget, verbose_var=None):
        super().__init__()
        self.text_widget = text_widget
        self.verbose_var = verbose_var
        self.formatter = logging.Formatter('%(message)s')

    def emit(self, record):
        msg = self.format(record)
        
        # Filter logic
        if self.verbose_var and self.verbose_var.get() == 0:
            if "Skipping:" in msg or "Fetching" in msg or "Found" in msg:
                return

        def append():
            self.text_widget.configure(state="normal")
            
            # Determine tag
            tags = "info"
            if record.levelno >= logging.ERROR: tags = "error"
            elif record.levelno >= logging.WARNING: tags = "warning"
            elif "✅" in msg: tags = "success"
            
            self.text_widget._textbox.insert("end", msg + "\n", tags)
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
        # Ensure thread safety for GUI updates
        self.text_widget.after(0, append)
class MusicBridgeApp(ctk.CTk):
    def __init__(self):
        print("DEBUG: Entering __init__")
        super().__init__()
        print("DEBUG: Super init done")
        
        # Set App User Model ID for Taskbar Icon
        import ctypes
        myappid = 'musicbridge.app.v2.0' # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.title("MusicBridge")
        self.geometry("1100x700")
        print("DEBUG: Window geometry set")
        
        # Set Icon
        try:
            self.iconbitmap("assets/icon.ico")
        except:
            pass

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        print("DEBUG: Creating Sidebar...")
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MusicBridge", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Separator 1
        ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#333333").grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))

        # Navigation Buttons
        self.nav_buttons = {}
        
        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="📊 Dashboard", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("dashboard"), fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.btn_dashboard.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        self.nav_buttons["dashboard"] = self.btn_dashboard

        self.btn_library = ctk.CTkButton(self.sidebar_frame, text="📚 Library", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("library"), fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.btn_library.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        self.nav_buttons["library"] = self.btn_library

        self.btn_sync = ctk.CTkButton(self.sidebar_frame, text="🔄 Sync", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("sync"), fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.btn_sync.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        self.nav_buttons["sync"] = self.btn_sync
        
        self.btn_tools = ctk.CTkButton(self.sidebar_frame, text="🛠️ Tools", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("tools"), fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.btn_tools.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        self.nav_buttons["tools"] = self.btn_tools
        
        self.btn_logs = ctk.CTkButton(self.sidebar_frame, text="📜 Logs", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("logs"), fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.btn_logs.grid(row=6, column=0, padx=20, pady=5, sticky="ew")
        self.nav_buttons["logs"] = self.btn_logs

        # Spacer to push bottom items down
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        # Separator 2
        ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#333333").grid(row=8, column=0, sticky="ew", padx=20, pady=(10, 10))
        
        # Profile Info
        self.lbl_user = ctk.CTkLabel(self.sidebar_frame, text="👤 User", font=ctk.CTkFont(size=12), text_color="gray")
        self.lbl_user.grid(row=9, column=0, padx=20, pady=(0, 5))

        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="⚙️ Settings", font=ctk.CTkFont(family="Segoe UI Emoji", size=14), command=lambda: self.show_frame("settings"), fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"), anchor="w")
        self.btn_settings.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.nav_buttons["settings"] = self.btn_settings

        # Main Content Area
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.create_frames()
        
        self.load_user_info()
        
        self.show_frame("dashboard")
        self.center_window()

    def create_frames(self):
        print("DEBUG: create_frames started")
        # --- Dashboard Frame (Redesigned) ---
        dash = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["dashboard"] = dash
        print("DEBUG: Dashboard frame created")
        
        # Title
        ctk.CTkLabel(dash, text="Dashboard", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=(20, 10), anchor="w", padx=30)
        
        # 1. Stat Cards (Centered & Larger)
        stats_grid = ctk.CTkFrame(dash, fg_color="transparent")
        stats_grid.pack(pady=20, padx=20, fill="x")
        
        # Helper to create a large card
        def create_card(parent, title, icon):
            card = ctk.CTkFrame(parent, height=140, fg_color="#2B2B2B", corner_radius=20)
            card.pack(side="left", fill="both", expand=True, padx=15)
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.place(relx=0.5, rely=0.5, anchor="center")
            
            ctk.CTkLabel(content, text=icon, font=ctk.CTkFont(size=40)).pack(pady=(0, 5))
            
            lbl_val = ctk.CTkLabel(content, text="...", font=ctk.CTkFont(size=32, weight="bold"))
            lbl_val.pack()
            
            ctk.CTkLabel(content, text=title, text_color="gray", font=ctk.CTkFont(size=14)).pack()
            
            return lbl_val

        self.lbl_total_tracks = create_card(stats_grid, "Total Tracks", "🎵")
        self.lbl_total_playlists = create_card(stats_grid, "Playlists", "📂")
        print("DEBUG: Stat cards created")
        
        # 2. Top Playlists (Numeric List)
        list_frame = ctk.CTkFrame(dash, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        ctk.CTkLabel(list_frame, text="Top Playlists", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", pady=(0, 15))
        
        # Scrollable container for the list
        self.playlist_list = ctk.CTkScrollableFrame(list_frame, fg_color="#232323", corner_radius=15)
        self.playlist_list.pack(fill="both", expand=True)
        print("DEBUG: Playlist list created")
        
        # 3. System Status Footer
        self.report_box = ctk.CTkLabel(dash, text="System ready.", text_color="gray")
        self.report_box.pack(side="bottom", pady=20)

        # --- Library Frame (Redesigned) ---
        lib = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["library"] = lib
        print("DEBUG: Library frame created")
        
        # Header
        header_frame = ctk.CTkFrame(lib, fg_color="transparent")
        header_frame.pack(fill="x", pady=(40, 20), padx=40)
        ctk.CTkLabel(header_frame, text="Library Management", font=ctk.CTkFont(size=32, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header_frame, text="Scan to update your library or sort to organize your playlists.", text_color="gray", font=ctk.CTkFont(size=14)).pack(anchor="w")
        print("DEBUG: Library header created")
        
        # Main Content (Centered)
        content = ctk.CTkFrame(lib, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=40)
        
        # Action Grid
        grid_frame = ctk.CTkFrame(content, fg_color="transparent")
        grid_frame.pack(pady=40)
        
        def create_action_card(parent, title, icon, command, color, hover):
            card = ctk.CTkButton(parent, text=f"{icon}\n\n{title}", command=command, 
                                font=ctk.CTkFont(size=18, weight="bold"),
                                fg_color=color, hover_color=hover,
                                corner_radius=20, height=180, width=220)
            return card

        # Scan Card (Blue)
        create_action_card(grid_frame, "Scan Library", "🔍", self.run_scan, color="#2980b9", hover="#3498db").pack(side="left", padx=20)
        
        # Sort Card (Dark)
        create_action_card(grid_frame, "Sort All", "📂", self.run_sort, color="#2B2B2B", hover="#3A3A3A").pack(side="left", padx=20)
        print("DEBUG: Action cards created")

        # Options
        self.chk_force = ctk.CTkCheckBox(content, text="Force Full Scan (Re-download metadata)", font=ctk.CTkFont(size=12))
        self.chk_force.pack(pady=10)

        # Status Panel (Bottom)
        status_frame = ctk.CTkFrame(lib, fg_color="#1a1a1a", height=120, corner_radius=0)
        status_frame.pack(side="bottom", fill="x")
        
        status_content = ctk.CTkFrame(status_frame, fg_color="transparent")
        status_content.pack(fill="x", padx=40, pady=30)
        
        self.status_label = ctk.CTkLabel(status_content, text="Ready", font=ctk.CTkFont(size=14), anchor="w")
        self.status_label.pack(fill="x", pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(status_content, height=12, corner_radius=6)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        print("DEBUG: Status panel created")

        # --- Sync Frame ---
        sync = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["sync"] = sync
        print("DEBUG: Sync frame created")
        
        # Header
        header = ctk.CTkFrame(sync, fg_color="transparent")
        header.pack(fill="x", pady=(20, 10), padx=20)
        ctk.CTkLabel(header, text="Synchronization Center", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="🔄 Refresh Lists", command=self.load_sync_lists, width=120).pack(side="right")

        # Columns Container
        cols = ctk.CTkFrame(sync, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Left: YouTube Music
        left_col = ctk.CTkFrame(cols, fg_color="#2B2B2B", corner_radius=10)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(left_col, text="YouTube Music", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        self.yt_listbox = ctk.CTkScrollableFrame(left_col, fg_color="transparent")
        self.yt_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.yt_selection = ctk.StringVar(value="")

        # Right: Spotify
        right_col = ctk.CTkFrame(cols, fg_color="#2B2B2B", corner_radius=10)
        right_col.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(right_col, text="Spotify", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        self.sp_listbox = ctk.CTkScrollableFrame(right_col, fg_color="transparent")
        self.sp_listbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.sp_selection = ctk.StringVar(value="")

        # Controls (Bottom)
        controls = ctk.CTkFrame(sync, fg_color="#232323", corner_radius=15)
        controls.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(controls, text="Sync Actions", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 10))
        
        btns = ctk.CTkFrame(controls, fg_color="transparent")
        btns.pack(pady=(0, 15))
        
        ctk.CTkButton(btns, text="YT ➡️ Spotify", command=self.run_sync_export, fg_color="#1DB954", hover_color="#1ed760", text_color="black").pack(side="left", padx=20)
        ctk.CTkButton(btns, text="Spotify ➡️ YT", command=self.run_sync_import, fg_color="#FF0000", hover_color="#cc0000", text_color="white").pack(side="left", padx=20)
        
        self.chk_smart = ctk.CTkCheckBox(controls, text="Smart Sync (Add new songs only)", onvalue=1, offvalue=0)
        self.chk_smart.select()
        self.chk_smart.pack(pady=(0, 15))

        
        # --- Tools Frame ---
        tools = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.frames["tools"] = tools
        
        ctk.CTkLabel(tools, text="Advanced Tools", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        # 1. Smart Maintenance
        maint_frame = ctk.CTkFrame(tools, fg_color="#2B2B2B", corner_radius=15)
        maint_frame.pack(fill="x", padx=40, pady=10)
        
        ctk.CTkLabel(maint_frame, text="Smart Maintenance", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        
        self.lbl_health_status = ctk.CTkLabel(maint_frame, text="System health unknown.", text_color="gray")
        self.lbl_health_status.pack(pady=5)
        
        self.btn_health_check = ctk.CTkButton(maint_frame, text="🩺 Check Library Health", command=self.run_health_check, width=200)
        self.btn_health_check.pack(pady=15)
        
        self.btn_fix_issues = ctk.CTkButton(maint_frame, text="🧹 Fix Found Issues", command=self.run_auto_clean, fg_color="#e74c3c", hover_color="#c0392b", width=200)
        # Hidden by default

        # 2. Restore Backup
        restore_frame = ctk.CTkFrame(tools, fg_color="#2B2B2B", corner_radius=15)
        restore_frame.pack(fill="x", padx=40, pady=10)
        
        ctk.CTkLabel(restore_frame, text="↩️ Restore Backup", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkLabel(restore_frame, text="Restore your library from the last backup.").pack(pady=5)
        ctk.CTkButton(restore_frame, text="⚠️ Restore Database", command=self.run_restore, fg_color="#e74c3c", hover_color="#c0392b").pack(pady=10)

        # 3. Export
        export_frame = ctk.CTkFrame(tools, fg_color="#2B2B2B", corner_radius=15)
        export_frame.pack(fill="x", padx=40, pady=10)
        
        ctk.CTkLabel(export_frame, text="📤 Export Data", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkLabel(export_frame, text="Export your entire library database to CSV.").pack(pady=5)
        ctk.CTkButton(export_frame, text="💾 Export to CSV", command=self.run_export).pack(pady=10)





        # --- Logs Frame ---
        logs = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["logs"] = logs
        
        # Header with Buttons
        log_header = ctk.CTkFrame(logs, fg_color="transparent")
        log_header.pack(fill="x", pady=(20, 10))
        
        ctk.CTkLabel(log_header, text="Application Logs", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        btn_frame = ctk.CTkFrame(log_header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        # Verbose Toggle
        self.chk_verbose = ctk.CTkCheckBox(btn_frame, text="Show Verbose", width=100)
        self.chk_verbose.pack(side="left", padx=10)
        
        def copy_logs():
            try:
                self.clipboard_clear()
                self.clipboard_append(self.console_box.get("0.0", "end"))
                self.status_label.configure(text="Logs copied to clipboard!")
            except: pass

        def clear_logs():
            self.console_box.configure(state="normal")
            self.console_box.delete("0.0", "end")
            self.console_box.configure(state="disabled")
            
        ctk.CTkButton(btn_frame, text="📋 Copy", width=80, command=copy_logs, fg_color="#2B2B2B", hover_color="#3A3A3A").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🗑️ Clear", width=80, command=clear_logs, fg_color="#c0392b", hover_color="#e74c3c").pack(side="left", padx=5)

        # Console Box (Increased spacing)
        self.console_box = ctk.CTkTextbox(logs, width=700, height=400, font=("Consolas", 12))
        self.console_box.pack(pady=10, padx=20, fill="both", expand=True)
        self.console_box.configure(state="disabled", spacing1=4, spacing3=4) # Add line spacing
        
        # Configure Tags for Colors (Accessing underlying tkinter widget)
        self.console_box._textbox.tag_config("error", foreground="#ff5555")  # Red
        self.console_box._textbox.tag_config("success", foreground="#50fa7b") # Green
        self.console_box._textbox.tag_config("warning", foreground="#ffb86c") # Orange
        self.console_box._textbox.tag_config("info", foreground="#f8f8f2")    # White
        self.console_box._textbox.tag_config("dim", foreground="#6272a4")     # Grey

        # --- Settings Frame ---
        settings = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.frames["settings"] = settings
        ctk.CTkLabel(settings, text="Settings", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)
        
        # Form Container
        form = ctk.CTkFrame(settings, fg_color="#2B2B2B", corner_radius=15)
        form.pack(fill="x", padx=40, pady=10)
        
        # Spotify Section
        ctk.CTkLabel(form, text="Spotify Configuration", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10), padx=20, anchor="w")
        
        ctk.CTkLabel(form, text="Client ID:", text_color="gray").pack(padx=20, anchor="w")
        self.entry_sp_client = ctk.CTkEntry(form, placeholder_text="Paste Client ID here", width=400)
        self.entry_sp_client.pack(pady=(0, 10), padx=20, anchor="w")
        
        ctk.CTkLabel(form, text="Client Secret:", text_color="gray").pack(padx=20, anchor="w")
        secret_row = ctk.CTkFrame(form, fg_color="transparent")
        secret_row.pack(pady=(0, 20), padx=20, anchor="w")
        
        self.entry_sp_secret = ctk.CTkEntry(secret_row, placeholder_text="Paste Client Secret here", width=350, show="*", height=30)
        self.entry_sp_secret.pack(side="left", padx=(0, 10))
        
        def toggle_secret():
            if self.entry_sp_secret.cget("show") == "*":
                self.entry_sp_secret.configure(show="")
            else:
                self.entry_sp_secret.configure(show="*")
                
        ctk.CTkButton(secret_row, text="👁️", width=40, height=30, command=toggle_secret, font=ctk.CTkFont(family="Segoe UI Emoji", size=14), anchor="center").pack(side="left")

        # YouTube Section
        ctk.CTkLabel(form, text="YouTube Configuration", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 10), padx=20, anchor="w")
        
        ctk.CTkLabel(form, text="User Filter (Your Name):", text_color="gray").pack(padx=20, anchor="w")
        self.entry_yt_user = ctk.CTkEntry(form, placeholder_text="e.g. Anthony Buitrago", width=400)
        self.entry_yt_user.pack(pady=(0, 20), padx=20, anchor="w")

        # Load initial values
        self.load_config_form()
            
        ctk.CTkButton(settings, text="💾 Save Configuration", command=self.save_config_form, font=ctk.CTkFont(size=16, weight="bold"), height=40).pack(pady=20)

        # Redirect stdout/stderr
        sys.stdout = TextRedirector(self.console_box)
        sys.stderr = TextRedirector(self.console_box)
        
        # Attach Logger Handler
        logger = logging.getLogger("MusicBridge")
        gui_handler = GuiHandler(self.console_box, verbose_var=self.chk_verbose)
        logger.addHandler(gui_handler)

    def show_frame(self, name):
        # Hide all
        for frame in self.frames.values():
            frame.grid_forget()
        # Show selected
        self.frames[name].grid(row=0, column=0, sticky="nsew")
        
        # Update Sidebar Buttons
        for btn_name, btn in self.nav_buttons.items():
            if btn_name == name:
                btn.configure(fg_color=("#3B8ED0", "#1F6AA5")) # Active color (Blue)
            else:
                btn.configure(fg_color="transparent") # Inactive

        if name == "dashboard":
            self.refresh_stats()

    def load_user_info(self):
        try:
            import json
            with open("config.json", "r") as f:
                config = json.load(f)
                user = config.get("youtube", {}).get("user_filter", "User")
                self.lbl_user.configure(text=f"👤 {user}")
        except:
            self.lbl_user.configure(text="👤 Guest")

    def save_config_form(self):
        try:
            import json
            
            # Load existing or create new
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
            except:
                config = {}
                
            # Update Spotify
            if "spotify" not in config: config["spotify"] = {}
            config["spotify"]["client_id"] = self.entry_sp_client.get().strip()
            config["spotify"]["client_secret"] = self.entry_sp_secret.get().strip()
            
            # Update YouTube
            if "youtube" not in config: config["youtube"] = {}
            config["youtube"]["user_filter"] = self.entry_yt_user.get().strip()
            
            # Save
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
                
            tkinter.messagebox.showinfo("Configuration Saved", "Settings have been saved successfully.\nPlease restart the application for changes to take effect.")
            
            # Update User Label immediately
            self.lbl_user.configure(text=f"👤 {config['youtube']['user_filter']}")
            
        except Exception as e:
            tkinter.messagebox.showerror("Save Error", f"Could not save configuration: {e}")

    def refresh_stats(self):
        try:
            from db_manager import DBManager
            db = DBManager()
            
            # 1. Total Tracks
            db.cursor.execute("SELECT COUNT(*) FROM tracks")
            total_tracks = db.cursor.fetchone()[0]
            self.lbl_total_tracks.configure(text=f"{total_tracks:,}")
            
            # 2. Total Playlists
            db.cursor.execute("SELECT COUNT(*) FROM playlists")
            total_playlists = db.cursor.fetchone()[0]
            self.lbl_total_playlists.configure(text=f"{total_playlists}")
            
            # 3. Top Playlists (Numeric List)
            # Clear existing list
            for widget in self.playlist_list.winfo_children():
                widget.destroy()
                
            db.cursor.execute("""
                SELECT p.title, COUNT(pt.track_id) as count 
                FROM playlists p 
                JOIN playlist_tracks pt ON p.id = pt.playlist_id 
                GROUP BY p.id 
                ORDER BY count DESC 
                LIMIT 10
            """)
            top_playlists = db.cursor.fetchall()
            
            for i, (name, count) in enumerate(top_playlists, 1):
                row = ctk.CTkFrame(self.playlist_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                
                # Format: "1. Playlist Name ............ 123 songs"
                ctk.CTkLabel(row, text=f"{i}.", width=30, anchor="w", font=ctk.CTkFont(family="Consolas", size=14)).pack(side="left")
                ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=14)).pack(side="left", padx=10)
                
                # Spacer
                ctk.CTkLabel(row, text="."*20, text_color="#444444").pack(side="left", fill="x", expand=True)
                
                ctk.CTkLabel(row, text=f"{count} songs", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), text_color="#3498db").pack(side="right")

            db.close()
        except Exception as e:
            print(f"Error refreshing stats: {e}")

    def load_config_form(self):
        try:
            import json
            with open("config.json", "r") as f:
                config = json.load(f)
                
                # Spotify
                sp = config.get("spotify", {})
                self.entry_sp_client.delete(0, "end")
                self.entry_sp_client.insert(0, sp.get("client_id", ""))
                
                self.entry_sp_secret.delete(0, "end")
                self.entry_sp_secret.insert(0, sp.get("client_secret", ""))
                
                # YouTube
                yt = config.get("youtube", {})
                self.entry_yt_user.delete(0, "end")
                self.entry_yt_user.insert(0, yt.get("user_filter", ""))
        except:
            pass # No config yet

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
        # Switch to logs tab to show output
        # self.show_frame("logs")
        
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

    def update_report(self, message):
        self.report_box.configure(state="normal")
        self.report_box.delete("0.0", "end")
        self.report_box.insert("0.0", message)
        self.report_box.configure(state="disabled")

    def run_scan(self):
        # Check both checkboxes (Library tab and Dashboard tab)
        force = False
        try:
            if self.chk_force.get() == 1: force = True
        except: pass
        
        def scan_wrapper():
            result = scanner.scan_library(progress_callback=self.update_progress, force_update=force)
            
            # Update stats on main thread
            self.after(0, self.refresh_stats)
            
            # Generate Report
            added_songs = result.get('added_songs', {})
            if added_songs:
                report = "✅ Scan Complete. New songs added:\n\n"
                for playlist, songs in added_songs.items():
                    report += f"📂 {playlist}:\n"
                    for song in songs:
                        report += f"  • {song}\n"
                    report += "\n"
            else:
                report = "Scan complete. No new songs found."
            
            # Show report on Dashboard (Main Thread)
            self.after(0, lambda: self.update_report(report))
            
            # Also print to Logs
            print("\n" + report)
            
        self.run_in_thread(scan_wrapper, "🔍 Library Scan")

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

    def load_sync_lists(self):
        self.status_label.configure(text="Loading playlists...")
        self.update_idletasks()
        
        def _load():
            try:
                engine = sync_engine.SyncEngine()
                yt_pl, sp_pl = engine.get_playlists()
                
                def _update_ui():
                    # Clear
                    for w in self.yt_listbox.winfo_children(): w.destroy()
                    for w in self.sp_listbox.winfo_children(): w.destroy()
                    
                    # Populate YT
                    for p in yt_pl:
                        rb = ctk.CTkRadioButton(self.yt_listbox, text=p['title'], variable=self.yt_selection, value=p['playlistId'])
                        rb.pack(anchor="w", pady=2)
                        
                    # Populate Spotify
                    for p in sp_pl:
                        rb = ctk.CTkRadioButton(self.sp_listbox, text=p['name'], variable=self.sp_selection, value=p['id'])
                        rb.pack(anchor="w", pady=2)
                        
                    self.status_label.configure(text="Playlists loaded.")
                    
                self.after(0, _update_ui)
            except Exception as e:
                print(f"Error loading lists: {e}")
                self.after(0, lambda: self.status_label.configure(text="Error loading playlists."))
                
        threading.Thread(target=_load, daemon=True).start()

    def run_sync_export(self):
        pid = self.yt_selection.get()
        if not pid:
            tkinter.messagebox.showwarning("Selection Required", "Please select a YouTube playlist to export.")
            return
            
        smart = self.chk_smart.get() == 1
        
        def _action():
            engine = sync_engine.SyncEngine()
            # Get title for target name
            # We need to find the title from the list... or just let engine handle it?
            # Engine needs name if creating new.
            # Let's just pass None and let engine use default or we can look it up if we stored it.
            # For now, let's just pass None and let engine figure it out or ask user?
            # Actually, let's look it up from the radio button text? Hard to get.
            # Let's just pass None and let engine fetch it.
            
            result = engine.sync_to_spotify(pid, smart=smart, progress_callback=self.update_progress)
            print(f"\n✅ {result}")
            
        self.run_in_thread(_action, "YT ➡️ Spotify Sync")

    def run_sync_import(self):
        pid = self.sp_selection.get()
        if not pid:
            tkinter.messagebox.showwarning("Selection Required", "Please select a Spotify playlist to import.")
            return
            
        smart = self.chk_smart.get() == 1
        
        def _action():
            engine = sync_engine.SyncEngine()
            result = engine.sync_to_youtube(pid, smart=smart, progress_callback=self.update_progress)
            print(f"\n✅ {result}")
            
        self.run_in_thread(_action, "Spotify ➡️ YT Import")


    def run_restore(self):
        self.run_in_thread(lambda: restore_library.restore_library(progress_callback=self.update_progress), "↩️ Library Restore")

    def run_health_check(self):
        self.lbl_health_status.configure(text="Scanning all playlists...", text_color="orange")
        self.btn_fix_issues.pack_forget()
        self.update_idletasks()
        
        def check():
            import sorter
            pm = sorter.PlaylistManager()
            playlists = pm.get_my_playlists()
            
            total_dupes = 0
            self.affected_playlists = []
            
            for i, p in enumerate(playlists):
                # Update UI occasionally
                if i % 5 == 0:
                    self.after(0, lambda: self.lbl_health_status.configure(text=f"Checking {p['title']}..."))
                
                # Check for duplicates (logic from sorter.py)
                # We need to fetch tracks first. This might be slow, so we'll do a lighter check if possible
                # But for accuracy, we use the existing method which fetches tracks
                try:
                    # We can't easily "check" without fetching. 
                    # Let's use the DB for a quick check first? 
                    # Actually, let's just rely on the user wanting to do this.
                    pass
                except: pass
                
            # To make this "Smart", let's just iterate and count.
            # Since we don't want to re-implement logic, let's use a new helper in sorter if needed, 
            # or just iterate here.
            

            from db_manager import DBManager
            db = DBManager()
            
            # Find playlists with duplicate video_ids
            query = """
                SELECT playlist_id, COUNT(*) - COUNT(DISTINCT video_id) as dupes
                FROM playlist_tracks
                GROUP BY playlist_id
                HAVING dupes > 0
            """
            db.cursor.execute(query)
            results = db.cursor.fetchall()
            db.close()
            
            total_dupes = sum([r[1] for r in results])
            self.affected_playlists = [r[0] for r in results]
            
            def update_ui():
                if total_dupes > 0:
                    self.lbl_health_status.configure(text=f"⚠️ Found {total_dupes} duplicates in {len(results)} playlists.", text_color="#e74c3c")
                    self.btn_fix_issues.pack(pady=10)
                else:
                    self.lbl_health_status.configure(text="✅ System Healthy. No duplicates found.", text_color="#2ecc71")
            
            self.after(0, update_ui)
            
        threading.Thread(target=check, daemon=True).start()

    def run_auto_clean(self):
        def clean():
            # 1. Clean Local DB first
            self.after(0, lambda: self.lbl_health_status.configure(text="🧹 Cleaning local database..."))
            from db_manager import DBManager
            db = DBManager()
            removed = db.remove_local_duplicates()
            db.close()
            print(f"Removed {removed} local duplicates.")
            
            # 2. Clean Remote Playlists (if needed)
            # We only run this if we had specific affected playlists, but since we just nuked local dupes,
            # let's re-scan to see if we still have issues (which would imply remote dupes if we were checking that,
            # but our health check was purely local).
            
            # For now, just reporting the local cleanup is likely enough for the user's specific "22k" issue.
            
            msg = f"✅ Removed {removed} duplicates from local database."
            self.after(0, lambda: self.lbl_health_status.configure(text=msg, text_color="#2ecc71"))
            self.after(2000, self.run_health_check)
            
        self.run_in_thread(clean, "🧹 Auto-Repair")
            
    def run_reverse_sync(self):
        url = self.spotify_url_entry.get()
        if not url:
            print("Please enter a Spotify Playlist URL.")
            return
            
        # Import here to avoid circular imports if any
        import spotify_to_yt
        
        self.run_in_thread(lambda: spotify_to_yt.sync_spotify_to_yt(url, progress_callback=self.update_progress), "⬇️ Spotify Import")
        


    def run_export(self):
        def _action():
            try:
                tm = tools_manager.ToolsManager()
                success, msg = tm.export_library_to_csv()
                tm.close()
                
                if success:
                    tkinter.messagebox.showinfo("Export Success", msg)
                else:
                    tkinter.messagebox.showerror("Export Failed", msg)
            except Exception as e:
                print(f"Export Error: {e}")
                
        threading.Thread(target=_action, daemon=True).start()

    def load_config_form(self):
        try:
            import json
            with open("config.json", "r") as f:
                config = json.load(f)
                
            sp = config.get("spotify", {})
            yt = config.get("youtube", {})
            
            self.entry_sp_client.delete(0, "end")
            self.entry_sp_client.insert(0, sp.get("client_id", ""))
            
            self.entry_sp_secret.delete(0, "end")
            self.entry_sp_secret.insert(0, sp.get("client_secret", ""))
            
            self.entry_yt_user.delete(0, "end")
            self.entry_yt_user.insert(0, yt.get("user_filter", ""))
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config_form(self):
        try:
            import json
            
            # Read current config to preserve other keys if any
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
            except:
                config = {}
                
            # Update values
            if "spotify" not in config: config["spotify"] = {}
            if "youtube" not in config: config["youtube"] = {}
            
            config["spotify"]["client_id"] = self.entry_sp_client.get().strip()
            config["spotify"]["client_secret"] = self.entry_sp_secret.get().strip()
            # Ensure redirect_uri is set correctly
            config["spotify"]["redirect_uri"] = "http://127.0.0.1:8888/callback"
            
            config["youtube"]["user_filter"] = self.entry_yt_user.get().strip()
            
            # Save
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
                
            tkinter.messagebox.showinfo("Success", "Configuration saved successfully!\nPlease restart the application if you changed API keys.")
            
            # Update user label immediately
            self.load_user_info()
            
        except Exception as e:
            tkinter.messagebox.showerror("Error", f"Failed to save config: {e}")

            




if __name__ == "__main__":
    # --- Single Instance Check ---
    import socket
    from tkinter import messagebox
    import traceback
    
    # Create a socket and try to bind to a specific port
    # If it fails, another instance is likely running
    instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Port 12346 (Changed to avoid conflicts)
        instance_socket.bind(('127.0.0.1', 12346))
    except socket.error as e:
        print(f"Socket Error: {e}")
        try:
            messagebox.showerror("MusicBridge", "MusicBridge is already running!")
        except:
            pass
        sys.exit(1)
    # -----------------------------

    try:
        print("DEBUG: Setting appearance mode...")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        print("DEBUG: Initializing App...")
        app = MusicBridgeApp()
        print("DEBUG: App Initialized. Starting Mainloop...")
        app.mainloop()
        print("DEBUG: Mainloop exited.")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        try:
            messagebox.showerror("Critical Error", f"Application crashed:\n{e}")
        except:
            pass
