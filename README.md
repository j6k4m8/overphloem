# overphloem

> Framework for writing Overleaf bots

## Installation

```bash
pip install overphloem
```

[![PyPI version](https://img.shields.io/pypi/v/overphloem.svg?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/overphloem/)

## Features

-   Sync a local directory with an Overleaf project
-   Run edits / operations on the project and push
-   Monitor and detect changes in real-time
-   Handle concurrent changes with automatic rebasing

## Explanation

[Overleaf](https://www.overleaf.com/) is a collaborative LaTeX editor. Though it does not technically use git for version control, it does have a feature that allows you to sync your project with a git repository. This is useful for keeping your project in sync with a git repository, and for collaborating with others.

Because we can interact with the document project loosely like a git repository, we can automate syncs to and from the project.

## Examples

### Sync a local directory with an Overleaf project

```bash
uv run overphloem pull --project-id $PROJECT_ID
```

### Push a local directory to an Overleaf project

```bash
uv run overphloem push --project-id $PROJECT_ID
```

### Monitor changes in an Overleaf project

```bash
uv run overphloem listen --project-id $PROJECT_ID --verbose
```

### Run a script on the project when it changes

```bash
uv run overphloem attach --on=change --project-id $PROJECT_ID --script ./examples/change_detector.sh
```

This can also be done using the `overphloem.on` decorator in Python:

```python
from overphloem import on, Event, Project

PROJECT_ID = '1234567890'

@on(Event.CHANGE, PROJECT_ID, push=True)
def on_change(project: Project):
    # Replace all occurrences of 'foo' with 'bar'
    for file in project.files:
        if file.name.endswith('.tex'):
            file.content = file.content.replace('foo', 'bar')
    return True # Return True to push changes
```

## Change Monitoring

overphloem provides several ways to monitor and respond to changes in Overleaf projects:

1. **CLI Listen Command**: Use `listen` to monitor and display changes in real-time

    ```bash
    uv run overphloem listen --project-id $PROJECT_ID --verbose
    ```

2. **Attach Shell Scripts**: Run custom shell scripts when changes are detected

    ```bash
    uv run overphloem attach --project-id $PROJECT_ID --script ./examples/change_detector.sh
    ```

3. **Python Event API**: Create custom event handlers using the `@on` decorator

    ```python
    from overphloem import on, Event

    @on(Event.CHANGE, 'your-project-id')
    def on_change(project):
        print(f"Changes detected in {project.project_id}")
    ```

See [the examples directory](./examples/) for sample scripts demonstrating these approaches.

## Known Limitations

### `main_file`

The `Project#main_file` property is hard-coded to `main.tex`. This is a limitation because Overleaf does not report the main file.

### Event listeners vs loops

There is no way to add "hooks" to Overleaf, so we have to poll the project for changes. This is done using a loop that checks the project for changes every N seconds, with optional falloff. This is not ideal, but it is the best we can do for now.

### Git Synchronization

When both local and remote repositories have changes, the `push` command now automatically performs a rebase before pushing. This handles most concurrent editing scenarios gracefully, but complex merge conflicts may still require manual intervention.
