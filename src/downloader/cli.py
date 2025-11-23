# src/downloader/cli.py
import logging
import os
<<<<<<< HEAD
import sys
import logging
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
=======
import re
import sys
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import msvcrt  # type: ignore
except ImportError:
    msvcrt = None  # type: ignore

def get_single_key() -> str:
    if msvcrt:
        ch = msvcrt.getch()  # type: ignore
        if ch in {b"\x00", b"\xe0"}:
            ch2 = msvcrt.getch()  # type: ignore
            if ch2 == b"H": return "UP"
            if ch2 == b"P": return "DOWN"
            return ""
        if ch == b"\r": return "ENTER"
        try: return ch.decode("utf-8", errors="ignore")
        except Exception: return ""
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                if seq == "[A": return "UP"
                if seq == "[B": return "DOWN"
                return ""
            if ch in ("\r", "\n"): return "ENTER"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from . import settings as config_mgr
from .core import Downloader
from .parsers import extract_dois_from_file
from .utils import clean_doi

console = Console()
DEFAULT_UI_MODE = "research"
UI_MODES = ["research", "debug"]

def should_show_debug(settings: dict) -> bool:
    return config_mgr.should_show_debug(settings)

def phase(msg: str, settings: dict) -> None:
    console.print(Rule(f"[bold cyan]{msg}", style="cyan"))

def note(msg: str, settings: dict) -> None:
    if settings.get("ui_mode") in ["research", "debug"]:
        console.print(f"[dim italic]{msg}[/dim italic]")

def done(msg: str, settings: dict) -> None:
    console.print(f"✅ [bold green]{msg}[/bold green]")

def warn(msg: str, settings: dict) -> None:
    console.print(f"⚠️ [yellow]{msg}[/yellow]")

def err(msg: str, settings: dict) -> None:
    console.print(f"❌ [bold red]{msg}[/bold red]")

def save_config(cfg: dict) -> None:
    save = Prompt.ask("\nSave these settings?", choices=["y", "n"], default="n")
    if save == "y":
        config_mgr.save_config_data(cfg)
        note(f"Settings saved to {config_mgr.CONFIG_FILE}", {"ui_mode": "research"})

def clear_config() -> None:
    config_mgr.clear_config_files()
    done("Settings cleared.", {"ui_mode": "research"})

def get_settings(cfg: dict) -> dict:
    phase("Configure Settings", cfg)
    DEFAULT_DOWNLOADS_DIR = Path.home() / "Downloads"
    output_dir = Prompt.ask("📁 Save PDFs to", default=cfg.get("output_dir", str(DEFAULT_DOWNLOADS_DIR)))
    email = cfg.get("email")
    while not email:
        email = Prompt.ask("📧 Unpaywall email (required for metadata)")
        if not email: err("Email required.", cfg)
    core_api_key = Prompt.ask("🔑 CORE API Key (optional)", default=cfg.get("core_api_key", ""))
    max_workers = int(Prompt.ask("⚙️ Parallel downloads", default=str(cfg.get("max_workers", 10))))
    console.print("\n[bold]Interface Mode[/bold]")
    ui_mode = Prompt.ask("Choose mode", choices=UI_MODES, default=cfg.get("ui_mode", DEFAULT_UI_MODE))
    ssl_choice = Prompt.ask("Bypass SSL verification?", choices=["y", "n"], default="n")
    verify_ssl = ssl_choice != "y"
    return {
        "output_dir": output_dir,
        "email": email,
        "core_api_key": core_api_key,
        "max_workers": max_workers,
        "verify_ssl": verify_ssl,
        "ui_mode": ui_mode,
    }

