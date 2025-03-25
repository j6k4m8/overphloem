"""
Test file for the CLI module.
"""
import unittest
import sys
from unittest.mock import patch, MagicMock
from io import StringIO

from overphloem.cli.cli import (
    create_parser,
    pull_command,
    push_command,
    attach_command,
    main
)


class TestCLI(unittest.TestCase):
    """Test cases for the CLI module."""

    def test_create_parser(self):
        """Test create_parser function."""
        parser = create_parser()

        # Check parser attributes
        self.assertEqual(parser.description, "Framework for writing Overleaf bots")
        self.assertEqual(parser.prog, "overphloem")

        # Check that commands are available
        subparsers = [action for action in parser._actions if action.dest == 'command'][0]
        commands = subparsers.choices.keys()

        self.assertIn("pull", commands)
        self.assertIn("push", commands)
        self.assertIn("attach", commands)

    @patch('overphloem.cli.cli.Project')
    def test_pull_command(self, mock_project_class):
        """Test pull_command function."""
        # Set up mocks
        mock_project = MagicMock()
        mock_project_class.return_value = mock_project

        # Test successful pull
        mock_project.pull.return_value = True

        args = MagicMock()
        args.project_id = "test_project"
        args.path = "test_path"

        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            result = pull_command(args)

            output = fake_stdout.getvalue().strip()
            self.assertEqual(result, 0)
            self.assertIn("Successfully pulled", output)

        # Test failed pull
        mock_project.pull.return_value = False

        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            result = pull_command(args)

            output = fake_stdout.getvalue().strip()
            self.assertEqual(result, 1)
            self.assertIn("Failed to pull", output)

    @patch('overphloem.cli.cli.Project')
    def test_push_command(self, mock_project_class):
        """Test push_command function."""
        # Set up mocks
        mock_project = MagicMock()
        mock_project_class.return_value = mock_project

        # Test successful push
        mock_project.push.return_value = True

        args = MagicMock()
        args.project_id = "test_project"
        args.path = "test_path"

        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            result = push_command(args)

            output = fake_stdout.getvalue().strip()
            self.assertEqual(result, 0)
            self.assertIn("Successfully pushed", output)

        # Test failed push
        mock_project.push.return_value = False

        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            result = push_command(args)

            output = fake_stdout.getvalue().strip()
            self.assertEqual(result, 1)
            self.assertIn("Failed to push", output)

    @patch('overphloem.cli.cli.Path')
    def test_attach_command_script_not_exists(self, mock_path):
        """Test attach_command function with non-existent script."""
        # Set up mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value.absolute.return_value = mock_path_instance

        args = MagicMock()
        args.project_id = "test_project"
        args.script = "non_existent_script.sh"

        with patch('sys.stdout', new=StringIO()) as fake_stdout:
            result = attach_command(args)

            output = fake_stdout.getvalue().strip()
            self.assertEqual(result, 1)
            self.assertIn("does not exist", output)

    @patch('overphloem.cli.cli.create_parser')
    def test_main(self, mock_create_parser):
        """Test main function."""
        # Set up mocks
        mock_parser = MagicMock()
        mock_create_parser.return_value = mock_parser

        # Test pull command
        mock_args = MagicMock()
        mock_args.command = "pull"
        mock_parser.parse_args.return_value = mock_args

        with patch('overphloem.cli.cli.pull_command', return_value=0) as mock_pull:
            result = main()
            self.assertEqual(result, 0)
            mock_pull.assert_called_once_with(mock_args)

        # Test push command
        mock_args.command = "push"

        with patch('overphloem.cli.cli.push_command', return_value=0) as mock_push:
            result = main()
            self.assertEqual(result, 0)
            mock_push.assert_called_once_with(mock_args)

        # Test attach command
        mock_args.command = "attach"

        with patch('overphloem.cli.cli.attach_command', return_value=0) as mock_attach:
            result = main()
            self.assertEqual(result, 0)
            mock_attach.assert_called_once_with(mock_args)

        # Test invalid command
        mock_args.command = None

        with patch('sys.stdout', new=StringIO()):
            result = main()
            self.assertEqual(result, 1)
            mock_parser.print_help.assert_called_once()


if __name__ == "__main__":
    unittest.main()