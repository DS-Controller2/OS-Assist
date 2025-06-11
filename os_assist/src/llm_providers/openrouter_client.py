import os
import requests # For list_models
from openai import OpenAI, APIError # APIError for error handling

# Attempt to import ConfigManager relative to the 'src' directory
try:
    from ..config_manager import ConfigManager
except ImportError:
    # Fallback for scenarios where the script might be run directly
    # or the above relative import fails.
    # This assumes 'os_assist' is in PYTHONPATH or the CWD.
    from src.config_manager import ConfigManager


class OpenRouterProvider:
    BASE_URL = "https://openrouter.ai/api/v1"
    # Recommended headers by OpenRouter
    DEFAULT_HTTP_REFERER = "http://localhost/os-assist" # Replace with your actual site URL if deployed
    DEFAULT_X_TITLE = "OS-Assist" # Replace with your actual project name

    def __init__(self, config_manager=None):
        if config_manager is None:
            # If running this file directly for testing, config.json should be in os_assist/
            # Adjust path if necessary based on expected execution context.
            # Assuming config_manager.py is in os_assist/src and config.json is in os_assist/
            # The default ConfigManager path is: Path(__file__).resolve().parent.parent / "config.json"
            # If openrouter_client.py is in os_assist/src/llm_providers/, then parent.parent is os_assist/src/
            # So we need to go one more level up for the project root where config.json is.
            project_root_for_config = Path(__file__).resolve().parent.parent.parent
            self.config_manager = ConfigManager(config_path=project_root_for_config / "config.json")
        else:
            self.config_manager = config_manager

        openrouter_config = self.config_manager.get_openrouter_config()

        self.api_key = openrouter_config.get("api_key")
        self.default_route = openrouter_config.get("default_route")
        self.timeout_seconds = openrouter_config.get("timeout_seconds", 30)

        if not self.api_key:
            # Consider logging a warning or raising an error if API key is crucial
            print("Warning: OpenRouter API key is not set. Some operations may fail.")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.BASE_URL,
            timeout=self.timeout_seconds,
        )

        # Store headers for use in requests
        self.extra_headers = {
            "HTTP-Referer": self.DEFAULT_HTTP_REFERER,
            "X-Title": self.DEFAULT_X_TITLE,
        }
        if self.api_key:
            self.extra_headers["Authorization"] = f"Bearer {self.api_key}"


    def generate_chat_completion(self, messages: list, model: str = None, **kwargs) -> str | None:
        """
        Generates a chat completion using the OpenRouter API.

        Args:
            messages: A list of message dictionaries, e.g., [{"role": "user", "content": "Hello"}].
            model: The model to use (e.g., "mistralai/mistral-7b-instruct").
                   If None, uses default_route from config.
            **kwargs: Additional keyword arguments to pass to chat.completions.create().

        Returns:
            The content of the first choice's message, or None if an error occurs.
        """
        resolved_model = model if model else self.default_route
        if not resolved_model:
            print("Error: No model specified and no default_route configured.")
            # Consider raising a ValueError here:
            # raise ValueError("No model specified and no default_route configured.")
            return None

        try:
            completion = self.client.chat.completions.create(
                model=resolved_model,
                messages=messages,
                extra_headers=self.extra_headers, # Pass stored headers
                **kwargs
            )
            return completion.choices[0].message.content
        except APIError as e:
            print(f"OpenRouter API Error: {e}")
            # You might want to handle different types of APIErrors specifically
            # For example, authentication errors, rate limit errors, etc.
            return None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None

    def list_models(self) -> list:
        """
        Fetches the list of available models from OpenRouter.
        Requires the 'requests' library.
        """
        if not self.api_key:
            print("Error: API key is required to list models from OpenRouter.")
            return []

        try:
            response = requests.get(
                f"{self.BASE_URL}/models",
                headers=self.extra_headers # Use the same headers, includes Authorization
            )
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            models_data = response.json()
            return models_data.get("data", []) # The models are usually in a 'data' field
        except requests.exceptions.RequestException as e:
            print(f"Error fetching models from OpenRouter: {e}")
            return []
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response from OpenRouter /models endpoint.")
            return []

