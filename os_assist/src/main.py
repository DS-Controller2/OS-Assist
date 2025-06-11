import json # For pretty printing dicts, and potentially for LLM interaction if not handled by provider
import sys
from pathlib import Path

# Attempt to set up PYTHONPATH to include the project root 'os_assist'
# This is to help with module resolution if the script is run directly from os_assist/src
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config_manager import ConfigManager
from src.llm_providers.openrouter_client import OpenRouterProvider
from src.modules import os_operations
from src.llm_parser import parse_llm_response, LLMResponseParseError
from src.modules.quick_action_manager import QuickActionManager, QuickActionError
from src.utils import get_current_os

# Define command blacklist
COMMAND_BLACKLIST = [
    "sudo",
    "rm -rf /",
    "mkfs",
    ":(){:|:&};:",  # Fork bomb
    "mv /dev/null", # Example: moving critical system resources to null
    "dd ",          # Direct disk write, highly dangerous if misused
    "fdisk",
    "gdisk",
    "parted",
    # Common aliases for rm -rf /
    "rm -rf /*",
    "rm -rf . /",
    "rm -rf ./*",
]

# System prompt updated for Quick Actions
SYSTEM_PROMPT = """
You are an OS Assistant. Your goal is to help the user interact with their operating system by translating their natural language requests into specific, structured commands. You must respond with a JSON object containing an "action" and its "parameters".

Available OS actions and their parameters:

1.  `read_file`: Reads the content of a specified file.
    *   `parameters`: `{"filepath": "/path/to/file.txt"}`

2.  `write_file`: Writes content to a specified file. Parent directories will be created.
    *   `parameters`: `{"filepath": "/path/to/file.txt", "content": "text to write", "mode": "overwrite|append"}` (default mode is "overwrite" if not specified)

3.  `run_command`: Executes a terminal command.
    *   `parameters`: `{"command_string": "ls -l /tmp"}`

4.  `list_directory`: Lists files and subdirectories in a directory.
    *   `parameters`: `{"path": "/path/to/directory"}`

5.  `create_directory`: Creates a new directory. Parent directories will be created.
    *   `parameters`: `{"path": "/path/to/create"}`

6.  `generate_delete_command`: Generates a command to delete a file or directory. Does NOT execute.
    *   `parameters`: `{"path": "/path/to/delete", "is_recursive": false, "is_forced": false}`

Available Quick Actions management (these manage sequences of the OS actions above):

7.  `save_quick_action`: Saves a sequence of OS actions as a named quick action.
    *   `parameters`:
        *   `name` (string, required): The name for the quick action.
        *   `actions` (list of dicts, required): The sequence of OS action objects to save. Each object in the list should be like `{"action": "os_action_name", "parameters": {...}}`.

8.  `list_quick_actions`: Lists all saved quick actions and their definitions.
    *   `parameters`: {} (none needed)

9.  `execute_quick_action`: Executes a named, saved quick action sequence.
    *   `parameters`: `{"name": "name_of_quick_action"}`

10. `delete_quick_action`: Deletes a named quick action.
    *   `parameters`: `{"name": "name_of_quick_action_to_delete"}`

11. `find_files`: Finds files or directories matching a pattern.
    *   `parameters`:
        *   `search_path` (string, required): Directory to search in.
        *   `name_pattern` (string, optional, default: "*"): Glob pattern for name (e.g., "*.txt").
        *   `file_type` (string, optional, default: "any"): Type to find ('file', 'directory', 'any').
        *   `is_recursive` (boolean, optional, default: true): Whether to search subdirectories.
    *   Example: `{"action": "find_files", "parameters": {"search_path": "/tmp", "name_pattern": "*.log", "file_type": "file"}}`

**Important Instructions:**
*   Always respond with a single JSON object. No explanatory text outside the JSON.
*   The current detected operating system is [OS_NAME_HERE]. Please tailor system commands for `run_command` accordingly if they are OS-specific.
*   If a user asks to save a quick action, ensure the 'actions' parameter is a list of valid OS action objects.
*   For `generate_delete_command`, the user should be informed the command is not run automatically.
*   If ambiguous, ask for clarification: `{"action": "clarify", "parameters": {"question": "Your question here?"}}`
*   If unable to perform, respond with: `{"action": "error", "parameters": {"message": "Reason for error."}}`

Example for saving a quick action:
User: "Save a quick action called 'setup_project' that first creates a directory '/tmp/new_project' and then writes 'TODO' into '/tmp/new_project/todo.txt'."
LLM Response:
```json
{
  "action": "save_quick_action",
  "parameters": {
    "name": "setup_project",
    "actions": [
      {"action": "create_directory", "parameters": {"path": "/tmp/new_project"}},
      {"action": "write_file", "parameters": {"filepath": "/tmp/new_project/todo.txt", "content": "TODO"}}
    ]
  }
}
```
"""

