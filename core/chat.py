
from core.llm import OllamaError


def stream_reply(chunks, first, user_msg, memory_on, save_message):
    """Stream a reply and save only successfully completed turns."""
    full_reply = first

    try:
        if first:
            yield first

        for chunk in chunks:
            full_reply += chunk
            yield chunk

    except OllamaError as err:
        yield f"\n\n[Error: {err}]"
        return

    finally:
        close = getattr(chunks, "close", None)

        if close is not None:
            close()

    if memory_on:
        save_message("user", user_msg)
        save_message("assistant", full_reply)
