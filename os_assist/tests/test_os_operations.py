import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import subprocess
import tempfile
import shutil
from pathlib import Path

# Adjust import path based on test execution context
from os_assist.src.modules import os_operations
from os_assist.src.modules.os_operations import FileNotFoundError, DirectoryNotFoundError, CommandExecutionError, OperationError, write_file

class TestOsOperations(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for tests that perform real file I/O
        self.test_dir = Path(tempfile.mkdtemp(prefix="os_assist_test_"))

    def tearDown(self):
        # Remove the temporary directory after tests
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

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
    @patch('src.modules.os_operations.get_current_os')
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_file_linux(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'linux'
        mock_path_instance = MagicMock()
        resolved_path_str = '/resolved/dummy/file.txt'
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = False
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/file.txt')
        self.assertEqual(cmd, f'rm "{resolved_path_str}"')
        cmd_forced = os_operations.generate_delete_command('dummy/file.txt', is_forced=True)
        self.assertEqual(cmd_forced, f'rm -f "{resolved_path_str}"')


    @patch('src.modules.os_operations.get_current_os')
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_file_windows(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'windows'
        mock_path_instance = MagicMock()
        resolved_path_str = 'C:\\dummy\\file.txt'
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = False
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/file.txt')
        self.assertEqual(cmd, f'del "{resolved_path_str}"')
        # is_forced for basic del on Windows is not implemented with a specific flag in current code
        cmd_forced = os_operations.generate_delete_command('dummy/file.txt', is_forced=True)
        self.assertEqual(cmd_forced, f'del "{resolved_path_str}"') # Potentially add /f if desired for read-only


    @patch('src.modules.os_operations.get_current_os')
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_empty_dir_non_recursive_linux(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'linux'
        mock_path_instance = MagicMock()
        resolved_path_str = '/resolved/dummy/empty_dir'
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.iterdir.return_value = iter([])
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/empty_dir', is_recursive=False)
        self.assertEqual(cmd, f'rm "{resolved_path_str}"')

    @patch('src.modules.os_operations.get_current_os')
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_empty_dir_non_recursive_windows(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'windows'
        mock_path_instance = MagicMock()
        resolved_path_str = 'C:\\dummy\\empty_dir'
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.iterdir.return_value = iter([])
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/empty_dir', is_recursive=False)
        self.assertEqual(cmd, f'rmdir "{resolved_path_str}"')


    @patch('src.modules.os_operations.get_current_os')
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_non_empty_dir_non_recursive_raises_error_linux(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'linux'
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.iterdir.return_value = iter([MagicMock()])
        mock_path_constructor.return_value = mock_path_instance

        with self.assertRaises(OperationError) as context:
            os_operations.generate_delete_command('dummy/non_empty_dir', is_recursive=False)
        self.assertIn("Cannot generate non-recursive delete command for non-empty directory", str(context.exception))

    @patch('src.modules.os_operations.get_current_os')
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_non_empty_dir_non_recursive_raises_error_windows(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'windows'
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.iterdir.return_value = iter([MagicMock()])
        mock_path_constructor.return_value = mock_path_instance

        with self.assertRaises(OperationError) as context:
            os_operations.generate_delete_command('dummy/non_empty_dir', is_recursive=False)
        self.assertIn("Cannot generate non-recursive delete command for non-empty directory", str(context.exception))


    @patch('src.modules.os_operations.get_current_os')
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_dir_recursive_forced_linux(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'linux'
        mock_path_instance = MagicMock()
        resolved_path_str = '/resolved/dummy/dir_to_del'
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/dir_to_del', is_recursive=True, is_forced=True)
        self.assertEqual(cmd, f'rm -f -r "{resolved_path_str}"')

    @patch('src.modules.os_operations.get_current_os')
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_dir_recursive_windows(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'windows'
        mock_path_instance = MagicMock()
        resolved_path_str = 'C:\\dummy\\dir_to_del'
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.__str__.return_value = resolved_path_str
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_constructor.return_value = mock_path_instance

        cmd = os_operations.generate_delete_command('dummy/dir_to_del', is_recursive=True, is_forced=False)
        self.assertEqual(cmd, f'rmdir /s "{resolved_path_str}"') # No /q if not forced

        cmd_forced = os_operations.generate_delete_command('dummy/dir_to_del', is_recursive=True, is_forced=True)
        self.assertEqual(cmd_forced, f'rmdir /q /s "{resolved_path_str}"')


    @patch('src.modules.os_operations.get_current_os') # OS doesn't matter if path doesn't exist
    @patch('src.modules.os_operations.Path')
    def test_generate_delete_command_path_not_exist_raises_error(self, mock_path_constructor, mock_get_os):
        mock_get_os.return_value = 'linux' # Could be any OS
        mock_path_instance = MagicMock()
        mock_path_instance.resolve.return_value = mock_path_instance
        mock_path_instance.exists.return_value = False
        mock_path_constructor.return_value = mock_path_instance
        with self.assertRaises(FileNotFoundError):
            os_operations.generate_delete_command('dummy/ghost_path')

    # --- Tests for find_files ---

    @patch('src.modules.os_operations.Path')
    def test_find_files_basic_recursive_all_types(self, mock_path_constructor):
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = True
        mock_search_path_obj.is_dir.return_value = True
        mock_path_constructor.return_value = mock_search_path_obj

        mock_item1 = MagicMock(spec=Path); mock_item1.resolve.return_value = mock_item1; mock_item1.__str__.return_value = '/search/path/file1.txt'; mock_item1.is_file.return_value = True; mock_item1.is_dir.return_value = False
        mock_item2 = MagicMock(spec=Path); mock_item2.resolve.return_value = mock_item2; mock_item2.__str__.return_value = '/search/path/subdir'; mock_item2.is_file.return_value = False; mock_item2.is_dir.return_value = True
        mock_item3 = MagicMock(spec=Path); mock_item3.resolve.return_value = mock_item3; mock_item3.__str__.return_value = '/search/path/another.doc'; mock_item3.is_file.return_value = True; mock_item3.is_dir.return_value = False

        mock_search_path_obj.rglob.return_value = iter([mock_item1, mock_item2, mock_item3])

        result = os_operations.find_files(search_path='/search/path', name_pattern='*', file_type='any', is_recursive=True)

        mock_search_path_obj.rglob.assert_called_once_with('*')
        self.assertEqual(sorted(result), sorted(['/search/path/file1.txt', '/search/path/subdir', '/search/path/another.doc']))
        # For file_type='any', is_file/is_dir on items are not called for filtering, only for characterization if needed by other parts (not in this func)

    @patch('src.modules.os_operations.Path')
    def test_find_files_recursive_txt_files_only(self, mock_path_constructor):
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = True
        mock_search_path_obj.is_dir.return_value = True
        mock_path_constructor.return_value = mock_search_path_obj

        mock_file1 = MagicMock(spec=Path); mock_file1.resolve.return_value = mock_file1; mock_file1.__str__.return_value = '/search/path/file1.txt'; mock_file1.is_file.return_value = True
        mock_dir = MagicMock(spec=Path); mock_dir.resolve.return_value = mock_dir; mock_dir.__str__.return_value = '/search/path/docs'; mock_dir.is_file.return_value = False; mock_dir.is_dir.return_value = True # Won't match file_type='file'
        mock_file2 = MagicMock(spec=Path); mock_file2.resolve.return_value = mock_file2; mock_file2.__str__.return_value = '/search/path/notes.log'; mock_file2.is_file.return_value = True # Won't match *.txt
        mock_file3 = MagicMock(spec=Path); mock_file3.resolve.return_value = mock_file3; mock_file3.__str__.return_value = '/search/path/report.txt'; mock_file3.is_file.return_value = True

        # rglob should only yield items whose names match the pattern.
        # The filtering by is_file happens *after* rglob yields them.
        mock_search_path_obj.rglob.return_value = iter([mock_file1, mock_file3]) # Assume rglob itself filters by name

        result = os_operations.find_files(search_path='/search/path', name_pattern='*.txt', file_type='file', is_recursive=True)

        mock_search_path_obj.rglob.assert_called_once_with('*.txt')
        mock_file1.is_file.assert_called_once()
        mock_file3.is_file.assert_called_once()
        self.assertEqual(sorted(result), sorted(['/search/path/file1.txt', '/search/path/report.txt']))

    @patch('src.modules.os_operations.Path')
    def test_find_files_non_recursive_directories_only(self, mock_path_constructor):
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = True
        mock_search_path_obj.is_dir.return_value = True
        mock_path_constructor.return_value = mock_search_path_obj

        mock_dir1 = MagicMock(spec=Path); mock_dir1.resolve.return_value = mock_dir1; mock_dir1.__str__.return_value = '/search/path/dir1'; mock_dir1.is_dir.return_value = True
        mock_file1 = MagicMock(spec=Path); mock_file1.resolve.return_value = mock_file1; mock_file1.__str__.return_value = '/search/path/file.txt'; mock_file1.is_dir.return_value = False # Not a dir
        mock_dir2 = MagicMock(spec=Path); mock_dir2.resolve.return_value = mock_dir2; mock_dir2.__str__.return_value = '/search/path/dir2'; mock_dir2.is_dir.return_value = True

        mock_search_path_obj.glob.return_value = iter([mock_dir1, mock_file1, mock_dir2])

        result = os_operations.find_files(search_path='/search/path', name_pattern='*', file_type='directory', is_recursive=False)

        mock_search_path_obj.glob.assert_called_once_with('*')
        mock_dir1.is_dir.assert_called_once()
        mock_file1.is_dir.assert_called_once()
        mock_dir2.is_dir.assert_called_once()
        self.assertEqual(sorted(result), sorted(['/search/path/dir1', '/search/path/dir2']))

    @patch('src.modules.os_operations.Path')
    def test_find_files_search_path_not_exist(self, mock_path_constructor):
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = False # Path does not exist
        mock_path_constructor.return_value = mock_search_path_obj

        with self.assertRaisesRegex(DirectoryNotFoundError, "Search path '/non_existent_path' does not exist."):
            os_operations.find_files(search_path='/non_existent_path')
        mock_search_path_obj.exists.assert_called_once()

    @patch('src.modules.os_operations.Path')
    def test_find_files_search_path_is_not_directory(self, mock_path_constructor):
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = True
        mock_search_path_obj.is_dir.return_value = False # Path is a file, not a directory
        mock_path_constructor.return_value = mock_search_path_obj

        with self.assertRaisesRegex(DirectoryNotFoundError, "Search path '/file_path' is not a directory."):
            os_operations.find_files(search_path='/file_path')
        mock_search_path_obj.is_dir.assert_called_once()

    @patch('src.modules.os_operations.Path') # Minimal mock needed as it should fail before globbing
    def test_find_files_invalid_file_type(self, mock_path_constructor):
        # This test, and others above it, are mock-based and should remain as they are.
        # New tests for write_file using real I/O will be added below.
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = True
        mock_search_path_obj.is_dir.return_value = True
        mock_path_constructor.return_value = mock_search_path_obj

        with self.assertRaisesRegex(OperationError, "Invalid file_type 'document'. Must be 'file', 'directory', or 'any'."):
            os_operations.find_files(search_path='/search/path', file_type='document')

    @patch('src.modules.os_operations.Path')
    def test_find_files_no_results(self, mock_path_constructor):
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = True
        mock_search_path_obj.is_dir.return_value = True
        mock_path_constructor.return_value = mock_search_path_obj

        mock_search_path_obj.rglob.return_value = iter([]) # No items found

        result = os_operations.find_files(search_path='/search/path')
        self.assertEqual(result, [])
        mock_search_path_obj.rglob.assert_called_once_with('*') # Default pattern

    @patch('src.modules.os_operations.Path')
    def test_find_files_os_error_during_globbing(self, mock_path_constructor):
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = True
        mock_search_path_obj.is_dir.return_value = True
        mock_path_constructor.return_value = mock_search_path_obj

        mock_search_path_obj.rglob.side_effect = OSError("Simulated disk error")

        with self.assertRaisesRegex(OperationError, "Error during find operation in '/search/path': Simulated disk error"):
            os_operations.find_files(search_path='/search/path')

    @patch('src.modules.os_operations.Path')
    def test_find_files_pattern_case_sensitivity_mocked(self, mock_path_constructor):
        # This test demonstrates how to mock items with specific names to test pattern matching.
        # Actual case sensitivity of rglob/glob depends on the OS, but we control the mock.
        mock_search_path_obj = MagicMock(spec=Path)
        mock_search_path_obj.resolve.return_value = mock_search_path_obj
        mock_search_path_obj.exists.return_value = True
        mock_search_path_obj.is_dir.return_value = True
        mock_path_constructor.return_value = mock_search_path_obj

        # Items that rglob will "find" based on the pattern '*'
        # The actual filtering happens in the find_files logic if name_pattern is more specific
        # or by rglob if we assume rglob handles it. For this test, let's assume rglob does its job with the pattern.
        item_project = MagicMock(spec=Path); item_project.resolve.return_value = item_project; item_project.__str__.return_value = '/search/path/Project.txt'; item_project.is_file.return_value = True
        item_pproject = MagicMock(spec=Path); item_pproject.resolve.return_value = item_pproject; item_pproject.__str__.return_value = '/search/path/project.txt'; item_pproject.is_file.return_value = True
        item_other = MagicMock(spec=Path); item_other.resolve.return_value = item_other; item_other.__str__.return_value = '/search/path/Other.md'; item_other.is_file.return_value = True

        # Scenario 1: rglob returns only 'Project.txt' for pattern 'Project*'
        mock_search_path_obj.rglob.return_value = iter([item_project])
        result = os_operations.find_files(search_path='/search/path', name_pattern='Project*', file_type='file')
        mock_search_path_obj.rglob.assert_called_with('Project*')
        self.assertEqual(result, ['/search/path/Project.txt'])

        # Scenario 2: rglob returns 'Project.txt' and 'project.txt' for pattern '[Pp]roject*'
        mock_search_path_obj.rglob.reset_mock() # Reset call stats for next assertion
        mock_search_path_obj.rglob.return_value = iter([item_project, item_pproject])
        result = os_operations.find_files(search_path='/search/path', name_pattern='[Pp]roject*', file_type='file')
        mock_search_path_obj.rglob.assert_called_with('[Pp]roject*')
        self.assertEqual(sorted(result), sorted(['/search/path/Project.txt', '/search/path/project.txt']))

    # --- New tests for write_file with real file I/O ---

    def test_write_file_overwrite_new_file(self):
        file_path = self.test_dir / "overwrite_new.txt"
        content = "Hello Overwrite!"
        write_file(str(file_path), content) # Default mode is overwrite
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), content)

    def test_write_file_overwrite_existing_file(self):
        file_path = self.test_dir / "overwrite_existing.txt"
        initial_content = "Initial content."
        file_path.write_text(initial_content)

        new_content = "Overwritten content."
        write_file(str(file_path), new_content, mode="overwrite")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), new_content)

    def test_write_file_append_new_file(self):
        file_path = self.test_dir / "append_new.txt"
        content = "Hello Append!"
        write_file(str(file_path), content, mode="append")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), content)

    def test_write_file_append_existing_file(self):
        file_path = self.test_dir / "append_existing.txt"
        initial_content = "Initial."
        file_path.write_text(initial_content)

        append_content = " Appended."
        write_file(str(file_path), append_content, mode="append")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), initial_content + append_content)

    def test_write_file_append_multiple_times(self):
        file_path = self.test_dir / "append_multiple.txt"
        write_file(str(file_path), "Part1.", mode="append")
        write_file(str(file_path), "Part2.", mode="append")
        write_file(str(file_path), "Part3.", mode="append")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), "Part1.Part2.Part3.")

    def test_write_file_overwrite_creates_parents(self):
        file_path = self.test_dir / "parents" / "sub" / "overwrite_parents.txt"
        content = "Parents created for overwrite."
        write_file(str(file_path), content, mode="overwrite")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), content)
        self.assertTrue(file_path.parent.exists())
        self.assertTrue(file_path.parent.parent.exists())


    def test_write_file_append_creates_parents(self):
        file_path = self.test_dir / "parents_append" / "sub_append" / "append_parents.txt"
        content = "Parents created for append."
        write_file(str(file_path), content, mode="append")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), content)
        self.assertTrue(file_path.parent.exists())
        self.assertTrue(file_path.parent.parent.exists())

    def test_write_file_overwrite_empty_content_new_file(self):
        file_path = self.test_dir / "overwrite_empty_new.txt"
        write_file(str(file_path), "", mode="overwrite")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), "")

    def test_write_file_overwrite_empty_content_existing_file(self):
        file_path = self.test_dir / "overwrite_empty_existing.txt"
        file_path.write_text("Some pre-existing content.")
        write_file(str(file_path), "", mode="overwrite")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), "")

    def test_write_file_append_empty_content_new_file(self):
        file_path = self.test_dir / "append_empty_new.txt"
        write_file(str(file_path), "", mode="append")
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), "")

    def test_write_file_append_empty_content_existing_file(self):
        file_path = self.test_dir / "append_empty_existing.txt"
        initial_content = "Existing data."
        file_path.write_text(initial_content)
        write_file(str(file_path), "", mode="append") # Appending empty string
        self.assertTrue(file_path.is_file())
        self.assertEqual(file_path.read_text(), initial_content)

    def test_write_file_invalid_mode_raises_error(self):
        file_path = self.test_dir / "invalid_mode.txt"
        with self.assertRaises(OperationError) as context:
            # This test assumes that os_operations.write_file itself will raise an error for an invalid mode
            # if the caller (e.g. main.py) doesn't sanitize it first.
            # The main.py logic *does* sanitize, so this specific error might only be raised
            # if write_file is called directly with a bad mode.
            write_file(str(file_path), "content", mode="invalid_mode")
        self.assertIn("Invalid mode 'invalid_mode' specified for write_file", str(context.exception))
        self.assertFalse(file_path.exists()) # File should not be created


if __name__ == '__main__':
    unittest.main()
