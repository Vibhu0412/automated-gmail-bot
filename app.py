import base64
import os
from email.mime.text import MIMEText

import google.generativeai as genai
from dotenv import load_dotenv
from flask import Flask
from flask import request
from flask_cors import CORS
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_google_genai import ChatGoogleGenerativeAI

from config import Config, config, personalized_prompt
from logger import logger
from version import create_v1_blueprint
from zconsoleicons import get_console_icon

app = Flask(__name__)

load_dotenv()

# Initialize Gemini
genai.configure(api_key=config.GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")
# client = OpenAI(api_key=config.OPEN_API_KEY)

# In-memory context store (replace with Redis/Mongo for prod)
conversation_history = {}

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
LABEL_TO_PROCESS = "tec_summary"
LABEL_DONE = "summary_done"


def create_llm(temperature=0, model="gemini-2.0-flash"):
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        api_key=config.GOOGLE_API_KEY
    )


def authenticate_gmail():
    creds = None

    # Load from token if exists
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # Refresh if expired and refresh_token exists
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # First-time login or token is invalid (e.g., missing refresh_token)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES
        )
        creds = flow.run_local_server(
            port=8080,
            access_type='offline',  # 💡 key for refresh_token
            prompt='consent'  # 💡 key to always get refresh_token
        )
        # Save token for reuse
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def get_label_id_by_name(service, label_name):
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for label in labels:
        if label['name'].lower() == label_name.lower():
            return label['id']
    return None


def create_label_if_not_exists(service, label_name):
    label_id = get_label_id_by_name(service, label_name)
    if label_id:
        return label_id
    label_object = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }
    created_label = service.users().labels().create(userId='me', body=label_object).execute()
    return created_label['id']


def get_threads_with_label(service, label):
    try:
        response = service.users().messages().list(userId='me', labelIds=[label]).execute()
        return response.get('messages', [])
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def get_thread_messages(service, thread_id):
    try:
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
    except HttpError as error:
        if error.resp.status == 404:
            print(f"Thread not found: {thread_id}")
            return ""
        raise

    messages = []
    for msg in thread.get('messages', []):
        parts = msg['payload'].get('parts', [])
        data = ''
        if parts:
            for part in parts:
                if part.get('mimeType') == 'text/plain' and 'data' in part['body']:
                    data = part['body']['data']
                    break
                elif part.get('mimeType') == 'text/html' and 'data' in part['body']:
                    data = part['body']['data']
        else:
            if 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                data = msg['payload']['body']['data']
        if data:
            text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            messages.append(text)
    return "\n\n".join(messages)


def create_reply_message(service, thread_id, reply_text):
    message = {
        'raw': base64.urlsafe_b64encode(
            f"Content-Type: text/plain; charset=UTF-8\n"
            f"MIME-Version: 1.0\n"
            f"Thread-Id: {thread_id}\n"
            f"In-Reply-To: {thread_id}\n"
            f"References: {thread_id}\n"
            f"Subject: Re: Summary of your thread\n\n"
            f"{reply_text}".encode("utf-8")
        ).decode("utf-8"),
        'threadId': thread_id,
    }
    return message


def send_reply(service, thread_id, reply_text, original_message):
    headers = original_message['payload']['headers']
    to_email = None
    message_id = None
    for header in headers:
        if header['name'].lower() == 'from':
            to_email = header['value']
        elif header['name'].lower() == 'message-id':
            message_id = header['value']

    if not to_email:
        raise Exception("Original sender email address not found, can't send reply")

    message = MIMEText(reply_text, _charset='utf-8')
    message['To'] = to_email
    message['Subject'] = "Re: Summary of your thread"
    if message_id:
        message['In-Reply-To'] = message_id
        message['References'] = message_id

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {
        'raw': raw,
        'threadId': thread_id
    }

    return service.users().messages().send(userId='me', body=body).execute()


