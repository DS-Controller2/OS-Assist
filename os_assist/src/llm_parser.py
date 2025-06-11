import json

class LLMResponseParseError(Exception):
    """Custom exception for errors during LLM response parsing."""
    pass

def parse_llm_response(json_string: str) -> dict:
    """
    Parses the JSON string response from the LLM.

    Args:
        json_string: The JSON string received from the LLM.

    Returns:
        A dictionary representing the parsed JSON action and parameters.

    Raises:
        LLMResponseParseError: If the string is not valid JSON, or if the expected
                               'action' key is missing.
    """
    try:
        if not json_string or not json_string.strip():
            raise LLMResponseParseError("LLM response is empty or whitespace.")

        # The LLM might sometimes include markdown code blocks around the JSON
        # Strip common markdown code block fences ```json ... ``` or ``` ... ```
        cleaned_json_string = json_string.strip()
        if cleaned_json_string.startswith("```json"):
            cleaned_json_string = cleaned_json_string[7:] # Remove ```json
            if cleaned_json_string.endswith("```"):
                cleaned_json_string = cleaned_json_string[:-3] # Remove ```
        elif cleaned_json_string.startswith("```") and cleaned_json_string.endswith("```"):
            cleaned_json_string = cleaned_json_string[3:-3]

        cleaned_json_string = cleaned_json_string.strip() # Ensure no leading/trailing whitespace remains

        parsed_response = json.loads(cleaned_json_string)
    except json.JSONDecodeError as e:
        raise LLMResponseParseError(f"Invalid JSON response from LLM: {e}. Response was: '{json_string[:200]}'...")
    except Exception as e:
        raise LLMResponseParseError(f"An unexpected error occurred during JSON parsing: {e}. Response was: '{json_string[:200]}'...")

    if not isinstance(parsed_response, dict):
        raise LLMResponseParseError("Parsed JSON is not a dictionary.")

    if "action" not in parsed_response:
        raise LLMResponseParseError("LLM response JSON missing 'action' key.")

    # Basic validation for parameters if present
    if "parameters" in parsed_response and not isinstance(parsed_response["parameters"], dict):
        raise LLMResponseParseError("'parameters' key exists but is not a dictionary.")

    # Ensure parameters is at least an empty dict if not present for actions that might expect it
    if "parameters" not in parsed_response:
        parsed_response["parameters"] = {} # Default to empty dict if no params sent

    return parsed_response

if __name__ == '__main__':
    print("--- Testing LLM Response Parser ---")

    # Test cases
    valid_responses = [
        ('{"action": "read_file", "parameters": {"filepath": "/path/to/file.txt"}}', {"action": "read_file", "parameters": {"filepath": "/path/to/file.txt"}}),
        ('  { "action": "run_command", "parameters": {"command_string": "ls -l"} }  ', {"action": "run_command", "parameters": {"command_string": "ls -l"}}),
        ('{"action": "clarify", "parameters": {"question": "Which file?"}}', {"action": "clarify", "parameters": {"question": "Which file?"}}),
        ('{"action": "no_params_action"}', {"action": "no_params_action", "parameters": {}}),
        ('```json\n{"action": "markdown_wrapped", "parameters": {"data": true}}\n```', {"action": "markdown_wrapped", "parameters": {"data": True}}),
        ('```\n{"action": "simple_markdown", "parameters": {}}\n```', {"action": "simple_markdown", "parameters": {}}),
        ('  ```json\n  { "action": "spaced_markdown", "parameters": {"value": 123} }\n  ```  ', {"action": "spaced_markdown", "parameters": {"value": 123}}),
    ]

    invalid_responses = [
        ("not a json string", LLMResponseParseError),
        ("{'action': 'read_file', 'parameters': {'filepath': '/path/to/file.txt'}}", LLMResponseParseError), # Single quotes
        ('{"parameters": {"filepath": "/path/to/file.txt"}}', LLMResponseParseError), # Missing action
        ('{"action": "read_file", "parameters": "not a dict"}', LLMResponseParseError), # Invalid parameters type
        ('[]', LLMResponseParseError), # Not a dictionary
        ('{"action": "read_file", "parameters": null}', LLMResponseParseError), # Parameters as null should be caught
        ('', LLMResponseParseError),
        ('   ', LLMResponseParseError),
        ('```json { "action": "unterminated_markdown" }', LLMResponseParseError), # Unterminated markdown
    ]

    print("\n--- Testing Valid Responses ---")
    for i, (json_str, expected_dict) in enumerate(valid_responses):
        try:
            result = parse_llm_response(json_str)
            assert result == expected_dict, f"Test {i} failed: Expected {expected_dict}, got {result}"
            print(f"Test {i} passed for: {json_str[:50]}...")
        except LLMResponseParseError as e:
            print(f"Test {i} failed unexpectedly for {json_str[:50]}...: {e}")
            assert False

    print("\n--- Testing Invalid Responses ---")
    for i, (json_str, expected_exception) in enumerate(invalid_responses):
        try:
            parse_llm_response(json_str)
            print(f"Test {i} failed: Expected {expected_exception} for {json_str[:50]}... but got no error.")
            assert False
        except expected_exception as e:
            print(f"Test {i} correctly caught {expected_exception.__name__} for: {json_str[:50]}... Error: {e}")
        except Exception as e:
            print(f"Test {i} failed: Expected {expected_exception} but got {type(e).__name__} for: {json_str[:50]}... Error: {e}")
            assert False

    # The specific test for null parameters is now part of invalid_responses and should be caught.
    # The logic `if "parameters" in parsed_response and not isinstance(parsed_response["parameters"], dict):`
    # correctly identifies `null` (which becomes `None` in Python) as not a dictionary.

    print("\nLLM Parser testing complete.")
