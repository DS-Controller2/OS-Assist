# OS-Assist: Your Command-Line AI Companion

OS-Assist is an experimental OS-level assistant that uses a Large Language Model (LLM) to help you perform various tasks directly from your command line. You can interact with your file system, run terminal commands, find files, and even create 'Quick Actions' to automate frequent sequences of operations—all using natural language.

**Current Version:** Alpha (Experimental - Use with Extreme Caution)

## Table of Contents

- [Core Features](#core-features)
- [Important Security Warning](#important-security-warning)
- [Setup and Configuration](#setup-and-configuration)
  - [1. Dependencies](#1-dependencies)
  - [2. API Provider (OpenRouter)](#2-api-provider-openrouter)
  - [3. Configuration File (`config.json`)](#3-configuration-file-configjson)
  - [4. Quick Actions File (`quick_actions.json`)](#4-quick-actions-file-quick_actionsjson)
- [How to Run](#how-to-run)
- [Interacting with the Assistant](#interacting-with-the-assistant)
  - [Basic OS Operations](#basic-os-operations)
  - [Quick Actions](#quick-actions)
- [Cross-Platform Considerations](#cross-platform-considerations)
- [LLM Interaction Details](#llm-interaction-details)
- [Troubleshooting](#troubleshooting)

## Core Features

*   **Natural Language Interface:** Talk to your OS in plain English.
*   **File System Operations:** Read files, write to files, list directory contents, create directories.
*   **File Finding:** Search for files and directories based on patterns, type, and recursion.
*   **Terminal Command Execution:** Run shell commands directly.
*   **OS-Aware Delete Command Generation:** Generate delete commands appropriate for your OS (Linux, macOS, Windows) for review before potential execution.
*   **Quick Actions:** Define, save, list, execute, and delete custom multi-step command sequences.
*   **Security Confirmations:** Prompts for confirmation before executing potentially destructive actions like writing files or running commands.
*   **Command Blacklist:** A basic blacklist helps prevent execution of some highly dangerous commands.
*   **OS-Informed LLM:** The assistant informs the LLM about your current operating system to help it tailor suggestions, especially for terminal commands.

## IMPORTANT SECURITY WARNING

**USE OS-ASSIST AT YOUR OWN RISK. THIS IS EXPERIMENTAL SOFTWARE.**

Giving an LLM direct access to your operating system is **inherently risky**. While OS-Assist includes safety features like confirmation prompts, a command blacklist, and OS-aware command generation, these are not foolproof.

*   **Always carefully review the commands and file paths** that the assistant proposes before confirming execution, especially for `run_command` and `write_file`.
*   **Do not run this assistant with elevated privileges (e.g., as root or using `sudo`)** unless you are an expert and fully understand the implications.
*   The command blacklist is a basic safeguard and may not cover all dangerous commands or variations.
*   Maliciously crafted input or unexpected LLM behavior could potentially lead to unintended system modifications, data loss, or security vulnerabilities.

**By using OS-Assist, you acknowledge these risks and agree to take full responsibility for any outcomes.**

## Setup and Configuration

### 1. Dependencies

Ensure you have Python 3.8+ installed. Then, install the required Python dependencies:

```bash
pip install -r requirements.txt
```

(`requirements.txt` includes `openai` and `requests`.)

### 2. API Provider (OpenRouter)

OS-Assist uses [OpenRouter](https://openrouter.ai/) to connect to various LLMs. You'll need an OpenRouter API key.

### 3. Configuration File (`config.json`)

Create a `config.json` file in the project's root directory (`os_assist/config.json`). Here's a template:

```json
{
  "api_providers": {
    "openrouter": {
      "api_key_env_var": "OPENROUTER_API_KEY",
      "api_key": null,
      "default_route": "mistralai/mistral-7b-instruct",
      "timeout_seconds": 30
    }
  },
  "logging": {
    "level": "INFO"
  }
}
```

**Configuration Options:**

*   `api_key_env_var`: (Recommended) Set this to the name of an environment variable that holds your OpenRouter API key (e.g., `"OPENROUTER_API_KEY"`). The application will then read the key from this environment variable.
*   `api_key`: (Alternative) You can paste your OpenRouter API key directly here (e.g., `"sk-or-v1-..."`). **This is less secure**, especially if you share your `config.json`.
*   `default_route`: (Optional) Specify a default LLM model to use (e.g., `"mistralai/mistral-7b-instruct"`, `"openai/gpt-4o"`).
*   `timeout_seconds`: (Optional) API request timeout in seconds (default: 30).

### 4. Quick Actions File (`quick_actions.json`)

A file named `quick_actions.json` will be automatically created in the `os_assist/data/` directory when you first save a quick action. You typically don't need to edit this file manually.

## How to Run

Navigate to the project's root directory (`os_assist/`) in your terminal and run:

```bash
python src/main.py
```

Upon starting, the assistant will print the detected Operating System (e.g., Linux, Windows, macOS).

## Interacting with the Assistant

Once running, OS-Assist will prompt you for commands with `> `.

### Basic OS Operations

Here are examples of what you can ask the assistant to do:

*   **Read a file:**
    *   `> Read the file /path/to/my/document.txt`
    *   `> Show me the contents of notes.md`
*   **Write to a file:** (You will be asked for confirmation)
    *   `> Write 'Hello, World!' to /tmp/greeting.txt`
    *   `> Create a new file named 'report.md' with the content '# Sales Report'`
*   **Find files or directories:**
    *   `> Find all text files in /home/user/documents recursively` (translates to `find_files` with `name_pattern='*.txt'`, `file_type='file'`, `is_recursive=True`)
    *   `> Find all folders named 'backup' inside /var/logs, not recursive`
    *   `> Search for any file starting with 'data_' in the current directory`
*   **Run a terminal command:** (You will be asked for confirmation after blacklist check)
    *   `> Run the command 'ls -la /tmp'`
    *   `> What's my current directory?` (might translate to `pwd` on Linux/macOS or `cd` on Windows)
    *   `> Execute 'python my_script.py --input data.csv'`
    *   *See [Cross-Platform Considerations](#cross-platform-considerations) for more on commands.*
*   **List directory contents:**
    *   `> List files in /home/user/images`
    *   `> Show me what's in the current project's data folder`
*   **Create a directory:**
    *   `> Create a directory named 'my_new_folder' in /tmp`
    *   `> Make a new folder called 'archive' inside 'documents'`
*   **Generate a delete command:** (This only *generates* the command; it does not run it. The command generated will be OS-specific.)
    *   `> Generate the command to delete the file /tmp/old_file.txt`
    *   `> How do I delete the folder /tmp/junk_folder recursively?`
    *   The assistant will output the OS-appropriate command (e.g., `rm "/tmp/old_file.txt"` on Linux, `del "C:\tmp\old_file.txt"` on Windows). You can then choose to copy this command and ask the assistant to run it using the `run_command` action if you are sure.

### Quick Actions

Quick Actions allow you to save and reuse sequences of OS operations.

*   **Save a Quick Action:**
    *   `> Save a quick action named 'setup_python_project'. It should first create a directory '~/my_py_project', then create a file '~/my_py_project/main.py' with the content '# My Python script', and finally create '~/my_py_project/README.md' with '# Project Title'.`
*   **List Quick Actions:**
    *   `> List all my quick actions`
*   **Execute a Quick Action:** (Each sensitive step within the quick action will require confirmation)
    *   `> Execute the quick action 'setup_python_project'`
*   **Delete a Quick Action:**
    *   `> Delete the quick action 'old_action_name'`

## Cross-Platform Considerations

OS-Assist aims to provide a degree of cross-platform compatibility:

*   **OS Detection:** The assistant detects your OS (Linux, macOS, Windows) at startup and informs the LLM. This helps the LLM tailor suggestions for `run_command`.
*   **Path Handling:** Uses `pathlib` internally, which handles OS-specific path formats.
*   **`generate_delete_command`:** This command is OS-aware and will generate `rm`-style commands for Linux/macOS and `del`/`rmdir` commands for Windows.
*   **`run_command`:** While the LLM is informed of your OS, the `run_command` action executes the given string directly in your system's shell.
    *   **Be Mindful:** If you ask the LLM to formulate a complex shell command, ensure it's appropriate for your OS. Basic commands might be similar, but many utilities and syntax differ.
    *   The assistant primarily supports Linux-style commands for its direct operations, but the `run_command` action is flexible if the LLM provides the correct command string for your OS.

## LLM Interaction Details

OS-Assist sends your natural language command, along with a system prompt detailing available functions and the detected OS, to an LLM (via OpenRouter). The LLM's task is to translate your request into a structured JSON object specifying an `action` (like `read_file`, `run_command`, `find_files`) and its `parameters`. The Python application then parses this JSON and executes the corresponding operation, including any necessary security checks and confirmations.

## Troubleshooting

*   **API Key Issues:** Ensure your OpenRouter API key is correctly set in `config.json` or as an environment variable (`OPENROUTER_API_KEY` by default).
*   **LLM Not Understanding:** If the assistant doesn't understand your request or makes mistakes:
    *   Try rephrasing your command to be more specific and clear.
    *   Break down complex requests into simpler steps.
    *   The LLM's ability to translate commands depends on the model chosen in `config.json`, the clarity of your instructions, and its knowledge of the detected OS.
*   **Command Blacklisted / Confirmation Denied:** If a command is blacklisted or you deny confirmation, the operation will not proceed. This is a safety feature.

---
*This is experimental software. Use with caution and at your own risk.*
