"""
Open-Access PDF Retrieval System — TUI Elements
"""

import logging
import re
import sys
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from . import settings_manager
from .core import Downloader
from .parsers import extract_dois_from_file
from .utils import clean_doi

console = Console()

def get_single_key():
    if msvcrt:
        ch = msvcrt.getch()
        if ch in {b"\x00", b"\xe0"}:
            ch2 = msvcrt.getch()
            if ch2 == b"H":
                return "UP"
            if ch2 == b"P":
                return "DOWN"
            return ""
        if ch == b"\r":
            return "ENTER"
        try:
            return ch.decode("utf-8", errors="ignore")
        except Exception:
            return ""
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
                if seq == "[A":
                    return "UP"
                if seq == "[B":
                    return "DOWN"
                return ""
            if ch in ("\r", "\n"):
                return "ENTER"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

def phase(msg, settings):
    console.print(Rule(f"[bold cyan]{msg}", style="cyan"))

def note(msg, settings):
    if settings and settings.get("ui_mode") in ["research", "debug"]:
        console.print(f"[dim italic]{msg}[/dim italic]")

def done(msg, settings):
    console.print(f"✅ [bold green]{msg}[/bold green]")

def warn(msg, settings):
    console.print(f"⚠️ [yellow]{msg}[/yellow]")

def err(msg, settings):
    console.print(f"❌ [bold red]{msg}[/bold red]")

def should_show_debug(settings):
    if not settings:
        return False
    return settings.get("ui_mode", settings_manager.DEFAULT_UI_MODE) == "debug"

def load_config():
    cfg = settings_manager.read_config_raw()
    if cfg is None:
        console.print(
            "[yellow]Warning: Could not parse settings. Resetting.[/yellow]"
        )
    return cfg

def save_config(cfg):
    save = Prompt.ask("\nSave these settings?", choices=["y", "n"], default="n")
    if save == "y":
        settings_manager.write_config_raw(cfg)
        note(f"Settings saved to {settings_manager.CONFIG_FILE}", {"ui_mode": "research"})

def clear_config():
    settings_manager.delete_config_raw()
    done("Settings cleared.", {"ui_mode": "research"})

def get_settings(cfg):
    phase("Configure Settings", cfg or {})

    DEFAULT_DOWNLOADS_DIR = Path.home() / "Downloads"

    output_dir = Prompt.ask(
        "📁 Save PDFs to",
        default=(cfg or {}).get("output_dir", str(DEFAULT_DOWNLOADS_DIR)),
    )

    email = (cfg or {}).get("email")
    while not email:
        email = Prompt.ask("📧 Unpaywall email (required for metadata)")
        if not email:
            err("Email required.", cfg or {})

    core_api_key = Prompt.ask(
        "🔑 CORE API Key (optional, for OA metadata/links)",
        default=(cfg or {}).get("core_api_key", ""),
    )

    max_workers = int(
        Prompt.ask(
            "⚙️ Parallel downloads", default=str((cfg or {}).get("max_workers", 10))
        )
    )

    console.print("\n[bold]Interface Mode[/bold]")
    ui_mode = Prompt.ask(
        "Choose mode",
        choices=settings_manager.UI_MODES,
        default=(cfg or {}).get("ui_mode", settings_manager.DEFAULT_UI_MODE),
    )

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

def get_dois(settings):
    phase("Input Source", settings or {})
    file = Prompt.ask("📄 Citation file or press Enter for manual input")
    dois = set()

    if file:
        try:
            extracted = extract_dois_from_file(file)
            dois.update(extracted)
            note(f"Found {len(dois)} unique DOIs in {Path(file).name}", settings or {})
        except Exception as e:
            err(f"Error reading file: {e}", settings or {})
            return []
    else:
        raw = Prompt.ask("✍️ Enter DOIs (comma/space/newline)")
        for token in re.split(r"[,\s\n]+", raw):
            if cleaned := clean_doi(token.strip()):
                dois.add(cleaned)

    return sorted(list(dois))

def show_failed_dois(settings):
    if not settings:
        err("No settings yet.", {})
        return

    output_dir = Path(settings["output_dir"])
    fp = output_dir / "failed_dois.txt"
    if fp.exists() and fp.read_text():
        console.print(Rule("Failed DOIs"))
        console.print(fp.read_text())
    else:
        done("No failed DOIs list found.", {})


