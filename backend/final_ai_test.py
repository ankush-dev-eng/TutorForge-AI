import os
import asyncio
from dotenv import load_dotenv
from google import genai
from config import settings
from ai_provider import llm_provider, GeminiProvider, ProviderError

async def run_final_test():
    load_dotenv()
    print("AI PROVIDER")
    print(f"- SDK: google.genai")
    print(f"- API key configured: {'YES' if os.environ.get('GEMINI_API_KEY') else 'NO'}")
    
    if isinstance(llm_provider, GeminiProvider):
        print(f"- Primary model: {llm_provider._primary_model}")
        try:
            res = llm_provider._call_model(llm_provider._primary_model, "Reply exactly: TutorForge connected.")
            print(f"- Primary test: SUCCESS ({res})")
        except Exception as e:
            print(f"- Primary test: FAILED ({e})")
            
        print(f"- Fallback 1: {llm_provider._fallback_model}")
        if llm_provider._fallback_model:
            try:
                res = llm_provider._call_model(llm_provider._fallback_model, "Reply exactly: TutorForge connected.")
                print(f"- Fallback 1 test: SUCCESS ({res})")
            except Exception as e:
                print(f"- Fallback 1 test: FAILED ({e})")
        else:
            print(f"- Fallback 1 test: SKIPPED")
            
        print(f"- Fallback 2: {llm_provider._secondary_fallback}")
        if llm_provider._secondary_fallback:
            try:
                res = llm_provider._call_model(llm_provider._secondary_fallback, "Reply exactly: TutorForge connected.")
                print(f"- Fallback 2 test: SUCCESS ({res})")
            except Exception as e:
                print(f"- Fallback 2 test: FAILED ({e})")
        else:
            print(f"- Fallback 2 test: SKIPPED")

        print("\nTESTING CHAT ROUTE WITH RETRY/FALLBACK...")
        try:
            res = llm_provider.chat([{"role": "user", "content": "Reply exactly: TutorForge connected."}])
            print(f"- Final active model response: SUCCESS ({res})")
        except ProviderError as pe:
            print(f"- Final active model response: FAILED with ProviderError ({pe.code}: {pe})")
    else:
        print("Provider is not GeminiProvider!")

if __name__ == "__main__":
    asyncio.run(run_final_test())
