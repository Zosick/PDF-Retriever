import sys
import os
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
import shutil
import glob
import argparse
import getpass
import hashlib
from datetime import datetime

console = Console()

# --- Configuration ---
MAIN_SCRIPT = "run.py"
EXE_NAME = "PDF Retriever.exe"
VERSION_FILE = "version_info.txt"
ICON_FILE = "assets/favicon.ico"

DIST_PATH = Path("dist")
BUILD_PATH = Path("build")
EXE_PATH = DIST_PATH / EXE_NAME
# ---------------------


def clean_build_artifacts():
    """Remove previous build artifacts."""
    console.print("🧹 Cleaning up old build artifacts...")
    try:
        if DIST_PATH.exists():
            shutil.rmtree(DIST_PATH)
        if BUILD_PATH.exists():
            shutil.rmtree(BUILD_PATH)
        for f in glob.glob("*.spec"):
            Path(f).unlink()
        console.print("[green]✓ Cleanup complete.[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not clean all artifacts: {e}[/yellow]")


def run_build():
    """Run the PyInstaller build process with a Rich display."""
    console.rule("📦 Building Executable with PyInstaller", style="bold cyan")
    clean_build_artifacts()

    console.print("Verifying required files...")
    if not Path(MAIN_SCRIPT).exists():
        console.print(f"[red]✗ Error: Main script '{MAIN_SCRIPT}' not found.[/red]")
        return False

    pyinstaller_args = []

    if Path(VERSION_FILE).exists():
        console.print(f"   [green]✓ Found version information[/green]")
        pyinstaller_args.append(f"--version-file={VERSION_FILE}")
    else:
        console.print(
            f"   [yellow]⚠ Version file '{VERSION_FILE}' not found, building without metadata.[/yellow]"
        )

    if Path(ICON_FILE).exists():
        console.print(f"   [green]✓ Found icon file[/green]")
        pyinstaller_args.append(f"--icon={ICON_FILE}")
    else:
        console.print(
            f"   [yellow]⚠ Icon file '{ICON_FILE}' not found, using default icon.[/yellow]"
        )

    pyinstaller_args.extend(
        [
            "--onefile",
            "--console",
            f"--name={EXE_NAME.replace('.exe', '')}",
            "--clean",
            "--noconfirm",
            "--hidden-import=bibtexparser",
            "--hidden-import=rispy",
            "--hidden-import=requests",
            "--hidden-import=msvcrt",
            "--paths=src",
            "--exclude-module=tests",
            "--exclude-module=pytest",
            MAIN_SCRIPT,
        ]
    )

    pyinstaller_cmd = [sys.executable, "-m", "PyInstaller"] + pyinstaller_args

    console.print(f"\nRunning PyInstaller for [cyan]{MAIN_SCRIPT}[/cyan]...")
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Building {EXE_NAME}...", total=None)
            result = subprocess.run(
                pyinstaller_cmd,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
            )
            progress.update(
                task, completed=True, description="[green]✓ Build complete[/green]"
            )

        if not EXE_PATH.exists():
            console.print(
                f"[red]✗ Build finished, but EXE not found at '{EXE_PATH}'[/red]"
            )
            console.print(
                Panel(
                    result.stdout,
                    title="PyInstaller Log",
                    style="yellow",
                    border_style="yellow",
                )
            )
            return False

        console.print(
            f"[bold green]✅ Build successful! Executable at: {EXE_PATH}[/bold green]"
        )
        return True

    except subprocess.CalledProcessError as e:
        console.print("[red]✗ Build failed[/red]")
        error_output = e.stdout + "\n---\n" + e.stderr
        console.print(
            Panel(
                error_output, title="PyInstaller Error", style="red", border_style="red"
            )
        )
        return False
    except FileNotFoundError:
        console.print(
            "[red]✗ Error: PyInstaller not found. Please install it with: [cyan]pip install pyinstaller[/cyan][/red]"
        )
        return False
    except Exception as e:
        console.print(f"[red]✗ An unexpected error occurred during build: {e}")
        return False


def find_signtool() -> Path | None:
    """Automatically find the path to signtool.exe."""
    if "ProgramFiles(x86)" not in os.environ:
        return None
    base_path = Path(os.environ["ProgramFiles(x86)"]) / "Windows Kits" / "10" / "bin"
    if not base_path.exists():
        return None

    signtool_paths = list(base_path.rglob("signtool.exe"))
    if not signtool_paths:
        return None

    x64_tool = next(
        (path for path in signtool_paths if "x64" in str(path).lower()), None
    )
    return x64_tool or signtool_paths[0]


