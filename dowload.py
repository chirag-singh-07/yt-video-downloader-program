import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp

class VideoDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Downloader")
        self.root.geometry("640x460")
        self.root.minsize(560, 400)

        # Apply a clean ttk theme
        self.style = ttk.Style()
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.download_dir = os.path.abspath("Downloaded_Videos")
        self.is_downloading = False

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="16 16 16 16")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title / Header
        title_label = ttk.Label(
            main_frame,
            text="Video Downloader",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(anchor=tk.W, pady=(0, 12))

        # URL Input Section
        url_frame = ttk.LabelFrame(main_frame, text=" Video URL ", padding="10 10 10 10")
        url_frame.pack(fill=tk.X, pady=(0, 10))

        url_inner = ttk.Frame(url_frame)
        url_inner.pack(fill=tk.X)

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_inner, textvariable=self.url_var, font=("Segoe UI", 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.url_entry.focus()

        # Add context menu (Cut/Copy/Paste)
        self._setup_context_menu(self.url_entry)

        paste_btn = ttk.Button(url_inner, text="Paste", width=7, command=self.paste_from_clipboard)
        paste_btn.pack(side=tk.LEFT, padx=(0, 4))

        clear_btn = ttk.Button(url_inner, text="Clear", width=7, command=lambda: self.url_var.set(""))
        clear_btn.pack(side=tk.LEFT)

        # Options Section (Download Location & Format)
        options_frame = ttk.LabelFrame(main_frame, text=" Options ", padding="10 10 10 10")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        # Save Folder row
        folder_row = ttk.Frame(options_frame)
        folder_row.pack(fill=tk.X, pady=(0, 6))

        folder_label = ttk.Label(folder_row, text="Save to:", width=10)
        folder_label.pack(side=tk.LEFT)

        self.folder_var = tk.StringVar(value=self.download_dir)
        self.folder_entry = ttk.Entry(folder_row, textvariable=self.folder_var, font=("Segoe UI", 9))
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        browse_btn = ttk.Button(folder_row, text="Browse...", width=10, command=self.browse_folder)
        browse_btn.pack(side=tk.LEFT)

        # Format row
        format_row = ttk.Frame(options_frame)
        format_row.pack(fill=tk.X)

        format_label = ttk.Label(format_row, text="Format:", width=10)
        format_label.pack(side=tk.LEFT)

        self.format_var = tk.StringVar(value="Best Quality Video (MP4)")
        format_combo = ttk.Combobox(
            format_row,
            textvariable=self.format_var,
            values=[
                "Best Quality Video (MP4)",
                "Audio Only (MP3)",
                "Audio Only (M4A)"
            ],
            state="readonly",
            width=26
        )
        format_combo.pack(side=tk.LEFT)

        # Action Button
        self.download_btn = ttk.Button(
            main_frame,
            text="Start Download",
            command=self.start_download_thread
        )
        self.download_btn.pack(fill=tk.X, pady=(4, 10))

        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text=" Progress ", padding="10 10 10 10")
        progress_frame.pack(fill=tk.BOTH, expand=True)

        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(2, 6))

        self.status_label = ttk.Label(
            progress_frame,
            text="Ready. Paste a link and click Start Download.",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(anchor=tk.W, pady=(0, 4))

        # Log / Detail output box
        self.log_text = tk.Text(
            progress_frame,
            height=6,
            wrap=tk.WORD,
            font=("Consolas", 8),
            state=tk.DISABLED,
            bg="#f9f9f9"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _setup_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.select_range(0, tk.END))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def paste_from_clipboard(self):
        try:
            clipboard_content = self.root.clipboard_get().strip()
            if clipboard_content:
                self.url_var.set(clipboard_content)
        except tk.TclError:
            pass

    def browse_folder(self):
        selected_dir = filedialog.askdirectory(initialdir=self.folder_var.get())
        if selected_dir:
            self.folder_var.set(os.path.abspath(selected_dir))

    def append_log(self, text):
        def _update():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, text + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        self.root.after(0, _update)

    def update_status(self, text):
        self.root.after(0, lambda: self.status_label.config(text=text))

    def update_progress(self, percent):
        self.root.after(0, lambda: self.progress_bar.config(value=percent))

    def start_download_thread(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter or paste a video URL.")
            return

        if self.is_downloading:
            messagebox.showinfo("Busy", "A download is already in progress.")
            return

        target_dir = self.folder_var.get().strip()
        if not target_dir:
            target_dir = os.path.abspath("Downloaded_Videos")
            self.folder_var.set(target_dir)

        os.makedirs(target_dir, exist_ok=True)

        self.is_downloading = True
        self.download_btn.config(state=tk.DISABLED)
        self.progress_bar.config(value=0)
        self.update_status("Starting download...")
        self.append_log(f"--- Downloading: {url} ---")

        # Run yt-dlp in a background daemon thread to keep UI fully responsive
        thread = threading.Thread(target=self._download_worker, args=(url, target_dir), daemon=True)
        thread.start()

    def progress_hook(self, d):
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            percent_str = d.get('_percent_str', '').strip()
            speed_str = d.get('_speed_str', '').strip()
            eta_str = d.get('_eta_str', '').strip()

            percent_clean = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).replace('%', '')
            try:
                percent = float(percent_clean)
                self.update_progress(percent)
            except ValueError:
                if total > 0:
                    percent = (downloaded / total) * 100
                    self.update_progress(percent)

            status_msg = f"Downloading: {percent_str} | Speed: {speed_str} | ETA: {eta_str}"
            self.update_status(status_msg)

        elif status == 'finished':
            self.update_progress(100)
            self.update_status("Download finished. Processing / Converting file...")
            self.append_log("File downloaded, finalizing...")

    def _download_worker(self, url, download_folder):
        selected_format = self.format_var.get()

        ydl_opts = {
            'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),
            'continuedl': True,
            'retries': 20,
            'fragment_retries': 20,
            'ignoreerrors': False,
            'progress_hooks': [self.progress_hook],
        }

        if "Audio Only (MP3)" in selected_format:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif "Audio Only (M4A)" in selected_format:
            ydl_opts.update({
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
            })
        else:
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Video')

            self.update_status("Download completed successfully!")
            self.append_log(f"Successfully saved: {title}\nFolder: {download_folder}")
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Download completed:\n{title}"))

        except Exception as e:
            err_msg = str(e)
            self.update_status("Download failed.")
            self.append_log(f"Error: {err_msg}")
            self.root.after(0, lambda: messagebox.showerror("Download Error", f"An error occurred:\n{err_msg}"))

        finally:
            self.is_downloading = False
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))


def main():
    root = tk.Tk()
    app = VideoDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
