"""
Documentation for Git synchronization in overphloem.

This document explains the Git synchronization strategies used in overphloem
to handle concurrent changes between local and remote Overleaf projects.
"""

# Git Synchronization in overphloem

## Overview

overphloem uses Git to synchronize changes between local directories and Overleaf projects.
When multiple users edit an Overleaf project simultaneously, or when changes are made both
locally and on the Overleaf web interface, Git branches can diverge. This document explains
how overphloem handles these concurrent changes.

## How Rebasing Works

When you push changes to an Overleaf project using `overphloem push`, the following sequence occurs:

1. Local changes are staged and committed
2. A `git pull --rebase origin master` is performed to fetch and integrate remote changes
3. Your local commits are then replayed on top of the updated base
4. Finally, the changes are pushed to the Overleaf project

This rebasing strategy ensures that your local changes are always applied on top of the latest
remote changes, creating a clean, linear history without unnecessary merge commits.

## Benefits of Automatic Rebasing

- **Cleaner History**: Avoids creating merge commits, keeping the history linear
- **Reduced Conflicts**: Many conflicts are resolved automatically during replay
- **Improved Success Rate**: Reduces push failures due to divergent branches
- **Simplified Workflow**: No need for manual Git operations before pushing

## Handling Conflict Scenarios

### Scenario 1: Simple Divergent Changes

When changes are made to different files or different parts of the same file:

```
Before:
  Remote: A → B → C
  Local:  A → B → D

After rebasing:
  Local:  A → B → C → D
```

These changes are resolved automatically during rebasing.

### Scenario 2: Conflicting Changes

When changes affect the same lines in the same files:

```
Before:
  Remote: A → B → C (changes line 10 in main.tex)
  Local:  A → B → D (changes line 10 in main.tex)

During rebase: Conflict detected
```

In this case:
1. The rebase operation will fail
2. overphloem will automatically abort the rebase
3. Your local changes will remain intact
4. The push will fail with an error message

### Manual Conflict Resolution

For complex conflicts, you may need to manually:

1. Navigate to your project directory
2. Run `git pull --rebase origin master`
3. Resolve any conflicts in the affected files
4. Run `git add .` to stage the resolved files
5. Run `git rebase --continue` to complete the rebase
6. Finally, run `uv run overphloem push --project-id YOUR_PROJECT_ID` again

## Best Practices

### 1. Pull Before Making Changes

Always run `uv run overphloem pull --project-id YOUR_PROJECT_ID` before starting to make local changes.
This ensures you're working with the latest version of the project.

### 2. Push Frequently

Frequent pushes reduce the likelihood of conflicts by keeping your local repository
more closely synchronized with the remote Overleaf project.

### 3. Coordinate with Collaborators

If possible, coordinate with collaborators to avoid simultaneous edits to the same sections
of files, which is the most common source of conflicts.

### 4. Use Atomic Changes

Make small, focused changes and push them individually rather than making large batches
of unrelated changes. This makes conflicts easier to resolve when they do occur.

## Troubleshooting

### Push Rejection

**Symptom**: `Failed to push project: Command '['git', 'push', 'origin', 'master']' returned non-zero exit status 1.`

**Solution**: This usually indicates a conflict that couldn't be resolved automatically. Try:
1. Pull with rebase manually: `git pull --rebase origin master`
2. Resolve any conflicts
3. Push again: `uv run overphloem push --project-id YOUR_PROJECT_ID`

### Rebase Conflicts

**Symptom**: `Pull with rebase failed: ... hint: You have divergent branches and need to specify how to reconcile them.`

**Solution**: Follow the manual conflict resolution steps above. If conflicts are too complex, you might need to:
1. Back up your changes
2. Run `git reset --hard origin/master` to reset to the remote state
3. Re-apply your changes manually
4. Push again

## Advanced Configuration

For power users who want to customize Git behavior, you can set global Git configuration options:

```bash
# Set default pull behavior to rebase
git config --global pull.rebase true

# Automatically stash uncommitted changes before rebasing
git config --global rebase.autoStash true
```

These settings can make manual Git operations more consistent with overphloem's behavior.