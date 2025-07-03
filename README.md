# maid-alpha
A prototype for jarvis-like AI system

Still figuring out the UX and make things feel natural.

## Features
I plan to make it a passive AI system where you only need to talk with it naturally.
The AI has 3 states
- Idle: Waiting for [one-shot] or [session] starting commands
- One-shot: Waiting for prompts or [stop_and_send] or [clear] or [cancel]
- Session: Similar to One-shot but the conversation continues until the user send a blank prompt or [cancel]

The specific words for each command can be found in static/commands.json

## Installation
1. First you need an OpenAI account with an API key.
2. Then download the whole folder and place it anywhere.
3. Place your key in `project.key`
4. Open your terminal and nevigate to this folder. Then run
```
pip install -r requirements.txt
python app.py
```
5. Go to the localhost page and enjoy
