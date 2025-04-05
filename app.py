import requests
import json
import numpy as np
import pyaudio

OLLAMA_URL = 'http://10.0.0.10:11434/api/generate'
OLLAMA_MODEL = "llama3:latest"
OLLAMA_SYSTEM = "Limit your responses to three sentences. You are a voice assistant. Please refrain from providing unnecessary information."

PIPER_URL = "http://10.0.0.10:5000"

RESPEAKER_INDEX = 1

def generate_response(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": OLLAMA_SYSTEM,
        "stream": False
    }

    with requests.post(OLLAMA_URL, json=payload) as response:
        if response.status_code == 200:
            return response.json().get("response", "No response received.")
        else:
            return f"Error: {response.status_code} - {response.text}"

def stream_tts(text):
    params = {"text": text}

    with requests.get(PIPER_URL, params=params, stream=True) as response:
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return

        p = pyaudio.PyAudio()

        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=22050,
                        output=True,
			output_device_index = RESPEAKER_INDEX,
                        frames_per_buffer=1024)

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                int_data = np.frombuffer(chunk, dtype=np.int16)
                stream.write(int_data.tobytes())

        stream.stop_stream()
        stream.close()
        p.terminate()


if __name__ == "__main__":
    while True:
        user_input = input(">> ")
        if user_input.lower() == "exit":
            break

        response = generate_response(user_input)
        print("AI Response:", response)

        stream_tts(response)
