# src/downloader/cli.py
import logging
import os
import sys
from pathlib import Path

from rich.logging import RichHandler

from . import settings_manager
from .tui import (
    show_main_panel, get_dois, run_download, run_status_test, err, done, console,
    load_config, save_config, clear_config, get_settings, should_show_debug,
    show_failed_dois
)

def main():
    settings = load_config() or None

    log_level_name = "DEBUG" if should_show_debug(settings or {}) else "WARNING"
    log_level = logging.DEBUG if log_level_name == "DEBUG" else logging.WARNING

    requests_log_level = (
        logging.WARNING if log_level == logging.DEBUG else logging.ERROR
    )

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console, show_path=False, rich_tracebacks=True, show_level=False
            )
        ],
    )
    logging.getLogger("urllib3").setLevel(requests_log_level)
    logging.getLogger("requests").setLevel(requests_log_level)

    dois: list = []
    while True:
        try:
            os.system("cls" if os.name == "nt" else "clear")
            ch = show_main_panel(settings, dois)

            if ch == "1":
                current = settings or {}
                settings = get_settings(current)
                if load_config() != settings:
                    save_config(settings)

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

            elif ch == "2":
                dois = get_dois(settings or {"ui_mode": settings_manager.DEFAULT_UI_MODE})

            elif ch == "3":
                if not settings:
                    err("Configure settings first.", {})
                elif not dois:
                    err("Load DOIs first.", {})
                else:
                    run_download(settings, dois)
                input("\nPress Enter...")

            elif ch == "4":
                show_failed_dois(settings)
                input("\nPress Enter...")

            elif ch == "5":
                if not settings:
                    err("No settings yet.", {})
                else:
                    out = Path(settings["output_dir"])
                    out.mkdir(exist_ok=True)
                    if os.name == "nt":
                        os.startfile(out)
                    elif sys.platform == "darwin":
                        os.system(f'open "{out}"')
                    else:
                        os.system(f'xdg-open "{out}"')
                input("\nPress Enter...")

            elif ch == "6":
                if not settings:
                    err("Configure settings first.", {})
                else:
                    run_status_test(settings)
                input("\nPress Enter...")

            elif ch == "7":
                clear_config()
                settings = None
                input("\nPress Enter...")

            elif ch == "8":
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