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

2.  `write_file`: Writes or overwrites content to a specified file. Parent directories will be created.
    *   `parameters`: `{"filepath": "/path/to/file.txt", "content": "text to write"}`

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

def _execute_os_action(action_name: str, params: dict) -> bool:
    """
    Helper function to execute a single OS-level action.
    Returns True if successful, False otherwise.
    """
    try:
        if action_name == "read_file":
            filepath = params.get("filepath")
            if filepath:
                content = os_operations.read_file(filepath)
                print(f"--- File Content: {filepath} ---\n{content}\n-------------------------------")
            else:
                print("Error: 'filepath' not provided for read_file action.")
                return False

        elif action_name == "write_file":
            filepath = params.get("filepath")
            content = params.get("content") # Content can be None for empty file, but filepath must exist
            if filepath is not None:
                print(f"CONFIRM: About to write to file: '{filepath}'. This may overwrite existing content or create a new file.")
                confirm_input = input("Are you sure? (yes/no): ").strip().lower()
                if confirm_input == "yes":
                    os_operations.write_file(filepath, content if content is not None else "")
                    print(f"Successfully wrote to file: {filepath}")
                else:
                    print("Operation cancelled by user.")
                    return False # Cancelled
            else:
                print("Error: 'filepath' not provided for write_file action.")
                return False

        elif action_name == "run_command":
            command_string = params.get("command_string")
            if command_string:
                # Blacklist check
                cleaned_command = command_string.strip()
                for blocked_cmd_prefix in COMMAND_BLACKLIST:
                    if cleaned_command.startswith(blocked_cmd_prefix):
                        # Special handling for "rm -rf /" to avoid false positives on "rm -rf /some/path"
                        if blocked_cmd_prefix == "rm -rf /" and cleaned_command != "rm -rf /":
                            # Check if it's exactly "rm -rf /" or "rm -rf / "
                            # This is a simple check; more sophisticated logic might be needed for robust detection
                            # For example, "rm -rf /usr" is bad, but "rm -rf /tmp/foo" might be okay depending on policy
                            # The current blacklist aims for very specific dangerous patterns.
                            if cleaned_command == "rm -rf /" or cleaned_command.startswith("rm -rf / "): # Catches "rm -rf / " and "rm -rf /etc" etc.
                                print(f"Error: Command '{command_string}' is blacklisted for security reasons (exact match to dangerous pattern).")
                                return False
                            # If it's like "rm -rf /some/path" (not root itself), it might be okay, let confirmation handle it.
                            # This part is tricky; for now, we are strict on "rm -rf /" and "rm -rf /*"
                        elif blocked_cmd_prefix in ["rm -rf /*", "rm -rf . /", "rm -rf ./*"] and cleaned_command == blocked_cmd_prefix:
                             print(f"Error: Command '{command_string}' is blacklisted for security reasons (matches dangerous pattern).")
                             return False
                        elif blocked_cmd_prefix != "rm -rf /": # For other blacklist items like sudo, mkfs etc.
                            print(f"Error: Command '{command_string}' starts with a blacklisted prefix '{blocked_cmd_prefix}'.")
                            return False

                print(f"CONFIRM: About to execute terminal command: '{command_string}'")
                confirm_input = input("Are you sure? (yes/no): ").strip().lower()
                if confirm_input == "yes":
                    result = os_operations.run_command(command_string)
                    print(f"--- Command Result ---")
                    if result['stdout']:
                        print(f"STDOUT:\n{result['stdout']}")
                    if result['stderr']:
                        print(f"STDERR:\n{result['stderr']}")
                    print(f"Return Code: {result['returncode']}")
                    print(f"Success: {result['success']}")
                    print(f"----------------------")
                    if not result['success']:
                        print(f"Command executed but reported failure (return code {result['returncode']}).")
                        # This still means the OS action itself "succeeded" in running the command
                else:
                    print("Operation cancelled by user.")
                    return False # Cancelled
            else:
                print("Error: 'command_string' not provided for run_command action.")
                return False

        elif action_name == "list_directory":
            dir_path = params.get("path")
            if dir_path:
                items = os_operations.list_directory(dir_path)
                print(f"--- Directory Listing: {dir_path} ---")
                if items:
                    for item in items:
                        print(item)
                else:
                    print("(Directory is empty)")
                print(f"-----------------------------------")
            else:
                print("Error: 'path' not provided for list_directory action.")
                return False

        elif action_name == "create_directory":
            dir_path = params.get("path")
            if dir_path:
                os_operations.create_directory(dir_path)
                print(f"Successfully created directory (or it already existed): {dir_path}")
            else:
                print("Error: 'path' not provided for create_directory action.")
                return False

        elif action_name == "generate_delete_command":
            del_path = params.get("path")
            is_recursive = params.get("is_recursive", False)
            is_forced = params.get("is_forced", False)
            if del_path:
                command = os_operations.generate_delete_command(del_path, is_recursive, is_forced)
                print(f"Generated delete command: {command}")
                print("IMPORTANT: This command has NOT been executed. ")
                print("To execute, copy the command and use the 'run_command' action.")
            else:
                print("Error: 'path' not provided for generate_delete_command action.")
                return False

        elif action_name == "find_files":
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
                    for item in found_items:
                        print(item)
                else:
                    print("(No items found matching criteria)")
                print("---------------------------------------------------")
                # This action is considered successful even if no items are found, as long as the search itself didn't error.
            except os_operations.DirectoryNotFoundError as e: # Catch specific errors from find_files
                print(f"Error finding files: {e}")
                return False
            except os_operations.OperationError as e: # Catch specific errors from find_files
                print(f"OS Operation Error during find: {e}")
                return False
            # Generic OS operation errors and others are caught by the main try-except in this function.

        else:
            # This case should ideally not be reached if called from main dispatcher
            print(f"Error: Unknown OS action '{action_name}' in _execute_os_action.")
            return False

        return True # Assume success if no specific error or return False occurred

    except os_operations.FileNotFoundError as e:
        print(f"Error: {e}")
        return False
    except os_operations.DirectoryNotFoundError as e:
        print(f"Error: {e}")
        return False
    except os_operations.CommandExecutionError as e:
        print(f"Command Execution Error: {e.stdout}\n{e.stderr}")
        return False
    except os_operations.OperationError as e:
        print(f"OS Operation Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during OS action execution: {e}")
        return False


def main():
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
