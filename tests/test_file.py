"""
Test file for the File class.
"""
import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from overphloem.core.file import File


class TestFile(unittest.TestCase):
    """Test cases for the File class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create a test file
        self.test_file_path = self.temp_path / "test.tex"
        with open(self.test_file_path, "w") as f:
            f.write("Test content")

        # Create a mock project
        self.mock_project = MagicMock()
        self.mock_project.local_path = self.temp_path

        # Create a File object
        self.relative_path = Path("test.tex")
        self.file = File(self.test_file_path, self.relative_path, self.mock_project)

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test File initialization."""
        self.assertEqual(self.file.path, self.test_file_path)
        self.assertEqual(self.file.relative_path, self.relative_path)
        self.assertEqual(self.file.project, self.mock_project)
        self.assertIsNone(self.file._content)

    def test_name(self):
        """Test name property."""
        self.assertEqual(self.file.name, "test.tex")

    def test_content(self):
        """Test content property."""
        # First access should read from file
        self.assertEqual(self.file.content, "Test content")
        self.assertEqual(self.file._content, "Test content")

        # Change the file content
        with open(self.test_file_path, "w") as f:
            f.write("New content")

        # Second access should use cached content
        self.assertEqual(self.file.content, "Test content")

        # Reset cache and read again
        self.file._content = None
        self.assertEqual(self.file.content, "New content")

    def test_content_setter(self):
        """Test content setter."""
        self.file.content = "Updated content"

        # Check that file content was updated
        with open(self.test_file_path, "r") as f:
            self.assertEqual(f.read(), "Updated content")

        # Check that cached content was updated
        self.assertEqual(self.file._content, "Updated content")

    def test_is_tex(self):
        """Test is_tex method."""
        # Test .tex file
        self.assertTrue(self.file.is_tex())

        # Test non-.tex file
        non_tex_path = self.temp_path / "test.png"
        with open(non_tex_path, "w") as f:
            f.write("PNG content")

        non_tex_file = File(non_tex_path, Path("test.png"), self.mock_project)
        self.assertFalse(non_tex_file.is_tex())

    def test_repr(self):
        """Test __repr__ method."""
        self.assertEqual(repr(self.file), "File(test.tex)")


if __name__ == "__main__":
    unittest.main()