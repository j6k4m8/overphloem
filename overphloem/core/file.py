"""
File module for handling files in Overleaf projects.
"""
from typing import Optional, Union
from pathlib import Path


class File:
    """
    Class representing a file in an Overleaf project.

    Attributes:
        path (Path): Absolute path to the file.
        relative_path (Path): Path relative to the project root.
        project: Reference to the parent Project object.
    """

    def __init__(self, path: Path, relative_path: Path, project):
        """
        Initialize a File object.

        Args:
            path (Path): Absolute path to the file.
            relative_path (Path): Path relative to the project root.
            project: Reference to the parent Project object.
        """
        self.path = path
        self.relative_path = relative_path
        self.project = project
        self._content = None

    @property
    def name(self) -> str:
        """
        Get the filename.

        Returns:
            str: The filename without directory path.
        """
        return self.path.name

    @property
    def content(self) -> str:
        """
        Get the file content.

        Returns:
            str: Content of the file.
        """
        if self._content is None:
            with open(self.path, "r", encoding="utf-8") as f:
                self._content = f.read()
        return self._content

    @content.setter
    def content(self, new_content: str) -> None:
        """
        Set the file content.

        Args:
            new_content (str): New content to write to the file.
        """
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(new_content)
        self._content = new_content

    def is_tex(self) -> bool:
        """
        Check if the file is a TeX file.

        Returns:
            bool: True if the file has a .tex extension, False otherwise.
        """
        return self.path.suffix.lower() == ".tex"

    def __repr__(self) -> str:
        """
        Get string representation of the file.

        Returns:
            str: String representation of the file.
        """
        return f"File({self.relative_path})"