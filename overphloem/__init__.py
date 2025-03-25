"""
Overphloem: Framework for writing Overleaf bots.

This package provides tools to sync, monitor, and automate operations on Overleaf projects.
"""

from overphloem.core.project import Project
from overphloem.core.events import Event, on
from overphloem.core.file import File

__version__ = "0.1.0"
__all__ = ["Project", "Event", "on", "File"]