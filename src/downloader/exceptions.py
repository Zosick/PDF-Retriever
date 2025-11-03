# downloader/exceptions.py
"""Custom exceptions for the downloader application."""


class PDFNotFound(Exception):
    """Raised when a PDF cannot be found from any source for a given DOI."""

    pass


class UnrecoverableError(Exception):
    """Raised for non-retriable request or file-saving errors."""

    pass


class DOIExtractionError(Exception):
    """Raised when DOI extraction from an input file fails."""

    pass
