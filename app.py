from core.prompt import SYSTEM_PROMPT
from flask import Flask, jsonify, render_template, request, Response


from core.language import detect_language
from core.intent import extract_name
from core.llm import ask_llm_stream
from core.memory import (
    save_message,
    get_history,
    save_user_name,
    get_user_name
)

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
    user_lower = user_msg.lower()

    if not user_msg:
        return Response("", mimetype="text/plain")

    # Language detect
    language = detect_language(user_msg)

    # Greeting shortcut (NO LLM)
    if user_lower in ["hi", "hello", "hey"]:
        reply = (
            "Hello! How can I help you?"
            if language == "english"
            else "హలో! నేను మీకు ఎలా సహాయం చేయగలను?"
        )

        def stream():
            yield reply
            if memory_on:
                save_message("user", user_msg)
                save_message("assistant", reply)

        return Response(stream(), mimetype="text/plain")

    # Capture user name (FACT ONLY)
    name = extract_name(user_msg)
    if name:
        if memory_on:
            save_user_name(name)
            reply = f"Got it. Your name is {name}."
        else:
            reply = f"Nice to meet you, {name}. Memory is off, so I won't remember your name."

        return Response(reply, mimetype="text/plain")

    # Answer name from memory (NO LLM)
    if "what is my name" in user_lower:
        name = get_user_name() if memory_on else None
        reply = name if name else "I don't know."
        if memory_on:
            save_message("user", user_msg)
            save_message("assistant", reply)
        return Response(reply, mimetype="text/plain")

    # Format rules
    if "bullet" in user_lower or "points" in user_lower:
        format_rule = (
            "- Answer ONLY in bullet points\n"
            "- Maximum 5 points\n"
            "- No paragraphs\n"
        )
    elif "paragraph" in user_lower:
        format_rule = (
            "- Answer in ONE short paragraph\n"
            "- Maximum 5 lines\n"
            "- No bullet points\n"
        )
    else:
        format_rule = (
            "- Answer briefly\n"
            "- Maximum 3 lines\n"
        )

    # Language rule
    language_rule = (
        "Answer ONLY in Telugu."
        if language == "telugu"
        else "Answer ONLY in English."
    )

    # Memory context
    history_block = get_history().strip() if memory_on else ""

    # Updated Prompt (using SYSTEM_PROMPT)
    prompt = f"""
{SYSTEM_PROMPT}

FORMAT RULES:
{format_rule}

LANGUAGE RULE:
{language_rule}

FACTUAL MEMORY:
{history_block}

User:
{user_msg}

Assistant:
""".strip()

    def stream():
        full_reply = ""
        for chunk in ask_llm_stream(prompt):
            full_reply += chunk
            yield chunk

        if memory_on:
            save_message("user", user_msg)
            save_message("assistant", full_reply)

    return Response(stream(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(debug=True)
