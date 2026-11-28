
from flask import Flask, Response, jsonify, render_template, request

from core.chat import stream_reply
from core.intent import classify, extract_name, shortcut_reply
from core.language import detect_language
from core.llm import OllamaError, ask_llm_stream
from core.memory import (
    get_history,
    get_user_name,
    save_message,
    save_user_name,
)
from core.prompt import build_prompt


app = Flask(
    __name__,
    template_folder="web/templates",
    static_folder="web/static"
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}

    memory_on = data.get("memory", True)
    if not isinstance(memory_on, bool):
        return jsonify(error="memory must be true or false"), 400

    user_msg = data.get("message", "").strip()

    if not user_msg:
        return Response("", mimetype="text/plain")

    language = detect_language(user_msg)

    # Deterministic shortcuts
    intent = classify(user_msg)
    if intent:
        user_name = (
            get_user_name()
            if memory_on and intent == "ask_name"
            else None
        )
        reply = shortcut_reply(intent, language, user_name)

        if memory_on:
            save_message("user", user_msg)
            save_message("assistant", reply)

        return Response(reply, mimetype="text/plain")

    # Explicit name capture
    name = extract_name(user_msg)
    if name:
        if memory_on:
            save_user_name(name)
            reply = f"Got it. Your name is {name}."
        else:
            reply = (
                f"Nice to meet you, {name}. "
                "Memory is off, so I won't remember your name."
            )

        return Response(reply, mimetype="text/plain")

    # Build the LLM prompt
    history_block = get_history().strip() if memory_on else ""
    prompt = build_prompt(user_msg, language, history_block)

    # Handle initial Ollama failures
    chunks = iter(ask_llm_stream(prompt))
    try:
        first = next(chunks, "")
    except OllamaError as err:
        return jsonify(error=str(err)), 503

    return Response(
        stream_reply(chunks, first, user_msg, memory_on, save_message),
        mimetype="text/plain",
    )


if __name__ == "__main__":
    app.run(debug=True)
