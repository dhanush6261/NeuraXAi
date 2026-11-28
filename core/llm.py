import json

import requests
from urllib3.exceptions import ReadTimeoutError

from core import config


class OllamaError(Exception):
    """An Ollama failure with a message suitable for the chat UI."""


def ask_llm_stream(prompt):
    model = config.MODEL
    base_url = config.OLLAMA_URL
    unreachable = f"Ollama is not reachable at {base_url}. Start Ollama and try again."
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        # Thinking models stream empty responses, hiding client disconnects and preventing Stop.
        "think": False,
        "options": {
            "temperature": config.TEMPERATURE
        }
    }

    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/generate",
            json=payload,
            stream=True,
            timeout=(config.CONNECT_TIMEOUT, config.READ_TIMEOUT),
        )
    except (requests.ConnectionError, requests.Timeout) as err:
        raise OllamaError(unreachable) from err

    try:
        status = response.status_code
        if status == 404:
            raise OllamaError(f'Model "{model}" is not installed. Run: ollama pull {model}')
        if not 200 <= status < 300:
            try:
                body = response.json()
            except (ValueError, requests.RequestException):
                body = None
            detail = body.get("error") if isinstance(body, dict) else None
            message = f"Ollama returned HTTP {status}"
            raise OllamaError(f"{message}: {detail}" if detail else f"{message}.")

        try:
            for line in response.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    if "error" in data:
                        raise OllamaError(str(data["error"]))
                    if "response" in data:
                        yield data["response"]
        except requests.Timeout as err:
            raise OllamaError("Ollama timed out while streaming a reply.") from err
        except requests.ConnectionError as err:
            # Requests wraps urllib3 read timeouts in ConnectionError during iteration.
            if err.args and isinstance(err.args[0], ReadTimeoutError):
                raise OllamaError("Ollama timed out while streaming a reply.") from err
            raise OllamaError(unreachable) from err
    finally:
        response.close()