# Example Usage (for testing purposes)
if __name__ == "__main__":
    # This assumes that you have a config.json in the os_assist/ directory
    # and OPENROUTER_API_KEY environment variable is set if api_key is null in config.json

    # Create a dummy config.json in os_assist/ for this test if it doesn't exist
    # Or ensure your ConfigManager can find it.
    # The ConfigManager by default looks for 'config.json' in the project root (os_assist/)

    # Adjust path for ConfigManager if running this script directly
    from pathlib import Path

    # Assuming this script (openrouter_client.py) is in os_assist/src/llm_providers
    # and config.json is in os_assist/
    # The ConfigManager default path is relative to its own location.
    # config_manager.py is in os_assist/src
    # DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / CONFIG_FILE_NAME
    # So, ConfigManager() will look for os_assist/config.json if run from os_assist/src or below

    print("Attempting to initialize OpenRouterProvider...")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Path of this script: {Path(__file__).resolve()}")

    # Create a ConfigManager instance. It should find os_assist/config.json
    # The default path in ConfigManager is: Path(__file__).resolve().parent.parent / "config.json"
    # If config_manager.py is in os_assist/src, this becomes os_assist/config.json
    try:
        # config_manager_instance = ConfigManager() # This should work if CWD or PYTHONPATH is os_assist
        # More robustly:
        script_dir = Path(__file__).resolve().parent # os_assist/src/llm_providers
        project_root = script_dir.parent.parent # os_assist
        config_file_path = project_root / "config.json"

        if not config_file_path.exists():
            print(f"WARNING: Test config file not found at {config_file_path}")
            print("Please create os_assist/config.json for testing.")
            # Create a minimal config for the test to proceed if it doesn't exist
            with open(config_file_path, 'w') as f:
                json.dump({
                    "api_providers": {
                        "openrouter": {
                            "api_key_env_var": "OPENROUTER_API_KEY",
                            "api_key": None, # Expecting env var
                            "default_route": "mistralai/mistral-7b-instruct",
                            "timeout_seconds": 20
                        }
                    }
                }, f, indent=2)
            print(f"Created minimal {config_file_path} for testing.")

        config_manager_instance = ConfigManager(config_path=config_file_path)

        print(f"ConfigManager using config file: {config_manager_instance.config_path}")

        # Check if API key is actually loaded (useful for debugging)
        # temp_or_config = config_manager_instance.get_openrouter_config()
        # print(f"Loaded OpenRouter API Key for test: {'Set' if temp_or_config.get('api_key') else 'Not Set'}")
        # print(f"OPENROUTER_API_KEY env var: {os.getenv('OPENROUTER_API_KEY')}")


        provider = OpenRouterProvider(config_manager=config_manager_instance)

        if not provider.api_key:
            print("\nWARNING: OpenRouter API key is not configured. Live tests will likely fail.")
            print("Please ensure OPENROUTER_API_KEY environment variable is set or api_key is in config.json.")

        print("\nTesting list_models():")
        models = provider.list_models()
        if models:
            print(f"Found {len(models)} models. First few:")
            for model_info in models[:3]:
                print(f"  ID: {model_info.get('id')}, Name: {model_info.get('name')}")
        else:
            print("No models listed or an error occurred.")

        print("\nTesting generate_chat_completion():")
        if provider.api_key: # Only attempt if API key is present
            messages = [
                {"role": "user", "content": "What is the capital of France?"}
            ]
            # Using a known free model for testing if default_route isn't set or is a paid model
            test_model = provider.default_route or "mistralai/mistral-7b-instruct-v0.1"
            # Some models might require specific formatting or might not be available.
            # Using a generally available model:
            # test_model = "gryphe/mythomist-7b:free" # Example of a free model if default is not free

            print(f"Using model for test: {test_model}")

            try:
                response_content = provider.generate_chat_completion(messages, model=test_model)
                if response_content:
                    print(f"Chat completion response: {response_content}")
                else:
                    print("Chat completion failed or returned no content.")
            except Exception as e:
                print(f"Error during generate_chat_completion test: {e}")
        else:
            print("Skipping generate_chat_completion test as API key is not set.")

    except ImportError as e:
        print(f"ImportError during setup: {e}")
        print("Ensure that the os_assist package is correctly structured and in PYTHONPATH if necessary.")
    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")
