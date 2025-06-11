# OS-Assist: Your Command-Line AI Companion

OS-Assist is an experimental OS-level assistant that uses a Large Language Model (LLM) to help you perform various tasks directly from your command line. You can interact with your file system, run terminal commands, and even create 'Quick Actions' to automate frequent sequences of operations—all using natural language.

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
- [LLM Interaction Details](#llm-interaction-details)
- [Troubleshooting](#troubleshooting)

## Core Features

*   **Natural Language Interface:** Talk to your OS in plain English.
*   **File System Operations:** Read files, write to files, list directory contents, create directories.
*   **Terminal Command Execution:** Run shell commands directly.
*   **Safe Deletion:** Generate delete commands for review before potential execution.
*   **Quick Actions:** Define, save, list, execute, and delete custom multi-step command sequences.
*   **Security Confirmations:** Prompts for confirmation before executing potentially destructive actions like writing files or running commands.
*   **Command Blacklist:** A basic blacklist helps prevent execution of some highly dangerous commands.

## IMPORTANT SECURITY WARNING

**USE OS-ASSIST AT YOUR OWN RISK. THIS IS EXPERIMENTAL SOFTWARE.**

Giving an LLM direct access to your operating system is **inherently risky**. While OS-Assist includes safety features like confirmation prompts and a command blacklist, these are not foolproof.

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
*   **Run a terminal command:** (You will be asked for confirmation after blacklist check)
    *   `> Run the command 'ls -la /tmp'`
    *   `> What's my current directory?` (might translate to `pwd`)
    *   `> Execute 'python my_script.py --input data.csv'`
*   **List directory contents:**
    *   `> List files in /home/user/images`
    *   `> Show me what's in the current project's data folder`
*   **Create a directory:**
    *   `> Create a directory named 'my_new_folder' in /tmp`
    *   `> Make a new folder called 'archive' inside 'documents'`
*   **Generate a delete command:** (This only *generates* the command; it does not run it)
    *   `> Generate the command to delete the file /tmp/old_file.txt`
    *   `> How do I delete the folder /tmp/junk_folder recursively?`
    *   The assistant will output the command (e.g., `rm "/tmp/old_file.txt"`). You can then choose to copy this command and ask the assistant to run it using the `run_command` action if you are sure.

### Quick Actions

Quick Actions allow you to save and reuse sequences of OS operations.

*   **Save a Quick Action:**
    *   `> Save a quick action named 'setup_python_project'. It should first create a directory '~/my_py_project', then create a file '~/my_py_project/main.py' with the content '# My Python script', and finally create '~/my_py_project/README.md' with '# Project Title'.`
    *   The LLM will translate this into a `save_quick_action` command with the specified name and a list of action objects.
*   **List Quick Actions:**
    *   `> List all my quick actions`
    *   `> Show me the available quick actions`
*   **Execute a Quick Action:** (Each step within the quick action that is destructive will require its own confirmation if not already confirmed via a higher-level context, though current implementation confirms each sensitive OS op individually).
    *   `> Execute the quick action 'setup_python_project'`
    *   `> Run 'my_daily_backup'`
*   **Delete a Quick Action:**
    *   `> Delete the quick action 'old_action_name'`
    *   `> Remove 'setup_python_project' from my quick actions`

## LLM Interaction Details

OS-Assist sends your natural language command, along with a system prompt detailing available functions, to an LLM (via OpenRouter). The LLM's task is to translate your request into a structured JSON object specifying an `action` (like `read_file`, `run_command`, `save_quick_action`) and its `parameters`. The Python application then parses this JSON and executes the corresponding operation, including any necessary security checks and confirmations.

## Troubleshooting

*   **API Key Issues:** Ensure your OpenRouter API key is correctly set in `config.json` or as an environment variable (`OPENROUTER_API_KEY` by default).
*   **LLM Not Understanding:** If the assistant doesn't understand your request or makes mistakes:
    *   Try rephrasing your command to be more specific and clear.
    *   Break down complex requests into simpler steps.
    *   The LLM's ability to translate commands depends on the model chosen in `config.json` and the clarity of your instructions.
*   **Command Blacklisted / Confirmation Denied:** If a command is blacklisted or you deny confirmation, the operation will not proceed. This is a safety feature.

---
*This is experimental software. Use with caution and at your own risk.*
