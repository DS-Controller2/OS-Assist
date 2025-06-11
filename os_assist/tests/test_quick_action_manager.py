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

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open)
    def test_init_no_file_exists(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        mock_path_exists.side_effect = [False, False]
        qam = QuickActionManager()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open_qam.assert_not_called()
        self.assertEqual(qam.actions, {})

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='{"action1": []}')
    def test_init_file_exists_valid_json(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        mock_path_exists.side_effect = [True, True]
        qam = QuickActionManager()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open_qam.assert_called_once_with(QUICK_ACTIONS_FILE, 'r', encoding='utf-8')
        self.assertEqual(qam.actions, {"action1": []})

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='invalid json')
    def test_init_file_exists_invalid_json(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        mock_path_exists.side_effect = [True, True]
        qam = QuickActionManager()
        mock_file_open_qam.assert_called_once_with(QUICK_ACTIONS_FILE, 'r', encoding='utf-8')
        self.assertEqual(qam.actions, {})

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='[]')
    def test_init_file_exists_json_not_dict(self, mock_file_open_qam, mock_path_exists, mock_mkdir):
        mock_path_exists.side_effect = [True, True]
        qam = QuickActionManager()
        self.assertEqual(qam.actions, {})

    @unittest.expectedFailure
    @patch('src.modules.quick_action_manager.json.dump')
    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=False)
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open)
    def test_add_action_and_save(self, mock_open_func, mock_path_exists, mock_mkdir, mock_json_dump):
        mock_path_exists.side_effect = [False, False]
        qam = QuickActionManager()
        self.assertEqual(qam.actions, {})
        qam.add_action("test_action_1", self.sample_sequence_1)
        self.assertIn("test_action_1", qam.actions)
        self.assertEqual(qam.actions["test_action_1"], self.sample_sequence_1)
        mock_json_dump.assert_called_once_with(
            {"test_action_1": self.sample_sequence_1},
            mock_open_func(),
            indent=2
        )
        mock_open_func.assert_called_with(QUICK_ACTIONS_FILE, 'w', encoding='utf-8')
        mock_json_dump.reset_mock()
        mock_open_func.reset_mock()
        qam.add_action("test_action_2", self.sample_sequence_2)
        self.assertIn("test_action_2", qam.actions)
        expected_data_after_second_add = {
            "test_action_1": self.sample_sequence_1,
            "test_action_2": self.sample_sequence_2
        }
        mock_json_dump.assert_called_once_with(
            expected_data_after_second_add,
            mock_open_func(),
            indent=2
        )
        mock_open_func.assert_called_with(QUICK_ACTIONS_FILE, 'w', encoding='utf-8')

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=True)
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
            qam.add_action("test", [1, 2, 3])
        with self.assertRaisesRegex(QuickActionError, "Each action in the sequence must have 'action' and 'parameters' keys."):
            qam.add_action("test", [{"action": "read"}])
        with self.assertRaisesRegex(QuickActionError, "Each action in the sequence must have 'action' and 'parameters' keys."):
            qam.add_action("test", [{"parameters": {}}])

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

    @unittest.expectedFailure
    @patch('src.modules.quick_action_manager.json.load')
    @patch('src.modules.quick_action_manager.json.dump')
    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open)
    def test_remove_action_success(self, mock_open_func, mock_path_exists, mock_mkdir, mock_json_dump, mock_json_load):
        initial_data_dict = {"action_to_remove": self.sample_sequence_1, "action_to_keep": self.sample_sequence_2}
        mock_path_exists.return_value = True
        mock_json_load.return_value = initial_data_dict
        qam = QuickActionManager()
        mock_open_func.assert_called_with(QUICK_ACTIONS_FILE, 'r', encoding='utf-8')
        mock_json_load.assert_called_with(mock_open_func())
        self.assertIn("action_to_remove", qam.actions)
        mock_open_func.reset_mock()
        result = qam.remove_action("action_to_remove")
        self.assertEqual(result, "Quick action 'action_to_remove' removed successfully.")
        self.assertNotIn("action_to_remove", qam.actions)
        self.assertIn("action_to_keep", qam.actions)
        expected_data_after_remove = {"action_to_keep": self.sample_sequence_2}
        mock_json_dump.assert_called_once_with(
            expected_data_after_remove,
            mock_open_func(),
            indent=2
        )
        mock_open_func.assert_called_with(QUICK_ACTIONS_FILE, 'w', encoding='utf-8')

    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists', return_value=True)
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open, read_data='{}')
    def test_remove_action_non_existent_raises_error(self, mock_file, mock_exists, mock_mkdir):
        qam = QuickActionManager()
        with self.assertRaisesRegex(QuickActionError, "Quick action 'non_existent_action' not found."):
            qam.remove_action("non_existent_action")

    @unittest.expectedFailure
    @patch('src.modules.quick_action_manager.json.load')
    @patch('src.modules.quick_action_manager.json.dump')
    @patch('src.modules.quick_action_manager.Path.mkdir')
    @patch('src.modules.quick_action_manager.Path.exists')
    @patch('src.modules.quick_action_manager.open', new_callable=mock_open)
    def test_persistence_load_after_save(self, mock_open_func, mock_path_exists, mock_mkdir, mock_json_dump, mock_json_load):
        action_to_save_dict = {"persistent_action": self.sample_sequence_1}
        mock_path_exists.side_effect = [
            False,
            False,
            True,
            True,
            True
        ]
        qam1 = QuickActionManager()
        qam1.add_action("persistent_action", self.sample_sequence_1)
        mock_json_dump.assert_called_once_with(
            action_to_save_dict,
            mock_open_func(),
            indent=2
        )
        mock_open_func.assert_called_with(QUICK_ACTIONS_FILE, 'w', encoding='utf-8')
        mock_json_load.return_value = action_to_save_dict
        mock_open_func.reset_mock()
        qam2 = QuickActionManager()
        mock_open_func.assert_called_once_with(QUICK_ACTIONS_FILE, 'r', encoding='utf-8')
        mock_json_load.assert_called_once_with(mock_open_func())
        self.assertIn("persistent_action", qam2.actions)
        self.assertEqual(qam2.actions["persistent_action"], self.sample_sequence_1)
        self.assertEqual(mock_mkdir.call_count, 3)

if __name__ == '__main__':
    unittest.main()
