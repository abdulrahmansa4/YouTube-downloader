import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import os
import re
import webbrowser
from datetime import datetime
import json
import sys
import platform
from PIL import Image, ImageTk
import requests
from io import BytesIO
import sv_ttk

# -------- Constants --------
CONFIG_FILE = "config.json"
SUPPORTED_SITES = [
    "YouTube", "Facebook", "Twitter", "Instagram", 
    "TikTok", "Vimeo", "Dailymotion", "Twitch",
    "SoundCloud", "Reddit", "LinkedIn", "Tumblr"
]

# -------- Utility Functions --------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "download_path": os.path.join(os.path.expanduser("~"), "Downloads"),
        "theme": "superhero",
        "language": "ar",
        "format_preference": "best",
        "history": []
    }

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def validate_url(url):
    """Check if URL is from a supported site"""
    patterns = {
        "YouTube": r"(youtube\.com|youtu\.be)",
        "Facebook": r"facebook\.com",
        "Twitter": r"twitter\.com",
        "Instagram": r"instagram\.com",
        "TikTok": r"tiktok\.com",
        "Vimeo": r"vimeo\.com",
        "Dailymotion": r"dailymotion\.com",
        "Twitch": r"twitch\.tv",
        "SoundCloud": r"soundcloud\.com",
        "Reddit": r"reddit\.com",
        "LinkedIn": r"linkedin\.com",
        "Tumblr": r"tumblr\.com"
    }
    
    for site, pattern in patterns.items():
        if re.search(pattern, url):
            return site
    return None

def get_video_thumbnail(url):
    """Try to get video thumbnail using yt-dlp"""
    try:
        result = subprocess.run(
            ["yt-dlp", "--get-thumbnail", url],
            capture_output=True, text=True
        )
        thumbnail_url = result.stdout.strip()
        if thumbnail_url.startswith("http"):
            response = requests.get(thumbnail_url)
            img = Image.open(BytesIO(response.content))
            img.thumbnail((200, 200))
            return ImageTk.PhotoImage(img)
    except:
        return None

