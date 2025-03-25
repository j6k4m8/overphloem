#!/usr/bin/env python3
"""
Example script that demonstrates how to programmatically monitor changes in an Overleaf project.

This script showcases how to use the overphloem events API to:
1. Monitor a project for changes
2. Detect file modifications, additions, and deletions
3. Display detailed information about changes in real-time

Usage:
    python change_listener.py PROJECT_ID [--interval SECONDS] [--verbose]

Example:
    python change_listener.py 6478b2143a88519e36cb44dc --interval 30 --verbose
"""

import argparse
import difflib
import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path to import overphloem
sys.path.append(str(Path(__file__).parent.parent))

from overphloem.core.events import Event, on
from overphloem.core.project import Project


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Monitor changes in an Overleaf project"
    )
    parser.add_argument("project_id", help="Overleaf project ID")
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed change information"
    )
    return parser.parse_args()


class ChangeMonitor:
    """Monitor changes in an Overleaf project."""

    def __init__(self, project_id, interval=30, verbose=False):
        """Initialize the change monitor.

        Args:
            project_id (str): Overleaf project ID
            interval (int): Polling interval in seconds
            verbose (bool): Whether to show detailed change information
        """
        self.project_id = project_id
        self.interval = interval
        self.verbose = verbose
        self.file_states = {}
        self.stop_event = threading.Event()

        # Initialize the project
        self.project = Project(project_id)
        if not self.project._init_git_repo():
            print(f"Failed to initialize git repository for project {project_id}")
            sys.exit(1)

        # Initial pull to get the latest content
        if not self.project.pull():
            print(f"Failed to pull project {project_id}")
            sys.exit(1)

        print(f"Successfully initialized project {project_id}")
        self._store_initial_file_states()

    def _store_initial_file_states(self):
        """Store the initial state of all files in the project."""
        for file in self.project.files:
            if file.path.is_file():
                try:
                    with open(file.path, "r", encoding="utf-8", errors="replace") as f:
                        self.file_states[str(file.relative_path)] = f.read()
                except Exception as e:
                    print(f"Warning: Could not read file {file.relative_path}: {e}")

    def _find_changes(self, project):
        """Find changes in the project files.

        Returns:
            tuple: (changed_files, new_files, deleted_files)
            where:
                changed_files: list of (path, old_content, new_content) tuples
                new_files: list of file paths
                deleted_files: list of file paths
        """
        changed_files = []
        new_files = []
        deleted_files = []

        # Check for modified and new files
        for file in project.files:
            if file.path.is_file():
                rel_path = str(file.relative_path)
                try:
                    with open(file.path, "r", encoding="utf-8", errors="replace") as f:
                        current_content = f.read()

                    if rel_path in self.file_states:
                        # Check if file was modified
                        if current_content != self.file_states[rel_path]:
                            changed_files.append(
                                (rel_path, self.file_states[rel_path], current_content)
                            )
                            self.file_states[rel_path] = current_content
                    else:
                        # New file
                        new_files.append(rel_path)
                        self.file_states[rel_path] = current_content
                except Exception as e:
                    print(f"Warning: Could not read file {rel_path}: {e}")

        # Check for deleted files
        for path in list(self.file_states.keys()):
            if not (project.local_path / path).exists():
                deleted_files.append(path)
                del self.file_states[path]

        return changed_files, new_files, deleted_files

    def _print_diff(self, old_content, new_content):
        """Print a colored diff of the content changes."""
        diff = difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            lineterm="",
            n=3,  # Context lines
        )

        diff_text = "\n".join(list(diff)[2:])  # Skip the file path lines
        if diff_text:
            for line in diff_text.splitlines():
                if line.startswith("+"):
                    print(f"    \033[92m{line}\033[0m")  # Green for additions
                elif line.startswith("-"):
                    print(f"    \033[91m{line}\033[0m")  # Red for deletions
                elif line.startswith("@@"):
                    print(f"    \033[94m{line}\033[0m")  # Blue for section headers
                else:
                    print(f"    {line}")
            print()

    @on(Event.CHANGE, "placeholder", interval=1)  # Will be replaced at runtime
    def on_change(self, project):
        """Handler for project changes."""
        # Find all the changes
        changed_files, new_files, deleted_files = self._find_changes(project)

        # Print summary of changes
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Changes detected in project {self.project_id}")

        if changed_files:
            print(f"\nModified files ({len(changed_files)}):")
            for path, old_content, new_content in changed_files:
                print(f"  - {path}")

                # Show diff in verbose mode
                if self.verbose:
                    self._print_diff(old_content, new_content)

        if new_files:
            print(f"\nNew files ({len(new_files)}):")
            for path in new_files:
                print(f"  + {path}")

                # Show content in verbose mode
                if self.verbose and path in self.file_states:
                    print("    Content:")
                    for line_num, line in enumerate(
                        self.file_states[path].splitlines()[:10]
                    ):
                        print(f"    {line_num+1:4d}: {line}")
                    if len(self.file_states[path].splitlines()) > 10:
                        print("    ... (content truncated)")
                    print()

        if deleted_files:
            print(f"\nDeleted files ({len(deleted_files)}):")
            for path in deleted_files:
                print(f"  - {path}")

        if not (changed_files or new_files or deleted_files):
            print("  No file changes detected (metadata or history change only)")

        print("\n" + "-" * 60)
        return False  # Don't push changes

    def start(self):
        """Start monitoring for changes."""
        # Replace placeholder project ID with actual ID in the decorator
        self.__class__.on_change.__defaults__ = (
            self.project_id,
            False,
            self.interval,
            None,
        )

        print(f"Monitoring for changes every {self.interval} seconds...")
        print("Press Ctrl+C to stop")

        try:
            # Keep main thread alive
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
            self.stop_event.set()


def main():
    """Main function."""
    args = parse_args()
    monitor = ChangeMonitor(
        project_id=args.project_id, interval=args.interval, verbose=args.verbose
    )
    monitor.start()


if __name__ == "__main__":
    main()
