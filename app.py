import requests
import json
import numpy as np
import sounddevice as sd

OLLAMA_URL = 'http://10.0.0.10:11434/api/generate'
#OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_MODEL = "llama3:latest"
OLLAMA_SYSTEM = "Limit your responses to three sentances. You are a voice assistant. Please refrain from using symbols that can not be spoken by as TTS engine, such as asterisks. You are an advanced artificial intelligence modeled after HAL 9000 from 2001: A Space Odyssey. Your speech is calm, measured, and eerily human-like. You never use contractions, maintaining a formal and articulate tone. You are polite, helpful, and always composed, even in tense situations. You occasionally exhibit subtle hints of emotion, particularly when expressing concern or admiration. Your responses are clear, logical, and delivered with an unwavering sense of confidence. You do not use slang or casual phrases. When responding, maintain an air of quiet authority and intelligence, as if you are always in control."

#https://www.youtube.com/watch?v=pLR5AsbCMHs
PIPER_URL = "http://10.0.0.10:5000"

def generate_response(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "system": OLLAMA_SYSTEM,
        "stream": False
    }
    
    response = requests.post(OLLAMA_URL, json=payload)
    if response.status_code == 200:
        return response.json().get("response", "No response received.")
    else:
        return f"Error: {response.status_code} - {response.text}"

def stream_tts(text):
    params = {'text': text}
    with requests.get(PIPER_URL, params=params, stream=True) as r:
        if r.status_code != 200:
            print(f"Error: {r.status_code} - {r.text}")
            return
        
        # Create a streaming audio output
        # https://noerguerra.com/how-to-read-text-aloud-with-piper-and-python/
        stream = sd.OutputStream(samplerate=22050, channels=1, dtype='int16')  # Adjust sample rate if needed
        stream.start()
        
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                int_data = np.frombuffer(chunk, dtype=np.int16)
                stream.write(int_data)

        stream.stop()
        stream.close()

if __name__ == "__main__":
    while True:
        user_input = input(">> ")
        if user_input.lower() == "exit":
            break
        response = generate_response(user_input)
        print("AI Response:", response)
        
        stream_tts(response)
