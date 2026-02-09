import asyncio
import os
import sys

# Ensure we can import from the app directory
sys.path.append('/app')

from services.gemini_service import GeminiService

async def test_generation():
    print("Testing Gemini Imagen 3 Generation inside Docker...")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment")
        return

    print(f"API Key found: {api_key[:5]}...")
    
    service = GeminiService()
    
    # Test prompt
    prompt = "A futuristic city with flying cars, neon lights, cyberpunk style, high resolution, 8k"
    template_type = "event"
    
    try:
        # Call the method
        image_path = await service.get_background_image(prompt, template_type)
        print(f"Success! Image generated at: {image_path}")
        
        # Verify file exists
        if os.path.exists(image_path.replace("file://", "")):
             print("File verified on disk.")
        else:
             print("Warning: File returned but not found on disk (check path format)")
             
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_generation())
