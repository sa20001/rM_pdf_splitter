from pathlib import Path
import os
import sys

if hasattr(sys, "_MEIPASS"): # if bundled by PyInstaller
    APP_DATA_DIR = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "rM_pdf_splitter"
else: # if dev environment
    APP_DATA_DIR = Path(__file__).resolve().parents[1]
