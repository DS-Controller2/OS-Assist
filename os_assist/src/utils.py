import platform

def get_current_os() -> str:
    """
    Detects the current operating system and returns a simplified name.

    Returns:
        A string: "windows", "linux", "macos", or "unknown".
    """
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    elif "linux" in system:
        return "linux"
    elif "darwin" in system: # macOS system name is 'darwin'
        return "macos"
    else:
        return "unknown"

if __name__ == '__main__':
    # Simple test print
    current_os = get_current_os()
    print(f"Detected OS: {current_os}")
    # You can add more assertions here if run as part of a manual test
    assert current_os in ["windows", "linux", "macos", "unknown"]
