"""
Command-line interface for overphloem.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List, Any

from overphloem.core.project import Project


def create_parser() -> argparse.ArgumentParser:
    """
    Create command-line argument parser.

    Returns:
        argparse.ArgumentParser: The argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Framework for writing Overleaf bots", prog="overphloem"
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to run")

    # Pull command
    pull_parser = subparsers.add_parser("pull", help="Pull from Overleaf project")
    pull_parser.add_argument("--project-id", required=True, help="Overleaf project ID")
    pull_parser.add_argument("--path", default="", help="Local directory to pull to")

    # Push command
    push_parser = subparsers.add_parser("push", help="Push to Overleaf project")
    push_parser.add_argument("--project-id", required=True, help="Overleaf project ID")
    push_parser.add_argument("--path", default=".", help="Local directory to push from")

    # Attach command
    attach_parser = subparsers.add_parser(
        "attach", help="Attach script to project events"
    )
    attach_parser.add_argument(
        "--project-id", required=True, help="Overleaf project ID"
    )
    attach_parser.add_argument(
        "--script", required=True, help="Script to execute on event"
    )
    attach_parser.add_argument(
        "--on",
        choices=["change", "pull", "push"],
        default="change",
        help="Event to attach to",
    )
    attach_parser.add_argument(
        "--interval", type=int, default=60, help="Polling interval in seconds"
    )
    attach_parser.add_argument(
        "--falloff",
        type=float,
        default=None,
        help="Falloff factor for increasing interval",
    )
    attach_parser.add_argument(
        "--push", action="store_true", help="Push changes after script execution"
    )

    # Listen command
    listen_parser = subparsers.add_parser(
        "listen", help="Listen for changes in Overleaf project and print them"
    )
    listen_parser.add_argument(
        "--project-id", required=True, help="Overleaf project ID"
    )
    listen_parser.add_argument(
        "--path", default=".", help="Local directory to sync with"
    )
    listen_parser.add_argument(
        "--interval", type=int, default=30, help="Polling interval in seconds"
    )
    listen_parser.add_argument(
        "--falloff",
        type=float,
        default=1.5,
        help="Falloff factor for increasing interval when no changes detected",
    )
    listen_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed change information"
    )

    return parser


def pull_command(args: argparse.Namespace) -> int:
    """
    Execute pull command.

    Args:
        args (argparse.Namespace): Command-line arguments.

    Returns:
        int: Exit code.
    """
    project = Project(args.project_id, args.path)
    success = project.pull()

    if success:
        print(f"Successfully pulled project {args.project_id} to {args.path}")
        return 0
    else:
        print(f"Failed to pull project {args.project_id}")
        return 1


def push_command(args: argparse.Namespace) -> int:
    """
    Execute push command.

    Args:
        args (argparse.Namespace): Command-line arguments.

    Returns:
        int: Exit code.
    """
    project = Project(args.project_id, args.path)
    success = project.push()

    if success:
        print(
            f"Successfully pushed changes from {args.path} to project {args.project_id}"
        )
        return 0
    else:
        print(f"Failed to push changes to project {args.project_id}")
        return 1


def attach_command(args: argparse.Namespace) -> int:
    """
    Execute attach command.

    Args:
        args (argparse.Namespace): Command-line arguments.

    Returns:
        int: Exit code.
    """
    import time
    import threading
    from overphloem.core.events import Event

    event_type = Event(args.on)
    project = Project(args.project_id)
    script_path = Path(args.script).absolute()

    if not script_path.exists():
        print(f"Script {args.script} does not exist")
        return 1

    def callback(project: Project) -> bool:
        """Execute script and return whether to push changes."""
        try:
            subprocess.run([str(script_path)], cwd=project.local_path, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    # Start monitoring for changes
    stop_event = threading.Event()

    def monitor_changes() -> None:
        """Monitor for changes to the project."""
        print(f"Monitoring project {args.project_id} for {args.on} events...")
        print(f"Press Ctrl+C to stop")

        last_hash = None
        interval = args.interval

        while not stop_event.is_set():
            try:
                project.pull()
                current_hash = _get_commit_hash(project)

                if current_hash != last_hash and last_hash is not None:
                    print(f"Change detected in project {args.project_id}")
                    should_push = callback(project)

                    if should_push and args.push:
                        project.push()
                        print(f"Pushed changes to project {args.project_id}")

                    # Reset interval after successful event
                    interval = args.interval
                elif args.falloff is not None:
                    # Apply falloff to increase wait time
                    interval = min(
                        interval * args.falloff, 3600  # Max interval: 1 hour
                    )

                last_hash = current_hash
                time.sleep(interval)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval)

    thread = threading.Thread(target=monitor_changes)
    thread.daemon = True
    thread.start()

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping monitoring...")
        stop_event.set()
        thread.join(timeout=5)
        return 0


