import os
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from loguru import logger
from tkinterdnd2 import DND_FILES, TkinterDnD
from src.core import DEFAULT_MARGIN_MM, split_pdf
from src.tools.rm_pusher import push_template_to_rm
from src.consts import APP_DATA_DIR

LOGIN_DATA_PATH = APP_DATA_DIR / "login.json"


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip_window is not None:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            wraplength=280,
            padx=6,
            pady=4,
        )
        label.pack()

    def hide(self, event=None):
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class PushTemplateDialog:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("Push template to reMarkable")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()

        self.hostname_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.key_file_var = tk.StringVar()
        self.save_login_var = tk.BooleanVar(value=True)
        self.auth_mode_var = tk.StringVar(value="password")
        self.push_button = None
        self.spinner = None

        self._load_saved_login()
        self._build_ui()
        logger.debug("Opened push template dialog.")

    def _build_ui(self):
        container = ttk.Frame(self.window, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="IP / Hostname").grid(row=0, column=0, sticky="w")
        ttk.Entry(container, textvariable=self.hostname_var, width=34).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(container, text="User").grid(row=2, column=0, sticky="w")
        ttk.Entry(container, textvariable=self.username_var, width=34).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        auth_frame = ttk.LabelFrame(container, text="Authentication", padding=10)
        auth_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Radiobutton(auth_frame, text="Password", variable=self.auth_mode_var, value="password", command=self._refresh_auth_state).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(auth_frame, text="SSH key file", variable=self.auth_mode_var, value="key", command=self._refresh_auth_state).grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.password_label = ttk.Label(auth_frame, text="Password")
        self.password_label.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.password_entry = ttk.Entry(auth_frame, textvariable=self.password_var, width=28, show="*")
        self.password_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.key_label = ttk.Label(auth_frame, text="Login / key file")
        self.key_label.grid(row=3, column=0, sticky="w")
        key_row = ttk.Frame(auth_frame)
        key_row.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.key_file_entry = ttk.Entry(key_row, textvariable=self.key_file_var, width=24)
        self.key_file_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(key_row, text="Browse", command=self._browse_key_file).pack(side="left", padx=(6, 0))

        ttk.Checkbutton(container, text="Save login data", variable=self.save_login_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.spinner = ttk.Progressbar(container, mode="indeterminate")
        self.spinner.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.spinner.grid_remove()

        button_row = ttk.Frame(container)
        button_row.grid(row=7, column=0, columnspan=2, sticky="e")
        self.push_button = ttk.Button(button_row, text="Push", command=self._push)
        ttk.Button(button_row, text="Cancel", command=self.window.destroy).pack(side="right")
        self.push_button.pack(side="right", padx=(0, 8))

        self._refresh_auth_state()

    def _load_saved_login(self):
        if not LOGIN_DATA_PATH.exists():
            logger.debug("No saved login data found at {}.", LOGIN_DATA_PATH)
            return

        try:
            with LOGIN_DATA_PATH.open("r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
        except (OSError, json.JSONDecodeError):
            logger.warning("Saved login data at {} could not be read.", LOGIN_DATA_PATH)
            return

        self.hostname_var.set(data.get("hostname", ""))
        self.username_var.set(data.get("username", ""))
        self.auth_mode_var.set(data.get("auth_mode", "password"))
        self.password_var.set(data.get("password", ""))
        self.key_file_var.set(data.get("key_file", ""))
        logger.info("Loaded saved login data from {}.", LOGIN_DATA_PATH)

    def _browse_key_file(self):
        file_path = filedialog.askopenfilename(title="Select SSH key file")
        if file_path:
            self.key_file_var.set(file_path)
            self.auth_mode_var.set("key")
            self._refresh_auth_state()

    def _refresh_auth_state(self):
        uses_password = self.auth_mode_var.get() == "password"
        password_state = "normal" if uses_password else "disabled"
        key_state = "disabled" if uses_password else "normal"

        self.password_label.config(state=password_state)
        self.password_entry.config(state=password_state)
        self.key_label.config(state=key_state)
        self.key_file_entry.config(state=key_state)

    def _save_login(self):
        data = {
            "hostname": self.hostname_var.get().strip(),
            "username": self.username_var.get().strip(),
            "auth_mode": self.auth_mode_var.get(),
            "password": self.password_var.get(),
            "key_file": self.key_file_var.get().strip(),
        }
        try:
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            with LOGIN_DATA_PATH.open("w", encoding="utf-8") as file_handle:
                json.dump(data, file_handle, indent=4)
            logger.info("Saved login data to {}.", LOGIN_DATA_PATH)
        except OSError:
            logger.exception("Failed to save login data to {}.", LOGIN_DATA_PATH)
            raise

    def _set_busy(self, is_busy):
        if not self.window.winfo_exists():
            return

        if self.spinner is not None:
            if is_busy:
                self.spinner.grid()
                self.spinner.start(12)
            else:
                self.spinner.stop()
                self.spinner.grid_remove()

        if self.push_button is not None:
            self.push_button.config(state="disabled" if is_busy else "normal")

        logger.debug("Push dialog busy state set to {}.", is_busy)

    def _push(self):
        hostname = self.hostname_var.get().strip()
        username = self.username_var.get().strip()

        if not hostname or not username:
            logger.warning("Push requested with missing hostname or username.")
            messagebox.showerror("Error", "IP / hostname and user are required.", parent=self.window)
            return

        if self.auth_mode_var.get() == "password":
            password = self.password_var.get()
            key_file = None
            if not password:
                logger.warning("Password auth selected but password is empty.")
                messagebox.showerror("Error", "Password is required when password auth is selected.", parent=self.window)
                return
        else:
            password = None
            key_file = self.key_file_var.get().strip()
            if not key_file:
                logger.warning("Key auth selected but no key file was provided.")
                messagebox.showerror("Error", "A key file is required when SSH key auth is selected.", parent=self.window)
                return

        if self.save_login_var.get():
            self._save_login()

        self._set_busy(True)
        logger.info(
            "Starting template push for host={} user={} auth_mode={}.",
            hostname,
            username,
            self.auth_mode_var.get(),
        )

        def worker():
            try:
                logger.debug("Background push worker started.")
                push_template_to_rm(
                    hostname=hostname,
                    username=username,
                    password=password,
                    key_filename=key_file,
                )
                logger.success("Template push finished for {}.", hostname)
                self.parent.after(0, lambda: messagebox.showinfo("Success", "Template pushed to reMarkable.\nreMarkable will now reboot.", parent=self.parent))
                self.parent.after(0, self.window.destroy)
            except Exception as exc:
                logger.exception("Template push failed for {}.", hostname)
                self.parent.after(
                    0,
                    lambda error=exc: messagebox.showerror("Error", f"Push failed: {error}", parent=self.window),
                )
            finally:
                self.parent.after(0, lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()


class PdfSplitterApp:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("PDF Splitter")
        self.root.geometry("400x460")

        self.pdf_path = tk.StringVar()
        self.header_var = tk.DoubleVar(value=DEFAULT_MARGIN_MM)
        self.footer_var = tk.DoubleVar(value=DEFAULT_MARGIN_MM)
        self.use_default_margins_var = tk.BooleanVar(value=True)
        self.display_var = tk.BooleanVar(value=False)
        self.remove_blank_pages_var = tk.BooleanVar(value=True)
        self.progress_var = tk.DoubleVar()

        self._build_ui()
        self._build_menu()
        self.toggle_use_default_margins()
        logger.info("PDF Splitter UI initialized.")

    def _build_menu(self):
        menu_bar = tk.Menu(self.root)
        options_menu = tk.Menu(menu_bar, tearoff=0)
        options_menu.add_command(label="Push template to reMarkable...", command=self.open_push_template_dialog)
        menu_bar.add_cascade(label="Options", menu=options_menu)
        self.root.config(menu=menu_bar)
        logger.debug("Menu bar configured.")

    def _build_ui(self):
        tk.Label(self.root, text="Drag & Drop PDF or Browse").pack(pady=5)

        self.pdf_entry = tk.Entry(self.root, textvariable=self.pdf_path, width=40)
        self.pdf_entry.pack(pady=5)
        self.pdf_entry.drop_target_register(DND_FILES)
        self.pdf_entry.dnd_bind("<<Drop>>", self.drop_pdf)

        browse_button = tk.Button(self.root, text="Browse", command=self.browse_pdf)
        browse_button.pack(pady=5)

        tk.Label(self.root, text="Header Height (mm)").pack()
        self.header_entry = tk.Entry(self.root, textvariable=self.header_var, width=5)
        self.header_entry.pack()
        self.header_slider = tk.Scale(
            self.root,
            from_=0.0,
            to=200.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.header_var,
            command=self.update_header_slider,
        )
        self.header_slider.pack()

        tk.Label(self.root, text="Footer Height (mm)").pack()
        self.footer_entry = tk.Entry(self.root, textvariable=self.footer_var, width=5)
        self.footer_entry.pack()
        self.footer_slider = tk.Scale(
            self.root,
            from_=0.0,
            to=200.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.footer_var,
            command=self.update_footer_slider,
        )
        self.footer_slider.pack()

        use_default_checkbox = tk.Checkbutton(
            self.root,
            text=f"Use default margins ({DEFAULT_MARGIN_MM} mm)",
            variable=self.use_default_margins_var,
            command=self.toggle_use_default_margins,
        )
        use_default_checkbox.pack()

        display_checkbox = tk.Checkbutton(
            self.root,
            text="Display Page Numbers",
            variable=self.display_var,
        )
        display_checkbox.pack()

        remove_blank_pages_frame = tk.Frame(self.root)
        remove_blank_pages_frame.pack(pady=2)
        remove_blank_pages_checkbox = tk.Checkbutton(
            remove_blank_pages_frame,
            text="Remove blank pages",
            variable=self.remove_blank_pages_var,
        )
        remove_blank_pages_checkbox.pack(side="left")
        remove_blank_pages_help = tk.Label(remove_blank_pages_frame, text="?", fg="blue", cursor="question_arrow")
        remove_blank_pages_help.pack(side="left", padx=(6, 0))
        Tooltip(
            remove_blank_pages_help,
            "When enabled, blank pages created during the splitting process will be removed from the output PDF.",
        )

        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(pady=5, fill="x")

        self.progress_label = tk.Label(self.root, text="0 page(s) done / 0 total pages")
        self.progress_label.pack()

        process_button = tk.Button(self.root, text="Split PDF", command=self.threaded_process_pdf)
        process_button.pack(pady=10)

    def open_push_template_dialog(self):
        logger.info("Opening push template dialog.")
        PushTemplateDialog(self.root)

    def browse_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.pdf_path.set(file_path)
            logger.info("Selected input PDF: {}", file_path)

    def drop_pdf(self, event):
        self.pdf_path.set(event.data.strip("{}"))
        logger.info("Dropped input PDF: {}", self.pdf_path.get())

    def update_header_slider(self, value):
        self.header_var.set(float(value))

    def update_footer_slider(self, value):
        self.footer_var.set(float(value))

    def toggle_use_default_margins(self):
        if self.use_default_margins_var.get():
            self.header_var.set(DEFAULT_MARGIN_MM)
            self.footer_var.set(DEFAULT_MARGIN_MM)
            state = "disabled"
        else:
            state = "normal"

        self.header_entry.config(state=state)
        self.header_slider.config(state=state)
        self.footer_entry.config(state=state)
        self.footer_slider.config(state=state)
        logger.debug("Default margins toggled: {}.", self.use_default_margins_var.get())

    def threaded_process_pdf(self):
        input_file = self.pdf_path.get()
        if not input_file or not os.path.exists(input_file):
            logger.warning("Split requested without a valid PDF selected.")
            messagebox.showerror("Error", "Please select a valid PDF file.")
            return

        output_file = os.path.splitext(input_file)[0] + "_split.pdf"
        logger.info("Starting split thread for {} -> {}.", input_file, output_file)
        thread = threading.Thread(target=self._process_pdf, args=(input_file, output_file), daemon=True)
        thread.start()

    def _process_pdf(self, input_file, output_file):
        try:
            logger.debug("PDF split worker started.")
            split_pdf(
                input_file,
                output_file,
                self.header_var.get(),
                self.footer_var.get(),
                self.display_var.get(),
                rm_blank_pages=self.remove_blank_pages_var.get(),
                use_default_margins=self.use_default_margins_var.get(),
                progress_callback=self._update_progress,
                status_callback=self._update_status,
                completion_callback=self._show_success,
            )
        except ValueError as exc:
            logger.error("Invalid split configuration: {}", exc)
        except Exception as exc:
            logger.exception("Unexpected error while splitting PDF.")

    def _update_progress(self, current_page, total_pages):
        percent = (current_page / total_pages) * 100 if total_pages else 0
        self.root.after(0, lambda: self.progress_var.set(percent))
        if current_page == 1 or current_page == total_pages or current_page % 10 == 0:
            logger.info("Split progress: {}/{} pages ({}%).", current_page, total_pages, round(percent, 1))

    def _update_status(self, current_page, total_pages):
        self.root.after(
            0,
            lambda: self.progress_label.config(text=f"Split {current_page} / {total_pages} pages"),
        )
        self.root.after(0, self.root.update_idletasks)

    def _show_success(self, output_pdf, total_pages):
        logger.success("Split completed successfully: {} ({} pages).", output_pdf, total_pages)
        self.root.after(
            0,
            lambda: messagebox.showinfo(
                "Success",
                f"PDF saved as\n{output_pdf}\n\nTotal pages: {total_pages}"
            )
        )

    def run(self):
        self.root.mainloop()


def launch_app():
    PdfSplitterApp().run()