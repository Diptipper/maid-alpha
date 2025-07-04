#!/usr/bin/env python3
"""
Run with…

    python app.py           # web UI (default)
    python app.py --console # interactive console that understands [listen] etc.
"""
from __future__ import annotations
import argparse, json, os, sys
from typing import List, Dict

from flask import Flask, render_template, request, jsonify
from openai import OpenAI

# ── Paths ──────────────────────────────────────────────────────────────────────
APP_DIR      = os.path.dirname(os.path.abspath(__file__))
KEY_PATH     = os.path.join(APP_DIR, "project.key")
COMMANDS_JSON = os.path.join(APP_DIR, "static", "commands.json")  # ← NEW

# ── OpenAI & Flask ─────────────────────────────────────────────────────────────
client = OpenAI(api_key=open(KEY_PATH).read().strip())
model  = "gpt-4o-mini"
app    = Flask(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────
def load_console_commands() -> Dict[str, List[str]]:
    """Load command phrases from static/commands.json, with sensible fallbacks."""
    defaults = {
        "start_single": ["listen"],
        "start_session": ["let's talk"],
        "stop_and_send": ["thanks"],
        "clear": ["reset"],
        "cancel": ["cancel"]
    }
    try:
        with open(COMMANDS_JSON, encoding="utf-8") as f:
            data: Dict[str, List[str]] = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("commands.json must contain a JSON object")
            # Merge defaults → anything missing in the file still works
            merged = {**defaults, **data}
            return merged
    except FileNotFoundError:
        print(f"⚠️  {COMMANDS_JSON} not found; falling back to built-ins.")
    except Exception as e:
        print(f"⚠️  Failed to load commands.json ({e}); falling back to built-ins.")
    return defaults

# The console REPL will call this once, lazily:
COMMANDS: Dict[str, List[str]] | None = None

# ── Web routes ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    messages = request.json.get("messages", [])
    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    try:
        resp = client.chat.completions.create(model=model, messages=messages)
        print(resp.choices[0].message.content)
        return jsonify({"response": resp.choices[0].message.content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Console mode ───────────────────────────────────────────────────────────────
def run_console() -> None:
    global COMMANDS
    if COMMANDS is None:                      # load once
        COMMANDS = load_console_commands()
        COMMANDS.setdefault("quit", ["quit", "exit"])

    print("🔹 Console mode — press ↵ on an empty line to send, [quit] to exit.")
    capturing, session_mode, transcript_buf = False, False, ""
    history: List[Dict[str, str]] = []

    while True:
        try:
            line = input("» ").rstrip()      # ← keep trailing spaces out
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye!")
            break

        # ── ①  NEW: empty line auto-sends  ────────────────────────────────────
        if capturing and line == "":
            final_inp = transcript_buf.strip()
            if final_inp == "":
                # behaves like an “empty [thanks]”
                capturing = session_mode = False
                print("👋 Empty input — session ended.")
            else:
                _send_and_print(final_inp, history, session_mode)
                transcript_buf = ""
                capturing = session_mode          # stay in session if needed
            continue

        # ── bracket commands ---------------------------------------------------
        if line.startswith("[") and line.endswith("]"):
            cmd = line[1:-1].strip().lower()

            if cmd in COMMANDS["quit"]:
                print("👋 Bye!")
                break

            if cmd in COMMANDS["start_single"] and not capturing:
                capturing, session_mode, transcript_buf = True, False, ""
                print("🎙️  One-shot recording …")
                continue

            if cmd in COMMANDS["start_session"] and not capturing:
                capturing, session_mode, transcript_buf, history = True, True, "", []
                print("🎙️  Session recording …")
                continue

            if cmd in COMMANDS["clear"]:
                transcript_buf = ""
                print("↺ Buffer cleared.")
                continue

            if cmd in COMMANDS["cancel"]:
                capturing, session_mode, transcript_buf, history = False, False, "", []
                print("🚫 Cancelled.")
                continue

            if cmd in COMMANDS["stop_and_send"] and capturing:
                final_inp = transcript_buf.strip()
                if final_inp == "":
                    capturing = session_mode = False
                    print("👋 Empty thanks — session ended.")
                else:
                    _send_and_print(final_inp, history, session_mode)
                    transcript_buf = ""
                    capturing = session_mode
                continue

            print("⚠️  Unknown command:", cmd)
            continue

        # ── regular text -------------------------------------------------------
        if capturing:
            transcript_buf += line + " "
        else:
            _send_and_print(line, [], False)


def _send_and_print(user_prompt: str, history: List[Dict[str, str]],
                    session_mode: bool) -> None:
    if session_mode:
        history.append({"role": "user", "content": user_prompt})
        payload = {"messages": history}
    else:
        payload = {"messages": [{"role": "user", "content": user_prompt}]}

    try:
        resp = client.chat.completions.create(
            model=model, messages=payload["messages"]
        ).choices[0].message.content
    except Exception as e:
        print("⚠️  Error:", e)
        return

    print("🤖", resp, "\n")
    if session_mode:
        history.append({"role": "assistant", "content": resp})

# ── Main entry-point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Maid Alpha runner")
    parser.add_argument("--console", action="store_true",
                        help="Run interactive console instead of Flask web UI")
    args = parser.parse_args()

    if args.console:
        run_console()
    else:
        app.run(debug=True)
