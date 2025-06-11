import os
import subprocess
import shutil
from pathlib import Path

from os_assist.src.utils import get_current_os

# Define custom exceptions for more specific error handling
class OperationError(Exception):
    """Base class for errors in this module."""
    pass

class FileNotFoundError(OperationError):
    """Custom exception for file not found."""
    pass

class DirectoryNotFoundError(OperationError):
    """Custom exception for directory not found."""
    pass

class CommandExecutionError(OperationError):
    """Custom exception for errors during command execution."""
    def __init__(self, message, stdout, stderr, returncode):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

def read_file(filepath: str) -> str:
    """
    Reads the content of a file.

    Args:
        filepath: The path to the file.

    Returns:
        The content of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        OperationError: For other OS-related errors.
    """
    try:
        path = Path(filepath).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"File not found at: {filepath}")
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError: # Re-raise custom FileNotFoundError
        raise
    except IOError as e:
        raise OperationError(f"Error reading file {filepath}: {e}")
    except Exception as e:
        raise OperationError(f"An unexpected error occurred while reading file {filepath}: {e}")

def write_file(filepath: str, content: str, mode: str = "overwrite") -> None:
    """
    Writes content to a file. Creates the file if it doesn't exist.
    Parent directories will be created if they don't exist.

    Args:
        filepath: The path to the file.
        content: The content to write to the file.
        mode: "overwrite" to overwrite the file (default), "append" to append to the file.

    Raises:
        OperationError: For OS-related errors during writing or if an invalid mode is somehow passed.
    """
    try:
        path = Path(filepath).resolve()
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        open_mode = ''
        if mode == "append":
            open_mode = 'a'
        elif mode == "overwrite":
            open_mode = 'w'
        else:
            # This case should ideally be handled by the caller, but as a fallback:
            raise OperationError(f"Invalid mode '{mode}' specified for write_file. Must be 'overwrite' or 'append'.")

        with open(path, open_mode, encoding='utf-8') as f:
            f.write(content)
    except IOError as e:
        raise OperationError(f"Error writing to file {filepath} (mode: {mode}): {e}")
    except Exception as e:
        raise OperationError(f"An unexpected error occurred while writing to file {filepath}: {e}")

def run_command(command_string: str) -> dict:
    """
    Executes a terminal command and captures its output.

    Args:
        command_string: The command to execute.

    Returns:
        A dictionary containing:
            'stdout': The standard output of the command.
            'stderr': The standard error of the command.
            'returncode': The return code of the command.
            'success': True if return code is 0, False otherwise.

    Raises:
        CommandExecutionError: If the command execution fails fundamentally (e.g., command not found),
                               or if the command returns a non-zero exit code (optional, depending on desired strictness).
                               For now, it will return details even for non-zero exit codes, and 'success' field will indicate status.
    """
    try:
        process = subprocess.run(
            command_string,
            shell=True,        # Be cautious with shell=True due to security risks if command_string is from untrusted input
            capture_output=True,
            text=True,
            check=False        # Do not raise CalledProcessError for non-zero exit codes, handle it manually
        )
        success = process.returncode == 0
        return {
            "stdout": process.stdout.strip(),
            "stderr": process.stderr.strip(),
            "returncode": process.returncode,
            "success": success,
        }
    except Exception as e:
        raise CommandExecutionError(
            f"Failed to execute command '{command_string}': {e}",
            stdout="",
            stderr=str(e),
            returncode=-1 # Indicate a failure to even run the command
        )


def list_directory(path_str: str) -> list[str]:
    """
    Lists the contents of a directory.

    Args:
        path_str: The path to the directory.

    Returns:
        A list of names of files and subdirectories.

    Raises:
        DirectoryNotFoundError: If the directory does not exist or is not a directory.
        OperationError: For other OS-related errors.
    """
    try:
        path = Path(path_str).resolve()
        if not path.exists():
            raise DirectoryNotFoundError(f"Path not found: {path_str}")
        if not path.is_dir():
            raise DirectoryNotFoundError(f"Path is not a directory: {path_str}")
        return sorted(os.listdir(path))
    except DirectoryNotFoundError: # Re-raise custom DirectoryNotFoundError
        raise
    except OSError as e:
        raise OperationError(f"Error listing directory {path_str}: {e}")
    except Exception as e:
        raise OperationError(f"An unexpected error occurred while listing directory {path_str}: {e}")

