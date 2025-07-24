from os import system as cmd
from ollama import chat, generate
from TTS.api import TTS
from pathlib import Path
from openai import OpenAI
import contextlib
import threading
import keyboard
import time
import sounddevice as sd
import soundfile as sf
import tempfile
import os
import re
from datetime import datetime

cmd("cls")

allowed_gpt = False

# === AI configuration ===
model_name = "my_maid"  # based on "dolphin-mixtral:8x7b"
user_name = "Diptip"
ai_name = "Alaska"
persona_assignment = [
	{
		'role': 'assistant',
		'content': f'My name is now {ai_name}.'
					+ f'It is recently given by my master {user_name}.'
					+ f' I am now speaking to {user_name}.'
	}
]

def main():
	global exit_flag, reroll_flag
	messages = []
	
	cmd("cls")

	while True:
		if exit_flag :
			user_input = "Goodbye."
		elif reroll_flag :
			user_input = messages[-1]["content"]
			messages = messages[:-1] # remove this entry to avoid duplicate appending
			reroll_flag = False
		else :
			user_input = input('>> ')

		if user_input == "":
			print("\033[F", end="")
			continue

		if user_input.lower() in ['exit', 'bye']:
			exit_flag = True
			continue

		if user_input.lower() in ['clear', 'reset']:
			messages = []
			cmd("cls")
			with open(log_path,"a") as file:
				file.write(f"[reset]\n\n")
			continue

		if user_input.lower() in ['reroll']:
			messages = messages[:-1]
			reroll_flag = True
			with open(log_path,"a") as file:
				file.write(f"[reroll]\n\n")
			continue

		# Reprint everything
		messages.append({'role': 'user', 'content': user_input})
		if not exit_flag :
			cmd("cls")
			for entry in messages :
				if entry['role'] == 'user' :
					print(">> "+entry['content']+"\n")
				elif entry['role'] == 'assistant' :
					print("🩵: "+entry['content']+"\n")

		new_convo_entry = []
		if not exit_flag :
			if allowed_gpt and search_engine_check(user_input):
				print("\n🩵: *Asking the head maid*")
				openai_resp = client.chat.completions.create(
					model=gpt_model,
					messages=[{"role": "user", "content": user_input}]
				)
				gpt_answer = openai_resp.choices[0].message.content
				new_convo_entry = [
				{'role': 'assistant', 'content': f'(thinking to myself: I asked the head maid, Reina onee-sama, and she told me the following answer:\n{gpt_answer}\nI have to relay this to master next...)'},
				{'role': 'user', 'content': 'Tell me what the head maid says.'},
				]

				with open(log_path,"a") as file:
					file.write(f"gpt: {gpt_answer}\n\n")

		response_content = ""

		# Response streaming
		for ichunk, chunk in enumerate(chat(
			model=model_name,
			messages=(persona_assignment + messages + new_convo_entry),
			stream=True
		)):
			if ichunk == 0:
				print("🩵: ", end='', flush=True)
			if chunk.message:
				response_chunk = chunk.message.content
				print(response_chunk, end='', flush=True)
				response_content += response_chunk
		print()
		print()

		if exit_flag :
			print()
			break

		
		messages.append({'role': 'assistant', 'content': response_content})

		with open(log_path,"a") as file:
			file.write(f"user: {user_input}\n\n")
			file.write(f"assistant: {response_content}\n\n")

		# Replace name pronunciation tweaks
		response_content = response_content.replace("Onee", "onee")
		response_content = response_content.replace("onee", "o-nay")
		response_content = response_content.replace("diptip", "Diptip")
		response_content = response_content.replace("Diptip", "Dip-tip")
		response_content = response_content.replace("* ", ".* ")
		response_content = response_content.replace("*", "")
		while response_content.count("  ")>0:
			response_content = response_content.replace("  ", " ")
		while response_content.count("..")>0:
			response_content = response_content.replace("..", ".")

		speak_text_async(response_content)


def speak_text_async(text):
	monitor_thread = threading.Thread(target=speak_text, args=(text,))
	monitor_thread.start()
	monitor_thread.join()

def speak_text(text):
    global stop_speech
    stop_speech = False

    if not text.strip():
        return

    # Clean up text
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = text.replace("  ", " ").strip()

    # Split text by newline instead of sentence endings
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    chunks = lines

    # Synthesize and play each chunk
    for chunk in chunks:
        if stop_speech:
            break

        # Save audio to temp file
        os.makedirs("audio_files", exist_ok=True)
        with tempfile.NamedTemporaryFile(dir="audio_files", delete=False, suffix=".wav") as fp:
            tmp_path = fp.name

        with open(os.devnull, 'w', encoding='utf-8') as devnull:
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                tts.tts_to_file(text=chunk, file_path=tmp_path)

        # Load and play
        data, samplerate = sf.read(tmp_path)
        def playback():
            sd.play(data, samplerate)
            sd.wait()
        thread = threading.Thread(target=playback)
        thread.start()

        # Monitor enter key to interrupt
        while thread.is_alive():
            if keyboard.is_pressed('enter'):
                stop_speech = True
                sd.stop()
                break
            time.sleep(0.01)

        # Clean up
        os.remove(tmp_path)


def search_engine_check(user_input):

	for attempt in range(10) :
		# If the user_input requires searching, call chatGPT
		query = f"You are a helper AI who reads the prompt and will decide if we need to use the head maid (who is very smart) to answer or not. Note that the main AI who you are helping is REALLY stupid and cannot answer knowledgable things very well. So you need to pass it to the head maid if necessary, or master Diptip will be angry if the main AI gives incorrect information. This in cludes things like general knowledge and information about specific things like location or person. Don't trust the main AI. Trust the head maid. But if it's just a casual conversation without requesting for serious information, we do not use the head maid so we can save time. But of course, if the user said that we should ask the head maid, then the answer is yes. Here is the user input:\n{user_input}\n----------------------------\nNow answer if we need the head maid or not; a one-word yes or no. \nYour answer:"
		response = generate(model=model_name, prompt=query)["response"]
		#print("\n🚨: ", response)

		with open(log_path,"a") as file:
			file.write(f"    inner: {response}\n")

		while response[0] == " ":
			response = response[1:]
		is_no  = response[:2].lower()=="no"
		is_yes = response[:3].lower()=="yes"
		if is_no or is_yes :
			return is_yes

	return False


stop_speech = False
exit_flag = False
reroll_flag = False

cmd("cls")
# preparation
print(f"{ai_name} is coming...")

app_dir = Path(__file__).parent
log_folder_path = app_dir / f"conversations"
if not os.path.exists(log_folder_path):
    os.makedirs(log_folder_path)

# create the conversation file
now    = datetime.now()
ts     = now.strftime("%y%m%d.%H%M%S.")+f"{now.microsecond//1000:03d}"
log_path = app_dir / f"conversations/convo.{ts}.log"

# startup the llm models
dummy_prompt = "What is 1+1?"
generate(model=model_name, prompt=dummy_prompt)
tts = TTS(model_name="tts_models/en/ljspeech/vits--neon", progress_bar=False)
if allowed_gpt :
	key_path = app_dir / "project.key"
	client = OpenAI(api_key=key_path.read_text().strip())
	gpt_model = "gpt-4o-mini"


main()

