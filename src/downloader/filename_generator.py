from typing import Any
from .utils import format_authors_apa, safe_filename

class FilenameGenerator:
    def generate_filename(self, metadata: dict[str, Any]) -> str:
        title = (metadata.get("title") or "Unknown Title").strip()
        year = (metadata.get("year") or "Unknown").strip()
        authors = metadata.get("authors", [])
        doi_part = metadata.get("doi", "unknown").replace("/", "_")
        author_str = format_authors_apa(authors)
        parts = []
        
        if author_str != "Unknown Author" and year != "Unknown":
            parts.append(f"{author_str}, {year}")
        elif author_str != "Unknown Author":
            parts.append(author_str)
        elif year != "Unknown":
            parts.append(year)
        if title != "Unknown Title":
            parts.append(title)
        parts.append(doi_part)
        
        name = " - ".join(parts)
        return safe_filename(name) + ".pdf"