def create_app():
    """Create and configure the Flask application."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    temp_Path = os.path.abspath(os.path.join(BASE_DIR, '../../shared/templates'))

    app = Flask(__name__, template_folder=temp_Path)
    app.config.from_object(Config)

    # Fetch allowed origins from config
    allowed_origins = config.ALLOWED_ORIGINS.split(',') if config.ALLOWED_ORIGINS != '*' else config.ALLOWED_ORIGINS

    # Enable CORS for all routes
    CORS(app, resources={r"/v1.0/*": {"origins": allowed_origins}, r"/admin/*": {"origins": allowed_origins}},
         supports_credentials=True)

    logger.info(f"{get_console_icon('alert')} Starting VP Proc 03 AutoReply WP Service "
                f"{get_console_icon('alert')}", extra={"extra_info": "Welcome Vaibhav | VS2411"})

    # Add health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return {"status": "VP Proc 03 Service is Healthy"}, 200

    @app.route("/webhook", methods=["POST"])
    def whatsapp_webhook():
        incoming_msg = request.form.get("Body")
        sender = request.form.get("From")

        # Retrieve context
        history = conversation_history.get(sender, [])
        history.append(incoming_msg)

        # Keep last 5 messages only
        if len(history) > 5:
            history = history[-5:]

        # Save updated history
        conversation_history[sender] = history

        # Construct context-aware prompt
        chat_context = "\n".join([f"User: {msg}" for msg in history[:-1]])
        latest = history[-1]

        prompt = f"""
        You are a helpful WhatsApp assistant. Maintain context and language used by the user.
        Here's the recent conversation:

        {chat_context}
        User: {latest}
        Assistant:"""

        response = model.generate_content(prompt)
        ai_reply = response.text.strip()

        # Respond using Twilio
        from twilio.twiml.messaging_response import MessagingResponse
        resp = MessagingResponse()
        resp.message(ai_reply)

        return str(resp)

    # @app.route("/summarize_and_reply", methods=["GET"])
    @app.route("/sr", methods=["GET"])
    def summarize_and_reply():
        service = authenticate_gmail()

        label_process_id = create_label_if_not_exists(service, LABEL_TO_PROCESS)
        label_done_id = create_label_if_not_exists(service, LABEL_DONE)
        threads = get_threads_with_label(service, label_process_id)

        if not threads:
            return {"message": f"No threads found with label '{LABEL_TO_PROCESS}'."}

        llm = create_llm()

        results = []
        for thread_meta in threads[:5]:
            thread_id = thread_meta['id']
            thread = service.users().threads().get(userId='me', id=thread_id).execute()
            conversation = get_thread_messages(service, thread_id)
            if not conversation:
                continue

            prompt = f"""
            You are replying to an email thread. Below is the conversation history. 

            {conversation}

            Generate a reply as per the following:
            {personalized_prompt}
            """
            summary = llm.invoke(prompt).content

            # Send reply using first message for headers
            first_message = thread['messages'][0]
            sent_message = send_reply(service, thread_id, summary, first_message)

            service.users().threads().modify(
                userId='me',
                id=thread_id,
                body={
                    "addLabelIds": [label_done_id],
                    "removeLabelIds": [label_process_id]
                }
            ).execute()

            results.append({
                "thread_id": thread_id,
                "summary": summary,
                "reply_message_id": sent_message.get('id')
            })

        return {"results": results}

    # Register Blueprints
    v1_blueprint = create_v1_blueprint()
    app.register_blueprint(v1_blueprint)

    app.config['SECRET_KEY'] = config.FLASK_SECRET_KEY

    return app


if __name__ == "__main__":
    app = create_app()
    # app.run(host=config.LOOPBACK_HOST, port=config.INTERNAL_PORT, ssl_context=config.SSL_CONTEXT)
    app.run(host=config.LOOPBACK_HOST, port=config.INTERNAL_PORT)

# Present in vp-test1
