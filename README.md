# SMA Scoring Engine

## Configuration

### API Keys and Environment Variables

To protect sensitive information like API keys, this project uses a `.env` file to manage environment variables. This file is included in the `.gitignore` file to prevent it from being accidentally committed to your repository.

**To set up your environment variables:**

1.  **Create a `.env` file** in the root of the project directory.
2.  **Add your API key** to the `.env` file in the following format:

    ```
    API_KEY="your_api_key_here"
    ```

3.  **Access the API key** in your Python scripts using the `os` library:

    ```python
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("API_KEY")
    ```

4.  **Install the `python-dotenv` library** to load the `.env` file:

    ```bash
    pip install python-dotenv
    ```

By following this approach, you can ensure that your API keys and other secrets are not exposed in your codebase or your git history.