# -------- Main Application --------
class VideoDownloaderApp:
    def __init__(self):
        self.config = load_config()
        self.app = ttk.Window(
            title="Professional Video Downloader Pro",
            themename=self.config.get("theme", "superhero"),
            size=(1100, 750),  # Initial size
            resizable=(True, True),  # Allow resizing
            iconphoto='icon.ico'
        )
        self.app.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Optional: set a reasonable minimum size
        self.app.minsize(800, 600)

        # Style configuration
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Arial', 10))
        self.style.configure('TLabel', font=('Arial', 10))
        
        # Main container
        self.main_frame = ttk.Frame(self.app)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # URL Entry Section
        self.setup_url_section()
        
        # Thumbnail Preview
        self.thumbnail_label = ttk.Label(self.main_frame)
        self.thumbnail_label.pack(pady=5)
        
        # Format Selection
        self.setup_format_section()
        
        # Output Console
        self.setup_output_section()
        
        # Progress and Status
        self.setup_progress_section()
        
        # Bottom Buttons
        self.setup_action_buttons()
        
        # Initialize variables
        self.download_thread = None
        self.thumbnail_image = None
        self.current_url = ""
        self.format_cache = {}  # Add this line
        self._download_process = None

        # Try to auto-fill URL from clipboard
        try:
            clipboard = self.app.clipboard_get()
            if clipboard and validate_url(clipboard):
                self.url_entry.insert(0, clipboard)
        except:
            pass
        
    def setup_url_section(self):
        url_frame = ttk.LabelFrame(self.main_frame, text="Video URL", padding=10)
        url_frame.pack(fill=tk.X, pady=5)
        
        self.url_entry = ttk.Entry(url_frame, width=80, font=('Arial', 11))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.url_entry.bind("<Control-v>", self.paste_event)
        self.url_entry.bind("<Control-V>", self.paste_event)
        
        # Add URL from clipboard button
        ttk.Button(
            url_frame, 
            text="Paste", 
            bootstyle=SECONDARY,
            command=self.paste_from_clipboard,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        # Add history dropdown
        self.history_btn = ttk.Menubutton(url_frame, text="History ▼", bootstyle=INFO)
        self.history_menu = tk.Menu(self.history_btn, tearoff=0)
        self.history_btn['menu'] = self.history_menu
        self.history_btn.pack(side=tk.RIGHT, padx=5)
        self.setup_history_menu()
        
        # Fetch button
        ttk.Button(
            url_frame, 
            text="Get Formats", 
            bootstyle=PRIMARY,
            command=self.fetch_formats,
            width=12
        ).pack(side=tk.RIGHT, padx=5)
    
    def setup_format_section(self):
        format_frame = ttk.LabelFrame(self.main_frame, text="Download Options", padding=10)
        format_frame.pack(fill=tk.X, pady=5)

        # Format selection
        ttk.Label(format_frame, text="Select Format:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.format_combobox = ttk.Combobox(
            format_frame, 
            width=60, 
            font=('Arial', 10), 
            state="readonly"
        )
        self.format_combobox.grid(row=0, column=1, sticky=tk.EW, padx=5)

        # Quality preference
        ttk.Label(format_frame, text="Quality Preference:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.quality_var = tk.StringVar(value=self.config.get("format_preference", "best"))
        quality_options = ["best", "worst", "fastest", "smallest"]
        ttk.OptionMenu(
            format_frame, 
            self.quality_var, 
            self.quality_var.get(), 
            *quality_options
        ).grid(row=0, column=3, sticky=tk.W, padx=5)

        # Download path
        ttk.Label(format_frame, text="Download Folder:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.path_var = tk.StringVar(value=self.config.get("download_path", ""))
        ttk.Entry(
            format_frame, 
            textvariable=self.path_var, 
            width=60,
            font=('Arial', 10)
        ).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(
            format_frame, 
            text="Browse", 
            bootstyle=SECONDARY,
            command=self.browse_folder,
            width=8
        ).grid(row=1, column=3, sticky=tk.E, padx=5, pady=5)

        # Additional options
        self.audio_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            format_frame, 
            text="Audio Only", 
            variable=self.audio_only_var,
            bootstyle="round-toggle"
        ).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)

        self.subtitles_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            format_frame, 
            text="Download Subtitles", 
            variable=self.subtitles_var,
            bootstyle="round-toggle"
        ).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # --- Merge Section ---
        merge_frame = ttk.LabelFrame(self.main_frame, text="Merge Video + Audio", padding=10)
        merge_frame.pack(fill=tk.X, pady=5)

        self.merge_custom_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            merge_frame,
            text="Merge custom video + audio",
            variable=self.merge_custom_var,
            bootstyle="round-toggle",
            command=self.on_merge_custom_toggle
        ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

        ttk.Label(merge_frame, text="Video Only:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.video_only_combobox = ttk.Combobox(
            merge_frame,
            width=30,
            font=('Arial', 10),
            state="disabled"
        )
        self.video_only_combobox.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(merge_frame, text="Audio Only:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.audio_only_combobox = ttk.Combobox(
            merge_frame,
            width=30,
            font=('Arial', 10),
            state="disabled"
        )
        self.audio_only_combobox.grid(row=1, column=3, sticky=tk.W, padx=5)

        # Merge Quality Preference
        ttk.Label(merge_frame, text="Merge Quality:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.merge_quality_var = tk.StringVar(value="best")
        merge_quality_options = ["best", "worst"]
        ttk.OptionMenu(
            merge_frame,
            self.merge_quality_var,
            self.merge_quality_var.get(),
            *merge_quality_options,
            command=lambda _: self.update_merge_quality_selection()
        ).grid(row=2, column=1, sticky=tk.W, padx=5)

        # Help label for quality preference
        ttk.Label(format_frame, text="(Best = highest quality, Worst = lowest size)", font=('Arial', 8)).grid(row=0, column=4, sticky=tk.W, padx=5)

        format_frame.columnconfigure(1, weight=1)

    def on_merge_custom_toggle(self):
        if self.merge_custom_var.get():
            self.format_combobox.config(state="disabled")
            self.video_only_combobox.config(state="readonly")
            self.audio_only_combobox.config(state="readonly")
            self.update_merge_quality_selection()  # <-- always update on toggle
        else:
            self.format_combobox.config(state="readonly")
            self.video_only_combobox.config(state="disabled")
            self.audio_only_combobox.config(state="disabled")

    def setup_output_section(self):
        output_frame = ttk.LabelFrame(self.main_frame, text="Output Console", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Text widget with scrollbar
        self.output_text = tk.Text(
            output_frame, 
            wrap=tk.WORD, 
            font=('Consolas', 10), 
            height=12,
            state=tk.DISABLED
        )
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(output_frame, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.config(yscrollcommand=scrollbar.set)
        
        # Add right-click context menu
        self.output_text.bind("<Button-3>", self.show_output_context_menu)
        self.output_context_menu = tk.Menu(self.output_text, tearoff=0)
        self.output_context_menu.add_command(label="Copy", command=self.copy_output_text)
        self.output_context_menu.add_command(label="Clear", command=self.clear_output_text)
        self.output_context_menu.add_command(label="Save Log", command=self.save_output_log)
    
    def setup_progress_section(self):
        progress_frame = ttk.Frame(self.main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            mode="determinate",
            bootstyle=INFO
        )
        self.progress_bar.pack(fill=tk.X, expand=True)
        
        status_frame = ttk.Frame(progress_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            font=('Arial', 9),
            bootstyle=SECONDARY
        ).pack(side=tk.LEFT)
        
        self.speed_var = tk.StringVar()
        ttk.Label(
            status_frame, 
            textvariable=self.speed_var,
            font=('Arial', 9),
            bootstyle=SECONDARY
        ).pack(side=tk.RIGHT)
    
    def setup_action_buttons(self):
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        ttk.Button(
            btn_frame, 
            text="Download", 
            bootstyle=SUCCESS,
            command=self.download_video,
            width=15
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        ttk.Button(
            btn_frame, 
            text="Stop", 
            bootstyle=DANGER,
            command=self.stop_download,
            width=15
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        ttk.Button(
            btn_frame, 
            text="Open Folder", 
            bootstyle=INFO,
            command=self.open_download_folder,
            width=15
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        ttk.Button(
            btn_frame, 
            text="Clear", 
            bootstyle=WARNING,
            command=self.clear_all,
            width=15
        ).pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
    
    def setup_menu(self):
        menubar = tk.Menu(self.app)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Download", command=self.clear_all)
        file_menu.add_command(label="Batch Download", command=self.show_batch_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Preferences", command=self.show_preferences)
        edit_menu.add_command(label="Check for Updates", command=self.check_for_updates)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        
        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        themes = ["superhero", "darkly", "cyborg", "vapor", "solar", "minty"]
        for theme in themes:
            theme_menu.add_command(
                label=theme.capitalize(),
                command=lambda t=theme: self.change_theme(t)
            )
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        
        # Language submenu
        lang_menu = tk.Menu(view_menu, tearoff=0)
        languages = ["English", "Arabic", "French", "Spanish", "German"]
        for lang in languages:
            lang_menu.add_command(
                label=lang,
                command=lambda l=lang: self.change_language(l)
            )
        view_menu.add_cascade(label="Language", menu=lang_menu)
        
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.app.config(menu=menubar)
    
    def setup_dark_title_bar(self):
        """Set dark title bar on Windows 10/11"""
        if platform.system() == "Windows":
            try:
                from ctypes import windll, byref, sizeof, c_int
                HWND = windll.user32.GetParent(self.app.winfo_id())
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                windll.dwmapi.DwmSetWindowAttribute(
                    HWND, 
                    DWMWA_USE_IMMERSIVE_DARK_MODE, 
                    byref(c_int(1)), 
                    sizeof(c_int)
                )
            except:
                pass
    
    # -------- Event Handlers --------
    def paste_event(self, event=None):
        try:
            self.url_entry.event_generate('<<Paste>>')
            return "break"
        except:
            pass
    
    def paste_from_clipboard(self):
        try:
            clipboard = self.app.clipboard_get()
            if clipboard:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, clipboard)
        except:
            pass
    
    def fetch_formats(self):
        url = self.url_entry.get().strip()
        if url in self.format_cache:
            formats, video_formats, audio_formats = self.format_cache[url]
            self._update_formats_ui(formats, video_formats, audio_formats)
            return
        if not url:
            messagebox.showerror("Error", "Please enter a valid URL.")
            return

        # Validate URL
        site = validate_url(url)
        if not site:
            messagebox.showerror("Error", f"Unsupported website. Supported sites: {', '.join(SUPPORTED_SITES)}")
            return

        # Add to history
        self.add_to_history(url)

        self.current_url = url
        self.update_status(f"Fetching formats from {site}...")
        self.clear_output()
        self.append_output(f"🔍 Fetching available formats from: {url}\n")

        # Disable controls during fetch
        self.toggle_controls(False)

        # Start indeterminate progress bar
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(10)

        # Try to get thumbnail
        self.show_thumbnail(url)

        # Run in background thread
        threading.Thread(target=self._fetch_formats_thread, args=(url,), daemon=True).start()
    
    def _fetch_formats_thread(self, url):
        try:
            cmd = ["yt-dlp", "-F", url]
            result = subprocess.run(
                cmd,
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            output = result.stdout if result.stdout else result.stderr
            self.app.after(0, self.append_output, output)

            video_formats = []
            audio_formats = []
            av_formats = []

            # Detect site
            site = validate_url(url)

            if site == "YouTube":
                for line in output.splitlines():
                    line = line.strip()
                    if (
                        not line
                        or line.startswith("ID ")
                        or set(line) == set("-")
                        or line.startswith("[")
                        or ":" in line and not line.split()[0].isalnum()
                    ):
                        continue
                    parts = line.split()
                    if not parts:
                        continue
                    format_id = parts[0]
                    format_desc = " ".join(parts[1:])
                    if "audio only" in format_desc.lower():
                        audio_formats.append((format_id, format_desc))
                    elif "video only" in format_desc.lower():
                        video_formats.append((format_id, format_desc))
                    else:
                        av_formats.append((format_id, format_desc))
            else:
                # TikTok/Instagram: show ALL real formats, sorted by resolution (highest first)
                av_formats = []
                for line in output.splitlines():
                    line = line.strip()
                    # Skip headers, separators, and yt-dlp info/debug lines
                    if (
                        not line
                        or line.startswith("ID ")
                        or set(line) == set("-")
                        or line.startswith("[")
                        or ":" in line and not line.split()[0].isalnum()
                    ):
                        continue
                    parts = line.split()
                    if not parts:
                        continue
                    format_id = parts[0]
                    format_desc = " ".join(parts[1:])
                    # Extract resolution for sorting
                    match = re.search(r'(\d{3,4})x(\d{3,4})|(\d{3,4})p', format_desc)
                    if match:
                        if match.group(1) and match.group(2):
                            res = int(match.group(2))  # height from WxH
                        elif match.group(3):
                            res = int(match.group(3))  # 720p, 1080p, etc.
                        else:
                            res = 0
                    else:
                        res = 0
                    av_formats.append((format_id, format_desc, res))
                # Sort by resolution (highest first)
                av_formats.sort(key=lambda x: x[2], reverse=True)
                # Remove the resolution from the tuple for display
                av_formats = [(fid, desc) for fid, desc, _ in av_formats]
                video_formats = []
                audio_formats = []

            # Combine for dropdown
            formats = []
            if site == "YouTube":
                if av_formats:
                    formats.append("=== Video+Audio Formats ===")
                    formats += [f"{fid} - {desc}" for fid, desc in av_formats]
                if video_formats:
                    formats.append("=== Video Only Formats ===")
                    formats += [f"{fid} - {desc}" for fid, desc in video_formats]
                if audio_formats:
                    formats.append("=== Audio Only Formats ===")
                    formats += [f"{fid} - {desc}" for fid, desc in audio_formats]
            else:
                if av_formats:
                    formats = [f"{fid} - {desc}" for fid, desc in av_formats]

            self.format_cache[url] = (formats, av_formats, video_formats, audio_formats)
            self.app.after(0, self._update_formats_ui, formats, av_formats, video_formats, audio_formats)

        except Exception as e:
            self.app.after(0, self.append_output, f"❌ Error: {str(e)}")
            self.app.after(0, self.update_status, "Error fetching formats")
        finally:
            self.app.after(0, self.progress_bar.stop)
            self.app.after(0, self.progress_bar.config, {"mode": "determinate"})
            self.app.after(0, self.toggle_controls, True)
    
    def _update_formats_ui(self, formats, av_formats, video_formats, audio_formats):
        self._video_formats = video_formats
        self._audio_formats = audio_formats
        if formats:
            self.format_combobox['values'] = formats
            self.format_combobox.current(0)  # Always select the first format
            # Fill video only and audio only comboboxes with size if available
            self.video_only_combobox['values'] = [
                f"{fid} - {desc}{self._get_size_from_desc(desc)}" for fid, desc in video_formats
            ]
            self.audio_only_combobox['values'] = [
                f"{fid} - {desc}{self._get_size_from_desc(desc)}" for fid, desc in audio_formats
            ]
            if video_formats:
                self.video_only_combobox.current(0)
            if audio_formats:
                self.audio_only_combobox.current(0)
            self.update_status(f"Found {len(formats)} format{'s' if len(formats) > 1 else ''}")
            # Show explanation label only for YouTube
            if hasattr(self, 'format_explain_label'):
                self.format_explain_label.pack_forget()
            if video_formats or audio_formats:
                if not hasattr(self, 'format_explain_label'):
                    self.format_explain_label = ttk.Label(
                        self.main_frame,
                        text="ℹ️ You can merge any video-only and audio-only format you want.",
                        font=('Arial', 9),
                        bootstyle=INFO,
                        wraplength=600,
                        justify=tk.LEFT
                    )
                self.format_explain_label.pack(pady=(0, 5))
        else:
            self.append_output("❌ No valid formats found")
            self.update_status("No formats found")
            if hasattr(self, 'format_explain_label'):
                self.format_explain_label.pack_forget()
    
    def _get_size_from_desc(self, desc):
        match = re.search(r'(\d+(?:\.\d+)?[KMG]iB)', desc)
        return f" [{match.group(1)}]" if match else ""

    def update_merge_quality_selection(self):
        if not hasattr(self, '_video_formats') or not hasattr(self, '_audio_formats'):
            return
        video_formats = self._video_formats
        audio_formats = self._audio_formats
        if not video_formats or not audio_formats:
            return
        # Try to sort by resolution for video, by bitrate/size for audio
        def video_sort_key(item):
            desc = item[1]
            match = re.search(r'(\d{3,4})p', desc)
            return int(match.group(1)) if match else 0
        def audio_sort_key(item):
            desc = item[1]
            match = re.search(r'(\d+)k', desc)
            return int(match.group(1)) if match else 0
        if self.merge_quality_var.get() == "best":
            best_video = max(video_formats, key=video_sort_key)
            best_audio = max(audio_formats, key=audio_sort_key)
            self.video_only_combobox.set(f"{best_video[0]} - {best_video[1]}{self._get_size_from_desc(best_video[1])}")
            self.audio_only_combobox.set(f"{best_audio[0]} - {best_audio[1]}{self._get_size_from_desc(best_audio[1])}")
        else:
            worst_video = min(video_formats, key=video_sort_key)
            worst_audio = min(audio_formats, key=audio_sort_key)
            self.video_only_combobox.set(f"{worst_video[0]} - {worst_video[1]}{self._get_size_from_desc(worst_video[1])}")
            self.audio_only_combobox.set(f"{worst_audio[0]} - {worst_audio[1]}{self._get_size_from_desc(worst_audio[1])}")

    def download_video(self):
        url = self.url_entry.get().strip()
        selected = self.format_combobox.get().strip()

        if not url:
            messagebox.showerror("Error", "Please enter URL.")
            return

        try:
            # If merge custom is checked, use selected video+audio only
            if hasattr(self, 'merge_custom_var') and self.merge_custom_var.get():
                video_code = self.video_only_combobox.get().split()[0]
                audio_code = self.audio_only_combobox.get().split()[0]
                format_code = f"{video_code}+{audio_code}"
            elif selected and not selected.startswith("="):
                format_code = selected.split()[0]
                is_audio_only = "audio only" in selected.lower() or self.audio_only_var.get()
                if not is_audio_only:
                    format_code = f"{format_code}+bestaudio/best"
            else:
                # Fallback: just use best available
                format_code = "bestvideo+bestaudio/best"

            download_path = self.path_var.get()
            if not os.path.exists(download_path):
                os.makedirs(download_path)

            cmd = [
                self.get_ytdlp_path(),
                "-f", format_code,
                "-o", os.path.join(download_path, "%(title)s.%(ext)s"),
                "--no-playlist",
                "--ffmpeg-location", self.get_ffmpeg_path()
            ]

            if self.audio_only_var.get():
                cmd.extend(["--extract-audio", "--audio-format", "mp3"])

            if self.subtitles_var.get():
                cmd.extend(["--write-subs", "--sub-lang", "en"])

            cmd.append(url)

            self.update_status("Starting download...")
            self.append_output(f"⬇️ Downloading: {url}\nFormat: {format_code}\n")
            self.progress_bar.config(mode="determinate", maximum=100, value=0)
            self.progress_bar.update()
            self.speed_var.set("")
            self.toggle_controls(False)

            self._download_process = None
            self.download_thread = threading.Thread(
                target=self._download_thread,
                args=(cmd,),
                daemon=True
            )
            self.download_thread.start()

        except Exception as e:
            self.append_output(f"❌ Error: {str(e)}")
            self.update_status("Download failed")
            self.toggle_controls(True)

    def _download_thread(self, cmd):
        try:
            self._download_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            process = self._download_process
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                self.app.after(0, self.append_output, line)
                import re
                progress_match = re.search(r'\[download\]\s+(\d+\.\d+)%.*?at\s+([^\s]+).*?ETA\s+([^\s]+)', line)
                if progress_match:
                    percent = float(progress_match.group(1))
                    speed = progress_match.group(2)
                    eta = progress_match.group(3)
                    self.app.after(0, self.progress_bar.config, {"value": percent})
                    self.app.after(0, self.speed_var.set, f"{speed} | ETA: {eta}")
            process.wait()
            if process.returncode == 0:
                self.app.after(0, self.append_output, "\n✅ Download completed successfully!\n")
                self.app.after(0, self.update_status, "Download completed")
                self.app.after(0, lambda: messagebox.showinfo("Success", "Download completed successfully!"))
            else:
                self.app.after(0, self.append_output, "\n❌ Download failed!\n")
                self.app.after(0, self.update_status, "Download failed")
        except Exception as e:
            self.app.after(0, self.append_output, f"❌ Error: {str(e)}\n")
            self.app.after(0, self.update_status, "Download failed")
        finally:
            self.app.after(0, self.progress_bar.stop)
            self.app.after(0, self.progress_bar.config, {"mode": "determinate", "value": 0})
            self.app.after(0, self.speed_var.set, "")
            self.app.after(0, self.toggle_controls, True)
            self.download_thread = None

    def get_ffmpeg_path(self):
        ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
        if not os.path.exists(ffmpeg_path):
            messagebox.showerror(
                "FFmpeg Not Found",
                f"FFmpeg not found at:\n{ffmpeg_path}\n\n"
                "Please put ffmpeg.exe in the same folder as this program."
            )
            self.app.destroy()
            sys.exit(1)
        return ffmpeg_path

    def get_ytdlp_path(self):
        return "yt-dlp"
    
    def stop_download(self):
        if self.download_thread and self.download_thread.is_alive():
            if self._download_process and self._download_process.poll() is None:
                try:
                    self._download_process.terminate()
                except Exception:
                    pass
            self.append_output("\n⚠️ Download stopped by user\n")
            self.update_status("Stopped")
            self.progress_bar['value'] = 0
            self.speed_var.set("")
            self.toggle_controls(True)
    
    def open_download_folder(self):
        path = self.path_var.get()
        if os.path.exists(path):
            try:
                if platform.system() == "Windows":
                    os.startfile(path)
                elif platform.system() == "Darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
            except:
                messagebox.showerror("Error", "Could not open folder")
        else:
            messagebox.showerror("Error", "Folder does not exist")
    
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
            self.config["download_path"] = folder
            save_config(self.config)
    
    def clear_all(self):
        self.url_entry.delete(0, tk.END)
        self.format_combobox.set('')
        self.format_combobox['values'] = []
        self.clear_output()
        self.progress_bar['value'] = 0
        self.speed_var.set("")
        self.update_status("Ready")
        self.clear_thumbnail()
    
    def clear_output_text(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
    
    def copy_output_text(self):
        self.app.clipboard_clear()
        self.app.clipboard_append(self.output_text.get(1.0, tk.END))
    
    def save_output_log(self):
        file = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log Files", "*.log"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(self.output_text.get(1.0, tk.END))
    
    def show_output_context_menu(self, event):
        try:
            self.output_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.output_context_menu.grab_release()
    
    def toggle_controls(self, enable):
        state = tk.NORMAL if enable else tk.DISABLED
        self.url_entry.config(state=state)
        self.format_combobox.config(state=state)
    
    def update_status(self, message):
        self.status_var.set(message)
    
    def append_output(self, text):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
    
    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
    
    def show_thumbnail(self, url):
        self.clear_thumbnail()
        def fetch_thumb():
            try:
                img = get_video_thumbnail(url)
                if img:
                    # UI update in main thread
                    self.app.after(0, self._set_thumbnail, img)
            except:
                pass
        threading.Thread(target=fetch_thumb, daemon=True).start()

    def _set_thumbnail(self, img):
        self.thumbnail_image = img  # Keep reference
        self.thumbnail_label.config(image=img)
    
    def clear_thumbnail(self):
        self.thumbnail_label.config(image='')
        self.thumbnail_image = None
    
    def add_to_history(self, url):
        if url not in self.config["history"]:
            self.config["history"].insert(0, url)
            if len(self.config["history"]) > 10:
                self.config["history"] = self.config["history"][:10]
            save_config(self.config)
            self.setup_history_menu()
    
    def setup_history_menu(self):
        self.history_menu.delete(0, tk.END)
        for url in self.config["history"]:
            self.history_menu.add_command(
                label=url[:50] + ("..." if len(url) > 50 else ""),
                command=lambda u=url: self.load_from_history(u)
            )
        self.history_menu.add_separator()
        self.history_menu.add_command(label="Clear History", command=self.clear_history)
    
    def clear_history(self):
        self.config["history"] = []
        save_config(self.config)
        self.setup_history_menu()
    
    def load_from_history(self, url):
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)
    
    # -------- Menu Handlers --------
    def show_preferences(self):
        pref_window = ttk.Toplevel(self.app)
        pref_window.title("Preferences")
        pref_window.geometry("500x400")
        pref_window.resizable(False, False)
        
        # Theme selection
        ttk.Label(pref_window, text="Theme:").pack(pady=5)
        theme_var = tk.StringVar(value=self.config.get("theme", "superhero"))
        theme_menu = ttk.OptionMenu(
            pref_window, 
            theme_var, 
            theme_var.get(), 
            *["superhero", "darkly", "cyborg", "vapor", "solar", "minty"]
        )
        theme_menu.pack(fill=tk.X, padx=50, pady=5)
        
        # Language selection
        ttk.Label(pref_window, text="Language:").pack(pady=5)
        lang_var = tk.StringVar(value=self.config.get("language", "en"))
        lang_menu = ttk.OptionMenu(
            pref_window, 
            lang_var, 
            lang_var.get(), 
            *["en", "ar", "fr", "es", "de"]
        )
        lang_menu.pack(fill=tk.X, padx=50, pady=5)
        
        # Download path
        ttk.Label(pref_window, text="Default Download Path:").pack(pady=5)
        path_frame = ttk.Frame(pref_window)
        path_frame.pack(fill=tk.X, padx=50, pady=5)
        
        path_var = tk.StringVar(value=self.config.get("download_path", ""))
        ttk.Entry(path_frame, textvariable=path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            path_frame, 
            text="Browse", 
            command=lambda: self.browse_pref_folder(path_var),
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        # Format preference
        ttk.Label(pref_window, text="Default Quality Preference:").pack(pady=5)
        format_var = tk.StringVar(value=self.config.get("format_preference", "best"))
        ttk.OptionMenu(
            pref_window, 
            format_var, 
            format_var.get(), 
            *["best", "worst", "fastest", "smallest"]
        ).pack(fill=tk.X, padx=50, pady=5)
        
        # Save button
        ttk.Button(
            pref_window, 
            text="Save Preferences", 
            bootstyle=SUCCESS,
            command=lambda: self.save_preferences(
                theme_var.get(),
                lang_var.get(),
                path_var.get(),
                format_var.get()
            )
        ).pack(pady=20)
    
    def browse_pref_folder(self, path_var):
        folder = filedialog.askdirectory()
        if folder:
            path_var.set(folder)
    
    def save_preferences(self, theme, language, path, format_pref):
        self.config["theme"] = theme
        self.config["language"] = language
        self.config["download_path"] = path
        self.config["format_preference"] = format_pref
        save_config(self.config)
        
        # Apply theme change immediately
        self.style.theme_use(theme)
        messagebox.showinfo("Success", "Preferences saved successfully!")
    
    def change_theme(self, theme):
        self.style.theme_use(theme)
        self.config["theme"] = theme
        save_config(self.config)
    
    def change_language(self, language):
        # In a real app, you would implement proper internationalization
        self.config["language"] = language.lower()[:2]
        save_config(self.config)
        messagebox.showinfo("Info", "Language will change after restart")
    
    def show_batch_dialog(self):
        batch_window = ttk.Toplevel(self.app)
        batch_window.title("Batch Download")
        batch_window.geometry("600x400")
        
        ttk.Label(batch_window, text="Enter one URL per line:").pack(pady=5)
        
        text_frame = ttk.Frame(batch_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        text_scroll = ttk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        urls_text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            yscrollcommand=text_scroll.set
        )
        urls_text.pack(fill=tk.BOTH, expand=True)
        text_scroll.config(command=urls_text.yview)
        
        btn_frame = ttk.Frame(batch_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Download All", 
            bootstyle=SUCCESS,
            command=lambda: self.start_batch_download(urls_text.get("1.0", tk.END))
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            btn_frame, 
            text="Cancel", 
            bootstyle=DANGER,
            command=batch_window.destroy
        ).pack(side=tk.RIGHT, padx=10)
    
    def start_batch_download(self, urls_text):
        urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
        if not urls:
            messagebox.showerror("Error", "No URLs entered")
            return

        # Run batch download in a background thread
        threading.Thread(target=self._batch_download_thread, args=(urls,), daemon=True).start()

    def _batch_download_thread(self, urls):
        for url in urls:
            self.app.after(0, self.url_entry.delete, 0, tk.END)
            self.app.after(0, self.url_entry.insert, 0, url)
            self.app.after(0, self.fetch_formats)
            # Optionally, wait for formats to be fetched and then download
            # You may need to add synchronization if you want to automate the download step
    
    def check_for_updates(self):
        try:
            result = subprocess.run(
                ["yt-dlp", "--update"],
                capture_output=True, 
                text=True
            )
            
            if "up to date" in result.stdout.lower():
                messagebox.showinfo("Update", "yt-dlp is already up to date")
            else:
                messagebox.showinfo("Update", result.stdout)
        except Exception as e:
            messagebox.showerror("Update Error", f"Failed to check for updates: {str(e)}")
    
    def show_documentation(self):
        doc_window = ttk.Toplevel(self.app)
        doc_window.title("Documentation")
        doc_window.geometry("700x500")
        
        text_frame = ttk.Frame(doc_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_scroll = ttk.Scrollbar(text_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        doc_text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            yscrollcommand=text_scroll.set,
            font=('Arial', 10)
        )
        doc_text.pack(fill=tk.BOTH, expand=True)
        text_scroll.config(command=doc_text.yview)
        
        # Add documentation content
        docs = """
        Professional Video Downloader - Documentation
        
        1. Supported Websites:
        - YouTube
        - Facebook
        - Twitter
        - Instagram
        - TikTok
        - Vimeo
        - Dailymotion
        - Twitch
        - SoundCloud
        - Reddit
        - LinkedIn
        - Tumblr
        
        2. Basic Usage:
        - Paste a video URL in the input field
        - Click "Get Formats" to see available formats
        - Select your preferred format
        - Click "Download" to start downloading
        
        3. Advanced Features:
        - Audio Only: Extract audio only (MP3)
        - Subtitles: Download English subtitles if available
        - Quality Preference: Choose between best/worst quality
        - Batch Download: Download multiple videos at once
        
        4. Requirements:
        - yt-dlp must be installed and in your PATH
        - FFmpeg recommended for format conversion
        
        5. Troubleshooting:
        - If downloads fail, check your internet connection
        - Some sites may require cookies for private videos
        - Update yt-dlp regularly for latest fixes
        """
        
        doc_text.insert(tk.END, docs)
        doc_text.config(state=tk.DISABLED)
        
        btn_frame = ttk.Frame(doc_window)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Close", 
            command=doc_window.destroy
        ).pack()
    
    def show_about(self):
        about_window = ttk.Toplevel(self.app)
        about_window.title("About")
        about_window.geometry("400x300")
        about_window.resizable(False, False)
        
        ttk.Label(
            about_window, 
            text="Professional Video Downloader",
            font=('Arial', 14, 'bold')
        ).pack(pady=10)
        
        ttk.Label(
            about_window, 
            text="Version 2.0.0\n\n"
                 "A powerful video downloader supporting\n"
                 "multiple websites and formats.\n\n"
                 "Built with Python, yt-dlp, and Tkinter\n\n"
                 "© 2023 Video Downloader Team",
            justify=tk.CENTER
        ).pack(pady=10)
        
        ttk.Button(
            about_window, 
            text="Visit Website", 
            command=lambda: webbrowser.open("https://example.com")
        ).pack(pady=10)
        
        ttk.Button(
            about_window, 
            text="Close", 
            command=about_window.destroy
        ).pack()
    
    def check_yt_dlp_installed(self):
        try:
            subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                check=True
            )
        except:
            messagebox.showerror(
                "Error", 
                "yt-dlp is not installed or not in PATH.\n\n"
                "Please install yt-dlp first:\n"
                "https://github.com/yt-dlp/yt-dlp#installation"
            )
            self.app.after(100, self.app.destroy)
    
    def on_close(self):
        if self.download_thread and self.download_thread.is_alive():
            if messagebox.askokcancel(
                "Quit", 
                "A download is in progress. Are you sure you want to quit?"
            ):
                self.app.destroy()
        else:
            self.app.destroy()

    def on_merge_best_toggle(self):
        if self.merge_best_var.get():
            self.format_combobox.config(state="disabled")
            self.video_only_combobox.config(state="disabled")
            self.audio_only_combobox.config(state="disabled")
        else:
            self.format_combobox.config(state="readonly")
            self.video_only_combobox.config(state="readonly")
            self.audio_only_combobox.config(state="readonly")

    def on_url_drop(self, event):
        url = event.data.strip()
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)

# -------- Main Execution --------
if __name__ == "__main__":
    try:
        app = VideoDownloaderApp()
        app.app.mainloop()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        messagebox.showerror("Fatal Error", f"The application crashed:\n{str(e)}\n\n{tb}")
        sys.exit(1)

# Add this utility function:
def add_tooltip(widget, text):
    def on_enter(e):
        widget.tooltip = tk.Toplevel(widget)
        widget.tooltip.wm_overrideredirect(True)
        widget.tooltip.wm_geometry(f"+{e.x_root+10}+{e.y_root+10}")
        label = tk.Label(widget.tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
        label.pack()
    def on_leave(e):
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)

# Example usage after creating a button:
add_tooltip(self.url_entry, "Paste a video URL here")