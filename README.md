# Open-Access PDF Retrieval System

[MIT License](https://opensource.org/licenses/MIT)

A professional command-line interface (CLI) tool designed to efficiently download open-access PDF articles using their Digital Object Identifiers (DOIs). The system features a robust, multi-source retrieval pipeline and supports a wide range of academic citation file formats.

## Key Features ✨

- **Interactive CLI:** A modern, keyboard-navigable menu for a smooth user experience.
- **Broad File Support:** Extracts DOIs directly from various citation formats, including BibTeX (`.bib`), RIS (`.ris`), EndNote (`.xml`, `.enw`), JSON (`.json`), and plain text lists (`.txt`, `.csv`).
- **Multi-Source Pipeline:** Intelligently searches for PDFs across multiple services, starting with legal open-access sources like Unpaywall and OpenAlex before falling back to others.
- **Parallel Downloads:** Utilizes multi-threading to download multiple PDFs simultaneously, significantly speeding up the process.
- **Smart Filenaming:** Automatically generates clean, descriptive filenames from article metadata (e.g., `Year - Title - DOI.pdf`).
- **Standalone Executable:** Comes with a professional build script to compile the entire application into a single, distributable `.exe` file for Windows, complete with an icon, version info, and optional code signing.

---

## Installation 🚀

To get started, clone the repository and install the required Python packages.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Zosick/PDF-Retriever-project.git
    cd PDF-Retriever-project
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    ```

    Activate it:

    - On Windows: `.\venv\Scripts\activate`
    - On macOS/Linux: `source venv/bin/activate`

3.  **Install dependencies:**
    A `requirements.txt` file should be created to list all dependencies. For now, you can install them manually:

    ```bash
    pip install rich bibtexparser rispy requests
    ```

---

## Usage 💻

Run the application from the project's root directory:

```bash
python -m downloader
```

This will launch the interactive main menu. Use the **arrow keys** to navigate and **Enter** to select an option.

- **Configure Settings:** Set your output directory, Unpaywall email, and enable/disable Sci-Hub.
- **Input DOIs:** Load DOIs from a citation file or enter them manually.
- **Begin Download:** Start the retrieval process for all loaded DOIs.

---

## Building the Executable 📦

You can compile the entire project into a single `.exe` file using the included build script.

1.  **Install PyInstaller:**

    ```bash
    pip install pyinstaller
    ```

2.  **Run the build script:**

    ```bash
    python build.py
    ```

The script will automatically clean previous artifacts, build the executable, and place the final `PDF Retriever.exe` file inside the `dist` folder.

### Code Signing (Optional)

The build script includes a feature to digitally sign the executable. To use it:

- Place your `.pfx` code signing certificate anywhere in the project directory.
- The script will automatically find it and prompt you for the password during the build process.

---

## Project Structure

```
PDF-Retriever-project/
│
├── src/                               # Application source code
│   └── downloader/                    # Main PDF retriever package
│       ├── __init__.py                # Package marker + version export
│       ├── __main__.py                # Allows `python -m downloader` execution
│       ├── cli.py                     # Command-line interface (Click commands)
│       ├── config.py                  # App configuration settings & defaults
│       ├── core.py                    # Core logic for retrieving PDFs
│       ├── exceptions.py              # Custom exception classes
│       ├── parsers.py                 # DOI / URL parsing & handling logic
│       ├── sources.py                 # Handlers for different PDF sources
│       └── utils.py                   # Helper functions (I/O, logging, etc.)
│
├── tests/                             # Unit tests (pytest)
│   ├── __init__.py
│   ├── test_cli.py                    # Tests for CLI behavior
│   ├── test_core.py                   # Tests for core download logic
│   └── test_parsers.py                # Tests for DOI/URL parsing
│
├── assets/                            # Static files (icons, logos, etc.)
│   └── favicon.ico                    # App icon for executable builds
│
├── data/                              # Input data, configs, metadata
│
├── downloads/                         # Downloaded PDFs go here (ignored by Git)
│
├── output/                            # Output files (processed data, exports)
│
├── temp/                              # Temporary working directory
│
├── run.py                             # Simple entry script to run the app
├── build_exe.py                       # PyInstaller build script
├── requirements.txt                   # Python dependencies
├── version_info.txt                   # App version reference
│
├── README.md                          # Project overview & usage instructions
├── LICENSE.txt                        # MIT open-source license
│
└── .gitignore                         # Ignore files for Git
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.
