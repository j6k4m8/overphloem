"""
Test file for the events module.
"""
import unittest
import time
import threading
from unittest.mock import patch, MagicMock, call

from overphloem.core.events import Event, EventHandler, on


class TestEvents(unittest.TestCase):
    """Test cases for the events module."""

    def setUp(self):
        """Set up test environment."""
        # Create a fresh event handler for each test
        self.handler = EventHandler()
        # Clear existing listeners
        for event in Event:
            self.handler._listeners[event].clear()
        self.handler._running_threads.clear()

    def test_event_enum(self):
        """Test Event enum values."""
        self.assertEqual(Event.CHANGE.value, "change")
        self.assertEqual(Event.PULL.value, "pull")
        self.assertEqual(Event.PUSH.value, "push")

    def test_handler_singleton(self):
        """Test EventHandler is a singleton."""
        handler1 = EventHandler()
        handler2 = EventHandler()
        self.assertIs(handler1, handler2)

    def test_register(self):
        """Test register method."""
        callback = MagicMock(return_value=True)
        project_id = "test_project"

        # Register a listener
        listener_id = self.handler.register(
            Event.CHANGE, project_id, callback, push=True, interval=30, falloff=1.5
        )

        # Check that listener was registered
        self.assertIn(listener_id, self.handler._listeners[Event.CHANGE])
        listener = self.handler._listeners[Event.CHANGE][listener_id]

        self.assertEqual(listener["project_id"], project_id)
        self.assertEqual(listener["callback"], callback)
        self.assertTrue(listener["push"])
        self.assertEqual(listener["interval"], 30)
        self.assertEqual(listener["falloff"], 1.5)
        self.assertEqual(listener["current_interval"], 30)

    def test_unregister(self):
        """Test unregister method."""
        callback = MagicMock(return_value=True)
        project_id = "test_project"

        # Register a listener
        listener_id = self.handler.register(
            Event.CHANGE, project_id, callback
        )

        # Check that listener was registered
        self.assertIn(listener_id, self.handler._listeners[Event.CHANGE])

        # Unregister the listener
        result = self.handler.unregister(listener_id)
        self.assertTrue(result)

        # Check that listener was removed
        self.assertNotIn(listener_id, self.handler._listeners[Event.CHANGE])

        # Try to unregister non-existent listener
        result = self.handler.unregister("non_existent")
        self.assertFalse(result)

    @patch('overphloem.core.events.threading.Thread')
    def test_start_change_thread(self, mock_thread):
        """Test _start_change_thread method."""
        listener_id = "test_listener"
        project_id = "test_project"
        interval = 30

        self.handler._start_change_thread(listener_id, project_id, interval)

        # Check that thread was created and started
        self.assertIn(listener_id, self.handler._running_threads)
        self.assertFalse(self.handler._running_threads[listener_id]["stop"])

        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    @patch('overphloem.core.events.Project')
    @patch('overphloem.core.events.EventHandler._get_latest_commit_hash')
    def test_monitor_changes(self, mock_get_hash, mock_project_class):
        """Test _monitor_changes method."""
        # Set up mocks
        mock_project = MagicMock()
        mock_project_class.return_value = mock_project

        # Mock commit hashes (first same, then different to trigger callback)
        mock_get_hash.side_effect = ["hash1", "hash1", "hash2"]

        # Set up listener data
        callback = MagicMock(return_value=True)
        project_id = "test_project"

        listener_id = f"{project_id}_change_{id(callback)}"
        self.handler._listeners[Event.CHANGE][listener_id] = {
            "project_id": project_id,
            "callback": callback,
            "push": True,
            "interval": 1,  # 1 second for faster testing
            "falloff": 1.5,
            "current_interval": 1,
            "last_check": time.time()
        }

        # Create thread data with stop flag
        thread_data = {"stop": False}

        # Run monitor_changes in a separate thread
        thread = threading.Thread(
            target=self.handler._monitor_changes,
            args=(listener_id, thread_data)
        )
        thread.daemon = True
        thread.start()

        # Let it run for a bit
        time.sleep(3)

        # Stop the thread
        thread_data["stop"] = True
        thread.join(timeout=2)

        # Check that project was pulled
        mock_project.pull.assert_called()

        # Check that callback was called when hash changed
        callback.assert_called_with(mock_project)

        # Check that push was called (since callback returns True)
        mock_project.push.assert_called()

    @patch('subprocess.run')
    def test_get_latest_commit_hash(self, mock_run):
        """Test _get_latest_commit_hash method."""
        # Mock successful git command
        mock_run.return_value = MagicMock(
            stdout="abcdef1234567890",
            returncode=0
        )

        mock_project = MagicMock()
        mock_project.local_path = "/tmp/test"

        hash_value = self.handler._get_latest_commit_hash(mock_project)
        self.assertEqual(hash_value, "abcdef1234567890")

        # Check that git command was called
        mock_run.assert_called_with(
            ["git", "rev-parse", "HEAD"],
            cwd=mock_project.local_path,
            check=True,
            capture_output=True,
            text=True
        )

        # Test case where git command fails
        mock_run.side_effect = Exception("Git error")
        hash_value = self.handler._get_latest_commit_hash(mock_project)
        self.assertEqual(hash_value, "")

    @patch('overphloem.core.events._handler.register')
    def test_on_decorator(self, mock_register):
        """Test on decorator."""

        @on(Event.CHANGE, "test_project", push=True, interval=30, falloff=1.5)
        def test_callback(project):
            return True

        # Check that register was called with correct args
        mock_register.assert_called_with(
            Event.CHANGE, "test_project", test_callback, True, 30, 1.5
        )


if __name__ == "__main__":
    unittest.main()