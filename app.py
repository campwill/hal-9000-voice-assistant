import requests
import json
import numpy as np
import pyaudio
import os
from dotenv import load_dotenv
import pvporcupine
from lights import Lights
import time
import audioop
import wave
from websocket import create_connection
import traceback

load_dotenv()

OLLAMA_URL = 'http://10.0.0.10:11434/api/generate'
OLLAMA_MODEL = "llama3:latest"
OLLAMA_SYSTEM = "Limit your responses to three sentences. You are a voice assistant. Please refrain from providing unnecessary information."

VOSK_URL = "ws://10.0.0.10:2700"

PIPER_URL = "http://10.0.0.10:5000"

porcupine = pvporcupine.create(
  access_key=os.environ.get("PICOVOICE_KEY"),
  keyword_paths=[os.environ.get("PICOVOICE_MODEL_PATH")]
)

RESPEAKER_INDEX = 1

lights = Lights()

def listen_for_wake_word():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index = RESPEAKER_INDEX,
                    frames_per_buffer=512)

    print("Listening for wake word...")

    try:
        while True:
            pcm = np.frombuffer(stream.read(512), dtype=np.int16)

            keyword_index = porcupine.process(pcm)

            if keyword_index >= 0:
                print("Wake word detected!")
                return True
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def record_prompt():
    THRESHOLD = 25000
    SILENCE_DURATION = 3

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    input=True,
                    input_device_index=1,
                    frames_per_buffer=1024)

    print("Recording...")

    silence_start_time = None
    silence_counter = 0
    frames = []

    while True:
        data = stream.read(1024)
        frames.append(data)

        rms = audioop.rms(data, 2)

        if rms < THRESHOLD:
            if silence_start_time is None:
                silence_start_time = time.time()
            else:
                silence_counter = time.time() - silence_start_time
        else:
            silence_start_time = None
            silence_counter = 0

        if silence_counter >= SILENCE_DURATION:
            print("Silence detected, stopping recording.")
            break

    stream.stop_stream()
    stream.close()
    p.terminate()

    output_filename = "output.wav"
    with wave.open(output_filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(44100)
        wf.writeframes(b''.join(frames))

    print(f"Recording saved to {output_filename}")

def perform_stt():
    ws = create_connection(VOSK_URL)

    wf = wave.open("output.wav", "rb")
    ws.send('{ "config" : { "sample_rate" : %d } }' % (wf.getframerate()))
    buffer_size = int(wf.getframerate() * 0.2)

    try:

        while True:
            data = wf.readframes(buffer_size)

            if len(data) == 0:
                break

            ws.send_binary(data)
            response = ws.recv()
            response_json = json.loads(response)

            if "text" in response_json and response_json["text"]:
                return response_json["text"]

        ws.send('{"eof" : 1}')

    except Exception as err:
        print(''.join(traceback.format_exception(type(err), err, err.__traceback__)))

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
        try:
            if listen_for_wake_word():
                lights.fade_in()

                record_prompt()

                #user_input = input(">> ")
                #if user_input.lower() == "exit":
                #    break

                user_input = perform_stt()
                print(user_input)

                response = generate_response(user_input)
                print(response)

                stream_tts(response)

                lights.fade_out()
                time.sleep(1)

        except KeyboardInterrupt:
            break

    lights.off()
    time.sleep(1)
