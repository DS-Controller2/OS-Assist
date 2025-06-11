import json
import os
from pathlib import Path

CONFIG_FILE_NAME = "config.json"
# Assume the script is in os_assist/src, so two parents up is the project root.
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / CONFIG_FILE_NAME

class ConfigManager:
    def __init__(self, config_path=None):
        self.config_path = config_path if config_path else DEFAULT_CONFIG_PATH
        self.config_data = None
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                self.config_data = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Configuration file not found at {self.config_path}. Using default or empty config.")
            self.config_data = {}  # Or load defaults if you have them
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.config_path}. Check for syntax errors.")
            self.config_data = {} # Or raise an error

    def get_config_value(self, key_path, default=None):
        """
        Retrieves a value from the loaded configuration using a dot-separated key path.
        Example: get_config_value("api_providers.openrouter.timeout_seconds")
        """
        if not self.config_data:
            return default

        keys = key_path.split('.')
        value = self.config_data
        try:
            for key in keys:
                value = value[key]
            return value
        except (TypeError, KeyError):
            return default

    def get_openrouter_config(self):
        openrouter_settings = self.get_config_value("api_providers.openrouter", {})
        if not openrouter_settings: # if the key itself is missing or config is empty
            return {
                "api_key": None,
                "default_route": None,
                "timeout_seconds": 30 # A sensible default
            }

        api_key = None
        api_key_env_var = openrouter_settings.get("api_key_env_var")

        if api_key_env_var:
            api_key = os.getenv(api_key_env_var)

        if not api_key and "api_key" in openrouter_settings:
            api_key = openrouter_settings.get("api_key")

        # Ensure required keys exist, providing defaults if necessary
        return {
            "api_key": api_key,
            "default_route": openrouter_settings.get("default_route"),
            "timeout_seconds": openrouter_settings.get("timeout_seconds", 30)
        }

    def get_logging_config(self):
        return self.get_config_value("logging", {"level": "INFO"})

# Example usage (optional, can be removed or put under if __name__ == "__main__":)
if __name__ == "__main__":
    manager = ConfigManager()
    print(f"Config loaded from: {manager.config_path}")

    openrouter_config = manager.get_openrouter_config()
    print("\nOpenRouter Config:")
    if openrouter_config:
        print(f"  API Key: {'*' * 10 if openrouter_config.get('api_key') else 'Not set'}")
        print(f"  Default Route: {openrouter_config.get('default_route')}")
        print(f"  Timeout (seconds): {openrouter_config.get('timeout_seconds')}")
    else:
        print("  OpenRouter configuration not found.")

    logging_config = manager.get_logging_config()
    print("\nLogging Config:")
    if logging_config:
        print(f"  Level: {logging_config.get('level')}")
    else:
        print("  Logging configuration not found.")

    # Test with a non-existent config file
    print("\nTesting with a non-existent config path:")
    non_existent_manager = ConfigManager(config_path=Path("non_existent_config.json"))
    print(f"  OpenRouter API Key: {non_existent_manager.get_openrouter_config().get('api_key')}")

    # Test with an invalid JSON file (manual creation needed for this test)
    # Create a file named 'invalid_config.json' with content like: {"api_providers": {"openrouter": "invalid_json"
    # invalid_manager = ConfigManager(config_path=Path("invalid_config.json"))
    # print(f"\nInvalid JSON test: {invalid_manager.get_openrouter_config()}")
