import sys
from multiprocessing import Pool
from typing import Any
from pathlib import Path
import fitz  # PyMuPDF
from tqdm import tqdm
from loguru import logger
from src.tools.tools import splitter


# Default margins in millimetres used when the 'Use default margins' option is enabled.
# It takes the A4 remarkable template values and converts them to mm.
DEFAULT_MARGIN_MM = 0.0

def split_pdf(
    input_pdf,
    output_pdf,
    header_height,
    footer_height,
    display_pages,
    rm_blank_pages=True,
    use_default_margins=False,
    progress_callback=None,
    status_callback=None,
    completion_callback=None,
):
    logger.info("Starting PDF split: {} -> {}", input_pdf, output_pdf)

    mm_to_pt = 72.0 / 25.4
    if use_default_margins:
        header_height_pt = DEFAULT_MARGIN_MM * mm_to_pt
        footer_height_pt = DEFAULT_MARGIN_MM * mm_to_pt
    else:
        header_height_pt = header_height * mm_to_pt
        footer_height_pt = footer_height * mm_to_pt

    a4_width, a4_height = 595.0, 842.0
    content_height = a4_height - footer_height_pt - header_height_pt
    if content_height <= 0:
        logger.error(
            "Invalid margins: header={} mm footer={} mm make content height non-positive.",
            header_height,
            footer_height,
        )
        raise ValueError("Header and footer are too large for an A4 page.")
    

    parameters = [a4_width, a4_height, content_height, header_height_pt, rm_blank_pages]

    # Build items for imap for parallel processing
    jobs:list[tuple[int, list, Any]] = []
    doc = fitz.open(input_pdf)
    nPages = len(doc)
    logger.debug(
        "Input PDF opened. pages={} content_height_pt={:.2f} use_default_margins={} rm_blank_pages={}",
        nPages,
        content_height,
        use_default_margins,
        rm_blank_pages,
    )
    for page_num in range(nPages):
        jobs.append((page_num, parameters, input_pdf))
    
    
    output_doc = fitz.open() # Splitted PDF
    temp_files = []

    tqdm_disabled = not sys.stdout
    logger.info("Processing pages in parallel worker pool.")
    with Pool() as pool:
        for index, temp_file in enumerate(
            tqdm(
                pool.imap(splitter, jobs),
                total=nPages,
                desc="Processing PDF",
                unit="page",
                disable=tqdm_disabled,
            ),
            start=1,
        ):
            temp_files.append(temp_file)

            if progress_callback is not None:
                progress_callback(index, nPages)

            if status_callback is not None:
                status_callback(index, nPages)

            if index == 1 or index == nPages or index % 10 == 0:
                logger.info("Split progress: {}/{} pages processed.", index, nPages)

    # Merge temp files
    for file in temp_files:
        doc = fitz.open(file)
        output_doc.insert_pdf(doc)
        doc.close()
        tempFile = Path(file)
        tempFile.unlink(missing_ok=True)  # Delete the temporary file

    logger.debug("Temporary page fragments merged: {}", len(temp_files))

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
    totPages = len(output_doc)
    output_doc.close()

    logger.success("PDF split completed: {} pages written to {}", totPages, output_pdf)

    if completion_callback is not None:
        completion_callback(output_pdf, totPages)
