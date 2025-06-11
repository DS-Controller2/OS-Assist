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
