import os
import ssl
from pathlib import Path

import httpx
import truststore
from dotenv import load_dotenv

# Uses the OS's native certificate store (same one curl trusts) instead of
# the bundled certifi certs, so TLS to internal/corporate proxies whose
# certs are signed by a locally-installed CA (not a public CA) verifies
# correctly — no manual CA file needed.
_SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

# Loads sentinel-access/backend/.env (if present) into os.environ once at
# import time, so LITELLM_PROXY_URL/LITELLM_API_KEY/LITELLM_MODEL can be set
# by editing that file instead of exporting them in the shell each run.
# Vars already set in the environment are not overridden.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_TIMEOUT_SECONDS = 15.0


class AIServiceError(Exception):
    """Raised when the liteLLM proxy is unreachable, errors, or returns an unusable shape."""


_CHAT_COMPLETIONS_PATH = "/v1/chat/completions"


def _config() -> tuple[str, str, str]:
    proxy_url = os.environ.get("LITELLM_PROXY_URL", "http://localhost:4000").rstrip("/")
    # Tolerate LITELLM_PROXY_URL being set to either the proxy's base URL
    # (e.g. "http://localhost:4000") or the full chat-completions endpoint
    # (e.g. "http://localhost:4000/v1/chat/completions") — strip the
    # suffix if present so it isn't appended twice below.
    if proxy_url.endswith(_CHAT_COMPLETIONS_PATH):
        proxy_url = proxy_url[: -len(_CHAT_COMPLETIONS_PATH)]
    api_key = os.environ.get("LITELLM_API_KEY")
    model = os.environ.get("LITELLM_MODEL", "genailab-maas-Opus-4.6")
    if not api_key:
        raise AIServiceError("LITELLM_API_KEY is not configured")
    return proxy_url, api_key, model


def call_chat_completions(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """POSTs an OpenAI-compatible chat-completions request to the liteLLM proxy.

    Returns the parsed response's first choice message (dict with at least
    "content", and "tool_calls" when the model chose to call a tool).
    Raises AIServiceError on any network failure, non-2xx response, or a
    response missing usable choices (see research.md §7).
    """
    proxy_url, api_key, model = _config()

    body: dict = {"model": model, "messages": messages}
    if tools:
        body["tools"] = tools

    try:
        response = httpx.post(
            f"{proxy_url}{_CHAT_COMPLETIONS_PATH}",
            json=body,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT_SECONDS,
            verify=_SSL_CONTEXT,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise AIServiceError(f"liteLLM proxy request failed: {exc}") from exc

    choices = data.get("choices")
    if not choices:
        raise AIServiceError("liteLLM proxy response had no choices")

    message = choices[0].get("message")
    if not message:
        raise AIServiceError("liteLLM proxy response had no message")

    return message


def configured_model() -> str:
    return os.environ.get("LITELLM_MODEL", "genailab-maas-Opus-4.6")


def call_risk_context(messages: list[dict]) -> tuple[object, str]:
    """Call the existing proxy for the bounded Feature 004 JSON response."""
    message = call_chat_completions(messages)
    content = message.get("content")
    if content is None:
        raise AIServiceError("liteLLM risk-context response had no content")
    return content, configured_model()