def run_signing(exe_path, cli_password=None):
    """Run code signing by automatically locating the .pfx and signtool.exe files."""
    console.rule("🔐 Code Signing", style="bold yellow")

    pfx_files = list(Path(".").rglob("*.pfx"))
    if not pfx_files:
        console.print(
            "[yellow]⚠ Signing skipped: No .pfx certificate file found.[/yellow]"
        )
        return True
    elif len(pfx_files) > 1:
        console.print(
            "[red]✗ Signing failed: Multiple .pfx files found. Please ensure only one is present.[/red]"
        )
        return False
    pfx_path = pfx_files[0]

    signtool_path = find_signtool()
    if not signtool_path:
        console.print(
            "[yellow]⚠ Signing skipped: Could not find signtool.exe in the Windows Kits directory.[/yellow]"
        )
        return True

    console.print(f"   [green]✓ Found certificate:[/green] [dim]{pfx_path}[/dim]")
    console.print(f"   [green]✓ Found signtool:[/green] [dim]{signtool_path}[/dim]")

    try:
        if cli_password:
            password = cli_password
        else:
            password = getpass.getpass("Enter PFX password: ")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Signing executable...", total=1)
            sign_cmd = [
                str(signtool_path),
                "sign",
                "/f",
                str(pfx_path),
                "/p",
                password,
                "/fd",
                "sha256",
                "/tr",
                "http://timestamp.digicert.com",
                "/td",
                "sha256",
                str(exe_path),
            ]
            subprocess.run(
                sign_cmd, capture_output=True, text=True, check=True, encoding="utf-8"
            )
            progress.update(
                task, advance=1, description="[green]✓ Executable signed[/green]"
            )

            verify_task = progress.add_task("Verifying signature...", total=1)
            verify_cmd = [str(signtool_path), "verify", "/pa", "/v", str(exe_path)]
            subprocess.run(
                verify_cmd, capture_output=True, check=True, encoding="utf-8"
            )
            progress.update(
                verify_task,
                advance=1,
                description="[green]✓ Signature verified[/green]",
            )

        console.print(
            "[bold green]✅ Executable signed and verified successfully![/bold green]"
        )
        return True

    except subprocess.CalledProcessError as e:
        console.print("[red]✗ Signing failed[/red]")
        error_output = e.stdout + "\n---\n" + e.stderr
        console.print(
            Panel(error_output, title="Signing Error", style="red", border_style="red")
        )
        return False
    except Exception as e:
        console.print(f"[red]✗ Signing error: {e}")
        return False


# --- FINAL INTEGRATED HASHING FUNCTION ---
def generate_and_save_hashes(exe_path: Path):
    """Generates SHA2 & SHA3 hashes and saves them to a file."""
    console.rule("🧮 Generating File Hashes", style="bold blue")

    if not exe_path.exists():
        console.print(
            f"[red]✗ Cannot generate hashes: File not found at {exe_path}[/red]"
        )
        return

    algorithms = {
        "SHA-256": hashlib.sha256,
        "SHA-512": hashlib.sha512,
        "SHA3-256": hashlib.sha3_256,
        "SHA3-512": hashlib.sha3_512,
    }

    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Calculating hashes...", total=len(algorithms))

        for name, algo_constructor in algorithms.items():
            progress.update(task, description=f"Calculating {name}...")
            hasher = algo_constructor()
            try:
                # Use memory-safe chunking for robustness with large files
                with open(exe_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
                hash_value = hasher.hexdigest()
                results.append(f"{name:<10}: {hash_value}")
            except Exception as e:
                console.print(f"[red]✗ Hashing error for {name}: {e}[/red]")
                results.append(f"{name:<10}: FAILED")

            progress.update(task, advance=1)

        progress.update(task, description="[green]✓ Hashes calculated[/green]")

    # Create timestamped hash file
    timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    hash_file_path = exe_path.parent / f"hashes_{timestamp_str}.txt"

    try:
        with open(hash_file_path, "w", encoding="utf-8") as f:
            f.write(
                f"File: {exe_path.name}\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
            f.write("\n".join(results))

        console.print(f"[bold green]✅ Hashes saved to: {hash_file_path}[/bold green]")
        # Print results directly to console for immediate feedback
        console.print("\n".join(results))
    except Exception as e:
        console.print(f"[red]✗ Could not save hash file: {e}[/red]")


def main():
    parser = argparse.ArgumentParser(
        description="Build and optionally sign the PDF Retriever CLI."
    )
    parser.add_argument("-p", "--password", help="PFX password for code signing.")
    args = parser.parse_args()

    console.clear()
    console.rule("🚀 PDF Retriever Build, Sign & Hash", style="bold cyan")

    if not run_build():
        return 1

    if EXE_PATH.exists():
        # --- Signing Logic ---
        can_sign = any(Path(".").rglob("*.pfx")) and find_signtool()
        should_sign = False

        if args.password:
            console.print("\nPassword provided via argument, attempting to sign...")
            should_sign = True
        elif can_sign:
            sign = Prompt.ask(
                "\nProceed with code signing?", choices=["y", "n"], default="y"
            )
            if sign.lower() == "y":
                should_sign = True

        if should_sign:
            if not run_signing(EXE_PATH, cli_password=args.password):
                console.print("[yellow]⚠ Build completed but signing failed.[/yellow]")
        elif can_sign:
            console.print("\n[yellow]Build completed without signing.[/yellow]")

        # --- Hashing is now the final step in the workflow ---
        generate_and_save_hashes(EXE_PATH)

    console.rule("🎊 Process Complete", style="bold green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