def create_directory(path_str: str) -> None:
    """
    Creates a directory. Parent directories will also be created if they don't exist.
    If the directory already exists, it does nothing.

    Args:
        path_str: The path to the directory to create.

    Raises:
        OperationError: If the directory creation fails for reasons other than it already existing.
    """
    try:
        path = Path(path_str).resolve()
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OperationError(f"Error creating directory {path_str}: {e}")
    except Exception as e:
        raise OperationError(f"An unexpected error occurred while creating directory {path_str}: {e}")

def generate_delete_command(path_str: str, is_recursive: bool = False, is_forced: bool = False) -> str:
    """
    Generates a platform-appropriate command string for deleting a file or directory.
    This function *generates* the command, it does not execute it.
    The actual execution should be done via run_command, ideally after user confirmation.

    Args:
        path_str: The path to the file or directory to be deleted.
        is_recursive: True if a directory should be deleted recursively.
                      Ignored if the path is a file.
        is_forced: True to attempt to force deletion (e.g., -f option).

    Returns:
        A string representing the command to delete the path.

    Raises:
        FileNotFoundError: If the path does not exist.
        OperationError: If the path is a directory and is_recursive is False and the directory is not empty.
    """
    path = Path(path_str).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Cannot generate delete command: Path '{path_str}' does not exist.")

    current_os = get_current_os()

    if current_os == "windows":
        if path.is_dir():
            if not is_recursive:
                try:
                    if list(path.iterdir()): # Check if directory is empty
                        raise OperationError(
                            f"Cannot generate non-recursive delete command for non-empty directory '{path_str}'. "
                            "Use is_recursive=True for recursive deletion."
                        )
                    # For an empty directory on Windows
                    return f'rmdir "{path}"'
                except OSError as e:
                    raise OperationError(f"Could not determine if directory '{path_str}' is empty: {e}")
            else: # Recursive directory deletion for Windows
                command_parts = ["rmdir"]
                if is_forced: # /q implies quiet, similar to force by not asking for confirmation
                    command_parts.append("/q")
                command_parts.append("/s")
                command_parts.append(f'"{path}"')
                return " ".join(command_parts)
        else: # File deletion for Windows
            # 'del' command on Windows doesn't have a recursive flag.
            # is_forced for 'del' might map to /f, but /f forces read-only files to be deleted.
            # For simplicity, we'll use a basic del. If needed, /f could be added.
            command_parts = ["del"]
            if is_forced: # Optional: add /f if precise "force" for read-only is desired
                 pass # Example: command_parts.append("/f")
            command_parts.append(f'"{path}"')
            return " ".join(command_parts)
    else: # Linux, macOS, unknown
        if path.is_dir() and not is_recursive:
            try:
                if list(path.iterdir()): # Check if directory is empty
                    raise OperationError(
                        f"Cannot generate non-recursive delete command for non-empty directory '{path_str}'. "
                        "Use is_recursive=True for recursive deletion."
                    )
            except OSError as e: # Handle cases where path.iterdir() might fail (e.g. permissions)
                raise OperationError(f"Could not determine if directory '{path_str}' is empty: {e}")

        command_parts = ["rm"]
        if is_forced:
            command_parts.append("-f")
        if path.is_dir() and is_recursive:
            command_parts.append("-r")

        command_parts.append(f'"{path}"') # Quote the path to handle spaces
        return " ".join(command_parts)


