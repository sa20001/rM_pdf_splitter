import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from tqdm import tqdm
import os
import threading
import sys
import math
from tools import page_is_visually_blank 

# Default margins in millimetres used when the 'Use default margins' option is enabled
# It takes the A4 remarkable template values and converts them to mm
DEFAULT_MARGIN_MM = 0.0


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

def split_pdf(input_pdf, output_pdf, header_height, footer_height, display_pages, progress_var, progress_label, rmBlank, use_default_margins=False):
    doc = fitz.open(input_pdf)
    output_doc = fitz.open()

    # Convert header/footer from mm to points (1 mm = 72 / 25.4 points)
    mm_to_pt = 72.0 / 25.4
    if use_default_margins:
        header_height_pt = DEFAULT_MARGIN_MM * mm_to_pt
        footer_height_pt = DEFAULT_MARGIN_MM * mm_to_pt
    else:
        header_height_pt = header_height * mm_to_pt
        footer_height_pt = footer_height * mm_to_pt

    a4_width, a4_height = 595.0, 842.0 # A4 size in points
    content_height = a4_height - footer_height_pt - header_height_pt
    if content_height <= 0:
        messagebox.showerror("Error", "Header and footer are too large for an A4 page.")
        return
    page_counter = 1

    # Use math.ceil to compute exact number of tiles per page (no off-by-one)
    total_pages = sum(math.ceil(page.rect.height / content_height) * math.ceil(page.rect.width / a4_width) for page in doc)
    progress_var.set(0)

    tqdm_disabled = not sys.stdout  # Disable tqdm if there's no console (for release build)

    with tqdm(total=total_pages, desc="Processing PDF", unit="page", disable=tqdm_disabled) as pbar:
        
        # TODO: check if multithreading can be done (or if it causes havok with page ordering)
        for page in doc:
            page_width = page.rect.width
            page_height = page.rect.height

            y_offset = 0.0
            while y_offset < page_height:
                x_offset = 0.0
                while x_offset < page_width:
                    crop_rect = fitz.Rect(x_offset, y_offset, min(x_offset + a4_width, page_width), min(y_offset + content_height, page_height))
                    crop_w = crop_rect.width
                    crop_h = crop_rect.height

                    # Create A4 page and render the cropped region at its real size (avoid stretching).
                    new_page = output_doc.new_page(width=a4_width, height=a4_height) # create a new blank A4 page in the output PDF

                    # Center the crop horizontally and place it right below the header vertically
                    x_dest = (a4_width - crop_w) / 2
                    y_dest = header_height_pt
                    dest_rect = fitz.Rect(x_dest, y_dest, x_dest + crop_w, y_dest + crop_h)

                    new_page.show_pdf_page(dest_rect, doc, page.number, clip=crop_rect) # copies the the clipped content to the blank A4 page
                    
                    blank = page_is_visually_blank(new_page)
                    if blank:
                        total_pages -= 1  # Decrement total_pages if a blank page is detected
                        pageToRemove = page_counter -1
                        print(f"\nPage {page_counter} is blank, it will be removed from the output PDF.")
                        output_doc.delete_page(pageToRemove)
                        page_counter -= 1  # Decrement page_counter to account for the removed page
                    
                    pbar.update(1)
                    progress_var.set((page_counter / total_pages) * 100)
                    progress_label.config(text=f"{page_counter} page(s) done / {total_pages} total pages")
                    root.update_idletasks()
                    page_counter += 1

                    x_offset += a4_width
                y_offset += content_height

    total_pages = len(output_doc)
    if display_pages:
        for page_num, page in enumerate(output_doc, start=1):
                text = f"{page_num}/{total_pages}"
                page.insert_text(
                    (a4_width / 2 - 20, a4_height - 20),
                    text,
                    fontsize=12,
                    color=(0, 0, 0),
                )

    output_doc.save(output_pdf)
    print("PDF processing completed.")
    messagebox.showinfo("Success", f"PDF saved as {output_pdf}")

def browse_pdf():
    file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if file_path:
        pdf_path.set(file_path)

def drop_pdf(event):
    pdf_path.set(event.data.strip('{}'))

def update_header_slider(value):
    header_var.set(float(value))

