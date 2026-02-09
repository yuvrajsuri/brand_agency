import os
import httpx
import asyncio
import sys

# Ensure we can import from the app directory
sys.path.append('/app')

async def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"Found {len(models)} models:")
            for m in models:
                methods = m.get('supportedGenerationMethods', [])
                print(f"- {m['name']} ({methods})")
        else:
            print(f"Error listing models: {response.status_code} - {response.text}")

if __name__ == "__main__":
    asyncio.run(list_models())
