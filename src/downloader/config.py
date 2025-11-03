# downloader/config.py
"""Configuration constants for the downloader."""

MAX_FILENAME_LEN = 200

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36",
    "OA-PDF-Retriever/1.0 (https://github.com/user/repo; mailto:user@example.com)",
]

UNPAYWALL_API_URL = "https://api.unpaywall.org/v2/{doi}"
OPENALEX_API_URL = "https://api.openalex.org/works/https://doi.org/{doi}"
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/v1/paper/{doi}"
CORE_API_URL = "https://api.core.ac.uk/v3/works/{doi}"
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"
DOI_RESOLVER_URL = "https://doi.org/{doi}"