def listen_command(args: argparse.Namespace) -> int:
    """
    Execute listen command to monitor and print changes in an Overleaf project.

    Args:
        args (argparse.Namespace): Command-line arguments.

    Returns:
        int: Exit code.
    """
    import time
    import threading
    import datetime
    import subprocess
    import difflib
    from overphloem.core.events import Event

    project = Project(args.project_id, args.path)

    # Make sure we have a valid git repo
    if not project._init_git_repo():
        print(f"Failed to initialize git repository for project {args.project_id}")
        return 1

    # Do an initial pull to make sure we have the latest content
    if not project.pull():
        print(f"Failed to pull project {args.project_id}")
        return 1

    print(f"Successfully initialized project {args.project_id}")
    print(f"Monitoring for changes every {args.interval} seconds...")
    print("Press Ctrl+C to stop")

    # Track file states to detect changes
    file_states = {}

    # Store initial file states
    for file in project.files:
        if file.path.is_file():
            try:
                with open(file.path, "r", encoding="utf-8", errors="replace") as f:
                    file_states[str(file.relative_path)] = f.read()
            except Exception as e:
                print(f"Warning: Could not read file {file.relative_path}: {e}")

    last_hash = _get_commit_hash(project)
    current_interval = args.interval

    # Start monitoring thread
    stop_event = threading.Event()

    def monitor_changes() -> None:
        """Monitor project for changes and print them to console."""
        nonlocal last_hash, current_interval, file_states

        while not stop_event.is_set():
            time.sleep(current_interval)
            if stop_event.is_set():
                break

            try:
                # Pull the latest changes
                project.pull()
                current_hash = _get_commit_hash(project)

                # Only process if the commit hash changed
                if current_hash != last_hash and last_hash is not None:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        f"\n[{timestamp}] Changes detected in project {args.project_id}"
                    )
                    print(f"Commit hash: {current_hash}")

                    # Track changed files
                    changed_files = []
                    new_files = []
                    deleted_files = []

                    # Check for modified and new files
                    for file in project.files:
                        if file.path.is_file():
                            rel_path = str(file.relative_path)
                            try:
                                with open(
                                    file.path, "r", encoding="utf-8", errors="replace"
                                ) as f:
                                    current_content = f.read()

                                if rel_path in file_states:
                                    # Check if file was modified
                                    if current_content != file_states[rel_path]:
                                        changed_files.append(
                                            (
                                                rel_path,
                                                file_states[rel_path],
                                                current_content,
                                            )
                                        )
                                        file_states[rel_path] = current_content
                                else:
                                    # New file
                                    new_files.append(rel_path)
                                    file_states[rel_path] = current_content
                            except Exception as e:
                                print(f"Warning: Could not read file {rel_path}: {e}")

                    # Check for deleted files
                    for path in list(file_states.keys()):
                        if not (project.local_path / path).exists():
                            deleted_files.append(path)
                            del file_states[path]

                    # Print summary of changes
                    if changed_files:
                        print(f"\nModified files ({len(changed_files)}):")
                        for path, old_content, new_content in changed_files:
                            print(f"  - {path}")

                            # Show diff in verbose mode
                            if args.verbose:
                                diff = difflib.unified_diff(
                                    old_content.splitlines(),
                                    new_content.splitlines(),
                                    lineterm="",
                                    n=3,  # Context lines
                                )

                                diff_text = "\n".join(
                                    list(diff)[2:]
                                )  # Skip the file path lines
                                if diff_text:
                                    for line in diff_text.splitlines():
                                        if line.startswith("+"):
                                            print(
                                                f"    \033[92m{line}\033[0m"
                                            )  # Green for additions
                                        elif line.startswith("-"):
                                            print(
                                                f"    \033[91m{line}\033[0m"
                                            )  # Red for deletions
                                        elif line.startswith("@@"):
                                            print(
                                                f"    \033[94m{line}\033[0m"
                                            )  # Blue for section headers
                                        else:
                                            print(f"    {line}")
                                    print()

                    if new_files:
                        print(f"\nNew files ({len(new_files)}):")
                        for path in new_files:
                            print(f"  + {path}")

                    if deleted_files:
                        print(f"\nDeleted files ({len(deleted_files)}):")
                        for path in deleted_files:
                            print(f"  - {path}")

                    if not (changed_files or new_files or deleted_files):
                        print(
                            "  No file changes detected (metadata or history change only)"
                        )

                    print("\n" + "-" * 60)

                    # Reset interval after detecting changes
                    current_interval = args.interval
                elif args.falloff is not None:
                    # Apply falloff to increase wait time when no changes
                    current_interval = min(
                        current_interval * args.falloff, 3600  # Max interval: 1 hour
                    )

                last_hash = current_hash

            except Exception as e:
                print(f"Error monitoring changes: {e}")
                time.sleep(args.interval)

    thread = threading.Thread(target=monitor_changes)
    thread.daemon = True
    thread.start()

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        stop_event.set()
        thread.join(timeout=5)
        return 0


def _get_commit_hash(project: Project) -> str:
    """
    Get the latest commit hash for a project.

    Args:
        project (Project): Project to get commit hash for.

    Returns:
        str: The latest commit hash, or empty string on error.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project.local_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def main() -> int:
    """
    Main entry point for CLI.

    Returns:
        int: Exit code.
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "pull":
        return pull_command(args)
    elif args.command == "push":
        return push_command(args)
    elif args.command == "attach":
        return attach_command(args)
    elif args.command == "listen":
        return listen_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
