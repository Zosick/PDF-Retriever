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

def _get_key_windows():
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

def _get_key_unix():
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            import select
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
            if rlist:
                seq = sys.stdin.read(2)
                if seq == "[A":
                    return "UP"
                if seq == "[B":
                    return "DOWN"
                return ""
            else:
                return ch
        if ch in ("\r", "\n"):
            return "ENTER"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def get_single_key():
    if msvcrt:
        return _get_key_windows()
    else:
        return _get_key_unix()

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

def _prompt_for_output_dir(cfg):
    DEFAULT_DOWNLOADS_DIR = Path.home() / "Downloads"
    return Prompt.ask(
        "📁 Save PDFs to",
        default=(cfg or {}).get("output_dir", str(DEFAULT_DOWNLOADS_DIR)),
    )

def _prompt_for_email(cfg):
    email = (cfg or {}).get("email")
    while not email:
        email = Prompt.ask("📧 Unpaywall email (required for metadata)")
        if not email:
            err("Email required.", cfg or {})
    return email

def _prompt_for_api_key(cfg):
    return Prompt.ask(
        "🔑 CORE API Key (optional, for OA metadata/links)",
        default=(cfg or {}).get("core_api_key", ""),
    )

def _prompt_for_workers(cfg):
    default_workers = (cfg or {}).get("max_workers", 10)
    while True:
        raw = Prompt.ask(
            "⚙️ Parallel downloads", default=str(default_workers)
        )
        try:
            val = int(raw)
            if val > 0:
                return val
            console.print("[red]Please enter a positive integer.[/red]")
        except ValueError:
            console.print("[red]Invalid input. Please enter a number.[/red]")

def _prompt_for_ui_mode(cfg):
    console.print("\n[bold]Interface Mode[/bold]")
    return Prompt.ask(
        "Choose mode",
        choices=settings_manager.UI_MODES,
        default=(cfg or {}).get("ui_mode", settings_manager.DEFAULT_UI_MODE),
    )

def _prompt_for_ssl(cfg):
    ssl_choice = Prompt.ask("Bypass SSL verification?", choices=["y", "n"], default="n")
    return ssl_choice != "y"

def get_settings(cfg):
    phase("Configure Settings", cfg or {})
    return {
        "output_dir": _prompt_for_output_dir(cfg),
        "email": _prompt_for_email(cfg),
        "core_api_key": _prompt_for_api_key(cfg),
        "max_workers": _prompt_for_workers(cfg),
        "verify_ssl": _prompt_for_ssl(cfg),
        "ui_mode": _prompt_for_ui_mode(cfg),
    }

def _get_dois_from_file(file, settings):
    dois = set()
    try:
        extracted = extract_dois_from_file(file)
        dois.update(extracted)
        note(f"Found {len(dois)} unique DOIs in {Path(file).name}", settings or {})
        return list(dois)
    except Exception as e:
        err(f"Error reading file: {e}", settings or {})
        return []

def _get_dois_manual():
    dois = set()
    raw = Prompt.ask("✍️ Enter DOIs (comma/space/newline)")
    for token in re.split(r"[,\s\n]+", raw):
        if cleaned := clean_doi(token.strip()):
            dois.add(cleaned)
    return list(dois)

def get_dois(settings):
    phase("Input Source", settings or {})
    file = Prompt.ask("📄 Citation file or press Enter for manual input")
    
    if file:
        return sorted(_get_dois_from_file(file, settings))
    else:
        return sorted(_get_dois_manual())

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


def _setup_logging_for_download(settings):
    logger = logging.getLogger()
    previous_level = logger.level
    previous_handlers = list(logger.handlers)

    if not should_show_debug(settings):
        logger.setLevel(logging.CRITICAL)
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)
        logging.getLogger("requests").setLevel(logging.CRITICAL)
    return logger, previous_level, previous_handlers

def _restore_logging(logger, previous_level, previous_handlers, settings):
    logger.handlers = previous_handlers
    logger.setLevel(previous_level)
    if not should_show_debug(settings):
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)

def _create_progress_bar(total):
    progress = Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TextColumn("({task.completed} of {task.total})"),
    )
    task = progress.add_task("Overall Progress", total=total)
    return progress, task

