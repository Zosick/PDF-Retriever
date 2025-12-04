import logging
import sys
    source = ArxivSource(session)
    
    # Known Arxiv DOI: Attention Is All You Need
    doi = "10.48550/arXiv.1706.03762"
    
    print(f"Fetching metadata for {doi}...")
    metadata = source.get_metadata(doi)
    
    if metadata:
        print("Success!")
        print(metadata)
        if metadata['title'] == "Attention Is All You Need":
             print("Title verification passed.")
        else:
             print(f"Title verification failed. Got: {metadata['title']}")
    else:
        print("Failed to get metadata.")

if __name__ == "__main__":
    test_arxiv_metadata()
