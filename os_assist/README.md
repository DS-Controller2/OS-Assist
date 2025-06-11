# os-assist
An OS-level LLM assistant to help with various tasks.

## API Provider Configuration

### OpenRouter

`os-assist` uses [OpenRouter](https://openrouter.ai/) to connect to a wide variety of Large Language Models (LLMs). To use OpenRouter, you need to configure your API key and preferences in the `os_assist/config.json` file.

The relevant section in `config.json` looks like this:

```json
{
  "api_providers": {
    "openrouter": {
      "api_key_env_var": "OPENROUTER_API_KEY",
      "api_key": null,
      "default_route": "mistralai/mistral-7b-instruct",
      "timeout_seconds": 30
    }
  }
  // ... other configs like "logging" might be present
}
```

**Configuration Options:**

*   `api_key_env_var`: (Recommended) Specify the name of the environment variable that holds your OpenRouter API key. For example, if you set it to `"OPENROUTER_API_KEY"`, the application will look for an environment variable named `OPENROUTER_API_KEY`. This is the most secure method.
*   `api_key`: (Alternative) You can paste your OpenRouter API key directly into this field (e.g., `"sk-or-v1-..."`). However, this is less secure, especially if you commit `config.json` to a shared repository. If `api_key_env_var` is set and the environment variable is found, this `api_key` field will be ignored.
*   `default_route`: (Optional) Set a default model identifier (e.g., `"mistralai/mistral-7b-instruct"`, `"openai/gpt-4o"`) that the assistant will use if no specific model is requested for a task.
*   `timeout_seconds`: (Optional) The number of seconds to wait for a response from the OpenRouter API before timing out. Defaults to 30 if not specified.

**Dependencies:**

Ensure you have installed the required Python dependencies by running the following command in your project's root directory:
```bash
pip install -r requirements.txt
```