def get_dois(settings: dict) -> list:
    phase("Input Source", settings)
    file = Prompt.ask("📄 Citation file or press Enter for manual input")
    dois = set()
    if file:
        try:
            extracted = extract_dois_from_file(file)
            dois.update(extracted)
            note(f"Found {len(dois)} unique DOIs in {Path(file).name}", settings)
        except Exception as e:
            err(f"Error reading file: {e}", settings)
            return []
    else:
        raw = Prompt.ask("✍️ Enter DOIs (comma/space/newline)")
        for token in re.split(r"[,\s\n]+", raw):
            if cleaned := clean_doi(token.strip()): dois.add(cleaned)
    return sorted(list(dois))

def run_download(settings: dict, dois: list) -> None:
    dl = Downloader(
        output_dir=settings["output_dir"],
        email=settings["email"],
        core_api_key=settings.get("core_api_key"),
        verify_ssl=settings["verify_ssl"],
    )
    results = []
    recent_logs: deque = deque(maxlen=5)
    progress = Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("({task.completed} of {task.total})"),
    )
    progress_task = progress.add_task("Overall Progress", total=len(dois))

    def generate_live_panel() -> Panel:
        renderables: list = [progress]
        if recent_logs:
            renderables.insert(0, "\n".join(recent_logs))
            renderables.insert(0, "")
        content = Group(*renderables)
        return Panel(content, title=f"[bold cyan]Retrieving {len(dois)} PDFs[/bold cyan]", border_style="grey70")

    logger = logging.getLogger()
    previous_level = logger.level
    previous_handlers = list(logger.handlers)

    try:
        with Live(generate_live_panel(), console=console, screen=False, refresh_per_second=10, transient=True) as live:
            with ThreadPoolExecutor(max_workers=settings["max_workers"]) as ex:
                future_map = {ex.submit(dl.download_one, doi): doi for doi in dois}
                for f in as_completed(future_map):
                    log_message = ""
                    try:
                        result = f.result()
                        results.append(result)
                        doi = result.get("doi", "")
                        status = result.get("status", "failed")
                        if status == "success":
                            source = result.get("source", "Unknown")
                            filename = Path(result.get("filename", "")).name
                            display_name = filename if len(filename) <= 75 else filename[:72] + "...pdf"
                            log_message = f"✅ [green]Success ({source}):[/green] [dim]{display_name}[/dim]"
                        elif status == "skipped":
                            filename = Path(result.get("filename", "")).name
                            display_name = filename if len(filename) <= 75 else filename[:72] + "...pdf"
                            log_message = f"⏩ [dim]Skipped (Exists):[/dim] [dim]{display_name}[/dim]"
                        else:
                            log_message = f"❌ [red]Failed:[/red] [dim]{doi}[/dim]"
                    except Exception:
                        doi = future_map[f]
                        results.append({"doi": doi, "status": "exception"})
                        log_message = f"💥 [bold red]CRITICAL ERROR:[/bold red] [dim]{doi}[/dim]"
                    recent_logs.append(log_message)
                    progress.update(progress_task, advance=1)
                    live.update(generate_live_panel())
    finally:
        logger.handlers = previous_handlers
        logger.setLevel(previous_level)

    stats = dl.stats
    tbl = Table(title="[bold]Download Summary[/bold]", show_header=False, box=None)
    tbl.add_column("Metric", style="cyan")
    tbl.add_column("Value", style="bold", justify="right")
    tbl.add_row("✅ Success", str(stats["success"]))
    tbl.add_row("⏩ Skipped", str(stats["skipped"]))
    tbl.add_row("❌ Failed", str(stats["fail"]))
    console.print(Rule("[bold green]Download Complete[/bold green]"))
    console.print(tbl)

    failed = [r["doi"] for r in results if r.get("status") in ("failed", "exception")]
    if failed:
        fp = Path(settings["output_dir"]) / "failed_dois.txt"
        fp.write_text("\n".join(sorted(failed)))
        console.print(f" ⚠️ [yellow]{len(failed)} DOIs failed — see 'failed_dois.txt' in the output folder.[/yellow]")
        if len(failed) > 0 and len(failed) < len(dois):
            retry = Prompt.ask(f"\n🔄 Retry {len(failed)} failed downloads?", choices=["y", "n"], default="n")
            if retry == "y":
                # Recursive retry logic could go here, but simplest is to re-queue
                run_download(settings, failed)

