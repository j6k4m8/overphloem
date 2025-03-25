"""
Events module for handling Overleaf project events.
"""
import time
import enum
import threading
import logging
from typing import Callable, Optional, Any, Dict, Union
from pathlib import Path

from overphloem.core.project import Project

logger = logging.getLogger(__name__)


class Event(enum.Enum):
    """Enumeration of events that can be monitored."""
    CHANGE = "change"
    PULL = "pull"
    PUSH = "push"


class EventHandler:
    """
    Event handler for Overleaf projects.

    This class manages event listeners for Overleaf projects.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Implement singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventHandler, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the event handler."""
        if self._initialized:
            return

        self._listeners = {event: {} for event in Event}
        self._running_threads = {}
        self._initialized = True

    def register(self, event: Event, project_id: str, callback: Callable[[Project], bool],
                push: bool = False, interval: int = 60, falloff: Optional[float] = None) -> str:
        """
        Register an event listener.

        Args:
            event (Event): Event type to listen for.
            project_id (str): Overleaf project ID.
            callback (Callable[[Project], bool]): Callback function to execute when event occurs.
            push (bool, optional): Whether to push changes after callback. Defaults to False.
            interval (int, optional): Polling interval in seconds. Defaults to 60.
            falloff (Optional[float], optional): Falloff factor for increasing interval. Defaults to None.

        Returns:
            str: Listener ID for unregistering.
        """
        listener_id = f"{project_id}_{event.value}_{id(callback)}"
        self._listeners[event][listener_id] = {
            "project_id": project_id,
            "callback": callback,
            "push": push,
            "interval": interval,
            "falloff": falloff,
            "current_interval": interval,
            "last_check": time.time()
        }

        if event == Event.CHANGE:
            self._start_change_thread(listener_id, project_id, interval)

        return listener_id

    def unregister(self, listener_id: str) -> bool:
        """
        Unregister an event listener.

        Args:
            listener_id (str): Listener ID returned from register.

        Returns:
            bool: True if listener was removed, False otherwise.
        """
        for event in Event:
            if listener_id in self._listeners[event]:
                del self._listeners[event][listener_id]
                if listener_id in self._running_threads:
                    self._running_threads[listener_id]["stop"] = True
                return True
        return False

    def _start_change_thread(self, listener_id: str, project_id: str, interval: int) -> None:
        """
        Start a thread for monitoring project changes.

        Args:
            listener_id (str): Listener ID.
            project_id (str): Overleaf project ID.
            interval (int): Polling interval in seconds.
        """
        thread_data = {"stop": False}
        self._running_threads[listener_id] = thread_data

        thread = threading.Thread(
            target=self._monitor_changes,
            args=(listener_id, thread_data),
            daemon=True
        )
        thread.start()

    def _monitor_changes(self, listener_id: str, thread_data: Dict[str, Any]) -> None:
        """
        Monitor project for changes.

        Args:
            listener_id (str): Listener ID.
            thread_data (Dict[str, Any]): Thread control data.
        """
        event = Event.CHANGE
        if listener_id not in self._listeners[event]:
            return

        config = self._listeners[event][listener_id]
        project = Project(config["project_id"])
        project.pull()  # Initial pull

        last_commit_hash = self._get_latest_commit_hash(project)

        while not thread_data["stop"]:
            time.sleep(config["current_interval"])

            if thread_data["stop"]:
                break

            try:
                project.pull()
                current_hash = self._get_latest_commit_hash(project)

                if current_hash != last_commit_hash:
                    last_commit_hash = current_hash
                    should_push = config["callback"](project)

                    if should_push and config["push"]:
                        project.push()

                    # Reset interval after successful event
                    config["current_interval"] = config["interval"]
                elif config["falloff"] is not None:
                    # Apply falloff to increase wait time
                    config["current_interval"] = min(
                        config["current_interval"] * config["falloff"],
                        3600  # Max interval: 1 hour
                    )
            except Exception as e:
                logger.error(f"Error in change monitor: {e}")

    def _get_latest_commit_hash(self, project: Project) -> str:
        """
        Get the latest commit hash for a project.

        Args:
            project (Project): Project to get commit hash for.

        Returns:
            str: The latest commit hash, or empty string on error.
        """
        import subprocess

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=project.local_path,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return ""


# Global event handler instance
_handler = EventHandler()


def on(event: Event, project_id: str, push: bool = False, interval: int = 60,
       falloff: Optional[float] = None) -> Callable:
    """
    Decorator for registering event handlers.

    Args:
        event (Event): Event type to listen for.
        project_id (str): Overleaf project ID.
        push (bool, optional): Whether to push changes after callback. Defaults to False.
        interval (int, optional): Polling interval in seconds. Defaults to 60.
        falloff (Optional[float], optional): Falloff factor for increasing interval. Defaults to None.

    Returns:
        Callable: Decorator function.
    """
    def decorator(func: Callable) -> Callable:
        """Register the decorated function as an event listener."""
        _handler.register(event, project_id, func, push, interval, falloff)
        return func
    return decorator