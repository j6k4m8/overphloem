"""
Documentation for the example scripts provided with overphloem.

This document explains how to use the example scripts for monitoring and responding
to changes in Overleaf projects.
"""

# overphloem Example Scripts

This directory contains example scripts that demonstrate how to use overphloem
to monitor and respond to changes in Overleaf projects.

## 1. change_listener.py

A Python script that demonstrates programmatic monitoring of Overleaf project changes.

### Features

- Real-time monitoring of changes in an Overleaf project
- Detection of file modifications, additions, and deletions
- Detailed change information including diffs in verbose mode
- Customizable polling interval

### Usage

```bash
python examples/change_listener.py PROJECT_ID [--interval SECONDS] [--verbose]
```

### Example

```bash
python examples/change_listener.py 6478b2143a88519e36cb44dc --interval 10 --verbose
```

### How It Works

The script:
1. Uses the overphloem events API to set up a change handler
2. Tracks the state of all files in the project
3. Detects and reports changes when they occur
4. Shows detailed diffs when run in verbose mode

### Customization

You can use this script as a starting point for your own change monitoring applications.
Key points for customization:

- The `on_change` method is the core event handler
- The `_find_changes` method detects file modifications
- The `_print_diff` method formats change information

## 2. change_detector.sh

A shell script that can be used with the overphloem `attach` command to monitor
and report on changes in Overleaf projects.

### Features

- Lists all files in the project with details
- Shows section titles for LaTeX files
- Displays recent Git changes

### Usage

```bash
# Make the script executable first
chmod +x examples/change_detector.sh

# Use with the attach command
uv run overphloem attach --project-id YOUR_PROJECT_ID --script ./examples/change_detector.sh --on change
```

### How It Works

When changes are detected in the Overleaf project, the script:
1. Reports the current date and time
2. Lists all files in the project, with special handling for LaTeX files
3. Shows the most recent Git changes

### Customization

You can modify this script to:
- Process specific file types
- Run LaTeX compilation commands
- Send notifications
- Apply automatic formatting
- Generate reports

Just add your custom shell commands to the script.

## Using Examples as Templates

Both examples are designed to be used as templates for your own custom
change monitoring and automation workflows. You can:

1. Copy and rename the examples
2. Modify them to suit your specific needs
3. Use them as reference for implementing your own solutions

## Common Customizations

### LaTeX-Specific Processing

```python
@on(Event.CHANGE, 'your-project-id')
def process_latex_changes(project):
    for file in project.files:
        if file.name.endswith('.tex'):
            # Auto-format LaTeX code
            formatted_content = autoformat_latex(file.content)
            if formatted_content != file.content:
                file.content = formatted_content
                print(f"Reformatted {file.name}")
    return True  # Push changes back to Overleaf
```

### Citation Management

```python
@on(Event.CHANGE, 'your-project-id')
def manage_citations(project):
    # Check for new citations in .tex files
    citations = set()
    for file in project.files:
        if file.name.endswith('.tex'):
            import re
            cites = re.findall(r'\\cite\{(.*?)\}', file.content)
            for cite in cites:
                citations.update(cite.split(','))
    
    # Check if citations exist in bibliography
    bib_content = ""
    bib_file = None
    for file in project.files:
        if file.name.endswith('.bib'):
            bib_file = file
            bib_content = file.content
            break
    
    # Report missing citations
    if bib_file:
        missing = []
        for citation in citations:
            if f"@{citation}" not in bib_content and f"@*{{{citation}," not in bib_content:
                missing.append(citation)
        
        if missing:
            print(f"Missing citations in bibliography: {missing}")
    
    return False  # Don't push changes
```

### Error Checking

```python
@on(Event.CHANGE, 'your-project-id')
def check_errors(project):
    for file in project.files:
        if file.name.endswith('.tex'):
            # Check for common LaTeX errors
            errors = []
            if "\\begin{figure}" in file.content and "\\end{figure}" not in file.content:
                errors.append("Unclosed figure environment")
            if "\\begin{table}" in file.content and "\\end{table}" not in file.content:
                errors.append("Unclosed table environment")
                
            if errors:
                print(f"Errors in {file.name}:")
                for error in errors:
                    print(f"  - {error}")
    
    return False  # Don't push changes
```