def run_status_test(settings: dict) -> None:
    phase("Source Connection Status", settings)
    logger = logging.getLogger()
    current_level = logger.level
    if not should_show_debug(settings):
        logger.setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.ERROR)
        logging.getLogger("requests").setLevel(logging.ERROR)
    tbl = Table(title=None, box=None)
    tbl.add_column("Source", style="cyan", width=20)
    tbl.add_column("Status", style="bold", width=12)
    tbl.add_column("Details", style="dim")
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Testing sources...", total=1)
        try:
            dl = Downloader(
                output_dir=settings["output_dir"],
                email=settings["email"],
                core_api_key=settings.get("core_api_key"),
                verify_ssl=settings["verify_ssl"],
            )
            all_sources = {s.name: s for s in dl.metadata_sources + dl.pipeline}.values()
        except Exception as e:
            progress.stop()
            err(f"Failed to initialize downloader: {e}", settings)
            logger.setLevel(current_level)
            return
        for source in all_sources:
            status, msg = source.test_connection()
            status_style = "[green]OK[/green]" if status else "[red]FAILED[/red]"
            tbl.add_row(source.name, status_style, msg)
        progress.update(task, completed=True, description="")
    console.print(tbl)
    logger.setLevel(current_level)
    if not should_show_debug(settings):
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

