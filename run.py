import sys
import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging():
    """
    Configures the root logger to be quiet on console
    and detailed in a dedicated log file.
    """

    # --- 1. Create a dedicated 'logs' directory ---
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # --- 2. Define the log format ---
    log_format = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] [%(name)-25s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- 3. Get the root logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture ALL log levels

    # --- 4. Console Handler (Quiet) ---
    # Only shows WARNINGS and ERRORS
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)  # <-- This makes your console clean
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # --- 5. Rotating File Handler (Detailed, in 'logs/' dir) ---
    # Writes ALL (DEBUG) messages to a file inside the 'logs' folder
    log_file_path = os.path.join(log_dir, "pdf_retriever.log")

    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)


# --- Original code to add 'src' to path ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

# --- Now we can import the app ---
from downloader.gui import main

if __name__ == "__main__":
    # --- Run the logging setup *before* the app starts ---
    setup_logging()

    logging.info("Application starting...")
    main()
    logging.info("Application closed.")
