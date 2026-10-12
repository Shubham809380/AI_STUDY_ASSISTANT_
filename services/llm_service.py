import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


load_dotenv()


def _read_secret(name: str):
    """Return a config value from the environment, `.env` or Streamlit secrets.

    Environment variables (including a local ``.env``) take precedence, then
    Streamlit Community Cloud secrets are checked. This lets the same code run
    locally (via ``.env``) and on Streamlit Cloud (via the Secrets manager)
    without changes.
    """
    value = os.getenv(name)

    if value:
        return value

    try:
        import streamlit as st

        if name in st.secrets:
            return st.secrets[name]
    except Exception:  # noqa: BLE001 - secrets may be absent/out of context
        return None

    return None


# Model can be overridden via the GEMINI_MODEL environment variable or secret.
MODEL_NAME = _read_secret("GEMINI_MODEL") or "gemini-flash-lite-latest"

# Hard timeout (milliseconds) so a stuck request never hangs the UI forever.
REQUEST_TIMEOUT_MS = 60000


def get_client():
    """
    Create and return a Gemini client only when an API key is available.
    This prevents the whole Streamlit app from crashing when no key is set.
    """

    api_key = _read_secret("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Gemini API key is not configured. Locally, create a .env file and "
            "add GEMINI_API_KEY=YOUR_GEMINI_API_KEY. On Streamlit Community "
            "Cloud, add it in 'Manage app' -> Settings -> Secrets as "
            'GEMINI_API_KEY = "your_key".'
        )

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )


def _friendly_error(error: errors.APIError) -> str:
    """Convert a Gemini API error into a clear, user-facing message."""

    code = getattr(error, "code", None)
    message = getattr(error, "message", None) or str(error)

    if code == 429:
        return (
            "Gemini API quota exceeded (HTTP 429). The free tier allows only a "
            "small number of requests per day. Please wait for the quota to "
            "reset, use a different API key, or enable billing. "
            f"Details: {message}"
        )
    if code in (401, 403):
        return (
            "Gemini API key is invalid or not authorized (HTTP "
            f"{code}). Check GEMINI_API_KEY in your .env file or Streamlit "
            f"secrets. Details: {message}"
        )
    if code and 500 <= code < 600:
        return (
            "Gemini API is temporarily unavailable (HTTP "
            f"{code}). Please try again in a moment. Details: {message}"
        )
    if code:
        return f"Gemini API error (HTTP {code}): {message}"
    return f"Gemini API error: {message}"


def ask_llm(prompt: str) -> str:
    """
    Send a prompt to Gemini and return the generated text.

    Uses ``models.generate_content`` (the stable API) rather than the
    experimental Interactions API, which can hang without returning an error.
    """

    if not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    client = get_client()

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                )
            ),
        )
    except errors.APIError as error:
        raise RuntimeError(_friendly_error(error)) from error
    except Exception as error:  # noqa: BLE001 - surface network/timeout failures
        raise RuntimeError(
            f"Could not reach the Gemini API: {type(error).__name__}: {error}"
        ) from error

    text = getattr(response, "text", None)

    if not text or not text.strip():
        raise RuntimeError("The LLM returned an empty response.")

    return text