def find_files(search_path: str, name_pattern: str = "*", file_type: str = "any", is_recursive: bool = True) -> list[str]:
    """
    Finds files or directories matching a pattern within a given path.

    Args:
        search_path: The directory path to start searching from.
        name_pattern: A glob-style pattern for the filename (e.g., "*.txt", "report_*.*"). Defaults to "*".
        file_type: Specifies what to find: 'file', 'directory', or 'any'. Defaults to 'any'.
        is_recursive: Whether to search subdirectories. Defaults to True.

    Returns:
        A sorted list of absolute string paths of found items.

    Raises:
        DirectoryNotFoundError: If search_path does not exist or is not a directory.
        OperationError: For other OS-related errors or invalid file_type.
    """
    base_path = Path(search_path).resolve()

    if not base_path.exists():
        raise DirectoryNotFoundError(f"Search path '{search_path}' does not exist.")
    if not base_path.is_dir():
        raise DirectoryNotFoundError(f"Search path '{search_path}' is not a directory.")

    if file_type not in ["file", "directory", "any"]:
        raise OperationError(f"Invalid file_type '{file_type}'. Must be 'file', 'directory', or 'any'.")

    results = []
    try:
        if is_recursive:
            glob_iterator = base_path.rglob(name_pattern)
        else:
            glob_iterator = base_path.glob(name_pattern)

        for path_object in glob_iterator:
            if file_type == "file" and path_object.is_file():
                results.append(str(path_object.resolve()))
            elif file_type == "directory" and path_object.is_dir():
                results.append(str(path_object.resolve()))
            elif file_type == "any":
                results.append(str(path_object.resolve()))

    except Exception as e:
        raise OperationError(f"Error during find operation in '{search_path}': {e}")

    return sorted(results)

