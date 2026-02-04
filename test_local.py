"""
Local Test Script for Text Overlay Engine
Tests the overlay generation without requiring R2 setup
"""

import asyncio
import httpx
import json
from pathlib import Path


async def test_overlay_generation():
    """Test the overlay generation endpoint"""
    
    # Test data with Punjabi text
    test_request = {
        "background_url": "https://images.unsplash.com/photo-1557683316-973673baf926?w=1080&h=1080&fit=crop",
        "texts": [
            {
                "content": "ਵਿਸ਼ੇਸ਼ ਪੇਸ਼ਕਸ਼",
                "type": "headline",
                "color": "#FFFFFF",
                "weight": "black"
            },
            {
                "content": "50% ਤੱਕ ਛੋਟ",
                "type": "subtext",
                "color": "#FFD700",
                "weight": "bold"
            },
            {
                "content": "ਹੁਣੇ ਆਰਡਰ ਕਰੋ",
                "type": "cta",
                "color": "#FFFFFF",
                "weight": "bold"
            }
        ],
        "language": "punjabi",
        "template_type": "offer",
        "brand_color": "#FF6B35",
        "output_width": 1080,
        "output_height": 1080
    }
    
    print("🚀 Testing Text Overlay Engine...")
    print(f"📝 Template: {test_request['template_type']}")
    print(f"🌐 Language: {test_request['language']}")
    print(f"📐 Dimensions: {test_request['output_width']}x{test_request['output_height']}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8000/api/generate-overlay",
                json=test_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Overlay generated successfully!")
                print(f"⏱️  Generation time: {result['generation_time']:.2f}s")
                print(f"🖼️  Image URL: {result['image_url']}")
                print(f"📊 Metadata: {json.dumps(result['metadata'], indent=2)}")
                
                # Check if file exists locally (for non-R2 testing)
                if result['image_url'].startswith('file://'):
                    local_path = result['image_url'].replace('file://', '')
                    if Path(local_path).exists():
                        print(f"✅ Local file exists: {local_path}")
                    else:
                        print(f"❌ Local file not found: {local_path}")
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
    except httpx.ConnectError:
        print("❌ Connection failed. Is the server running?")
        print("💡 Run: python main.py")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def test_health_check():
    """Test the health check endpoint"""
    
    print("🏥 Testing health check...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            
            if response.status_code == 200:
                health = response.json()
                print(f"✅ Service healthy: {health['status']}")
                print(f"📦 Version: {health['version']}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")


async def test_multiple_templates():
    """Test all template types"""
    
    templates = ["festival", "offer", "product", "event"]
    languages = ["punjabi", "hindi", "english"]
    
    test_texts = {
        "punjabi": [
            {"content": "ਵਿਸ਼ੇਸ਼ ਪੇਸ਼ਕਸ਼", "type": "headline"},
            {"content": "50% ਤੱਕ ਛੋਟ", "type": "subtext"},
            {"content": "ਹੁਣੇ ਆਰਡਰ ਕਰੋ", "type": "cta"}
        ],
        "hindi": [
            {"content": "विशेष ऑफर", "type": "headline"},
            {"content": "50% तक छूट", "type": "subtext"},
            {"content": "अभी ऑर्डर करें", "type": "cta"}
        ],
        "english": [
            {"content": "Special Offer", "type": "headline"},
            {"content": "Up to 50% Off", "type": "subtext"},
            {"content": "Order Now", "type": "cta"}
        ]
    }
    
    print("🧪 Testing all template types and languages...\n")
    
    for template in templates:
        for language in languages:
            print(f"📋 Testing: {template} template in {language}")
            
            request = {
                "background_url": "https://images.unsplash.com/photo-1557683316-973673baf926?w=1080&h=1080&fit=crop",
                "texts": [
                    {**text, "color": "#FFFFFF", "weight": "bold"}
                    for text in test_texts[language]
                ],
                "language": language,
                "template_type": template,
                "brand_color": "#FF6B35",
                "output_width": 1080,
                "output_height": 1080
            }
            
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "http://localhost:8000/api/generate-overlay",
                        json=request
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"   ✅ Success ({result['generation_time']:.2f}s)")
                    else:
                        print(f"   ❌ Failed: {response.status_code}")
                        
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
            
            await asyncio.sleep(0.5)  # Small delay between tests
        
        print()


async def main():
    """Run all tests"""
    
    print("=" * 60)
    print("TEXT OVERLAY ENGINE - LOCAL TESTING")
    print("=" * 60)
    print()
    
    # Test health check
    await test_health_check()
    print()
    
    # Test single overlay
    await test_overlay_generation()
    print()
    
    # Ask if user wants to test all templates
    print("=" * 60)
    choice = input("🤔 Test all templates and languages? (y/n): ")
    
    if choice.lower() == 'y':
        print()
        await test_multiple_templates()
    
    print("=" * 60)
    print("✅ Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
