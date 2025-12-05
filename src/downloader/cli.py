# src/downloader/cli.py
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from pathlib import Path

from rich.logging import RichHandler

from . import settings_manager
from .settings_manager import CONFIG_DIR
from .tui import (
    clear_config,
    console,
    err,
    get_dois,
    get_settings,
    load_config,
    run_download,
    run_status_test,
    save_config,
    should_show_debug,
    show_failed_dois,
    show_main_panel,
)

LOG_FILE = CONFIG_DIR / "app.log"


def _setup_logging(settings):
    log_level_name = "DEBUG" if should_show_debug(settings or {}) else "WARNING"
    log_level = logging.DEBUG if log_level_name == "DEBUG" else logging.WARNING

    requests_log_level = (
        logging.WARNING if log_level == logging.DEBUG else logging.ERROR
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console, show_path=False, rich_tracebacks=True, show_level=False
            ),
            file_handler,
        ],
    )
    logging.getLogger("urllib3").setLevel(requests_log_level)
    logging.getLogger("requests").setLevel(requests_log_level)


def _update_logging(settings):
    new_log_level_name = "DEBUG" if should_show_debug(settings) else "WARNING"
    new_log_level = (
        logging.DEBUG if new_log_level_name == "DEBUG" else logging.WARNING
    )
    new_requests_log_level = (
        logging.WARNING if new_log_level == logging.DEBUG else logging.ERROR
    )
    logging.getLogger().setLevel(new_log_level)
    logging.getLogger("urllib3").setLevel(new_requests_log_level)
    logging.getLogger("requests").setLevel(new_requests_log_level)


def _open_output_folder(settings):
    if not settings:
        err("No settings yet.", {})
        return

    out = Path(settings["output_dir"])
    out.mkdir(exist_ok=True)
    if os.name == "nt":
        os.startfile(out)
    elif sys.platform == "darwin":
        os.system(f'open "{out}"')
    else:
        os.system(f'xdg-open "{out}"')


def _handle_configure_settings(settings, dois):
    current = settings or {}
    settings = get_settings(current)
    if load_config() != settings:
        save_config(settings)
    _update_logging(settings)
    return settings, dois, True


def _handle_input_dois(settings, dois):
    dois = get_dois(settings or {"ui_mode": settings_manager.DEFAULT_UI_MODE})
    return settings, dois, True


def _handle_begin_download(settings, dois):
    if not settings:
        err("Configure settings first.", {})
    elif not dois:
        err("Load DOIs first.", {})
    else:
        run_download(settings, dois)
    input("\nPress Enter...")
    return settings, dois, True


def _handle_view_failed(settings, dois):
    show_failed_dois(settings)
    input("\nPress Enter...")
    return settings, dois, True


def _handle_open_output(settings, dois):
    _open_output_folder(settings)
    input("\nPress Enter...")
    return settings, dois, True


def _handle_test_status(settings, dois):
    if not settings:
        err("Configure settings first.", {})
    else:
        run_status_test(settings)
    input("\nPress Enter...")
    return settings, dois, True


def _handle_clear_settings(settings, dois):
    clear_config()
    settings = None
    input("\nPress Enter...")
    return settings, dois, True


def _handle_menu_choice(ch, settings, dois):
    handlers = {
        "1": _handle_configure_settings,
        "2": _handle_input_dois,
        "3": _handle_begin_download,
        "4": _handle_view_failed,
        "5": _handle_open_output,
        "6": _handle_test_status,
        "7": _handle_clear_settings,
    }

    if handler := handlers.get(ch):
        return handler(settings, dois)
    elif ch == "8":
        return settings, dois, False
    
    return settings, dois, True


def main():
    settings = load_config() or None
    _setup_logging(settings)

    dois: list = []
    while True:
        try:
            os.system("cls" if os.name == "nt" else "clear")
            ch = show_main_panel(settings, dois)
            
            settings, dois, continue_loop = _handle_menu_choice(ch, settings, dois)
            if not continue_loop:
                break

        except KeyboardInterrupt:
            console.print("\n[bold red]Exiting...[/bold red]")
            break
        except Exception as e:
            logging.critical("Unhandled exception", exc_info=True)
            console.print(f"[bold red]An error occurred:[/bold red] {e}")
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()