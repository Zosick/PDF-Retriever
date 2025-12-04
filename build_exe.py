import argparse
import getpass
import hashlib
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

console = Console()

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent.resolve()  # Get script's absolute directory

MAIN_SCRIPT = SCRIPT_DIR / "run.py"
EXE_NAME = "PDF Retriever.exe"
VERSION_FILE = SCRIPT_DIR / "version_info.txt"
ICON_FILE = SCRIPT_DIR / "assets/favicon.ico"

DIST_PATH = SCRIPT_DIR / "dist"
BUILD_PATH = SCRIPT_DIR / "build"
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
        # Search for .spec files in the script's directory
        for f in SCRIPT_DIR.glob("*.spec"):
            f.unlink()
        console.print("[green]✓ Cleanup complete.[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not clean all artifacts: {e}[/yellow]")


def _verify_files() -> bool:
    """Verify that required files exist."""
    console.print("Verifying required files...")
    if not MAIN_SCRIPT.exists():
        console.print(f"[red]✗ Error: Main script '{MAIN_SCRIPT}' not found.[/red]")
        return False
    return True


def _build_pyinstaller_args() -> list[str]:
    """Construct the arguments for PyInstaller."""
    args = []
    if VERSION_FILE.exists():
        console.print("   [green]✓ Found version information[/green]")
        args.append(f"--version-file={VERSION_FILE}")
    else:
        console.print(
            f"   [yellow]⚠ Version file '{VERSION_FILE}' not found, building without metadata.[/yellow]"
        )

    if ICON_FILE.exists():
        console.print("   [green]✓ Found icon file[/green]")
        args.append(f"--icon={ICON_FILE}")
    else:
        console.print(
            f"   [yellow]⚠ Icon file '{ICON_FILE}' not found, using default icon.[/yellow]"
        )

    args.extend(
        [
            "--onefile",
            "--windowed",
            f"--name={EXE_NAME.replace('.exe', '')}",
            "--clean",
            "--noconfirm",
            f"--add-data={ICON_FILE}{os.pathsep}assets",
            "--hidden-import=bibtexparser",
            "--hidden-import=rispy",
            "--hidden-import=requests",
            "--hidden-import=msvcrt",
            f"--paths={SCRIPT_DIR / 'src'}",
            "--exclude-module=tests",
            "--exclude-module=pytest",
            str(MAIN_SCRIPT),
        ]
    )
    return args


def _execute_pyinstaller(args: list[str]) -> bool:
    """Execute the PyInstaller command."""
    cmd = [sys.executable, "-m", "PyInstaller"] + args
    console.print(f"\nRunning PyInstaller for [cyan]{MAIN_SCRIPT.name}[/cyan]...")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Building {EXE_NAME}...", total=None)
            result = subprocess.run(
                cmd,
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


def run_build():
    """Run the PyInstaller build process with a Rich display."""
    console.rule("📦 Building Executable with PyInstaller", style="bold cyan")
    clean_build_artifacts()

    if not _verify_files():
        return False

    args = _build_pyinstaller_args()
    return _execute_pyinstaller(args)


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


def _find_pfx_file() -> tuple[Path | None, bool]:
    """
    Find the .pfx file.
    Returns: (path, success)
    """
    pfx_files = list(SCRIPT_DIR.rglob("*.pfx"))
    if not pfx_files:
        console.print(
            "[yellow]⚠ Signing skipped: No .pfx certificate file found.[/yellow]"
        )
        return None, True
    elif len(pfx_files) > 1:
        console.print(
            "[red]✗ Signing failed: Multiple .pfx files found. Please ensure only one is present.[/red]"
        )
        return None, False
    return pfx_files[0], True


def _perform_signing(signtool_path: Path, pfx_path: Path, exe_path: Path, password: str) -> bool:
    """Execute the signing and verification commands."""
    try:
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


def run_signing(exe_path, cli_password=None):
    """Run code signing by automatically locating the .pfx and signtool.exe files."""
    console.rule("🔐 Code Signing", style="bold yellow")

    pfx_path, success = _find_pfx_file()
    if not success:
        return False
    if not pfx_path:
        return True

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

        return _perform_signing(signtool_path, pfx_path, exe_path, password)
    except Exception as e:
        console.print(f"[red]✗ Signing error: {e}")
        return False


# --- FINAL INTEGRATED HASHING FUNCTION ---
def _calculate_hashes(exe_path: Path) -> dict[str, str]:
    """Calculate hashes for the executable using multiple algorithms."""
    algorithms = {
        "SHA-256": hashlib.sha256,
        "SHA-512": hashlib.sha512,
        "SHA3-256": hashlib.sha3_256,
        "SHA3-512": hashlib.sha3_512,
    }

    hash_results = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Calculating hashes...", total=len(algorithms))

        for name, algo in algorithms.items():
            progress.update(task, description=f"Calculating {name}...")
            h = algo()
            with open(exe_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            hash_results[name] = h.hexdigest()
            progress.update(task, advance=1)
    return hash_results


def _save_hash_files(exe_path: Path, hash_results: dict[str, str]):
    """Save the calculated hashes to files."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # ✅ Internal log with ALL algorithms
    full_log = exe_path.parent / f"hashes_{timestamp}.txt"
    with open(full_log, "w", encoding="utf-8") as f:
        f.write(f"File: {exe_path.name}\nGenerated: {datetime.now()}\n\n")
        for alg, value in hash_results.items():
            f.write(f"{alg:<10}: {value}\n")

    # ✅ Public hash file — SHA-256 only
    sha256_value = hash_results["SHA-256"]
    public_txt = exe_path.parent / "hash.txt"
    with open(public_txt, "w", encoding="utf-8") as f:
        f.write(f"SHA-256: {sha256_value}\n")

    # ✅ Linux/macOS style .sha256 file
    sha256_file = exe_path.parent / f"{exe_path.name}.sha256"
    with open(sha256_file, "w", encoding="utf-8") as f:
        f.write(f"{sha256_value}  {exe_path.name}\n")

    console.print(f"[green]✅ Internal hash log: {full_log}")
    console.print(f"[green]✅ Public hash file: {public_txt}")
    console.print(f"[green]✅ .sha256 checksum: {sha256_file}")


def generate_and_save_hashes(exe_path: Path):
    """Generate full internal hashes + public hash files."""
    console.rule("🧮 Generating File Hashes", style="bold blue")

    if not exe_path.exists():
        console.print(
            f"[red]✗ Cannot generate hashes: File not found at {exe_path}[/red]"
        )
        return

    hash_results = _calculate_hashes(exe_path)
    _save_hash_files(exe_path, hash_results)


def _should_sign(args) -> bool:
    """Determine if signing should be attempted."""
    can_sign = any(SCRIPT_DIR.rglob("*.pfx")) and find_signtool()

    if args.password:
        console.print("\nPassword provided via argument, attempting to sign...")
        return True

    if can_sign:
        sign = Prompt.ask(
            "\nProceed with code signing?", choices=["y", "n"], default="y"
        )
        if sign.lower() == "y":
            return True
        else:
            console.print("\n[yellow]Build completed without signing.[/yellow]")

    return False


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
        if _should_sign(args):
            if not run_signing(EXE_PATH, cli_password=args.password):
                console.print("[yellow]⚠ Build completed but signing failed.[/yellow]")
        
        # --- Hashing is now the final step in the workflow ---
        generate_and_save_hashes(EXE_PATH)

    console.rule("🎊 Process Complete", style="bold green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
