"""Small OpenAI-compatible chat-completions client for the configured Gemma API."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_TIMEOUT_SECONDS = 5


def _load_local_env():
    """Load simple KEY=value entries without overriding the real environment."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip("\"'")
        os.environ.setdefault(key.strip(), value)


def parse_with_llm(messages: list[dict]) -> dict:
    """Call a configured OpenAI-compatible endpoint and decode its JSON response.

    Catalog records are intentionally not accepted by this function or included
    in the request. The only user-controlled content sent to the model is the
    conversation text, which the system prompt labels as untrusted input.
    """
    _load_local_env()
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("LLM_MODEL", "gemma-4-31b").strip()
    if not api_key or not base_url or not model:
        raise RuntimeError("LLM_API_KEY, LLM_BASE_URL и LLM_MODEL должны быть настроены")

    endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    system_prompt = (PROJECT_ROOT / "prompts" / "parse.md").read_text(encoding="utf-8")
    user_messages = [
        {"role": message["role"], "content": message["text"]}
        for message in messages
        if isinstance(message, dict)
        and message.get("role") in {"user", "assistant"}
        and isinstance(message.get("text"), str)
    ]
    if not user_messages:
        raise ValueError("В запросе нет текстовых сообщений пользователя")

    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, *user_messages],
        "temperature": 0,
    }).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
        with urlopen(request, timeout=timeout) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"Ошибка вызова LLM API: {exc}") from exc

    try:
        content = response_data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Поле content должно быть строкой")
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"API вернул некорректный JSON ответа: {exc}") from exc