def run_download(settings, dois):
    dl = Downloader(
        output_dir=settings["output_dir"],
        email=settings["email"],
        core_api_key=settings.get("core_api_key"),
        verify_ssl=settings["verify_ssl"],
    )

    results = []
    recent_logs = deque(maxlen=5)

    progress = Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("({task.completed} of {task.total})"),
    )
    progress_task = progress.add_task("Overall Progress", total=len(dois))

    def generate_live_panel() -> Panel:
        renderables = [progress]
        if recent_logs:
            renderables.insert(0, "\n".join(recent_logs))
            renderables.insert(0, "")

        content = Group(*renderables)
        return Panel(
            content,
            title=f"[bold cyan]Retrieving {len(dois)} PDFs[/bold cyan]",
            border_style="grey70",
        )

    logger = logging.getLogger()
    previous_level = logger.level
    previous_handlers = list(logger.handlers)

    if not should_show_debug(settings):
        logger.setLevel(logging.CRITICAL)
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)
        logging.getLogger("requests").setLevel(logging.CRITICAL)

    try:
        with Live(
            generate_live_panel(),
            console=console,
            screen=False,
            refresh_per_second=10,
            transient=True,
        ) as live:
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
                            display_name = (
                                filename
                                if len(filename) <= 75
                                else filename[:72] + "...pdf"
                            )
                            log_message = f"✅ [green]Success ({source}):[/green] [dim]{display_name}[/dim]"
                        elif status == "skipped":
                            filename = Path(result.get("filename", "")).name
                            display_name = (
                                filename
                                if len(filename) <= 75
                                else filename[:72] + "...pdf"
                            )
                            log_message = f"⏩ [dim]Skipped (Exists):[/dim] [dim]{display_name}[/dim]"
                        else:
                            log_message = f"❌ [red]Failed:[/red] [dim]{doi}[/dim]"

                    except Exception:
                        doi = future_map[f]
                        results.append({"doi": doi, "status": "exception"})
                        log_message = (
                            f"💥 [bold red]CRITICAL ERROR:[/bold red] [dim]{doi}[/dim]"
                        )

                    recent_logs.append(log_message)
                    progress.update(progress_task, advance=1)
                    live.update(generate_live_panel())
    finally:
        logger.handlers = previous_handlers
        logger.setLevel(previous_level)
        if not should_show_debug(settings):
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("requests").setLevel(logging.WARNING)

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
        output_dir = Path(settings["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        fp = output_dir / "failed_dois.txt"
        fp.write_text("\n".join(sorted(failed)))
        console.print(
            f" ⚠️ [yellow]{len(failed)} DOIs failed — see 'failed_dois.txt' in the output folder.[/yellow]"
        )

def run_status_test(settings):
    """Initializes sources and tests their connections."""

    phase("Source Connection Status", settings or {})

    logger = logging.getLogger()
    current_level = logger.level

    if not should_show_debug(settings):
        logger.setLevel(logging.CRITICAL)
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)
        logging.getLogger("requests").setLevel(logging.CRITICAL)

    tbl = Table(title=None, box=None)

    tbl.add_column("Source", style="cyan", width=20)
    tbl.add_column("Status", style="bold", width=12)
    tbl.add_column("Details", style="dim")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Testing sources...", total=1)

        try:
            dl = Downloader(
                output_dir=settings["output_dir"],
                email=settings["email"],
                core_api_key=settings.get("core_api_key"),
                verify_ssl=settings["verify_ssl"],
            )

            all_sources = {
                s.name: s
                for s in dl.metadata_sources + dl.pipeline + [dl.unpaywall_source]
            }.values()

        except Exception as e:
            progress.stop()
            err(f"Failed to initialize downloader: {e}", settings or {})
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

def show_main_panel(settings, dois):
    force_refresh = False

    def handle_resize(signum, frame):
        """Force refresh on terminal resize"""
        nonlocal force_refresh
        force_refresh = True

    try:
        import signal

        signal.signal(signal.SIGWINCH, handle_resize)
    except (AttributeError, ImportError):
        pass

    status_s = "[green]Configured[/green]" if settings else "[dim]Not Set[/dim]"
    status_d = f"[green]{len(dois)}[/green]" if dois else "[dim]0[/dim]"

    options = [
        ("1", "Configure Settings"),
        ("2", "Input DOIs"),
        ("3", "Begin Download"),
        ("4", "View Failed List"),
        ("5", "Open Output Folder"),
        ("6", "Test System Status"),
        ("7", "Clear Settings"),
        ("8", "Quit"),
    ]

    current = 0

    def render():
        terminal_width = console.size.width

        welcome_message = Align.center(
            "\n[bold white]Welcome to the PDF Downloader CLI[/bold white]\n\n"
        )
        status_line = Align.center(
            f"[dim]Settings:[/dim] {status_s} | [dim]DOIs Loaded:[/dim] {status_d}\n"
        )
        menu_header = Text("[ MENU ]", style="bold cyan")

        separator = "[dim]" + "─" * min(40, terminal_width - 10) + "[/dim]"

        lines = []
        for i, (key, label) in enumerate(options):
            if i == current:
                lines.append(
                    f"[reverse][bold blue]{key}. {label}[/bold blue][/reverse]"
                )
            else:
                lines.append(f"[bold]{key}.[/bold] {label}")
            if i == 2:
                lines.append(separator)

        menu_block = "\n".join(lines)
        panel_content = Group(
            welcome_message,
            status_line,
            Align.left(menu_header),
            Align.left(menu_block),
            Text(""),
        )

        padding = (1, max(2, terminal_width // 20))

        return Panel(
            panel_content,
            title="[bold cyan]Open-Access PDF Retrieval System[/bold cyan]",
            title_align="center",
            border_style="grey70",
            padding=padding,
        )

    console.clear()
    console.print("")

    with Live(render(), console=console, refresh_per_second=30, screen=False) as live:
        while True:
            if force_refresh:
                force_refresh = False
                live.update(render())
                continue

            k = get_single_key()

            if k in ("\x1b[A", "H", "UP"):
                current = (current - 1) % len(options)
            elif k in ("\x1b[B", "P", "DOWN"):
                current = (current + 1) % len(options)
            elif k in ("\r", "\n", "ENTER"):
                return options[current][0]
            elif k in ("1", "2", "3", "4", "5", "6", "7", "8"):
                return k
            elif k in ("q", "\x1b"):
                return "8"

            live.update(render())