# --- Action Handler Functions ---

def _handle_read_file(params: dict, **kwargs) -> bool: # kwargs for unused quick_action_manager
    filepath = params.get("filepath")
    if not filepath:
        print("Error: 'filepath' not provided for read_file action.")
        return False
    try:
        content = os_operations.read_file(filepath)
        print(f"--- File Content: {filepath} ---\n{content}\n-------------------------------")
        return True
    except os_operations.FileNotFoundError as e:
        print(f"Error: {e}")
        return False
    except os_operations.OperationError as e:
        print(f"OS Operation Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during read_file: {e}")
        return False

def _handle_write_file(params: dict, **kwargs) -> bool:
    filepath = params.get("filepath")
    content = params.get("content")
    mode = params.get("mode", "overwrite").lower()

    if mode not in ["overwrite", "append"]:
        print(f"Info: Invalid mode '{mode}' provided for write_file. Defaulting to 'overwrite'.")
        mode = "overwrite"

    if filepath is None:
        print("Error: 'filepath' not provided for write_file action.")
        return False

    confirm_action_message = "overwrite" if mode == "overwrite" else "append to"
    print(f"CONFIRM: About to {confirm_action_message} file: '{filepath}'.")
    if mode == "overwrite":
        print("This will overwrite existing content if the file exists or create a new file.")
    else:  # append
        print("This will append to the file if it exists or create a new file.")

    try:
        confirm_input = input("Are you sure? (yes/no): ").strip().lower()
        if confirm_input == "yes":
            os_operations.write_file(filepath, content if content is not None else "", mode=mode)
            print(f"Successfully wrote to file: {filepath} (mode: {mode})")
            return True
        else:
            print("Operation cancelled by user.")
            return False
    except os_operations.OperationError as e:
        print(f"OS Operation Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during write_file: {e}")
        return False

def _handle_run_command(params: dict, **kwargs) -> bool:
    command_string = params.get("command_string")
    if not command_string:
        print("Error: 'command_string' not provided for run_command action.")
        return False

    cleaned_command = command_string.strip()
    for blocked_cmd_prefix in COMMAND_BLACKLIST:
        if cleaned_command.startswith(blocked_cmd_prefix):
            if blocked_cmd_prefix == "rm -rf /" and cleaned_command != "rm -rf /":
                if cleaned_command == "rm -rf /" or cleaned_command.startswith("rm -rf / "):
                    print(f"Error: Command '{command_string}' is blacklisted (exact match to dangerous pattern).")
                    return False
            elif blocked_cmd_prefix in ["rm -rf /*", "rm -rf . /", "rm -rf ./*"] and cleaned_command == blocked_cmd_prefix:
                 print(f"Error: Command '{command_string}' is blacklisted (matches dangerous pattern).")
                 return False
            elif blocked_cmd_prefix != "rm -rf /":
                print(f"Error: Command '{command_string}' starts with a blacklisted prefix '{blocked_cmd_prefix}'.")
                return False

    print(f"CONFIRM: About to execute terminal command: '{command_string}'")
    try:
        confirm_input = input("Are you sure? (yes/no): ").strip().lower()
        if confirm_input == "yes":
            result = os_operations.run_command(command_string)
            print(f"--- Command Result ---")
            if result['stdout']: print(f"STDOUT:\n{result['stdout']}")
            if result['stderr']: print(f"STDERR:\n{result['stderr']}")
            print(f"Return Code: {result['returncode']}")
            print(f"Success: {result['success']}")
            print(f"----------------------")
            if not result['success']:
                print(f"Command executed but reported failure (return code {result['returncode']}).")
            # Command execution itself is considered successful if it ran, regardless of script's success
            return True
        else:
            print("Operation cancelled by user.")
            return False
    except os_operations.CommandExecutionError as e: # Error from os_operations.run_command itself
        print(f"Command Execution Error: {e.message} (stdout: {e.stdout}, stderr: {e.stderr}, code: {e.returncode})")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during run_command: {e}")
        return False

def _handle_list_directory(params: dict, **kwargs) -> bool:
    dir_path = params.get("path")
    if not dir_path:
        print("Error: 'path' not provided for list_directory action.")
        return False
    try:
        items = os_operations.list_directory(dir_path)
        print(f"--- Directory Listing: {dir_path} ---")
        if items:
            for item in items: print(item)
        else:
            print("(Directory is empty)")
        print(f"-----------------------------------")
        return True
    except os_operations.DirectoryNotFoundError as e:
        print(f"Error: {e}")
        return False
    except os_operations.OperationError as e:
        print(f"OS Operation Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during list_directory: {e}")
        return False

