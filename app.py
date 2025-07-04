from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import os

app_dir = os.path.dirname(os.path.abspath(__file__))
key_dir = os.path.join(app_dir,"project.key")

app = Flask(__name__)
client = OpenAI(api_key=open(key_dir).read().strip())
model = "gpt-4o-mini"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    messages = request.json.get("messages", [])
    if not messages:
        return jsonify({"error": "No messages provided"}), 400

    is_placeholder = False  # ← set this to True to simulate responses

    if is_placeholder:
        last_input = messages[-1]["content"]
        fake_response = f"You said: '{last_input}'. This is a placeholder response."
        return jsonify({"response": fake_response})
    else:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            return jsonify({"response": response.choices[0].message.content})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)