if __name__ == '__main__':
    # Example Usage and Basic Tests
    test_dir = Path("_test_os_ops_temp_dir")
    file_to_read = test_dir / "read_me.txt"
    file_to_write = test_dir / "write_me.txt"
    dir_to_create = test_dir / "sub_dir"
    dir_to_list = test_dir
    file_to_delete = test_dir / "delete_me.txt"
    dir_to_delete_empty = test_dir / "empty_delete_dir"
    dir_to_delete_recursive = test_dir / "recursive_delete_dir"
    file_in_recursive_dir = dir_to_delete_recursive / "some_file.txt"

    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    print(f"Testing in progress in: {test_dir.resolve()}")

    try:
        print(f"\n--- Testing create_directory ---")
        create_directory(str(dir_to_create))
        print(f"Created directory: {dir_to_create}")
        assert dir_to_create.is_dir()
        create_directory(str(dir_to_create))
        print(f"Creating same directory again (should be fine).")
        assert dir_to_create.is_dir()

        print(f"\n--- Testing write_file ---")
        write_file(str(file_to_write), "Hello, OS Assistant!")
        print(f"Written to file: {file_to_write}")
        assert file_to_write.is_file()
        assert file_to_write.read_text() == "Hello, OS Assistant!"
        write_file(str(file_to_read), "Content for reading.")
        assert file_to_read.is_file()

        print(f"\n--- Testing read_file ---")
        content = read_file(str(file_to_read))
        print(f"Read from file {file_to_read}: '{content}'")
        assert content == "Content for reading."
        try:
            read_file(str(test_dir / "non_existent_file.txt"))
        except FileNotFoundError as e:
            print(f"Correctly caught FileNotFoundError: {e}")
        except Exception as e:
            print(f"Unexpected error during read_file non-existent test: {e}")
            assert False

        print(f"\n--- Testing list_directory ---")
        (test_dir / "item1.txt").touch()
        (test_dir / "item2.folder").mkdir()
        file_to_delete.write_text("delete this")
        dir_to_delete_empty.mkdir(exist_ok=True)
        dir_to_delete_recursive.mkdir(exist_ok=True)
        file_in_recursive_dir.write_text("do not lose me easily")

        all_items_in_test_dir = sorted([
            file_to_read.name, file_to_write.name, dir_to_create.name,
            "item1.txt", "item2.folder", file_to_delete.name,
            dir_to_delete_empty.name, dir_to_delete_recursive.name
        ])
        listed_items = list_directory(str(dir_to_list))
        print(f"Listed directory {dir_to_list}: {listed_items}")
        assert listed_items == all_items_in_test_dir

        print(f"\n--- Testing run_command ---")
        echo_result = run_command(f"echo Hello from command") # Simpler echo for cross-platform
        print(f"Echo command result: {echo_result}")
        assert echo_result["success"] is True
        # Exact stdout for echo varies too much (quotes, newlines). Check if it contains the core string.
        assert "Hello from command" in echo_result["stdout"]

        fail_result = run_command("non_existent_command_xyz123")
        print(f"Failed command result: {fail_result}")
        assert fail_result["success"] is False
        assert fail_result["returncode"] != 0

        list_files_cmd = "ls -a" if os.name != 'nt' else "dir /a"
        list_result = run_command(list_files_cmd)
        print(f"List files command ({list_files_cmd}) successful: {list_result['success']}")
        assert list_result["success"] is True

        print(f"\n--- Testing generate_delete_command ---")
        del_file_cmd = generate_delete_command(str(file_to_delete))
        print(f"Delete command for file '{file_to_delete.name}': {del_file_cmd}")
        assert f'"{(file_to_delete.resolve())}"' in del_file_cmd
        assert "rm" in del_file_cmd

        del_empty_dir_cmd = generate_delete_command(str(dir_to_delete_empty), is_recursive=False)
        print(f"Delete command for empty dir '{dir_to_delete_empty.name}' (non-recursive): {del_empty_dir_cmd}")
        assert f'"{(dir_to_delete_empty.resolve())}"' in del_empty_dir_cmd

        del_recursive_dir_cmd = generate_delete_command(str(dir_to_delete_recursive), is_recursive=True, is_forced=True)
        print(f"Delete command for recursive dir '{dir_to_delete_recursive.name}' (recursive, forced): {del_recursive_dir_cmd}")
        assert f'"{(dir_to_delete_recursive.resolve())}"' in del_recursive_dir_cmd
        assert "-r" in del_recursive_dir_cmd
        assert "-f" in del_recursive_dir_cmd

        try:
            generate_delete_command(str(dir_to_delete_recursive), is_recursive=False)
            assert False, "Should have raised OperationError for non-empty dir with is_recursive=False"
        except OperationError as e:
            print(f"Correctly caught error for non-empty dir, non-recursive: {e}")
        except Exception as e:
            print(f"Unexpected error for non-empty dir, non-recursive: {e}")
            assert False

        try:
            generate_delete_command(str(test_dir / "non_existent_for_delete.txt"))
            assert False, "Should have raised FileNotFoundError for non-existent path"
        except FileNotFoundError as e:
            print(f"Correctly caught FileNotFoundError for non-existent path: {e}")
        except Exception as e:
            print(f"Unexpected error for non-existent path delete command: {e}")
            assert False

        print(f"\n--- Testing Actual Deletion (using generated commands) ---")
        print(f"Attempting to delete file: {file_to_delete.name}")
        del_file_run_cmd = generate_delete_command(str(file_to_delete), is_forced=True)
        run_del_result = run_command(del_file_run_cmd)
        print(f"Result of deleting '{file_to_delete.name}': {run_del_result}")
        assert run_del_result["success"] is True
        assert not file_to_delete.exists()

        print(f"Attempting to delete directory recursively: {dir_to_delete_recursive.name}")
        del_rec_dir_run_cmd = generate_delete_command(str(dir_to_delete_recursive), is_recursive=True, is_forced=True)
        run_del_rec_result = run_command(del_rec_dir_run_cmd)
        print(f"Result of deleting '{dir_to_delete_recursive.name}' recursively: {run_del_rec_result}")
        assert run_del_rec_result["success"] is True
        assert not dir_to_delete_recursive.exists()

        print("\nAll os_operations tests seemed to pass basic checks.")

    except Exception as e:
        print(f"\nAn error occurred during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n--- Cleaning up ---")
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print(f"Removed temporary directory: {test_dir}")
