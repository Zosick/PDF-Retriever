import unittest
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock
from src.downloader.sources import PubMedCentralSource

class TestPMCAuthors(unittest.TestCase):
    def test_parse_metadata_authors_with_none(self):
        # Create a mock PMCSource instance (we don't need a real session for this test)
        mock_session = MagicMock()
        source = PubMedCentralSource(mock_session)
        
        # Create XML with one valid surname and one empty surname
        xml_content = """
        <article>
            <front>
                <article-meta>
                    <article-title>Test Title</article-title>
                    <pub-date><year>2023</year></pub-date>
                    <article-id pub-id-type="doi">10.1234/test</article-id>
                    <contrib-group>
                        <contrib contrib-type="author">
                            <name><surname>Smith</surname></name>
                        </contrib>
                        <contrib contrib-type="author">
                            <name><surname></surname></name>
                        </contrib>
                        <contrib contrib-type="author">
                            <name><surname>  </surname></name>
                        </contrib>
                    </contrib-group>
                </article-meta>
            </front>
        </article>
        """
        root = ET.fromstring(xml_content)
        
        # Call the private method _parse_metadata_xml
        metadata = source._parse_metadata_xml(root, "10.1234/test", "PMC12345")
        
        authors = metadata["authors"]
        
        # Check if None or empty strings are present
        # Currently, this test expects the behavior to be BROKEN (i.e., containing None or empty strings)
        # or we can write it to assert the DESIRED behavior and fail if it's broken.
        # Let's write it to assert the DESIRED behavior, so it fails initially.
        
        print(f"Authors found: {authors}")
        
        self.assertNotIn(None, authors, "Authors list should not contain None")
        self.assertNotIn("", authors, "Authors list should not contain empty strings")
        self.assertEqual(len(authors), 1, "Should only contain 'Smith'")
        self.assertEqual(authors[0], "Smith")

if __name__ == "__main__":
    unittest.main()
