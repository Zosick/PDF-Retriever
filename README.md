# Open-Access PDF Retrieval System

![Last Commit](https://img.shields.io/github/last-commit/Zosick/PDF-Retriever?style=flat-square)
![Forks](https://img.shields.io/github/forks/Zosick/PDF-Retriever?style=flat-square)
![Issues](https://img.shields.io/github/issues/Zosick/PDF-Retriever?style=flat-square)
![Contributors](https://img.shields.io/github/contributors/Zosick/PDF-Retriever?style=flat-square)
![Stars](https://img.shields.io/github/stars/Zosick/PDF-Retriever?style=flat-square)
![License](https://img.shields.io/github/license/Zosick/PDF-Retriever?style=flat-square)

A modern graphical user interface (GUI) application designed to efficiently download open-access PDF articles using their Digital Object Identifiers (DOIs). The system features a robust, multi-source retrieval pipeline and supports a wide range of academic citation file formats.

> [!NOTE]
> **Migration to GUI**: This project is transitioning from a command-line interface to a full-featured GUI using CustomTkinter for an improved user experience.

## ✨ Key Features

- **Modern GUI:** A sleek, user-friendly graphical interface built with `CustomTkinter` for an intuitive experience.
- **Broad File Support:** Extracts DOIs directly from various citation formats, including:
  - BibTeX (`.bib`)
  - RIS (`.ris`)
  - EndNote XML (`.xml`, `.enw`)
  - Zotero JSON (`.json`)
  - Plain text lists (`.txt`, `.csv`)
- **Advanced Metadata Pipeline:** Intelligently fetches and combines article metadata (Title, Author, Year) from a prioritized list of **10 sources**:
  - Crossref
  - Unpaywall
  - CORE
  - PubMed Central (PMC)
  - Directory of Open Access Journals (DOAJ)
  - Zenodo
  - Open Science Framework (OSF)
  - arXiv
  - OpenAlex
  - Semantic Scholar
- **Parallel Metadata Fetching:** Concurrently queries multiple metadata sources to find the best available metadata and PDF links faster.
- **Smart Download Pipeline:** If metadata is found, it attempts to download the PDF from a separate, prioritized pipeline of OA sources.
- **Parallel Downloads:** Utilizes multi-threading to download multiple PDFs simultaneously, significantly speeding up the process.
- **Standardized Naming:** Automatically generates clean, APA 7th-style filenames:
  `Author et al., Year - Title - DOI.pdf`
- **Standalone Executable:** Comes with a professional build script (`build_exe.py`) to compile the entire application into a single, distributable `.exe` file for Windows, complete with an icon, version info, and optional code signing.

---

## 🚀 Installation

To get started, clone the repository and install the required Python packages.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Zosick/PDF-Retriever.git
    cd PDF-Retriever
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    ```

    Activate it:

    - On Windows: `.\venv\Scripts\activate`
    - On macOS/Linux: `source venv/bin/activate`

3.  **Install dependencies:**
    A `requirements.txt` file is included.

    ```bash
    pip install -r requirements.txt
    ```

    _(The file includes: `rich`, `requests`, `bibtexparser`, `rispy`, `beautifulsoup4`)_

---

## 💻 Usage

Run the GUI application from the project's root directory:

```bash
python -m src.downloader.gui
```

Or use the standalone executable (after building):

```bash
.\dist\"PDF Retriever.exe"
```

### GUI Features:

- **Settings Panel:** Configure output directory, Unpaywall email (Required), CORE API key, SSL settings, and parallel download count.
- **DOI Input:** Load DOIs from citation files (.bib, .ris, .json, etc.) or paste them directly.
- **Real-time Progress:** Live progress bar and detailed logging of each download.
- **Retry Failed Downloads:** Automatically load and retry previously failed DOIs.
- **System Status Check:** Test connectivity to all 10+ APIs with one click.
- **Open Output Folder:** Quick access to your downloaded PDFs.

---

## 📦 Building the Executable

You can compile the entire project into a single `.exe` file using the included build script.

1.  **Install PyInstaller:**

    ```bash
    pip install pyinstaller
    ```

2.  **Run the build script:**

    ```bash
    python build_exe.py
    ```

The script will automatically clean previous artifacts, build the executable, and place the final `PDF Retriever.exe` file inside the `dist` folder.

### Code Signing (Optional)

The build script includes a feature to digitally sign the executable. To use it:

- Place your `.pfx` code signing certificate anywhere in the project directory.
- The script will automatically find it and prompt you for the password during the build process.

---

## ⚠️ Security, Limitations & Legal Notice

### Security

- **Antivirus:** This application writes `.pdf` files from the internet to your disk. While the tool only downloads from public academic repositories, all users should run active antivirus software (e.g., Windows Defender) that provides real-time scanning of all new files.
- **SSL Verification:** By default, this tool verifies SSL certificates. You can disable this in the settings (option `Bypass SSL verification?`), but it is **not recommended** as it makes you vulnerable to man-in-the-middle (MITM) attacks. Only use this if you are behind a corporate firewall that uses self-signed certificates.

### Limitations

- **Open Access Only:** This tool is **NOT** a "piracy" tool and **cannot** bypass paywalls. It _only_ searches for legally-hosted, open-access (OA) versions of articles. If a PDF is not available from one of the 10+ OA sources, the download for that DOI will fail.
- **API Rate Limits:** The tool is designed to be a "polite" client, but some APIs (like Unpaywall and Crossref) have rate limits. If you are processing thousands of DOIs, you may be temporarily rate-limited.
- **Metadata Quality:** The filename `Author et al., Year - Title - DOI.pdf` is 100% dependent on the metadata returned by the APIs. If an API provides incomplete data, the filename will reflect that (e.g., `Unknown Author, 2024 - Title - DOI.pdf`).

### Legal, Terms of Service, and Acknowledgments

This tool is an API client. As a user, you are responsible for abiding by the terms of service for all APIs this tool contacts. This tool is provided "as is," without warranty, and the authors are not liable for any misuse.

This project gratefully acknowledges the following open data services:

- **Crossref:** [https://www.crossref.org/services/metadata-retrieval/](https://www.crossref.org/services/metadata-retrieval/)
- **Unpaywall:** [https://unpaywall.org/products/api](https://unpaywall.org/products/api)
- **OpenAlex:** Please cite their paper:
  > Priem, J., Piwowar, H., & Orr, R. (2022). _OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts._ arXiv. [https://arxiv.org/abs/2205.01833](https://arxiv.org/abs/2205.01833)
- **CORE:** Please cite their paper:
  > Knoth, P. and Zdrahal, Z. (2012) _CORE: Three Access Levels to Underpin Open Access._ D-Lib Magazine, 18(11/12). [http://www.dlib.org/dlib/november12/knoth/11knoth.html](http://www.dlib.org/dlib/november12/knoth/11knoth.html)
- **Semantic Scholar:** This tool uses the Semantic Scholar API in accordance with its license. [https://www.semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)
- **arXiv:** [https://arxiv.org/](https://arxiv.org/)
- **PubMed Central (PMC):** [https://www.ncbi.nlm.nih.gov/pmc/](https://www.ncbi.nlm.nih.gov/pmc/)
- **Directory of Open Access Journals (DOAJ):** [https://doaj.org/](https://doaj.org/)
- **Zenodo:** [https://zenodo.org/](https://zenodo.org/)
- **Open Science Framework (OSF):** [https://osf.io/](https://osf.io/)

---

## 📂 Project Structure

This project has been refactored for clarity and maintainability.

```
PDF-Retriever-project/
│
├── src/
│   └── downloader/
│       ├── __init__.py
│       ├── __main__.py         # Makes the package runnable
│       ├── cli.py              # The interactive rich-based UI
│       ├── config.py           # API endpoints and constants
│       ├── core.py             # The main Downloader orchestration class
│       ├── download_manager.py # Threaded download manager
│       ├── exceptions.py
│       ├── gui.py              # CustomTkinter GUI
│       ├── parsers.py          # DOI extraction from .bib, .ris, etc.
│       ├── protocol.py         # Protocol definitions
│       ├── settings.py         # Settings models
│       ├── settings_manager.py # Settings persistence
│       ├── sources.py          # Abstract Base Source class
│       ├── tui.py              # Terminal UI components
│       ├── types.py            # Type definitions
│       ├── utils.py            # Filename sanitizers and author formatters
│       ├── arxiv_source.py     # Arxiv source
│       ├── core_api_source.py  # CORE API source
│       ├── crossref_source.py  # Crossref source
│       ├── doaj_source.py      # DOAJ source
│       ├── doi_resolver_source.py # Direct DOI resolution
│       ├── openalex_source.py  # OpenAlex source
│       ├── osf_source.py       # OSF source
│       ├── pmc_source.py       # PubMed Central source
│       ├── semantic_scholar_source.py # Semantic Scholar source
│       ├── unpaywall_source.py # Unpaywall source
│       └── zenodo_source.py    # Zenodo source
│
├── assets/
│   └── favicon.ico
│
├── data/                       # (GitIgnored) Saved settings
├── downloads/                  # (GitIgnored) Default PDF output folder
├── output/                     # (GitIgnored) Failed DOI lists
│
├── run.py                      # Simple entry script
├── build_exe.py                # PyInstaller build script
├── requirements.txt
│
├── README.md                   # This file
├── LICENSE.txt                 # MIT License for the source code
├── EULA.txt                    # End-User License Agreement for the executable
│
└── .gitignore
```

---

## 📜 License & EULA

This project's source code is licensed under the **MIT License**. See the `LICENSE.txt` file for details.

The distributed executable (`PDF Retriever.exe`) is governed by the **End-User License Agreement**. See the `EULA.txt` file for details on your rights and responsibilities when _using_ the software.
