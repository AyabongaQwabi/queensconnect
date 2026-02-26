# Simple existence + generation check using config model and API key.
import os
from google import genai

try:
    from config import GOOGLE_API_KEY, GEMINI_MODEL
except ImportError:
    from queens_connect.config import GOOGLE_API_KEY, GEMINI_MODEL

api_key = GOOGLE_API_KEY or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("No GOOGLE_API_KEY / GEMINI_API_KEY in env or config!")
    exit(1)

model_name = GEMINI_MODEL

try:
    client = genai.Client(api_key=api_key)
    # In new SDK, you often just pass model name to generate_content
    response = client.models.generate_content(
        model=model_name,
        contents="Say 'sharp sharp' if you alive my guy"
    )
    print(f"Model '{model_name}' WORKS! Response:")
    print(response.text.strip())
except Exception as e:
    print(f"Model '{model_name}' failed: {str(e)}")