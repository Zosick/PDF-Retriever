# Open-Access PDF Retrieval System

## Overview
This is a professional command-line interface (CLI) tool designed to efficiently download open-access PDF articles using their Digital Object Identifiers (DOIs). The system features a robust, multi-source retrieval pipeline and supports a wide range of academic citation file formats.

**Project Type:** Python TUI (Terminal User Interface) application  
**Main Framework:** Rich (for interactive terminal menus)  
**Current State:** Imported from GitHub and configured for Replit environment

## Purpose & Goals
- Provide researchers with an easy-to-use tool to download open-access PDFs
- Extract DOIs from various citation formats (BibTeX, RIS, EndNote XML, Zotero JSON, plain text)
- Intelligently fetch metadata from 10+ academic sources (Crossref, Unpaywall, CORE, PMC, DOAJ, etc.)
- Download PDFs with standardized APA 7th-style filenames
- Support parallel downloads for efficiency

## Recent Changes
- **2025-11-14:** Major improvements to PDF retrieval and UI
  - **Initial Setup:**
    - Installed Python 3.11 and all required dependencies
    - Updated .gitignore for Replit-specific files
    - Configured workflow to run the TUI application
    - Fixed missing imports (requests in utils.py, Path in pmc_source.py)
  - **PDF Retrieval Improvements:**
    - Added retry logic with exponential backoff for network failures (up to 3 attempts)
    - Enhanced PDF validation to detect corrupted/incomplete files (EOF marker check)
    - Better error detection for access-denied and forbidden responses
    - Improved robustness of download pipeline
  - **UI/CLI Enhancements:**
    - Fixed terminal resizing to work gracefully on all screen sizes
    - Adaptive UI that adjusts text and layout for narrow terminals (< 80 chars)
    - Eliminated UI flickering by disabling automatic refresh
    - Improved cross-platform compatibility for Windows, Linux, and macOS
    - Better screen clearing with fallback mechanisms
  - **Code Quality:**
    - Added proper error handling throughout
    - Respects API terms of service with rate limiting

## Project Architecture

### Technology Stack
- **Language:** Python 3.11
- **Key Libraries:**
  - `rich` - Terminal UI framework
  - `requests` - HTTP requests for API calls
  - `bibtexparser` - BibTeX file parsing
  - `rispy` - RIS file parsing
  - `beautifulsoup4` - HTML parsing
  - `cryptography` - Secure credential storage

### Directory Structure
```
PDF-Retriever-project/
├── src/downloader/          # Main application package
│   ├── __main__.py          # Package entry point
│   ├── cli.py               # Interactive TUI using rich
│   ├── core.py              # Main Downloader orchestration
│   ├── config.py            # API endpoints and constants
│   ├── parsers.py           # DOI extraction from files
│   ├── sources.py           # Base Source class and implementations
│   ├── *_source.py          # Specific API source implementations
│   └── utils.py             # Helper functions
├── tests/                   # Test suite
├── assets/                  # Application assets
├── run.py                   # Simple entry script
└── requirements.txt         # Python dependencies
```

### Key Features
1. **Interactive TUI:** Keyboard-navigable menu system
2. **Multiple Citation Formats:** BibTeX, RIS, EndNote XML, Zotero JSON, CSV, TXT
3. **10+ Metadata Sources:** Crossref, Unpaywall, CORE, PMC, DOAJ, Zenodo, OSF, arXiv, OpenAlex, Semantic Scholar
4. **Smart Download Pipeline:** Prioritized OA source checking
5. **Parallel Processing:** Multi-threaded downloads
6. **APA Formatting:** Standardized filename generation

### Application Entry Points
- Primary: `python -m src.downloader`
- Alternative: `python run.py`

## Configuration
The application stores user settings in `~/.pdf_retriever/`:
- `settings.json` - User preferences (output directory, API keys)
- `key.key` - Encryption key for secure credential storage

### Required API Keys
- **Unpaywall Email:** Required for Unpaywall API access
- **CORE API Key:** Optional, for enhanced CORE access

## User Preferences
None set yet (first-time setup)

## Development Notes
- This is a CLI/TUI application, not a web application
- No frontend server or database required
- Application runs in the terminal with interactive menus
- Replit environment uses Python 3.11 with all dependencies installed via pip

## Important Limitations
- **Open Access Only:** Cannot bypass paywalls, only retrieves legally-hosted OA versions
- **API Rate Limits:** Some APIs have rate limits for large batches
- **Metadata Quality:** Filenames depend on API metadata quality
