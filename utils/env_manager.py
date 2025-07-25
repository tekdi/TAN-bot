import os
from dotenv import load_dotenv
from llm import OpenAIChatClient, GroqChatClient, GeminiChatClient

load_dotenv()

def get_llm_client():
    llm_type = os.getenv("LLM_TYPE", "openai").lower()
    if llm_type == "openai":
        return OpenAIChatClient().get_client()
    elif llm_type == "groq":
        return GroqChatClient().get_client()
    elif llm_type == "gemini":
        return GeminiChatClient().get_client()
    else:
        raise ValueError(f"Unsupported LLM_TYPE: {llm_type}") 