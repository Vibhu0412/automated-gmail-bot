import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

chat_history = []


def get_reply(message):
    global chat_history
    if len(chat_history) > 10:
        chat_history = chat_history[-10:]  # keep last 10 for context

    prompt = f"You are a helpful, polite AI. Reply in the same language. The user said: '{message}'"
    chat_history.append({"role": "user", "parts": [message]})

    model = genai.GenerativeModel("gemini-2.0-flash")
    chat = model.start_chat(history=chat_history)

    response = chat.send_message(message)
    chat_history.append({"role": "model", "parts": [response.text]})
    return response.text.strip()