def _handle_create_directory(params: dict, **kwargs) -> bool:
    dir_path = params.get("path")
    if not dir_path:
        print("Error: 'path' not provided for create_directory action.")
        return False
    try:
        os_operations.create_directory(dir_path)
        print(f"Successfully created directory (or it already existed): {dir_path}")
        return True
    except os_operations.OperationError as e:
        print(f"OS Operation Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during create_directory: {e}")
        return False

def _handle_generate_delete_command(params: dict, **kwargs) -> bool:
    del_path = params.get("path")
    is_recursive = params.get("is_recursive", False)
    is_forced = params.get("is_forced", False)
    if not del_path:
        print("Error: 'path' not provided for generate_delete_command action.")
        return False
    try:
        command = os_operations.generate_delete_command(del_path, is_recursive, is_forced)
        print(f"Generated delete command: {command}")
        print("IMPORTANT: This command has NOT been executed. ")
        print("To execute, copy the command and use the 'run_command' action.")
        return True
    except os_operations.FileNotFoundError as e: # Specific to generate_delete_command
        print(f"Error generating delete command: {e}")
        return False
    except os_operations.OperationError as e:
        print(f"OS Operation Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during generate_delete_command: {e}")
        return False

def _handle_find_files(params: dict, **kwargs) -> bool:
    search_path = params.get("search_path")
    name_pattern = params.get("name_pattern", "*")
    file_type = params.get("file_type", "any")
    is_recursive = params.get("is_recursive", True)

    if not search_path:
        print("Error: 'search_path' not provided for find_files action.")
        return False
    try:
        found_items = os_operations.find_files(search_path, name_pattern, file_type, is_recursive)
        print(f"--- Items Found in '{search_path}' (Pattern: '{name_pattern}', Type: '{file_type}', Recursive: {is_recursive}) ---")
        if found_items:
            for item in found_items: print(item)
        else:
            print("(No items found matching criteria)")
        print("---------------------------------------------------")
        return True
    except os_operations.DirectoryNotFoundError as e:
        print(f"Error finding files: {e}")
        return False
    except os_operations.OperationError as e:
        print(f"OS Operation Error during find: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during find_files: {e}")
        return False

