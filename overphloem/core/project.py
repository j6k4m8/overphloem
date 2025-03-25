"""
Project module for interacting with Overleaf projects.
"""

from typing import List, Optional, Union
import shutil
import tempfile
import subprocess
import logging
from pathlib import Path

from overphloem.core.file import File

# Set up logging
logger = logging.getLogger(__name__)


class Project:
    """
    Class representing an Overleaf project.

    This class provides methods to interact with Overleaf projects,
    including syncing, pulling, pushing, and managing project files.

    Attributes:
        project_id (str): The Overleaf project ID.
        local_path (Path): Path to the local directory synced with the project.
        main_file (str): Name of the main file (hardcoded to 'main.tex').
        files (List[File]): List of files in the project.
    """

    def __init__(self, project_id: str, local_path: Optional[Union[str, Path]] = None):
        """
        Initialize a Project object.

        Args:
            project_id (str): The Overleaf project ID.
            local_path (Optional[Union[str, Path]]): Path to local directory.
                If None, a temporary directory will be created.
        """
        self.project_id = project_id

        if local_path is None:
            self.local_path = Path(tempfile.mkdtemp())
        else:
            self.local_path = Path(local_path)
            if not self.local_path.exists():
                self.local_path.mkdir(parents=True)

        self._files: Optional[List[File]] = None
        self._git_repo = None

    @property
    def main_file(self) -> str:
        """
        Get the main file of the project.

        Note:
            This is hardcoded to 'main.tex' due to Overleaf limitations.

        Returns:
            str: Name of the main file.
        """
        return "main.tex"

    @property
    def files(self) -> List[File]:
        """
        Get all files in the project.

        Returns:
            List[File]: List of File objects representing project files.
        """
        if self._files is None:
            self._load_files()
        return self._files or []

    def _load_files(self) -> None:
        """
        Load project files from the local directory.
        """
        self._files = []
        for path in self.local_path.glob("**/*"):
            if path.is_file() and ".git" not in path.parts:
                relative_path = path.relative_to(self.local_path)
                self._files.append(File(path, relative_path, self))

    def pull(self) -> bool:
        """
        Pull the latest changes from the Overleaf project.

        Returns:
            bool: True if pull was successful, False otherwise.
        """
        # Initialize or update git repo
        if not self._init_git_repo():
            logger.error(
                f"Failed to initialize git repository for project {self.project_id}"
            )
            return False

        # Pull latest changes
        try:
            logger.info(f"Pulling changes for project {self.project_id}")
            cmd = ["git", "pull", "origin", "master"]
            result = subprocess.run(
                cmd, cwd=self.local_path, check=True, capture_output=True, text=True
            )
            logger.debug(f"Git pull output: {result.stdout}")
            self._load_files()  # Reload files after pull
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to pull project: {e}")
            logger.error(
                f"Error output: {e.stderr if hasattr(e, 'stderr') else 'No error output'}"
            )
            return False

    def push(self) -> bool:
        """
        Push local changes to the Overleaf project.

        First performs a pull with rebase to ensure local repository is up-to-date
        with remote changes before attempting to push.

        Returns:
            bool: True if push was successful, False otherwise.
        """
        if not self._init_git_repo():
            logger.error(
                f"Failed to initialize git repository for project {self.project_id}"
            )
            return False

        try:
            # Add all changes
            logger.info(f"Adding changes for project {self.project_id}")
            subprocess.run(
                ["git", "add", "."],
                cwd=self.local_path,
                check=True,
                capture_output=True,
            )

            # Commit changes
            try:
                logger.info(f"Committing changes for project {self.project_id}")
                subprocess.run(
                    ["git", "commit", "-m", "Update via overphloem"],
                    cwd=self.local_path,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                # No changes to commit, continue with push
                logger.info("No changes to commit")
                pass

            # Pull with rebase before pushing to handle divergent branches
            logger.info(f"Pulling with rebase for project {self.project_id}")
            try:
                subprocess.run(
                    ["git", "pull", "--rebase", "origin", "master"],
                    cwd=self.local_path,
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Pull with rebase failed: {e}")
                logger.error(
                    f"Error output: {e.stderr if hasattr(e, 'stderr') else 'No error output'}"
                )
                # If there are conflicts, abort the rebase
                try:
                    subprocess.run(
                        ["git", "rebase", "--abort"],
                        cwd=self.local_path,
                        check=True,
                        capture_output=True,
                    )
                except:
                    pass
                return False

            # Push changes
            logger.info(f"Pushing changes for project {self.project_id}")
            subprocess.run(
                ["git", "push", "origin", "master"],
                cwd=self.local_path,
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to push project: {e}")
            logger.error(
                f"Error output: {e.stderr if hasattr(e, 'stderr') else 'No error output'}"
            )
            return False

    def _init_git_repo(self) -> bool:
        """
        Initialize or update the git repository for the project.

        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        git_dir = self.local_path / ".git"

        if not git_dir.exists():
            # Clone the repository
            git_url = f"https://git.overleaf.com/{self.project_id}"
            logger.info(f"Cloning repository from {git_url} to {self.local_path}")
            try:
                # Create a temporary directory for cloning
                temp_clone_dir = Path(tempfile.mkdtemp())

                # Clone into the temporary directory
                result = subprocess.run(
                    ["git", "clone", git_url, str(temp_clone_dir)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.debug(f"Git clone output: {result.stdout}")

                # Move .git directory from temp to target directory
                temp_git_dir = temp_clone_dir / ".git"
                if temp_git_dir.exists():
                    # Move all content from temp_clone_dir to local_path
                    for item in temp_clone_dir.iterdir():
                        if item.name == ".git":
                            # Move the .git directory
                            shutil.copytree(item, self.local_path / ".git")
                        else:
                            # Move other files only if they don't exist in target
                            dest_path = self.local_path / item.name
                            if not dest_path.exists():
                                if item.is_dir():
                                    shutil.copytree(item, dest_path)
                                else:
                                    shutil.copy2(item, dest_path)

                    # Clean up temporary directory
                    shutil.rmtree(temp_clone_dir)

                    # Set up git config in the local repo
                    subprocess.run(
                        ["git", "config", "core.sparsecheckout", "true"],
                        cwd=self.local_path,
                        check=True,
                        capture_output=True,
                    )

                    return True
                else:
                    logger.error("Git directory not found in cloned repository")
                    return False

            except subprocess.CalledProcessError as e:
                logger.error(f"Git clone failed: {e}")
                logger.error(
                    f"Error output: {e.stderr if hasattr(e, 'stderr') else 'No error output'}"
                )

                # Check for common errors
                if hasattr(e, "stderr"):
                    if "Authentication failed" in e.stderr:
                        logger.error(
                            "Authentication failed. Make sure you have access to this Overleaf project."
                        )
                    elif "Repository not found" in e.stderr:
                        logger.error(
                            f"Repository not found for project ID {self.project_id}. Check if the project ID is correct."
                        )
                    elif "does not appear to be a git repository" in e.stderr:
                        logger.error(
                            "The URL does not appear to be a git repository. Make sure the project has Git access enabled in Overleaf."
                        )

                return False
        return True

    def get_file(self, path: Union[str, Path]) -> Optional[File]:
        """
        Get a file from the project by path.

        Args:
            path (Union[str, Path]): Path to the file, relative to project root.

        Returns:
            Optional[File]: File object if found, None otherwise.
        """
        path_str = str(path)
        for file in self.files:
            if str(file.relative_path) == path_str:
                return file
        return None

    def create_file(self, path: Union[str, Path], content: str = "") -> File:
        """
        Create a new file in the project.

        Args:
            path (Union[str, Path]): Path to the file, relative to project root.
            content (str, optional): Initial file content. Defaults to "".

        Returns:
            File: The created File object.
        """
        rel_path = Path(path)
        abs_path = self.local_path / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        file = File(abs_path, rel_path, self)

        if self._files is not None:
            self._files.append(file)

        return file

    def delete_file(self, path: Union[str, Path]) -> bool:
        """
        Delete a file from the project.

        Args:
            path (Union[str, Path]): Path to the file, relative to project root.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        file = self.get_file(path)
        if file:
            try:
                file.path.unlink()
                if self._files is not None:
                    self._files.remove(file)
                return True
            except OSError:
                return False
        return False