def _generate_live_panel(progress, recent_logs, total_dois) -> Panel:
    renderables = [progress]
    if recent_logs:
        renderables.insert(0, "\n".join(recent_logs))
        renderables.insert(0, "")

    content = Group(*renderables)
    return Panel(
        content,
        title=f"[bold cyan]Retrieving {total_dois} PDFs[/bold cyan]",
        border_style="grey70",
    )

def _process_download_result(future, future_map, results, recent_logs):
    log_message = ""
    try:
        result = future.result()
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
        doi = future_map[future]
        results.append({"doi": doi, "status": "exception"})
        log_message = (
            f"💥 [bold red]CRITICAL ERROR:[/bold red] [dim]{doi}[/dim]"
        )
    
    recent_logs.append(log_message)

def _print_summary(stats):
    tbl = Table(title="[bold]Download Summary[/bold]", show_header=False, box=None)
    tbl.add_column("Metric", style="cyan")
    tbl.add_column("Value", style="bold", justify="right")
    tbl.add_row("✅ Success", str(stats["success"]))
    tbl.add_row("⏩ Skipped", str(stats["skipped"]))
    tbl.add_row("❌ Failed", str(stats["fail"]))

    console.print(Rule("[bold green]Download Complete[/bold green]"))
    console.print(tbl)

def _save_failed_dois(results, output_dir):
    failed = [r["doi"] for r in results if r.get("status") in ("failed", "exception")]
    if failed:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        fp = out_path / "failed_dois.txt"
        fp.write_text("\n".join(sorted(failed)))
        console.print(
            f" ⚠️ [yellow]{len(failed)} DOIs failed — see 'failed_dois.txt' in the output folder.[/yellow]"
        )

def run_download(settings, dois):
    dl = Downloader(
        output_dir=settings["output_dir"],
        email=settings["email"],
        core_api_key=settings.get("core_api_key"),
        verify_ssl=settings["verify_ssl"],
    )

    results = []
    recent_logs = deque(maxlen=5)
    progress, progress_task = _create_progress_bar(len(dois))

    logger, prev_level, prev_handlers = _setup_logging_for_download(settings)

    try:
        with Live(
            _generate_live_panel(progress, recent_logs, len(dois)),
            console=console,
            screen=False,
            refresh_per_second=10,
            transient=True,
        ) as live:
            with ThreadPoolExecutor(max_workers=settings["max_workers"]) as ex:
                future_map = {ex.submit(dl.download_one, doi): doi for doi in dois}

                for f in as_completed(future_map):
                    _process_download_result(f, future_map, results, recent_logs)
                    progress.update(progress_task, advance=1)
                    live.update(_generate_live_panel(progress, recent_logs, len(dois)))
    finally:
        _restore_logging(logger, prev_level, prev_handlers, settings)

    _print_summary(dl.stats)
    _save_failed_dois(results, settings["output_dir"])

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

def _render_main_menu(current, options, settings, dois):
    terminal_width = console.size.width

    status_s = "[green]Configured[/green]" if settings else "[dim]Not Set[/dim]"
    status_d = f"[green]{len(dois)}[/green]" if dois else "[dim]0[/dim]"

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

def _handle_menu_input(k, current, options):
    if k in ("\x1b[A", "H", "UP"):
        return (current - 1) % len(options), None
    elif k in ("\x1b[B", "P", "DOWN"):
        return (current + 1) % len(options), None
    elif k in ("\r", "\n", "ENTER"):
        return current, options[current][0]
    elif k in ("1", "2", "3", "4", "5", "6", "7", "8"):
        return current, k
    elif k in ("q", "\x1b"):
        return current, "8"
    return current, None

def show_main_panel(settings, dois):
    force_refresh = False

    def handle_resize(signum, frame):
        nonlocal force_refresh
        force_refresh = True

    try:
        import signal
        signal.signal(signal.SIGWINCH, handle_resize)
    except (AttributeError, ImportError):
        pass

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

    console.clear()
    console.print("")

    with Live(_render_main_menu(current, options, settings, dois), console=console, refresh_per_second=30, screen=False) as live:
        while True:
            if force_refresh:
                force_refresh = False
                live.update(_render_main_menu(current, options, settings, dois))
                continue

            k = get_single_key()
            current, selection = _handle_menu_input(k, current, options)
            
            if selection:
                return selection

            live.update(_render_main_menu(current, options, settings, dois))
