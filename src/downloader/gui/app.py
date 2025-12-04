import os
import queue
import re
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter

from .. import parsers, settings_manager
from ..core import Downloader
from ..download_manager import DownloadManager
from ..protocol import ProgressQueue
from ..utils import clean_doi

from .doi_frame import DoiFrame
from .right_frame import RightFrame
from .settings_frame import SettingsFrame


def get_asset_path(file_name: str) -> Path:
    """Gets the correct path for an asset (dev vs. bundled)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / file_name
    else:
        # Go up 3 levels from src/downloader/gui/app.py to project root
        return Path(__file__).parent.parent.parent.parent / file_name


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDF Retriever")

        self._load_icon()
        self.geometry("1000x600")
        self.is_downloading = False
        self.progress_queue: ProgressQueue = queue.Queue()
        self.download_manager = None
        self.total_dois_to_download = 0
        self.processed_doi_count = 0
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._create_frames()
        self.load_settings()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _load_icon(self):
        self.icon_path: Path | None = None
        try:
            icon_path = get_asset_path("assets/favicon.ico")
            if icon_path.exists():
                self.iconbitmap(icon_path)
                self.icon_path = icon_path
            else:
                print(f"Icon not found at: {icon_path}")
        except Exception as e:
            print(f"Error loading icon: {e}")

    def _create_frames(self):
        self.left_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nswe")
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(1, weight=0)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        self.settings_frame = SettingsFrame(master=self.left_frame, controller=self)
        self.settings_frame.grid(row=0, column=0, sticky="nswe")
        
        self.doi_frame = DoiFrame(master=self.left_frame, controller=self)
        self.doi_frame.grid(row=1, column=0, sticky="new")
        
        self.copyright_label = customtkinter.CTkLabel(
            self.left_frame,
            text="Copyright © 2025 Diffon Calungsod. All rights reserved.",
            font=("Roboto", 10),
            text_color="gray50",
        )
        self.copyright_label.grid(row=2, column=0, padx=10, pady=(5, 5), sticky="ew")

        self.right_frame = RightFrame(master=self, controller=self)
        self.right_frame.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)

    def on_closing(self):
        """Gracefully cancel all downloads and close the app."""
        if self.is_downloading and self.download_manager:
            if not messagebox.askyesno(
                "Download in Progress", "Cancel all downloads and exit?"
            ):
                return
        try:
            if self.download_manager and self.download_manager.is_alive():
                self.log_message("Closing... cancelling active downloads.", "orange")
                self.download_manager.cancel_download()
                self.download_manager.join()
        except Exception as e:
            print(f"Error during shutdown: {e}")
        self.destroy()

    def toggle_ui_lock(self, locked: bool):
        self.is_downloading = locked
        has_doi_text = self.doi_frame.doi_textbox.get("1.0", "end-1c").strip()
        self.settings_frame.set_locked(locked)
        self.doi_frame.set_locked(locked)
        self.right_frame.set_locked(locked, bool(has_doi_text))

        if locked:
            self.right_frame.start_download_button.grid_forget()
            self.right_frame.cancel_download_button.grid(
                row=0, column=0, padx=10, pady=10, sticky="we"
            )
        else:
            self.right_frame.cancel_download_button.grid_forget()
            self.right_frame.start_download_button.grid(
                row=0, column=0, padx=10, pady=10, sticky="we"
            )
            self.update_doi_input_widgets()
            self.check_failed_dois_file()

    def browse_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.settings_frame.output_dir_entry.delete(0, "end")
            self.settings_frame.output_dir_entry.insert(0, directory)
            self.check_failed_dois_file()

    def load_settings(self):
        settings = settings_manager.read_config_raw()
        default_output_dir = str(Path.home() / "Downloads" / "PDF_Retriever")
        output_dir = settings.get("output_dir", default_output_dir) if settings else default_output_dir
        if not output_dir:
            output_dir = default_output_dir
            
        self.settings_frame.output_dir_entry.insert(0, output_dir)
        self.settings_frame.email_entry.insert(0, settings.get("email", "") if settings else "")
        self.settings_frame.core_api_key_entry.insert(0, settings.get("core_api_key", "") if settings else "")
        
        verify_ssl = settings.get("verify_ssl", True) if settings else True
        if not verify_ssl:
            self.settings_frame.ssl_checkbox.select()
            
        max_workers = settings.get("max_workers", 10) if settings else 10
        self.settings_frame.parallel_downloads_slider.set(max_workers)
        self.update_parallel_downloads_label(max_workers)
        
        show_popup = settings.get("show_completion_popup", True) if settings else True
        if show_popup:
            self.settings_frame.show_completion_popup_checkbox.select()
            
        self.check_failed_dois_file()

    def save_settings(self):
        settings = {
            "output_dir": self.settings_frame.output_dir_entry.get(),
            "email": self.settings_frame.email_entry.get(),
            "core_api_key": self.settings_frame.core_api_key_entry.get(),
            "verify_ssl": not self.settings_frame.ssl_checkbox.get(),
            "max_workers": int(self.settings_frame.parallel_downloads_slider.get()),
            "show_completion_popup": self.settings_frame.show_completion_popup_checkbox.get(),
        }
        settings_manager.write_config_raw(settings)
        self.log_message("Settings saved.")

    def clear_settings(self):
        settings_manager.delete_config_raw()
        self.settings_frame.output_dir_entry.delete(0, "end")
        self.settings_frame.email_entry.delete(0, "end")
        self.settings_frame.core_api_key_entry.delete(0, "end")
        self.settings_frame.ssl_checkbox.deselect()
        self.settings_frame.parallel_downloads_slider.set(10)
        self.update_parallel_downloads_label(10)
        self.settings_frame.show_completion_popup_checkbox.select()
        self.check_failed_dois_file()
        default_dir = str(Path.home() / "Downloads" / "PDF_Retriever")
        self.settings_frame.output_dir_entry.insert(0, default_dir)

    def update_parallel_downloads_label(self, value):
        self.settings_frame.parallel_downloads_label.configure(
            text=f"Parallel Downloads: {int(value)}"
        )

    def toggle_email_visibility(self):
        if self.settings_frame.show_email_checkbox.get():
            self.settings_frame.email_entry.configure(show="")
        else:
            self.settings_frame.email_entry.configure(show="*")

    def load_dois_from_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            try:
                dois = parsers.extract_dois_from_file(filepath)
                self.doi_frame.doi_textbox.delete("1.0", "end")
                self.doi_frame.doi_textbox.insert("1.0", "\n".join(dois))
                self.update_doi_input_widgets()
            except Exception as e:
                self.log_message(f"Error reading file: {e}")

    def get_dois_from_textbox(self):
        raw_text = self.doi_frame.doi_textbox.get("1.0", "end")
        dois = set()
        for token in re.split(r"[,\s\n]+", raw_text):
            if cleaned := clean_doi(token.strip()):
                dois.add(cleaned)
        return sorted(list(dois))

    def update_doi_input_widgets(self, event=None):
        dois = self.get_dois_from_textbox()
        self.doi_frame.doi_input_label.configure(text=f"DOI Input ({len(dois)})")
        if not self.is_downloading:
            if self.doi_frame.doi_textbox.get("1.0", "end-1c").strip():
                self.right_frame.start_download_button.configure(
                    state="normal", fg_color=("#2CC985", "#2CC985")
                )
            else:
                self.right_frame.start_download_button.configure(
                    state="disabled", fg_color=("gray50", "gray50")
                )

    def cancel_download(self):
        """Cancel all running and pending downloads."""
        if self.download_manager and self.download_manager.is_alive():
            self.log_message("--- Cancel request received... ---", "orange")
            self.download_manager.cancel_download()

    def start_download(self):
        self.toggle_ui_lock(True)
        self.right_frame.progressbar.set(0)
        self.right_frame.progress_label.configure(text="0%")
        self.check_failed_dois_file()

        dois = self.get_dois_from_textbox()
        self.total_dois_to_download = len(dois)
        self.processed_doi_count = 0

        if not dois:
            self.log_message("No DOIs to download.")
            self.toggle_ui_lock(False)
            return

        settings = {
            "output_dir": self.settings_frame.output_dir_entry.get(),
            "email": self.settings_frame.email_entry.get(),
            "core_api_key": self.settings_frame.core_api_key_entry.get(),
            "verify_ssl": not self.settings_frame.ssl_checkbox.get(),
            "max_workers": int(self.settings_frame.parallel_downloads_slider.get()),
        }

        output_dir = settings["output_dir"]
        if not output_dir:
            self.log_message("Error: Output directory is not set.", "red")
            self.toggle_ui_lock(False)
            return

        try:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.log_message(f"Error creating output dir: {e}", "red")
            self.toggle_ui_lock(False)
            return

        failed_dois_path = Path(output_dir) / "failed_dois.txt"
        try:
            failed_dois_path.unlink(missing_ok=True)
        except Exception as e:
            self.log_message(f"Could not clear old fail log: {e}", "orange")

        self.download_manager = DownloadManager(
            settings, self.progress_queue, dois, failed_dois_path
        )
        self.download_manager.start()

        self.after(100, self.poll_progress_queue)

    def _handle_finished_status(self, msg):
        status = msg.get("status")
        self.toggle_ui_lock(False)
        self.check_failed_dois_file()

        if status == "cancelled":
            summary_msg = msg.get("message", "Download Cancelled.")
            self.log_message(f"--- {summary_msg} ---", "red")
            if self.settings_frame.show_completion_popup_checkbox.get():
                self.show_completion_popup("Download Cancelled", summary_msg)

        self.download_manager = None

    def _handle_start_status(self, msg):
        self.log_message(msg.get("message"))

    def _handle_complete_status(self, msg):
        summary_msg = msg.get("message")
        log_msg = f"--- Download Complete: {summary_msg.replace('Success:', 'S:').replace('Skipped:', 'K:').replace('Failed:', 'F:').replace(chr(10), ' ')} ---"
        self.log_message(log_msg, "light_blue")
        if self.settings_frame.show_completion_popup_checkbox.get():
            self.show_completion_popup("Download Complete", summary_msg)

    def _handle_critical_error_status(self, msg):
        self.log_message(f"A critical error occurred: {msg.get('message')}", "red")

    def _handle_default_status(self, msg):
        self.processed_doi_count += 1
        self._log_download_result(msg)
        if self.total_dois_to_download > 0:
            progress_value = self.processed_doi_count / self.total_dois_to_download
            self.right_frame.progressbar.set(progress_value)
            self.right_frame.progress_label.configure(text=f"{int(progress_value * 100)}%")

    def _handle_progress_update(self, msg):
        status = msg.get("status")
        if status == "start":
            self._handle_start_status(msg)
        elif status == "complete":
            self._handle_complete_status(msg)
        elif status == "critical_error":
            self._handle_critical_error_status(msg)
        else:
            self._handle_default_status(msg)

    def _process_queue_item(self):
        """Process a single item from the queue. Returns True if finished/cancelled."""
        try:
            msg = self.progress_queue.get_nowait()
            status = msg.get("status")

            if status == "finished" or status == "cancelled":
                self._handle_finished_status(msg)
                return True
            else:
                self._handle_progress_update(msg)
                return False
        except queue.Empty:
            return False

    def poll_progress_queue(self):
        try:
            while not self.progress_queue.empty():
                if self._process_queue_item():
                    return
        except Exception as e:
            self.log_message(f"Error in GUI queue poller: {e}", "red")
        finally:
            if self.download_manager and self.download_manager.is_alive():
                self.after(100, self.poll_progress_queue)
            elif self.is_downloading:
                self.toggle_ui_lock(False)

    def show_completion_popup(self, title, message):
        messagebox.showinfo(title, message)

    def _log_download_result(self, result: dict):
        status = result.get("status", "failed")
        citation = result.get("citation", result.get("doi", "Unknown"))

        self.right_frame.log_textbox.configure(state="normal")

        if status == "success":
            source = result.get("source", "Unknown")
            self.right_frame.log_textbox.insert("end", f"Success ({source}): ", "green")
            self.right_frame.log_textbox.insert("end", f"{citation}\n")
        elif status == "skipped":
            self.right_frame.log_textbox.insert("end", "Skipped (Exists): ", "light_blue")
            self.right_frame.log_textbox.insert("end", f"{citation}\n")
        else:
            self.right_frame.log_textbox.insert("end", "Failed: ", "red")
            self.right_frame.log_textbox.insert("end", f"{citation}\n", "red")

        self.right_frame.log_textbox.configure(state="disabled")
        self.right_frame.log_textbox.see("end")

    def log_message(self, message, tag=None):
        self.right_frame.log_textbox.configure(state="normal")
        if tag:
            self.right_frame.log_textbox.insert("end", message + "\n", tag)
        else:
            self.right_frame.log_textbox.insert("end", message + "\n")
        self.right_frame.log_textbox.configure(state="disabled")
        self.right_frame.log_textbox.see("end")

    def log_status_message(self, name, status, message):
        self.right_frame.log_textbox.configure(state="normal")
        self.right_frame.log_textbox.insert("end", f"{name:<20} ")
        if status == "OK":
            self.right_frame.log_textbox.insert("end", f"{status:<8}", "green")
        else:
            self.right_frame.log_textbox.insert("end", f"{status:<8}", "red")
        self.right_frame.log_textbox.insert("end", f" {message}\n")
        self.right_frame.log_textbox.configure(state="disabled")
        self.right_frame.log_textbox.see("end")

    def clear_log(self):
        self.right_frame.log_textbox.configure(state="normal")
        self.right_frame.log_textbox.delete("1.0", "end")
        self.right_frame.log_textbox.configure(state="disabled")
        self.log_message("Log cleared.")

    def _is_valid_failed_dois_file(self, fp: Path) -> bool:
        if not fp.exists():
            return False
        try:
            content = fp.read_text(encoding="utf-8").strip()
            return len(content) > 5 and bool(re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", content, re.I))
        except Exception:
            return False

    def check_failed_dois_file(self):
        """Enable 'View Failed' and 'Retry Failed' buttons if file is valid."""
        output_dir = self.settings_frame.output_dir_entry.get()
        if not output_dir:
            self._set_failed_buttons_state("disabled")
            return

        fp = Path(output_dir) / "failed_dois.txt"
        is_valid_file = self._is_valid_failed_dois_file(fp)

        if not self.is_downloading:
            state = "normal" if is_valid_file else "disabled"
            self._set_failed_buttons_state(state)

    def _set_failed_buttons_state(self, state):
        self.right_frame.view_failed_button.configure(state=state)
        self.right_frame.retry_failed_button.configure(state=state)

    def retry_failed_dois(self):
        output_dir = self.settings_frame.output_dir_entry.get()
        fp = Path(output_dir) / "failed_dois.txt"

        if not fp.exists():
            self.log_message("No failed DOIs file found to retry.", "orange")
            return

        try:
            with open(fp, encoding="utf-8") as f:
                failed_dois_set = {line.strip() for line in f if line.strip()}

            failed_dois = sorted(list(failed_dois_set))

            if not failed_dois:
                self.log_message("failed_dois.txt is empty. Nothing to retry.", "light_blue")
                return

            self.log_message(f"Loading {len(failed_dois)} failed DOIs for retry...", "light_blue")
            self.doi_frame.doi_textbox.delete("1.0", "end")
            self.doi_frame.doi_textbox.insert("1.0", "\n".join(failed_dois))
            self.update_doi_input_widgets()
            self.start_download()

        except Exception as e:
            self.log_message(f"Error reading failed_dois.txt: {e}", "red")

    def view_failed(self):
        output_dir = Path(self.settings_frame.output_dir_entry.get())
        if not output_dir.is_dir():
            self.log_message("Error: Output directory is not set or does not exist.", "red")
            return

        fp = output_dir / "failed_dois.txt"
        if not fp.exists():
            self.log_message(f"Error: File not found: {fp}", "red")
            self.check_failed_dois_file()
            return

        try:
            if sys.platform == "win32":
                os.startfile(fp)
            elif sys.platform == "darwin":
                os.system(f'open "{fp}"')
            else:
                os.system(f'xdg-open "{fp}"')
        except Exception as e:
            self.log_message(f"Error opening failed DOIs file: {e}", "red")

    def open_output_folder(self):
        output_dir = self.settings_frame.output_dir_entry.get()
        if output_dir:
            if not Path(output_dir).exists():
                self.log_message(f"Error: Output directory does not exist: {output_dir}", "red")
                return
            if sys.platform == "win32":
                os.startfile(output_dir)
            elif sys.platform == "darwin":
                os.system(f'open "{output_dir}"')
            else:
                os.system(f'xdg-open "{output_dir}"')
        else:
            self.log_message("Error: Output directory is not set.", "red")

    def test_status(self):
        test_thread = threading.Thread(target=self.test_status_thread)
        test_thread.start()

    def test_status_thread(self):
        self.log_message("--- Testing System Status ---")
        settings = {
            "output_dir": self.settings_frame.output_dir_entry.get(),
            "email": self.settings_frame.email_entry.get(),
            "core_api_key": self.settings_frame.core_api_key_entry.get(),
            "verify_ssl": not self.settings_frame.ssl_checkbox.get(),
        }
        output_dir = settings["output_dir"]
        if not output_dir:
            self.log_message("Error: Output directory is not set.", "red")
            return

        downloader = Downloader(
            output_dir=settings["output_dir"],
            email=settings["email"],
            core_api_key=settings.get("core_api_key"),
            verify_ssl=settings["verify_ssl"],
        )
        results = downloader.test_connections()
        results.sort(key=lambda r: r.get("name", "Z_Fallback"))

        self.log_message(f"{'Source':<20} {'Status':<8} {'Details'}")
        self.log_message("-" * 50)
        for result in results:
            status = "OK" if result.get("status") else "FAILED"
            self.after(
                0,
                self.log_status_message,
                result.get("name"),
                status,
                result.get("message"),
            )
