import json
from pathlib import Path

# Define the path for the quick actions file
# Assumes this module is in os_assist/src/modules/
# So, project_root is parent.parent.parent (os_assist/src/modules -> os_assist/src -> os_assist),
# and data is a subdirectory of project_root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
QUICK_ACTIONS_DIR = PROJECT_ROOT / "data"
QUICK_ACTIONS_FILE = QUICK_ACTIONS_DIR / "quick_actions.json"

class QuickActionError(Exception):
    """Base exception for quick action errors."""
    pass

class QuickActionManager:
    def __init__(self):
        self.quick_actions_dir = QUICK_ACTIONS_DIR
        self.quick_actions_file = QUICK_ACTIONS_FILE
        self._ensure_data_dir_exists()
        self.actions = self._load_actions()

    def _ensure_data_dir_exists(self):
        """Ensures the data directory for quick actions exists."""
        try:
            self.quick_actions_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # This is a critical error if we can't create the directory for storage.
            # However, the application might still run without quick actions if loading fails.
            # For now, print a warning. A more robust app might require this directory.
            print(f"Warning: Could not create data directory {self.quick_actions_dir}: {e}")

    def _load_actions(self) -> dict:
        """Loads quick actions from the JSON file."""
        if not self.quick_actions_file.exists():
            return {}
        try:
            with open(self.quick_actions_file, 'r', encoding='utf-8') as f:
                actions_data = json.load(f)
                if not isinstance(actions_data, dict):
                    print(f"Warning: Quick actions file {self.quick_actions_file} does not contain a valid JSON object. Starting with empty actions.")
                    return {}
                return actions_data
        except json.JSONDecodeError:
            print(f"Warning: Error decoding JSON from {self.quick_actions_file}. Starting with empty actions.")
            return {}
        except OSError as e:
            print(f"Warning: Could not read quick actions file {self.quick_actions_file}: {e}. Starting with empty actions.")
            return {}

    def _save_actions(self):
        """Saves the current quick actions to the JSON file."""
        try:
            self._ensure_data_dir_exists() # Ensure directory still exists before writing
            with open(self.quick_actions_file, 'w', encoding='utf-8') as f:
                json.dump(self.actions, f, indent=2)
        except OSError as e:
            raise QuickActionError(f"Could not save quick actions to {self.quick_actions_file}: {e}")
        except Exception as e:
            raise QuickActionError(f"An unexpected error occurred while saving quick actions: {e}")

    def add_action(self, name: str, action_sequence: list):
        """
        Adds or updates a quick action.

        Args:
            name: The name of the quick action.
            action_sequence: A list of action dictionaries (e.g.,
                             [{"action": "os_op_1", "parameters": {}}, ...]).

        Raises:
            QuickActionError: If the name is empty or action_sequence is not valid.
        """
        if not name or not name.strip():
            raise QuickActionError("Quick action name cannot be empty.")
        if not isinstance(action_sequence, list) or not all(isinstance(item, dict) for item in action_sequence):
            raise QuickActionError("Action sequence must be a list of action dictionaries.")
        for item in action_sequence:
            if 'action' not in item or 'parameters' not in item:
                 raise QuickActionError("Each action in the sequence must have 'action' and 'parameters' keys.")

        self.actions[name] = action_sequence
        self._save_actions()
        return f"Quick action '{name}' saved successfully."

    def get_action(self, name: str) -> list | None:
        """
        Retrieves a quick action sequence by its name.

        Args:
            name: The name of the quick action.

        Returns:
            The list of action dictionaries if found, else None.
        """
        return self.actions.get(name)

    def list_actions(self) -> dict:
        """Returns all defined quick actions."""
        return self.actions

    def remove_action(self, name: str):
        """
        Removes a quick action.

        Args:
            name: The name of the quick action to remove.

        Raises:
            QuickActionError: If the action name does not exist.
        """
        if name not in self.actions:
            raise QuickActionError(f"Quick action '{name}' not found.")

        del self.actions[name]
        self._save_actions()
        return f"Quick action '{name}' removed successfully."

