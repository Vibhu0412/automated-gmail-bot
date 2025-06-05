# Environment icons
console_icons = {
    "dev": "🛠️",  # Development icon
    "qa": "🧪",  # QA (Quality Assurance) icon
    "uat": "🏁",  # UAT icon
    "prod": "🚀",  # Production icon

    # Dev Icons
    "technologist": "👨‍💻",
    "person_with_wrench": "🧑‍🔧",
    "construction": "🏗️",
    "magnifying_glass": "🔍",
    "wrench": "🔧",
    "detective": "🕵️‍♂️",
    "checkered_flag": "🏁",
    "bullseye": "🎯",
    "trophy": "🏆",
    "package": "📦",
    "loading": "⏳",

    # Error Icons
    "error": "❌",
    "prohibited": "🚫",
    "warning": "⚠️",
    "alert": "🚨",
    "red_circle": "🔴",
    "green_circle": "🟢",

    # Service Icons
    "auth": "🔒",  # Lock icon
    "users": "👥",  # Busts in silhouette
    "knowledge_entries": "📚",  # Books
    "queues": "📥",  # Inbox tray
    # "queues": "🔄",  # Spinning Arrows
    "questions": "🔍",  # Question mark
    "conversations": "💬",  # Speech balloon
    "conversation_messages": "📨",  # Envelope with arrow
    "documents_processing": "📄",  # Page facing up
    "chat": "💬",  # Speech balloon
    "token": "🔑",  # Token

    # Misc Icons
    "greeting": "🙏",  # Folded hands
    "skull": "☠️",  # Skull
    "ghost": "👻",  # Ghost
    "spider": "🕷️",  # Spider
    "spider_web": "🕸️",  # Spider Web
    "zombie": "🧟",  # Zombie
    "mage": "🧙",  # Mage

    # Network Icons
    "celery": "🍃",
    "redis": "📡",
    "dashboard": "📈"
}


def get_console_icon(env):
    return console_icons.get(env, "❓")  # Fallback to a question mark if the environment is not found
