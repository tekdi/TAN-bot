import os
import redis
import json
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

HISTORY_KEY_PREFIX = "chat_history:"
HISTORY_MAX_PAIRS = 10  # Store up to 10 pairs, but use last 4 for prompt

def get_history(phone: str):
    key = HISTORY_KEY_PREFIX + str(phone)
    history_json = r.get(key)
    if not history_json:
        return []
    try:
        history = json.loads(history_json)
        if not isinstance(history, list):
            return []
        return history
    except Exception as e:
        print(f"Error getting history: {e}")
        return []

def store_history(phone: str, user_query: str, assistant_response: str):
    key = HISTORY_KEY_PREFIX + str(phone)
    history = get_history(phone)
    history.append({"user": user_query, "assistant": assistant_response})
    # Keep only the last HISTORY_MAX_PAIRS
    history = history[-HISTORY_MAX_PAIRS:]
    try:
        # Set the history with a 1-day TTL (86400 seconds)
        r.set(key, json.dumps(history), ex=86400)
    except Exception as e:
        print(f"Error storing history: {e}") 