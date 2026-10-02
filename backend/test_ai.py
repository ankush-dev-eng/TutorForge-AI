"""Test the correct model names."""
import os
os.chdir(os.path.dirname(__file__))
from config import settings
from google import genai

client = genai.Client(api_key=settings.gemini_api_key)

for model in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-flash-preview-05-20", "gemini-2.0-flash-exp"]:
    try:
        resp = client.models.generate_content(
            model=model,
            contents="Reply with exactly: TutorForge AI connected.",
            config={"max_output_tokens": 32}
        )
        print(f"SUCCESS model={model}: {resp.text.strip()}")
        break
    except Exception as e:
        err = str(e)[:120]
        print(f"FAIL model={model}: {err}")
