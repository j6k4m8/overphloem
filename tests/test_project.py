"""
Test file for the Project class.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from overphloem.core.project import Project
from overphloem.core.file import File


class TestProject(unittest.TestCase):
    """Test cases for the Project class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.project_id = "1234567890abcdef"

        # Create a mock git directory
        (self.temp_path / ".git").mkdir()

        # Create some test files
        test_files = [
            "main.tex",
            "bibliography.bib",
            "figures/figure1.png",
            "sections/introduction.tex"
        ]

        for file_path in test_files:
            full_path = self.temp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(f"Content of {file_path}")

        self.project = Project(self.project_id, self.temp_path)

    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test Project initialization."""
        self.assertEqual(self.project.project_id, self.project_id)
        self.assertEqual(self.project.local_path, self.temp_path)

        # Test with no local_path
        with patch('tempfile.mkdtemp', return_value="/tmp/mock_dir"):
            project = Project(self.project_id)
            self.assertEqual(project.local_path, Path("/tmp/mock_dir"))

    def test_main_file(self):
        """Test main_file property."""
        self.assertEqual(self.project.main_file, "main.tex")

    def test_files(self):
        """Test files property."""
        files = self.project.files
        self.assertEqual(len(files), 4)  # 4 test files

        # Check that all files are File objects
        for file in files:
            self.assertIsInstance(file, File)

        # Check specific files
        file_paths = [str(file.relative_path) for file in files]
        self.assertIn("main.tex", file_paths)
        self.assertIn("bibliography.bib", file_paths)
        self.assertIn("figures/figure1.png", file_paths)
        self.assertIn("sections/introduction.tex", file_paths)

    @patch('subprocess.run')
    def test_pull(self, mock_run):
        """Test pull method."""
        # Mock successful git pull
        mock_run.return_value = MagicMock(returncode=0)

        result = self.project.pull()
        self.assertTrue(result)

        # Check that git pull was called
        mock_run.assert_called_with(
            ["git", "pull", "origin", "master"],
            cwd=self.temp_path,
            check=True,
            capture_output=True
        )

        # Test case where git pull fails
        mock_run.side_effect = Exception("Git error")
        result = self.project.pull()
        self.assertFalse(result)

    @patch('subprocess.run')
    def test_push(self, mock_run):
        """Test push method."""
        # Mock successful git operations
        mock_run.return_value = MagicMock(returncode=0)

        result = self.project.push()
        self.assertTrue(result)

        # Check that git commands were called
        mock_run.assert_any_call(
            ["git", "add", "."],
            cwd=self.temp_path,
            check=True,
            capture_output=True
        )

        mock_run.assert_any_call(
            ["git", "commit", "-m", "Update via overphloem"],
            cwd=self.temp_path,
            check=True,
            capture_output=True
        )

        mock_run.assert_any_call(
            ["git", "push", "origin", "master"],
            cwd=self.temp_path,
            check=True,
            capture_output=True
        )

        # Test case where git push fails
        mock_run.side_effect = Exception("Git error")
        result = self.project.push()
        self.assertFalse(result)

    def test_get_file(self):
        """Test get_file method."""
        # Test getting existing file
        file = self.project.get_file("main.tex")
        self.assertIsNotNone(file)
        self.assertEqual(file.name, "main.tex")

        # Test getting non-existent file
        file = self.project.get_file("non_existent.tex")
        self.assertIsNone(file)

    def test_create_file(self):
        """Test create_file method."""
        # Create a new file
        new_file = self.project.create_file("new_file.tex", "New file content")

        # Check that file was created
        self.assertTrue((self.temp_path / "new_file.tex").exists())

        # Check returned File object
        self.assertEqual(new_file.name, "new_file.tex")
        self.assertEqual(new_file.content, "New file content")

        # Check that file is in project files
        self.assertIn(new_file, self.project.files)

    def test_delete_file(self):
        """Test delete_file method."""
        # Delete existing file
        result = self.project.delete_file("main.tex")
        self.assertTrue(result)

        # Check that file was deleted
        self.assertFalse((self.temp_path / "main.tex").exists())

        # Check that file is not in project files
        file_paths = [str(file.relative_path) for file in self.project.files]
        self.assertNotIn("main.tex", file_paths)

        # Delete non-existent file
        result = self.project.delete_file("non_existent.tex")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()