def show_main_panel(settings: dict | None, dois: list) -> str:
    force_refresh = False
    try:
        import signal
        def handle_resize(signum, frame): nonlocal force_refresh; force_refresh = True
        signal.signal(signal.SIGWINCH, handle_resize)
    except (AttributeError, ImportError): pass

    status_s = "[green]Configured[/green]" if settings else "[dim]Not Set[/dim]"
    status_d = f"[green]{len(dois)}[/green]" if dois else "[dim]0[/dim]"
    options = [
        ("1", "Configure Settings"), ("2", "Input DOIs"), ("3", "Begin Download"),
        ("4", "View Failed List"), ("5", "Open Output Folder"), ("6", "Test System Status"),
        ("7", "Clear Settings"), ("8", "Quit"),
    ]
    current = 0

    def render():
        terminal_width = max(50, console.size.width)
        title_text = "[bold cyan]PDF Retrieval[/bold cyan]" if terminal_width < 80 else "[bold cyan]Open-Access PDF Retrieval System[/bold cyan]"
        welcome_text = "[bold white]PDF Downloader[/bold white]" if terminal_width < 80 else "[bold white]Welcome to the PDF Downloader CLI[/bold white]"
        welcome_message = Align.center(f"\n{welcome_text}\n\n")
        status_line = Align.center(f"[dim]Settings:[/dim] {status_s} | [dim]DOIs:[/dim] {status_d}\n")
        menu_header = Text("[ MENU ]", style="bold cyan")
        sep_width = max(20, min(40, terminal_width - 10))
        separator = "[dim]" + "─" * sep_width + "[/dim]"
        lines = []
        for i, (key, label) in enumerate(options):
            if i == current: lines.append(f"[reverse][bold blue]{key}. {label}[/bold blue][/reverse]")
            else: lines.append(f"[bold]{key}.[/bold] {label}")
            if i == 2: lines.append(separator)
        menu_block = "\n".join(lines)
        panel_content = Group(welcome_message, status_line, Align.left(menu_header), Align.left(menu_block), Text(""))
        padding = (1, max(1, min(terminal_width // 20, 4)))
        return Panel(panel_content, title=title_text, title_align="center", border_style="grey70", padding=padding)

    console.clear()
    console.print(render())
    while True:
        k = get_single_key()
        needs_update = False
        if k in ("\x1b[A", "H", "UP"):
            current = (current - 1) % len(options)
            needs_update = True
        elif k in ("\x1b[B", "P", "DOWN"):
            current = (current + 1) % len(options)
            needs_update = True
        elif k in ("\r", "\n", "ENTER"): return options[current][0]
        elif k in ("1", "2", "3", "4", "5", "6", "7", "8"): return k
        elif k in ("q", "\x1b"): return "8"
        if needs_update or force_refresh:
            force_refresh = False
            console.clear()
            console.print(render())

def main() -> None:
    settings = config_mgr.load_config() or None
    is_debug_mode = config_mgr.should_show_debug(settings or {})
    console_log_level = logging.DEBUG if is_debug_mode else logging.WARNING
    requests_log_level = logging.WARNING if is_debug_mode else logging.ERROR
    
    console_handler = RichHandler(console=console, show_path=False, rich_tracebacks=True, show_level=False)
    console_handler.setLevel(console_log_level)
    handlers: list = [console_handler]
    
    log_file = config_mgr.CONFIG_DIR / "app.log"
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        file_handler.setLevel(logging.DEBUG)
        handlers.append(file_handler)
    except Exception: console.print("[yellow]Warning: Could not set up file logging.[/yellow]")
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8

    logging.basicConfig(level=logging.DEBUG, format="%(message)s", handlers=handlers)
    logging.getLogger("urllib3").setLevel(requests_log_level)
    logging.getLogger("requests").setLevel(requests_log_level)

    dois: list = []
    while True:
<<<<<<< HEAD
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
=======
        try:
            try: console.clear()
            except Exception: os.system("cls" if os.name == "nt" else "clear")
            ch = show_main_panel(settings, dois)
            if ch == "1":
                current = settings or {}
                settings = get_settings(current)
                if config_mgr.load_config() != settings: save_config(settings)
                new_console_level = logging.DEBUG if config_mgr.should_show_debug(settings) else logging.WARNING
                console_handler.setLevel(new_console_level)
            elif ch == "2": dois = get_dois(settings or {"ui_mode": DEFAULT_UI_MODE})
            elif ch == "3":
                if not settings: err("Configure settings first.", {})
                elif not dois: err("Load DOIs first.", {})
                else: run_download(settings, dois)
                input("\nPress Enter...")
            elif ch == "4":
                if not settings:
                    err("No settings yet.", {})
                else:
                    fp = Path(settings.get("output_dir", ".")) / "failed_dois.txt"
                    if fp.exists() and fp.read_text():
                        console.print(Rule("Failed DOIs"))
                        console.print(fp.read_text())
                    else:
                        done("No failed DOIs list found.", {})
                input("\nPress Enter...")
            elif ch == "5":
                if not settings: err("No settings yet.", {})
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8
                else:
                    out = Path(settings["output_dir"])
                    out.mkdir(exist_ok=True)
                    if os.name == "nt": os.startfile(out)  # type: ignore
                    elif sys.platform == "darwin": os.system(f'open "{out}"')
                    else: os.system(f'xdg-open "{out}"')
                input("\nPress Enter...")
            elif ch == "6":
                if not settings: err("Configure settings first.", {})
                else: run_status_test(settings)
                input("\nPress Enter...")
            elif ch == "7":
                clear_config()
                settings = None
                input("\nPress Enter...")
            elif ch == "8": break
        except KeyboardInterrupt:
            console.print("\n[bold red]Exiting...[/bold red]")
            break
<<<<<<< HEAD
=======
        except Exception as e:
            logging.critical("Unhandled exception", exc_info=True)
            console.print(f"[bold red]An error occurred:[/bold red] {e}")
            console.print(f"Log saved to: {log_file}")
            input("\nPress Enter to continue...")
>>>>>>> 85cb3d387c185462bcf3032d3f6a75495df95de8

if __name__ == "__main__":
    main()