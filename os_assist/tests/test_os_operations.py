import unittest
from unittest.mock import patch, mock_open, MagicMock, call # Add 'call' here
import subprocess # Keep this for subprocess.CalledProcessError if you plan to test check=True scenarios, though current run_command uses check=False
from pathlib import Path

# Adjust import path based on test execution context
# Assuming tests are run from the project root (os_assist/)
from src.modules import os_operations
from src.modules.os_operations import FileNotFoundError, DirectoryNotFoundError, CommandExecutionError, OperationError

class TestOsOperations(unittest.TestCase):

    @patch('src.modules.os_operations.Path.is_file')
    @patch('src.modules.os_operations.open', new_callable=mock_open, read_data='test content')
    def test_read_file_success(self, mock_file_open, mock_is_file):
        mock_is_file.return_value = True
        # Path().resolve() still creates a real Path object. We mock its methods.
        # The 'open' is mocked globally for where os_operations.open is called.

        # To make Path(filepath).resolve() work with mocks, we might need to patch Path itself
        # or ensure its methods are controlled.
        # For simplicity, let's assume Path().resolve() works and we mock its subsequent calls like is_file()
        with patch('src.modules.os_operations.Path') as mock_path_constructor:
            mock_path_instance = MagicMock()
            mock_path_instance.resolve.return_value = mock_path_instance # Return self after resolve
            mock_path_instance.is_file.return_value = True
            mock_path_constructor.return_value = mock_path_instance

            content = os_operations.read_file('dummy/path/file.txt')
            self.assertEqual(content, 'test content')
            mock_path_constructor.assert_called_with('dummy/path/file.txt')
            mock_path_instance.resolve.assert_called_once()
            mock_path_instance.is_file.assert_called_once()
            mock_file_open.assert_called_once_with(mock_path_instance, 'r', encoding='utf-8')

    @patch('src.modules.os_operations.Path')
    def test_read_file_not_found(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.is_file.return_value = False # Simulate file not existing
        mock_path_constructor.return_value = mock_path_instance

        with self.assertRaises(FileNotFoundError):
            os_operations.read_file('dummy/non_existent.txt')
        mock_path_constructor.assert_called_with('dummy/non_existent.txt')

    @patch('src.modules.os_operations.Path') # Patch Path
    @patch('src.modules.os_operations.open', new_callable=mock_open) # Patch open
    def test_write_file_success(self, mock_file_open, mock_path_constructor):
        # Setup mock Path instance
        mock_path_instance = MagicMock()
        mock_path_parent_instance = MagicMock() # For path.parent
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.parent = mock_path_parent_instance # Assign mock parent
        mock_path_constructor.return_value = mock_path_instance

        os_operations.write_file('dummy/path/output.txt', 'hello world')

        mock_path_constructor.assert_called_with('dummy/path/output.txt')
        mock_path_instance.resolve.assert_called_once()
        mock_path_parent_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open.assert_called_once_with(mock_path_instance, 'w', encoding='utf-8')
        mock_file_open().write.assert_called_once_with('hello world')

    @patch('src.modules.os_operations.subprocess.run')
    def test_run_command_success(self, mock_subprocess_run):
        mock_process = MagicMock()
        mock_process.stdout = 'command output'
        mock_process.stderr = ''
        mock_process.returncode = 0
        mock_subprocess_run.return_value = mock_process

        result = os_operations.run_command('ls -l')
        self.assertEqual(result['stdout'], 'command output')
        self.assertEqual(result['returncode'], 0)
        self.assertTrue(result['success'])
        mock_subprocess_run.assert_called_once_with('ls -l', shell=True, capture_output=True, text=True, check=False)

    @patch('src.modules.os_operations.subprocess.run')
    def test_run_command_failure_return_code(self, mock_subprocess_run):
        mock_process = MagicMock()
        mock_process.stdout = ''
        mock_process.stderr = 'error output'
        mock_process.returncode = 1
        mock_subprocess_run.return_value = mock_process

        result = os_operations.run_command('failing_command')
        self.assertEqual(result['stderr'], 'error output')
        self.assertEqual(result['returncode'], 1)
        self.assertFalse(result['success'])

    @patch('src.modules.os_operations.subprocess.run', side_effect=Exception('Subprocess failed'))
    def test_run_command_exception(self, mock_subprocess_run):
        with self.assertRaises(CommandExecutionError) as cm:
            os_operations.run_command('some_command')
        self.assertIn("Failed to execute command 'some_command': Exception('Subprocess failed')", str(cm.exception))
        self.assertEqual(cm.exception.returncode, -1)

    @patch('src.modules.os_operations.os.listdir')
    @patch('src.modules.os_operations.Path')
    def test_list_directory_success(self, mock_path_constructor, mock_os_listdir):
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_constructor.return_value = mock_path_instance
        mock_os_listdir.return_value = ['file1.txt', 'dir1']

        items = os_operations.list_directory('dummy/path')
        self.assertEqual(items, sorted(['file1.txt', 'dir1']))
        mock_os_listdir.assert_called_once_with(mock_path_instance)

    @patch('src.modules.os_operations.Path')
    def test_list_directory_not_found(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.exists.return_value = False # Simulate path not existing
        mock_path_constructor.return_value = mock_path_instance
        with self.assertRaises(DirectoryNotFoundError):
            os_operations.list_directory('dummy/non_existent_dir')

    @patch('src.modules.os_operations.Path')
    def test_list_directory_not_a_dir(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = False # Simulate path is not a directory
        mock_path_constructor.return_value = mock_path_instance
        with self.assertRaises(DirectoryNotFoundError):
            os_operations.list_directory('dummy/file_not_dir')

    @patch('src.modules.os_operations.Path')
    def test_create_directory_success(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_constructor.return_value = mock_path_instance

        os_operations.create_directory('new_dir/path')
        mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('src.modules.os_operations.Path')
    def test_create_directory_os_error(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.mkdir.side_effect = OSError("Creation failed")
        mock_path_constructor.return_value = mock_path_instance
        with self.assertRaises(OperationError):
            os_operations.create_directory('failing_dir')

    # Tests for generate_delete_command
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_file(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        resolved_path_str = '/resolved/dummy/file.txt'
        # Below, we configure the mock_path_instance that Path() will return
        mock_path_instance.resolve.return_value = mock_path_instance
        # Configure what str(path_object) will return, which is used in f'"{path}"'
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = False
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/file.txt')
        self.assertEqual(cmd, f'rm "{resolved_path_str}"')

    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_empty_dir_non_recursive(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        resolved_path_str = '/resolved/dummy/empty_dir'
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.iterdir.return_value = iter([]) # Empty directory
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/empty_dir', is_recursive=False)
        self.assertEqual(cmd, f'rm "{resolved_path_str}"')

    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_non_empty_dir_non_recursive_raises_error(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.iterdir.return_value = iter([MagicMock()]) # Non-empty directory
        mock_path_constructor.return_value = mock_path_instance

        with self.assertRaises(OperationError) as context:
            os_operations.generate_delete_command('dummy/non_empty_dir', is_recursive=False)
        self.assertIn("Cannot generate non-recursive delete command for non-empty directory", str(context.exception))

    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_dir_recursive_forced(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        resolved_path_str = '/resolved/dummy/dir_to_del'
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        # iterdir doesn't matter if recursive is True for command generation part
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/dir_to_del', is_recursive=True, is_forced=True)
        self.assertEqual(cmd, f'rm -f -r "{resolved_path_str}"')

    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_path_not_exist_raises_error(self, mock_path_constructor):
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.exists.return_value = False
        mock_path_constructor.return_value = mock_path_instance
        with self.assertRaises(FileNotFoundError):
            os_operations.generate_delete_command('dummy/ghost_path')

if __name__ == '__main__':
    unittest.main()