def update_footer_slider(value):
    footer_var.set(float(value))

def threaded_process_pdf():
    input_file = pdf_path.get()
    if not input_file or not os.path.exists(input_file):
        messagebox.showerror("Error", "Please select a valid PDF file.")
        return
    
    output_file = os.path.splitext(input_file)[0] + "_split.pdf"
    thread = threading.Thread(target=split_pdf, args=(input_file, output_file, header_var.get(), footer_var.get(), display_var.get(), progress_var, progress_label, remove_blank_pages_var.get() , use_default_margins_var.get()))
    thread.start()

def toggle_use_default_margins():
    """Disable/enable header/footer inputs and set default values when enabled."""
    if use_default_margins_var.get():
        header_var.set(DEFAULT_MARGIN_MM)
        footer_var.set(DEFAULT_MARGIN_MM)
        state = 'disabled'
    else:
        state = 'normal'

    # The widgets exist by the time this runs (called from UI), so it's safe to configure them
    header_entry.config(state=state)
    header_slider.config(state=state)
    footer_entry.config(state=state)
    footer_slider.config(state=state)

# UI Setup
root = TkinterDnD.Tk()
root.title("PDF Splitter")
root.geometry("400x460")

pdf_path = tk.StringVar()
header_var = tk.DoubleVar(value=DEFAULT_MARGIN_MM)
footer_var = tk.DoubleVar(value=DEFAULT_MARGIN_MM)
use_default_margins_var = tk.BooleanVar(value=True)
display_var = tk.BooleanVar(value=False)
progress_var = tk.DoubleVar()

tk.Label(root, text="Drag & Drop PDF or Browse").pack(pady=5)
pdf_entry = tk.Entry(root, textvariable=pdf_path, width=40)
pdf_entry.pack(pady=5)
pdf_entry.drop_target_register(DND_FILES)
pdf_entry.dnd_bind('<<Drop>>', drop_pdf)

browse_button = tk.Button(root, text="Browse", command=browse_pdf)
browse_button.pack(pady=5)

header_label = tk.Label(root, text="Header Height (mm)")
header_label.pack()
header_entry = tk.Entry(root, textvariable=header_var, width=5)
header_entry.pack()
header_slider = tk.Scale(root, from_=0.0, to=200.0, resolution=0.1, orient="horizontal", variable=header_var, command=update_header_slider)
header_slider.pack()

footer_label = tk.Label(root, text="Footer Height (mm)")
footer_label.pack()
footer_entry = tk.Entry(root, textvariable=footer_var, width=5)
footer_entry.pack()
footer_slider = tk.Scale(root, from_=0.0, to=200.0, resolution=0.1, orient="horizontal", variable=footer_var, command=update_footer_slider)
footer_slider.pack()

use_default_checkbox = tk.Checkbutton(root, text=f"Use default margins ({DEFAULT_MARGIN_MM} mm)", variable=use_default_margins_var, command=toggle_use_default_margins)
use_default_checkbox.pack()
# Apply the initial state so header/footer inputs are disabled at startup
toggle_use_default_margins()

display_checkbox = tk.Checkbutton(root, text="Display Page Numbers", variable=display_var)
display_checkbox.pack()

remove_blank_pages_var = tk.BooleanVar(value=True)
remove_blank_pages_frame = tk.Frame(root)
remove_blank_pages_frame.pack(pady=2)
remove_blank_pages_checkbox = tk.Checkbutton(remove_blank_pages_frame, text="Remove blank pages", variable=remove_blank_pages_var)
remove_blank_pages_checkbox.pack(side="left")
remove_blank_pages_help = tk.Label(remove_blank_pages_frame, text="?", fg="blue", cursor="question_arrow")
remove_blank_pages_help.pack(side="left", padx=(6, 0))
Tooltip(remove_blank_pages_help, "When enabled, blank pages created during the splitting process will be removed from the output PDF.")

progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress_bar.pack(pady=5, fill='x')

progress_label = tk.Label(root, text="0 page(s) done / 0 total pages")
progress_label.pack()

process_button = tk.Button(root, text="Split PDF", command=threaded_process_pdf)
process_button.pack(pady=10)

root.mainloop()