def _handle_save_quick_action(params: dict, quick_action_manager: QuickActionManager) -> bool:
    name = params.get("name")
    actions = params.get("actions")
    if not name or not actions:
        print("Error: 'name' and 'actions' are required for save_quick_action.")
        return False
    if not quick_action_manager:
        print("Error: QuickActionManager is not available.")
        return False
    try:
        # Validate structure of actions before saving
        if not isinstance(actions, list):
            print("Error: 'actions' parameter must be a list.")
            return False
        for i, act_item in enumerate(actions):
            if not isinstance(act_item, dict) or "action" not in act_item or "parameters" not in act_item:
                print(f"Error: Action item at index {i} is not correctly formatted. Expected {{'action': 'name', 'parameters': {{...}}}}.")
                return False
            # Further validation: check if the action name in the sequence is a known OS action
            # This requires access to the OS action names, e.g. keys of ACTION_HANDLERS for OS part
            # For now, basic structural validation.
            if act_item["action"] not in ACTION_HANDLERS_REGISTER: # Check against actual handlers
                 # Exclude quick action management actions from being nested directly this way
                if act_item["action"] in ["save_quick_action", "list_quick_actions", "execute_quick_action", "delete_quick_action"]:
                    print(f"Error: Quick action management action '{act_item['action']}' cannot be part of a saved quick action sequence.")
                    return False
                # We might want a specific list of "savable" OS actions if not all handlers are OS actions
                # print(f"Warning: Action '{act_item['action']}' in sequence is not a known OS action. It might fail during execution.")

        quick_action_manager.save_action(name, actions)
        print(f"Quick action '{name}' saved successfully.")
        return True
    except QuickActionError as e:
        print(f"Error saving quick action '{name}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False


def _handle_list_quick_actions(params: dict, quick_action_manager: QuickActionManager) -> bool:
    if not quick_action_manager:
        print("Error: QuickActionManager is not available.")
        return False
    try:
        actions = quick_action_manager.list_actions()
        if not actions:
            print("No quick actions saved yet.")
        else:
            print("--- Saved Quick Actions ---")
            for name, definition in actions.items():
                print(f"Name: {name}")
                print(f"  Actions: {json.dumps(definition['actions'], indent=2)}") # Pretty print actions
            print("-------------------------")
        return True
    except QuickActionError as e:
        print(f"Error listing quick actions: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

def _handle_execute_quick_action(params: dict, quick_action_manager: QuickActionManager) -> bool:
    name = params.get("name")
    if not name:
        print("Error: 'name' not provided for execute_quick_action.")
        return False
    if not quick_action_manager:
        print("Error: QuickActionManager is not available.")
        return False
    try:
        action_sequence = quick_action_manager.get_action(name)
        if not action_sequence:
            print(f"Error: Quick action '{name}' not found.")
            return False

        print(f"--- Executing Quick Action: {name} ---")
        for i, step_action in enumerate(action_sequence["actions"]):
            step_action_name = step_action.get("action")
            step_params = step_action.get("parameters", {})
            print(f"\nStep {i+1}: Action: {step_action_name}, Parameters: {json.dumps(step_params)}")

            handler = ACTION_HANDLERS_REGISTER.get(step_action_name)
            if handler:
                # OS actions might not need quick_action_manager, others might.
                # The handler signature should accept **kwargs or specific args.
                # For simplicity, all handlers will accept quick_action_manager, but OS ones won't use it.
                success = handler(step_params, quick_action_manager=quick_action_manager)
                if not success:
                    print(f"Step {i+1} ('{step_action_name}') failed. Aborting quick action '{name}'.")
                    return False
            else:
                print(f"Error: Unknown action '{step_action_name}' in quick action '{name}'. Aborting.")
                return False
        print(f"\n--- Quick Action '{name}' completed. ---")
        return True
    except QuickActionError as e:
        print(f"Error executing quick action '{name}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during quick action execution: {e}")
        return False

def _handle_delete_quick_action(params: dict, quick_action_manager: QuickActionManager) -> bool:
    name = params.get("name")
    if not name:
        print("Error: 'name' not provided for delete_quick_action.")
        return False
    if not quick_action_manager:
        print("Error: QuickActionManager is not available.")
        return False
    try:
        quick_action_manager.delete_action(name)
        print(f"Quick action '{name}' deleted successfully.")
        return True
    except QuickActionError as e: # Catches if action doesn't exist
        print(f"Error deleting quick action '{name}': {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

def _handle_clarify(params: dict, **kwargs) -> bool:
    question = params.get("question", "No question provided.")
    print(f"Clarification needed: {question}")
    return True # This action itself is successful in delivering the message

def _handle_error_action(params: dict, **kwargs) -> bool:
    message = params.get("message", "Unknown error from LLM.")
    print(f"LLM Error: {message}")
    return True # This action itself is successful in delivering the message

# --- Dispatch Dictionary ---
# Needs to be defined globally or passed around if some handlers need to call others via it (esp. execute_quick_action)
ACTION_HANDLERS_REGISTER = {
    "read_file": _handle_read_file,
    "write_file": _handle_write_file,
    "run_command": _handle_run_command,
    "list_directory": _handle_list_directory,
    "create_directory": _handle_create_directory,
    "generate_delete_command": _handle_generate_delete_command,
    "find_files": _handle_find_files,
    "save_quick_action": _handle_save_quick_action,
    "list_quick_actions": _handle_list_quick_actions,
    "execute_quick_action": _handle_execute_quick_action,
    "delete_quick_action": _handle_delete_quick_action,
    "clarify": _handle_clarify,
    "error": _handle_error_action,
}

def main():
    global ACTION_HANDLERS_REGISTER # Make sure it's accessible if defined globally
    print("Initializing OS Assistant...")
    current_os = get_current_os()
    print(f"Detected OS: {current_os}")

    # Initialize ConfigManager
    config_manager = ConfigManager()

    # Initialize OpenRouterProvider
    llm_provider = OpenRouterProvider(config_manager=config_manager)

    if not llm_provider.api_key:
        print("Error: OpenRouter API key is not configured. Please check your config.json or environment variables.")
        print("Refer to os_assist/README.md for setup instructions.")
        return

    # Initialize QuickActionManager
    try:
        quick_action_manager = QuickActionManager()
        print("QuickActionManager initialized.")
    except QuickActionError as e:
        print(f"Error initializing QuickActionManager: {e}. Quick actions may not be available.")
        quick_action_manager = None

    print("OS Assistant ready. Type 'exit' or 'quit' to end.")

    print("Enter your command:")

    while True:
        try:
            user_input = input("> ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting OS Assistant.")
                break
            if not user_input:
                continue

            print("\nThinking...")

            active_system_prompt = SYSTEM_PROMPT.replace("[OS_NAME_HERE]", current_os)
            messages = [
                {"role": "system", "content": active_system_prompt},
                {"role": "user", "content": user_input}
            ]

            llm_response_str = llm_provider.generate_chat_completion(messages=messages)

            if not llm_response_str:
                print("Error: Received no response from LLM.")
                continue

            print(f"Raw LLM response: {llm_response_str}") # For debugging

            try:
                parsed_action = parse_llm_response(llm_response_str)
                print(f"Parsed action: {json.dumps(parsed_action, indent=2)}") # For debugging
            except LLMResponseParseError as e:
                print(f"Error parsing LLM response: {e}")
                continue

            action_name = parsed_action.get("action")
            params = parsed_action.get("parameters", {})
