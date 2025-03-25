"""
Utility functions for overphloem.
"""
import os
import re
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Set up logging for overphloem.

    Args:
        level (int, optional): Logging level. Defaults to logging.INFO.

    Returns:
        logging.Logger: Logger instance.
    """
    logger = logging.getLogger("overphloem")
    logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def validate_project_id(project_id: str) -> bool:
    """
    Validate Overleaf project ID format.

    Args:
        project_id (str): The project ID to validate.

    Returns:
        bool: True if the project ID is valid, False otherwise.
    """
    # Most Overleaf project IDs are hexadecimal strings
    return bool(re.match(r'^[a-zA-Z0-9]{10,24}$', project_id))


def find_tex_files(directory: Path) -> List[Path]:
    """
    Find all TeX files in a directory.

    Args:
        directory (Path): Directory to search.

    Returns:
        List[Path]: List of paths to TeX files.
    """
    return list(directory.glob("**/*.tex"))


def extract_tex_commands(content: str, command: str) -> List[str]:
    """
    Extract TeX command arguments from content.

    Args:
        content (str): LaTeX content.
        command (str): LaTeX command to find (without backslash).

    Returns:
        List[str]: List of command arguments.
    """
    pattern = r'\\' + command + r'\{([^}]*)\}'
    return re.findall(pattern, content)


def get_bibtex_entries(bib_content: str) -> Dict[str, Dict[str, str]]:
    """
    Extract BibTeX entries from content.

    Args:
        bib_content (str): BibTeX content.

    Returns:
        Dict[str, Dict[str, str]]: Dictionary of BibTeX entries.
    """
    entries = {}
    current_entry = None
    current_key = None

    for line in bib_content.split('\n'):
        line = line.strip()

        # Start of new entry
        if line.startswith('@'):
            match = re.match(r'@(\w+)\{([^,]+),', line)
            if match:
                entry_type, key = match.groups()
                current_entry = {'type': entry_type}
                current_key = key
                entries[key] = current_entry

        # Entry field
        elif current_entry is not None and '=' in line:
            field, value = line.split('=', 1)
            field = field.strip().lower()
            value = value.strip()

            # Remove trailing comma
            if value.endswith(','):
                value = value[:-1]

            # Remove surrounding braces or quotes
            if (value.startswith('{') and value.endswith('}')) or \
               (value.startswith('"') and value.endswith('"')):
                value = value[1:-1]

            current_entry[field] = value

    return entries