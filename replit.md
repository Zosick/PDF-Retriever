# Open-Access PDF Retrieval System

## Overview
This is a professional command-line interface (CLI) tool designed to efficiently download open-access PDF articles using their Digital Object Identifiers (DOIs). The system features a robust, multi-source retrieval pipeline and supports a wide range of academic citation file formats.

**Current State**: Fully functional TUI application running on Replit with all dependencies installed.

## Recent Changes
- **2025-11-21**: Initial Replit environment setup
  - Installed Python 3.11
  - Installed all required dependencies from requirements.txt
  - Configured workflow to run the TUI application
  - Application tested and verified working

## Project Architecture

### Technology Stack
- **Language**: Python 3.11
- **UI Framework**: Rich (for terminal user interface)
- **Key Libraries**: 
  - requests (HTTP requests)
  - bibtexparser, rispy (citation file parsing)
  - beautifulsoup4 (HTML parsing)
  - cryptography (security)

### Project Structure
```
PDF-Retriever/
├── src/
│   └── downloader/           # Main application package
│       ├── __init__.py
│       ├── __main__.py       # Makes package runnable
│       ├── cli.py            # Interactive TUI (main entry point)
│       ├── core.py           # Downloader orchestration
│       ├── config.py         # API endpoints & constants
│       ├── settings.py       # Settings management
│       ├── parsers.py        # DOI extraction from citation files
│       ├── sources.py        # Base source class
│       ├── *_source.py       # Individual API source implementations
│       ├── exceptions.py     # Custom exceptions
│       └── utils.py          # Utility functions
├── tests/                    # Test suite
├── assets/                   # Application assets (favicon)
├── run.py                    # Simple entry script
├── build_exe.py             # PyInstaller build script (Windows only)
├── requirements.txt         # Python dependencies
└── pyproject.toml          # Tool configuration (ruff, mypy, pytest)
```

## Running the Application

### In Replit
The application runs automatically via the configured workflow. The TUI will display an interactive menu with the following options:

1. **Configure Settings** - Set output directory, Unpaywall email, CORE API key
2. **Input DOIs** - Load DOIs from citation files or enter manually
3. **Begin Download** - Start retrieving PDFs
4. **View Failed List** - Check DOIs that couldn't be retrieved
5. **Open Output Folder** - Access downloaded PDFs
6. **Test System Status** - Ping all API sources
7. **Clear Settings** - Reset configuration
8. **Quit** - Exit application

### Required Configuration
Before downloading PDFs, you must configure:
- **Email** (required): Needed for Unpaywall API
- **Output Directory** (optional): Where PDFs will be saved
- **CORE API Key** (optional): For enhanced metadata retrieval

## Data Sources
The application queries 10 open-access sources:
1. Crossref
2. Unpaywall
3. CORE
4. PubMed Central (PMC)
5. Directory of Open Access Journals (DOAJ)
6. Zenodo
7. Open Science Framework (OSF)
8. arXiv
9. OpenAlex
10. Semantic Scholar

## Features
- **Multi-format Support**: BibTeX, RIS, EndNote XML, Zotero JSON, plain text
- **Parallel Downloads**: Multi-threaded for speed
- **Smart Naming**: APA 7th style filenames (`Author et al., Year - Title - DOI.pdf`)
- **Metadata Pipeline**: Intelligently combines data from multiple sources
- **SSL Verification**: Secure by default (configurable)

## Limitations
- **Open Access Only**: Cannot bypass paywalls
- **API Rate Limits**: Some sources may throttle bulk requests
- **Metadata Quality**: Dependent on API responses

## Development Notes

### Local Development (Outside Replit)
```bash
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
python run.py
```

### Running Tests
```bash
pytest
```

### Code Quality Tools
- **Formatter**: ruff (configured in pyproject.toml)
- **Type Checker**: mypy
- **Testing**: pytest

### Building Executable (Windows Only)
The `build_exe.py` script uses PyInstaller to create a standalone .exe file. This is for Windows distribution only and not applicable to Replit environment.

## User Preferences
None set yet. This section will track coding style, workflow preferences, and other user-specific settings as the project evolves.

## License
- Source code: MIT License (see LICENSE.txt)
- Executable: EULA (see EULA.txt)
