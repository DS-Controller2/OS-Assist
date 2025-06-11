import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import json
import builtins # For patching global 'open' if it's not already in a specific module path

# Assuming tests are run from the project root (os_assist/)
from src.modules.quick_action_manager import QuickActionManager, QuickActionError, QUICK_ACTIONS_FILE, QUICK_ACTIONS_DIR

class TestQuickActionManager(unittest.TestCase):

    def setUp(self):
        # Basic valid action sequence for reuse
        self.sample_sequence_1 = [
            {"action": "create_directory", "parameters": {"path": "/tmp/my_project"}},
            {"action": "write_file", "parameters": {"filepath": "/tmp/my_project/README.md", "content": "# My Project"}}
        ]
        self.sample_sequence_2 = [{"action": "list_directory", "parameters": {"path": "/tmp"}}]

    # Patching strategy:
    # - Path.exists: To control if the quick_actions.json file or data directory exists.
    # - Path.mkdir: To check if directory creation is attempted.
    # - open (within quick_action_manager context): To mock reading/writing quick_actions.json.
    # - json.load/dump are not directly patched; their effect is tested via the content passed to/from mock_open.

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open)
    def test_init_no_file_exists(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        # Simulate data directory and quick_actions.json not existing initially
        # Path.exists needs to return False for the directory check in _ensure_data_dir_exists
        # and then False for the file check in _load_actions.
        mock_path_exists.side_effect = [False, False] # First call for dir, second for file

        qam = QuickActionManager()

        # Check dir creation was attempted
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        # Check file open was NOT called for reading as file doesn't exist
        mock_file_open_qam.assert_not_called()
        self.assertEqual(qam.actions, {}) # Should be empty if no file

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='{"action1": []}')
    def test_init_file_exists_valid_json(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        # Simulate data directory exists, and quick_actions.json exists and is valid
        mock_path_exists.side_effect = [True, True] # Dir exists, File exists

        qam = QuickActionManager()

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True) # Still called by _ensure_data_dir_exists
        mock_file_open_qam.assert_called_once_with(QUICK_ACTIONS_FILE, 'r', encoding='utf-8')
        self.assertEqual(qam.actions, {"action1": []})

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='invalid json')
    def test_init_file_exists_invalid_json(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        mock_path_exists.side_effect = [True, True] # Dir exists, File exists

        qam = QuickActionManager() # Should load empty due to decode error

        mock_file_open_qam.assert_called_once_with(QUICK_ACTIONS_FILE, 'r', encoding='utf-8')
        self.assertEqual(qam.actions, {}) # Should be empty

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='[]') # Not a dict
    def test_init_file_exists_json_not_dict(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        mock_path_exists.side_effect = [True, True]

        qam = QuickActionManager()
        self.assertEqual(qam.actions, {})


    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=False) # No pre-existing file
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open)
    def test_add_action_and_save(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        # Path.exists for _load_actions (file check)
        mock_path_exists.side_effect = [False, False] # Dir then file for init
                                         # then for save, dir exists, file write

        qam = QuickActionManager()
        self.assertEqual(qam.actions, {})

        qam.add_action("test_action_1", self.sample_sequence_1)
        self.assertIn("test_action_1", qam.actions)
        self.assertEqual(qam.actions["test_action_1"], self.sample_sequence_1)

        # Check that open was called to write the file
        expected_json_output = json.dumps({"test_action_1": self.sample_sequence_1}, indent=2)
        mock_file_open_qam.assert_called_with(QUICK_ACTIONS_FILE, 'w', encoding='utf-8')
        mock_file_open_qam().write.assert_called_once_with(expected_json_output)

        qam.add_action("test_action_2", self.sample_sequence_2)
        self.assertIn("test_action_2", qam.actions)

        expected_data_after_second_add = {
            "test_action_1": self.sample_sequence_1,
            "test_action_2": self.sample_sequence_2
        }
        expected_json_output_2 = json.dumps(expected_data_after_second_add, indent=2)
        # mock_open().write is called again, need to check the latest call or all calls
        self.assertEqual(mock_file_open_qam().write.call_args_list[-1], call(expected_json_output_2))


    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=True) # File exists
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='{}')
    def test_add_action_empty_name_raises_error(self, mock_file, mock_exists, mock_mkdir):
        qam = QuickActionManager()
        with self.assertRaisesRegex(QuickActionError, "Quick action name cannot be empty."):
            qam.add_action("", self.sample_sequence_1)
        with self.assertRaisesRegex(QuickActionError, "Quick action name cannot be empty."):
            qam.add_action("   ", self.sample_sequence_1)

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=True)
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='{}')
    def test_add_action_invalid_sequence_raises_error(self, mock_file, mock_exists, mock_mkdir):
        qam = QuickActionManager()
        with self.assertRaisesRegex(QuickActionError, "Action sequence must be a list of action dictionaries."):
            qam.add_action("test", "not a list")
        with self.assertRaisesRegex(QuickActionError, "Action sequence must be a list of action dictionaries."):
            qam.add_action("test", [1, 2, 3]) # List, but not of dicts
        with self.assertRaisesRegex(QuickActionError, "Each action in the sequence must have 'action' and 'parameters' keys."):
            qam.add_action("test", [{"action": "read"}]) # Missing parameters
        with self.assertRaisesRegex(QuickActionError, "Each action in the sequence must have 'action' and 'parameters' keys."):
            qam.add_action("test", [{"parameters": {}}]) # Missing action


    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=True)
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='{"act1": [], "act2": {}}')
    def test_list_actions(self, mock_file, mock_exists, mock_mkdir):
        qam = QuickActionManager()
        self.assertEqual(qam.list_actions(), {"act1": [], "act2": {}})

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=True)
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data=json.dumps({"my_action": [{"cmd": "ls"}]}))
    def test_get_action(self, mock_file, mock_exists, mock_mkdir):
        qam = QuickActionManager()
        self.assertEqual(qam.get_action("my_action"), [{"cmd": "ls"}])
        self.assertIsNone(qam.get_action("non_existent_action"))

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=True)
    @patch('src.modules.quick_action_manager.open') # Use default mock_open for more flexibility on read/write
    def test_remove_action_success(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        initial_data = {"action_to_remove": self.sample_sequence_1, "action_to_keep": self.sample_sequence_2}
        # Configure the mock_open behavior for multiple reads/writes
        mock_file_open_qam.side_effect = [
            mock_open(read_data=json.dumps(initial_data)).return_value,  # For initial load
            mock_open().return_value                                    # For save after remove
        ]

        qam = QuickActionManager()
        self.assertIn("action_to_remove", qam.actions)

        result = qam.remove_action("action_to_remove")
        self.assertEqual(result, "Quick action 'action_to_remove' removed successfully.")
        self.assertNotIn("action_to_remove", qam.actions)
        self.assertIn("action_to_keep", qam.actions) # Ensure other actions are preserved

        # Check that _save_actions was called correctly
        expected_json_output = json.dumps({"action_to_keep": self.sample_sequence_2}, indent=2)

        # The second time open is called is for writing:
        # Get the mock object that was used for the 'write' open call
        # This is a bit tricky with side_effect providing different mocks.
        # We need to check the write call on the mock returned for the 'w' open.
        # The mock_file_open_qam.return_value used for writing is the one from the second side_effect call.
        # This part of the test might need refinement if the mock_open setup is complex.
        # For now, let's rely on the internal state of qam.actions being correct and _save_actions being called.
        # A simpler check on the last write call to the mock_open object:
        # This assumes the last call to any file handle's write method.
        # This will fail if other file writes happen in a more complex test.
        # For this test, it should be the write for _save_actions.

        # Correct way to check write:
        # The second time mock_file_open_qam is called (for the write), it uses the second mock from side_effect.
        # That second mock is mock_open().return_value. We need to check its write method.
        # The instance used for writing is the return_value of the second call to mock_file_open_qam
        # This is tricky. A simpler way is to check the *arguments* to json.dump if we patched json.dump
        # Or, ensure the mock_file_open_qam is called with 'w' and then check its handle's write.

        # Let's check the calls to mock_file_open_qam itself
        calls = [
            call(QUICK_ACTIONS_FILE, 'r', encoding='utf-8'), # Initial load
            call(QUICK_ACTIONS_FILE, 'w', encoding='utf-8')  # Save after remove
        ]
        mock_file_open_qam.assert_has_calls(calls, any_order=False)

        # To check the content written:
        # The mock object returned by mock_open() is what has the write method.
        # If mock_file_open_qam is the mock for the 'open' function itself,
        # then mock_file_open_qam().write is how you access the write method of the file handle.
        # This assumes mock_open is configured globally or for the specific `open` used.
        # The current patch is `patch('src.modules.quick_action_manager.open', ...)`
        # So, the mock_file_open_qam is the one.
        mock_file_open_qam().write.assert_called_with(expected_json_output)


    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=True)
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='{}')
    def test_remove_action_non_existent_raises_error(self, mock_file, mock_exists, mock_mkdir):
        qam = QuickActionManager()
        with self.assertRaisesRegex(QuickActionError, "Quick action 'non_existent_action' not found."):
            qam.remove_action("non_existent_action")

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open')
    def test_persistence_load_after_save(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        # Simulate no file initially for the first QAM instance
        mock_path_exists.side_effect = [
            False, False, # QAM1: _ensure_data_dir_exists (dir), _load_actions (file)
            True, True    # QAM2: _ensure_data_dir_exists (dir), _load_actions (file)
        ]

        # Mock open for QAM1 (writing) and QAM2 (reading)
        # QAM1 writes, QAM2 reads what QAM1 wrote.
        # We need mock_open to store what was written and provide it back.

        # This is a more complex scenario for mocking open.
        # A simpler way for this specific test is to check that _save_actions is called,
        # then for QAM2, provide the expected data to mock_open's read_data.

        # Mock for QAM1 initialization (no file)
        mock_qam1_file_handle = mock_open()

        # Mock for QAM1 saving action
        mock_qam1_save_handle = mock_open()

        # Mock for QAM2 initialization (reading the saved data)
        # The data QAM2 reads should be what QAM1 saved.
        action_to_save = {"persistent_action": self.sample_sequence_1}
        mock_qam2_read_handle = mock_open(read_data=json.dumps(action_to_save))

        mock_file_open_qam.side_effect = [
            mock_qam1_file_handle.return_value, # QAM1 init (no read actually happens due to exists=False)
            mock_qam1_save_handle.return_value, # QAM1 save
            mock_qam2_read_handle.return_value  # QAM2 init (read)
        ]

        # QAM1: Initialize and save an action
        qam1 = QuickActionManager()
        qam1.add_action("persistent_action", self.sample_sequence_1)

        # Check save was called
        mock_qam1_save_handle().write.assert_called_once_with(json.dumps(action_to_save, indent=2))

        # QAM2: Initialize, should load the action saved by QAM1
        qam2 = QuickActionManager()
        self.assertIn("persistent_action", qam2.actions)
        self.assertEqual(qam2.actions["persistent_action"], self.sample_sequence_1)

        # Verify calls to open
        calls = [
            # QAM1 save call
            call(QUICK_ACTIONS_FILE, 'w', encoding='utf-8'),
            # QAM2 load call
            call(QUICK_ACTIONS_FILE, 'r', encoding='utf-8'),
        ]
        # mock_file_open_qam.assert_has_calls(calls, any_order=False)
        # The number of calls to open can be tricky due to __init__ also calling _ensure_data_dir_exists
        # and _load_actions. The side_effect count should match actual open calls.
        # For QAM1: init (_load_actions doesn't open as exists=F), add_action (_save_actions opens for write) -> 1 write open
        # For QAM2: init (_load_actions opens for read) -> 1 read open
        # So 2 actual 'open' calls that interact with file content for read/write.
        self.assertIn(call(QUICK_ACTIONS_FILE, 'w', encoding='utf-8'), mock_file_open_qam.call_args_list)
        self.assertIn(call(QUICK_ACTIONS_FILE, 'r', encoding='utf-8'), mock_file_open_qam.call_args_list)


if __name__ == '__main__':
    unittest.main()
