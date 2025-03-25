"""
Documentation for change monitoring in overphloem.

This module provides documentation on how to monitor and respond to changes
in Overleaf projects using overphloem.
"""

# Change Monitoring in overphloem

overphloem provides several approaches to monitor changes in Overleaf projects and respond
to them. This document explains the available methods and how to use them effectively.

## Methods for Monitoring Changes

### 1. Using the Listen Command (CLI)

The simplest way to monitor changes is using the `listen` command in the command-line interface.
This command will continuously poll an Overleaf project and display any changes detected.

```bash
uv run overphloem listen --project-id YOUR_PROJECT_ID [--options]
```

#### Available Options:

- `--project-id` (required): The Overleaf project ID to monitor
- `--path`: Local directory to sync with (default: current directory)
- `--interval`: Polling interval in seconds (default: 30)
- `--falloff`: Falloff factor for increasing the interval when no changes are detected (default: 1.5)
- `--verbose` or `-v`: Show detailed change information, including diffs

#### Example:

```bash
# Monitor with verbose output, checking every 10 seconds
uv run overphloem listen --project-id 6478b2143a88519e36cb44dc --interval 10 --verbose
```

The output will show file additions, modifications, and deletions as they occur in the Overleaf project.

### 2. Using the Attach Command with Shell Scripts

For more customized handling of changes, you can attach a shell script that will be executed
whenever changes are detected in the project.

```bash
uv run overphloem attach --project-id YOUR_PROJECT_ID --script ./path/to/script.sh [--options]
```

#### Available Options:

- `--project-id` (required): The Overleaf project ID to monitor
- `--script` (required): Path to the script that will be executed when changes are detected
- `--on`: Event type to attach to (`change`, `pull`, or `push`, default: `change`)
- `--interval`: Polling interval in seconds (default: 60)
- `--falloff`: Falloff factor for increasing the interval when no changes are detected
- `--push`: Push changes back to Overleaf after script execution

#### Example Shell Script:

See the provided example in `examples/change_detector.sh` for a complete script that:
- Lists all files in the project
- Shows special details for LaTeX files (e.g., sections)
- Displays recent changes using Git

### 3. Using Python API with Event Decorators

For the most flexibility, you can use the Python API to create custom event handlers
using the `@on` decorator.

```python
from overphloem import on, Event, Project

@on(Event.CHANGE, 'your-project-id', interval=30)
def on_change(project: Project):
    # Your custom change handling logic here
    print(f"Changes detected in project {project.project_id}")
    
    # You can examine files
    for file in project.files:
        if file.name.endswith('.tex'):
            # Process LaTeX files
            print(f"LaTeX file: {file.relative_path}")
    
    # Return True to push changes back to Overleaf
    return False  # Don't push changes
```

#### Available Events:

- `Event.CHANGE`: Triggered when changes are detected in the project
- `Event.PULL`: Triggered after a successful pull from Overleaf
- `Event.PUSH`: Triggered after a successful push to Overleaf

#### Advanced Example:

See the provided example in `examples/change_listener.py` for a complete implementation
that:
- Monitors changes in real-time
- Detects file modifications, additions, and deletions
- Displays detailed information about changes, including diffs

## Implementation Details

### How Change Detection Works

overphloem detects changes by:
1. Storing file states during initialization
2. Periodically pulling the latest changes from the Overleaf project
3. Comparing the current state with the stored state to identify differences
4. Triggering the appropriate event handlers when differences are found

### Handling Concurrent Changes

When both local and remote repositories have changes, the `push` command automatically
performs a rebase before pushing. This ensures that your local changes are applied on top
of the latest remote changes, reducing the likelihood of merge conflicts.

If complex merge conflicts do occur, you may need to manually resolve them by:
1. Using `git pull --rebase` directly
2. Resolving any conflicts
3. Using `git push` to push the resolved changes

## Optimizing Change Monitoring

### Polling Interval

The polling interval determines how frequently overphloem checks for changes:
- **Shorter intervals** provide more real-time monitoring but increase API load
- **Longer intervals** reduce API load but may delay detecting changes

### Falloff Strategy

The falloff factor gradually increases the polling interval when no changes are detected:
- This reduces unnecessary API calls during periods of inactivity
- The interval resets to the base value when changes are detected

Typical values range from 1.1 (slow increase) to 2.0 (rapid doubling).

## Practical Examples

### Monitoring LaTeX Section Changes

```python
@on(Event.CHANGE, 'your-project-id')
def detect_section_changes(project):
    for file in project.files:
        if file.name.endswith('.tex'):
            # Extract all section titles
            import re
            sections = re.findall(r'\\section\{(.*?)\}', file.content)
            print(f"Sections in {file.name}: {sections}")
    return False
```

### Tracking Citation Additions

```python
@on(Event.CHANGE, 'your-project-id')
def track_citations(project):
    for file in project.files:
        if file.name.endswith('.bib'):
            # Count bibliography entries
            import re
            entries = re.findall(r'@\w+\{', file.content)
            print(f"Bibliography has {len(entries)} entries")
    return False
```