if __name__ == '__main__':
    print("--- Testing QuickActionManager ---")
    # Adjust PROJECT_ROOT for __main__ context if needed, or use a fixed relative path from project root
    # This __main__ assumes it's run from os_assist/src/modules or that PROJECT_ROOT is correctly set
    # For the test, let's ensure quick_actions.json is created in a predictable place relative to test execution
    # If running this file directly, __file__ is os_assist/src/modules/quick_action_manager.py
    # PROJECT_ROOT should be os_assist

    # Test setup: Define test-specific paths to avoid interfering with app's actual data
    TEST_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # os_assist
    TEST_QUICK_ACTIONS_DIR = TEST_PROJECT_ROOT / "test_data_quick_actions" # /os_assist/test_data_quick_actions
    TEST_QUICK_ACTIONS_FILE = TEST_QUICK_ACTIONS_DIR / "quick_actions_test.json"

    # Temporarily override global paths for testing scope
    global QUICK_ACTIONS_DIR, QUICK_ACTIONS_FILE
    ORIG_QUICK_ACTIONS_DIR, ORIG_QUICK_ACTIONS_FILE = QUICK_ACTIONS_DIR, QUICK_ACTIONS_FILE
    QUICK_ACTIONS_DIR = TEST_QUICK_ACTIONS_DIR
    QUICK_ACTIONS_FILE = TEST_QUICK_ACTIONS_FILE

    # Ensure a clean slate for testing
    if TEST_QUICK_ACTIONS_FILE.exists():
        TEST_QUICK_ACTIONS_FILE.unlink()
    if TEST_QUICK_ACTIONS_DIR.exists():
        # Only remove if empty after file deletion, or if it was specifically created for this test
        try:
            if not list(TEST_QUICK_ACTIONS_DIR.iterdir()):
                 TEST_QUICK_ACTIONS_DIR.rmdir()
        except OSError: pass # If other files are there, leave it.

    qam = QuickActionManager() # Uses the overridden TEST paths
    print(f"Using test quick actions file: {qam.quick_actions_file}")
    assert qam.quick_actions_dir == TEST_QUICK_ACTIONS_DIR
    assert qam.quick_actions_file == TEST_QUICK_ACTIONS_FILE


    # Test add_action
    print("\n--- Testing add_action ---")
    sample_sequence_1 = [
        {"action": "create_directory", "parameters": {"path": "/tmp/my_project"}},
        {"action": "write_file", "parameters": {"filepath": "/tmp/my_project/README.md", "content": "# My Project"}}
    ]
    result = qam.add_action("create_project_readme", sample_sequence_1)
    print(result)
    assert "create_project_readme" in qam.list_actions()
    assert qam.get_action("create_project_readme") == sample_sequence_1

    sample_sequence_2 = [{"action": "list_directory", "parameters": {"path": "/tmp"}}]
    qam.add_action("list_tmp", sample_sequence_2)
    assert "list_tmp" in qam.list_actions()

    try:
        qam.add_action("", sample_sequence_1)
        assert False, "Should have raised error for empty name"
    except QuickActionError as e:
        print(f"Correctly caught: {e}")

    try:
        qam.add_action("bad_seq", [{"action": "read"}]) # Missing parameters
        assert False, "Should have raised error for malformed sequence"
    except QuickActionError as e:
        print(f"Correctly caught: {e}")

    # Test list_actions
    print("\n--- Testing list_actions ---")
    actions = qam.list_actions()
    print(f"Current actions: {json.dumps(actions, indent=2)}")
    assert len(actions) == 2

    # Test get_action
    print("\n--- Testing get_action ---")
    action_seq = qam.get_action("create_project_readme")
    assert action_seq == sample_sequence_1
    print(f"Retrieved 'create_project_readme': {action_seq}")
    assert qam.get_action("non_existent_action") is None

    # Test remove_action
    print("\n--- Testing remove_action ---")
    result = qam.remove_action("list_tmp")
    print(result)
    assert "list_tmp" not in qam.list_actions()
    assert len(qam.list_actions()) == 1

    try:
        qam.remove_action("non_existent_action")
        assert False, "Should have raised error for removing non-existent action"
    except QuickActionError as e:
        print(f"Correctly caught: {e}")

    # Test persistence (load actions again)
    print("\n--- Testing Persistence ---")
    qam_reloaded = QuickActionManager() # This will use TEST_QUICK_ACTIONS_FILE
    assert "create_project_readme" in qam_reloaded.list_actions()
    assert qam_reloaded.get_action("create_project_readme") == sample_sequence_1
    assert "list_tmp" not in qam_reloaded.list_actions() # Should still be removed
    print("Persistence test passed.")

    # Test data directory creation if it doesn't exist
    print("\n--- Testing Data Directory Creation ---")
    if TEST_QUICK_ACTIONS_FILE.exists():
        TEST_QUICK_ACTIONS_FILE.unlink()
    if TEST_QUICK_ACTIONS_DIR.exists():
        try:
            # Only remove if empty and it's our specific test dir
            if not list(TEST_QUICK_ACTIONS_DIR.iterdir()):
                TEST_QUICK_ACTIONS_DIR.rmdir()
                print(f"Removed directory {TEST_QUICK_ACTIONS_DIR} for test")
        except OSError as e:
            print(f"Could not remove {TEST_QUICK_ACTIONS_DIR} for recreate test: {e}. Skipping part of test.")

    if not TEST_QUICK_ACTIONS_DIR.exists():
        # This instance of QAM will use TEST_QUICK_ACTIONS_DIR due to global override
        qam_test_dir_create = QuickActionManager()
        assert TEST_QUICK_ACTIONS_DIR.exists() and TEST_QUICK_ACTIONS_DIR.is_dir(), "Test data directory should have been created"
        print(f"Test data directory {TEST_QUICK_ACTIONS_DIR} created or already existed and verified.")
    else:
        print(f"Test data directory {TEST_QUICK_ACTIONS_DIR} already exists, skipping explicit creation test.")

    # Clean up test file and directory
    if TEST_QUICK_ACTIONS_FILE.exists():
        TEST_QUICK_ACTIONS_FILE.unlink()
    try:
        if TEST_QUICK_ACTIONS_DIR.exists() and not list(TEST_QUICK_ACTIONS_DIR.iterdir()):
            TEST_QUICK_ACTIONS_DIR.rmdir()
    except OSError:
        pass

    # Restore original global paths
    QUICK_ACTIONS_DIR = ORIG_QUICK_ACTIONS_DIR
    QUICK_ACTIONS_FILE = ORIG_QUICK_ACTIONS_FILE

    print("\nQuickActionManager testing complete.")
