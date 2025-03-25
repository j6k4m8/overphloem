"""
Test file for utility functions.
"""
import os
import unittest
import logging
import tempfile
from pathlib import Path

from overphloem.utils.utils import (
    setup_logging,
    validate_project_id,
    find_tex_files,
    extract_tex_commands,
    get_bibtex_entries
)


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    def test_setup_logging(self):
        """Test setup_logging function."""
        logger = setup_logging(level=logging.DEBUG)

        self.assertEqual(logger.name, "overphloem")
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)
        self.assertEqual(logger.handlers[0].level, logging.DEBUG)

    def test_validate_project_id(self):
        """Test validate_project_id function."""
        # Valid project IDs
        self.assertTrue(validate_project_id("1234567890abcdef"))
        self.assertTrue(validate_project_id("abcdef1234567890abcdef"))

        # Invalid project IDs
        self.assertFalse(validate_project_id(""))
        self.assertFalse(validate_project_id("abc"))
        self.assertFalse(validate_project_id("12345!@#$%"))

    def test_find_tex_files(self):
        """Test find_tex_files function."""
        # Create test files
        test_files = [
            "document.tex",
            "sections/introduction.tex",
            "sections/conclusion.tex",
            "figures/figure1.png",
            "references.bib"
        ]

        for file_path in test_files:
            full_path = self.temp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(f"Content of {file_path}")

        # Find TeX files
        tex_files = find_tex_files(self.temp_path)

        # Check that only TeX files were found
        self.assertEqual(len(tex_files), 3)
        self.assertIn(self.temp_path / "document.tex", tex_files)
        self.assertIn(self.temp_path / "sections/introduction.tex", tex_files)
        self.assertIn(self.temp_path / "sections/conclusion.tex", tex_files)

    def test_extract_tex_commands(self):
        """Test extract_tex_commands function."""
        # Create test TeX content
        tex_content = r"""
        \documentclass{article}
        \title{Test Document}
        \author{Test Author}
        \date{\today}

        \begin{document}

        \maketitle

        \section{Introduction}
        This is a test document.

        \section{Methods}
        We used the \textit{example} method.

        \section{Results}
        \begin{figure}
            \includegraphics{figure1.png}
            \caption{A test figure.}
        \end{figure}

        \cite{reference1}
        \cite{reference2}

        \end{document}
        """

        # Extract commands
        sections = extract_tex_commands(tex_content, "section")
        citations = extract_tex_commands(tex_content, "cite")
        includes = extract_tex_commands(tex_content, "includegraphics")

        # Check extracted commands
        self.assertEqual(sections, ["Introduction", "Methods", "Results"])
        self.assertEqual(citations, ["reference1", "reference2"])
        self.assertEqual(includes, ["figure1.png"])

    def test_get_bibtex_entries(self):
        """Test get_bibtex_entries function."""
        # Create test BibTeX content
        bib_content = r"""
        @article{reference1,
            author = {Smith, John},
            title = {Test Article},
            journal = {Journal of Testing},
            year = {2023},
            volume = {1},
            pages = {1--10}
        }

        @book{reference2,
            author = {Doe, Jane},
            title = {Test Book},
            publisher = {Test Publisher},
            year = {2022}
        }
        """

        # Extract BibTeX entries
        entries = get_bibtex_entries(bib_content)

        # Check extracted entries
        self.assertEqual(len(entries), 2)

        # Check first entry
        self.assertIn("reference1", entries)
        self.assertEqual(entries["reference1"]["type"], "article")
        self.assertEqual(entries["reference1"]["author"], "Smith, John")
        self.assertEqual(entries["reference1"]["title"], "Test Article")
        self.assertEqual(entries["reference1"]["journal"], "Journal of Testing")
        self.assertEqual(entries["reference1"]["year"], "2023")
        self.assertEqual(entries["reference1"]["volume"], "1")
        self.assertEqual(entries["reference1"]["pages"], "1--10")

        # Check second entry
        self.assertIn("reference2", entries)
        self.assertEqual(entries["reference2"]["type"], "book")
        self.assertEqual(entries["reference2"]["author"], "Doe, Jane")
        self.assertEqual(entries["reference2"]["title"], "Test Book")
        self.assertEqual(entries["reference2"]["publisher"], "Test Publisher")
        self.assertEqual(entries["reference2"]["year"], "2022")


if __name__ == "__main__":
    unittest.main()