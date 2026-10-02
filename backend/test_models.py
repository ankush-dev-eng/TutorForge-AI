import os
from dotenv import load_dotenv
from google import genai
import time

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
print(f"API key configured: {'YES' if api_key else 'NO'}")

client = genai.Client(api_key=api_key)

models_to_test = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

print("\n--- MODEL AVAILABILITY TEST ---")
for model in models_to_test:
    print(f"\nTesting {model}...")
    try:
        t0 = time.time()
        response = client.models.generate_content(
            model=model,
            contents="Reply exactly: TutorForge connected.",
        )
        t1 = time.time()
        print(f"[OK] Success! Response: {response.text.strip()}")
        print(f"Latency: {t1 - t0:.2f}s")
    except Exception as e:
        print(f"[FAIL] Failed: {e}")
