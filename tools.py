import fitz

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

## Usage example:
# doc = fitz.open("file.pdf")
# page = doc[13]  # page 14

# if page_is_visually_blank(page):
#     print("Page 14 is visually blank")
# else:
#     print("Page 14 has visible content")