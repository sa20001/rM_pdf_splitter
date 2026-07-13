import fitz
from typing import Any
from pathlib import Path
import tempfile
from loguru import logger

def page_is_visually_blank(page, threshold=250):
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
    finally:
        fitz.TOOLS.mupdf_display_errors(True)
        fitz.TOOLS.mupdf_display_warnings(True)

    samples = pix.samples

    # Return False if any pixel is not close to white
    for i in range(0, len(samples), pix.n):
        if any(samples[i + j] < threshold for j in range(min(3, pix.n))):
            return False
    return True


def splitter(task:tuple[int, list, Any]):
    pageNumber, parameters , input_pdf = task

    logger.debug(f"Processing page {pageNumber} of {input_pdf}")

    doc = fitz.open(input_pdf)
    page = doc[pageNumber]
    a4_width, a4_height, content_height, header_height_pt, rm_blank_pages = parameters

    page_width = page.rect.width
    page_height = page.rect.height
    output_doc = fitz.open() # Splitted PDF

    page_counter = 0

    y_offset = 0.0
    while y_offset < page_height:
        x_offset = 0.0
        while x_offset < page_width:
            crop_rect = fitz.Rect(
                x_offset,
                y_offset,
                min(x_offset + a4_width, page_width),
                min(y_offset + content_height, page_height),
            )
            crop_w = crop_rect.width
            crop_h = crop_rect.height

            new_page = output_doc.new_page(width=a4_width, height=a4_height)
            x_dest = (a4_width - crop_w) / 2
            y_dest = header_height_pt
            dest_rect = fitz.Rect(x_dest, y_dest, x_dest + crop_w, y_dest + crop_h)

            new_page.show_pdf_page(dest_rect, doc, page.number, clip=crop_rect)

            if rm_blank_pages and page_is_visually_blank(new_page):
                output_doc.delete_page(page_counter)

            page_counter += 1
            x_offset += a4_width
        y_offset += content_height
    
    # Save the temp files
    temp_file = Path(tempfile.gettempdir()) / f"page_{pageNumber}.pdf"
    output_doc.save(temp_file)
    output_doc.close()
    doc.close()

    return str(temp_file)