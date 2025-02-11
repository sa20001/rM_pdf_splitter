import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from tqdm import tqdm
import os
import threading
import sys

def split_pdf(input_pdf, output_pdf, header_height, footer_height, display_pages, progress_var, progress_label):
    doc = fitz.open(input_pdf)
    output_doc = fitz.open()

    a4_width, a4_height = 595, 842
    content_height = a4_height - footer_height - header_height
    page_counter = 1

    total_pages = sum((int(page.rect.height) // content_height + 1) * (int(page.rect.width) // a4_width + 1) for page in doc)
    progress_var.set(0)

    tqdm_disabled = not sys.stdout  # Disable tqdm if there's no console (for release build)

    with tqdm(total=total_pages, desc="Splitting PDF", unit="page", disable=tqdm_disabled) as pbar:
        for page in doc:
            page_width = page.rect.width
            page_height = page.rect.height

            for y_offset in range(0, int(page_height), content_height):
                for x_offset in range(0, int(page_width), a4_width):
                    crop_rect = fitz.Rect(x_offset, y_offset, min(x_offset + a4_width, page_width), min(y_offset + content_height, page_height))
                    new_page = output_doc.new_page(width=a4_width, height=a4_height)
                    new_page.show_pdf_page(fitz.Rect(0, header_height, a4_width, header_height + content_height), doc, page.number, clip=crop_rect)

                    if display_pages:
                        text = f"Page {page_counter}/{total_pages}"
                        new_page.insert_text((a4_width / 2 - 20, a4_height - 20), text, fontsize=12, color=(0, 0, 0))
                    
                    pbar.update(1)
                    progress_var.set((page_counter / total_pages) * 100)
                    progress_label.config(text=f"{page_counter} page(s) done / {total_pages} total pages")
                    root.update_idletasks()
                    page_counter += 1
    
    output_doc.save(output_pdf)
    messagebox.showinfo("Success", f"PDF saved as {output_pdf}")

def browse_pdf():
    file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if file_path:
        pdf_path.set(file_path)

def drop_pdf(event):
    pdf_path.set(event.data.strip('{}'))

def update_header_slider(value):
    header_var.set(int(value))

def update_footer_slider(value):
    footer_var.set(int(value))

def threaded_process_pdf():
    input_file = pdf_path.get()
    if not input_file or not os.path.exists(input_file):
        messagebox.showerror("Error", "Please select a valid PDF file.")
        return
    
    output_file = os.path.splitext(input_file)[0] + "_split.pdf"
    thread = threading.Thread(target=split_pdf, args=(input_file, output_file, header_var.get(), footer_var.get(), display_var.get(), progress_var, progress_label))
    thread.start()

# UI Setup
root = TkinterDnD.Tk()
root.title("PDF Splitter")
root.geometry("400x420")

pdf_path = tk.StringVar()
header_var = tk.IntVar(value=15)
footer_var = tk.IntVar(value=15)
display_var = tk.BooleanVar(value=False)
progress_var = tk.DoubleVar()

tk.Label(root, text="Drag & Drop PDF or Browse").pack(pady=5)
pdf_entry = tk.Entry(root, textvariable=pdf_path, width=40)
pdf_entry.pack(pady=5)
pdf_entry.drop_target_register(DND_FILES)
pdf_entry.dnd_bind('<<Drop>>', drop_pdf)

browse_button = tk.Button(root, text="Browse", command=browse_pdf)
browse_button.pack(pady=5)

header_label = tk.Label(root, text="Header Height")
header_label.pack()
header_entry = tk.Entry(root, textvariable=header_var, width=5)
header_entry.pack()
header_slider = tk.Scale(root, from_=0, to=200, orient="horizontal", variable=header_var, command=update_header_slider)
header_slider.pack()

footer_label = tk.Label(root, text="Footer Height")
footer_label.pack()
footer_entry = tk.Entry(root, textvariable=footer_var, width=5)
footer_entry.pack()
footer_slider = tk.Scale(root, from_=0, to=200, orient="horizontal", variable=footer_var, command=update_footer_slider)
footer_slider.pack()

display_checkbox = tk.Checkbutton(root, text="Display Page Numbers", variable=display_var)
display_checkbox.pack()

progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress_bar.pack(pady=5, fill='x')

progress_label = tk.Label(root, text="0 page(s) done / 0 total pages")
progress_label.pack()

process_button = tk.Button(root, text="Split PDF", command=threaded_process_pdf)
process_button.pack(pady=10)

root.mainloop()