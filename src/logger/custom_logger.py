import os
import sys
from pathlib import Path
from typing import Any
from src.consts import APP_DATA_DIR

from loguru import logger


logger.remove()
LOGS_PATH = APP_DATA_DIR / "logs"
VERBOSE = True
log_ids: list[Any] = []

console_stream = next(
    (stream for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__) if stream is not None),
    None,
)

if VERBOSE and console_stream is not None:
    log_ids.append(
        logger.add(
            console_stream,
            level="TRACE",
            colorize=True,
            format="<cyan>{time:HH:mm:ss}</cyan> | <level>{level: <8}</level> | <magenta>{file}:{function}:{line}</magenta> | <level>{message}</level>",
        )
    )
elif console_stream is not None:
    log_ids.append(
        logger.add(
            console_stream,
            level="INFO",
            colorize=True,
            format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        )
    )

os.makedirs(LOGS_PATH, exist_ok=True)
log_ids.append(logger.add(LOGS_PATH / "trace.log", level="TRACE", rotation="10 MB", compression="zip"))
log_ids.append(logger.add(LOGS_PATH / "info.log", level="INFO", rotation="10 MB", compression="zip"))

logger.info("Loguru initialized with console and file sinks at {}.", LOGS_PATH)