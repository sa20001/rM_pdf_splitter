from multiprocessing import freeze_support

from src.logger import custom_logger  # noqa: F401 - configure logging on import
from src.gui import launch_app
import platform


if __name__ == "__main__":
    if platform.system() == "Windows":
        # Required for multiprocessing in frozen Windows executables (e.g. PyInstaller)
        freeze_support()
    launch_app()