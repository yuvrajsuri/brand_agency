# Text Overlay Engine - Implementation Guide

## 📚 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Component Breakdown](#component-breakdown)
4. [How It Works: Step-by-Step](#how-it-works-step-by-step)
5. [Template System Explained](#template-system-explained)
6. [Font Rendering Technology](#font-rendering-technology)
7. [Local Testing Workflow](#local-testing-workflow)
8. [Production Deployment](#production-deployment)
9. [Integration Patterns](#integration-patterns)
10. [Troubleshooting & Debugging](#troubleshooting--debugging)

---

## System Overview

### The Problem We're Solving

**Original Challenge:**
- LLM image generators (DALL-E, Midjourney, SD) produce garbled Punjabi/Hindi text
- Gurmukhi matras and Devanagari diacriticals are rendered incorrectly
- No control over text positioning or brand consistency
- Manual editing required for every image

**Our Solution:**
- Separate background generation (Runware) from text rendering (Playwright)
- Use browser-grade font rendering for pixel-perfect Indic scripts
- Dynamic positioning based on marketing templates
- Automated pipeline: API request → CDN URL in ~2-3 seconds

### High-Level Flow

```
┌─────────────────┐
│ n8n Workflow    │
│ (WhatsApp Bot)  │
└────────┬────────┘
         │
         ├─→ Gemini: Generate marketing copy
         │   Output: headline, subtext, CTA in Punjabi/Hindi/English
         │
         ├─→ Runware: Generate background image (NO TEXT)
         │   Output: 1080x1080 JPG URL
         │
         └─→ Text Overlay Engine: Combine them
             Input: background URL + text blocks + template type
             Process:
               1. Download background
               2. Calculate text positions (dynamic per template)
               3. Generate HTML with Google Noto fonts
               4. Render with Playwright (Chromium headless)
               5. Upload PNG to Cloudflare R2
             Output: Public CDN URL
```

---

## Architecture Deep Dive

### Component Stack

```
┌──────────────────────────────────────────────────────────┐
│                     FastAPI Server                        │
│                    (main.py - Port 8000)                  │
└───────────────────┬──────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
   ┌────▼────┐          ┌──────▼──────┐
   │ Renderer│          │  R2 Storage │
   │ Service │          │   Service   │
   └────┬────┘          └──────┬──────┘
        │                      │
   ┌────▼─────────────┐   ┌───▼────────┐
   │   Playwright     │   │   boto3    │
   │  (Chromium)      │   │ S3 Client  │
   └──────────────────┘   └────────────┘
```

### Why This Stack?

| Component | Why This Choice? |
|-----------|------------------|
| **FastAPI** | Fast async API, Pydantic validation, auto OpenAPI docs |
| **Playwright** | Real browser rendering = perfect fonts. Alternatives (Pillow, cairo) lack proper Gurmukhi shaping |
| **Chromium** | Best Unicode support, Google Noto fonts built-in, headless-friendly |
| **R2 (S3)** | Cheap CDN ($0 egress), S3-compatible API, 10GB free tier |
| **Docker** | Consistent environments (fonts, Playwright), easy VPS deployment |

---

## Component Breakdown

### 1. FastAPI Server (`main.py`)

**Purpose:** HTTP API interface for overlay generation

**Key Features:**
- **Request validation:** Pydantic models ensure correct data types
- **Async processing:** Non-blocking I/O for downloads/uploads
- **Error handling:** Catches and logs failures, returns HTTP 500 with details
- **Health check:** `/health` endpoint for monitoring

**Request Model:**
```python
class OverlayRequest(BaseModel):
    background_url: str              # Where to get the background
    texts: list[TextBlock]           # What to write (headline, subtext, CTA)
    language: "punjabi"|"hindi"|"english"
    template_type: "festival"|"offer"|"product"|"event"
    brand_color: str = "#FF6B35"    # For CTA button background
    output_width: int = 1080
    output_height: int = 1080
```

**Response Model:**
```python
class OverlayResponse(BaseModel):
    success: bool
    image_url: str                   # CDN URL of final image
    generation_time: float           # Performance metric
    metadata: dict                   # Template type, language, etc.
```

---

### 2. Overlay Renderer (`services/renderer.py`)

**Purpose:** Core logic for text positioning and HTML rendering

#### 2.1 Background Download

```python
async def download_background(self, url: str) -> Path:
    # Uses httpx for async HTTP
    # Saves to /tmp/overlay-engine/bg_<random>.jpg
    # Returns local file path
```

**Why not stream directly?**
- Playwright needs local file path
- Allows caching for repeated requests
- Easier debugging (inspect temp files)

#### 2.2 Position Calculator

**Dynamic positioning** based on template type:

```python
def calculate_positions(template_type, text_blocks, width, height):
    if template_type == "festival":
        # Centered vertical: 35%, 50%, 65% from top
    elif template_type == "offer":
        # Top-heavy: 25%, 50%, 75%
    elif template_type == "product":
        # Bottom-third: 68%, 80%, 90%
    elif template_type == "event":
        # Asymmetric: left 20%, left 40%, right 85%
```

**Position format:**
```python
{
    "x": 0.5,           # Horizontal (0.0 = left, 0.5 = center, 1.0 = right)
    "y": 0.35,          # Vertical (0.0 = top, 1.0 = bottom)
    "align": "center",  # Text alignment
    "max_width": 0.85   # Maximum width as fraction of image
}
```

#### 2.3 Font Size Calculator

**Responsive sizing** based on text block type:

```python
def calculate_font_sizes(text_blocks, base_size=72):
    multipliers = {
        "headline": 1.5,   # 108px - large and bold
        "subtext": 1.0,    # 72px - standard
        "cta": 0.8         # 58px - readable but not dominant
    }
```

Users can override with custom `font_size` in request.

#### 2.4 HTML Template Generator

**Converts data → HTML with embedded background:**

```html
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?
                 family=Noto+Sans+Gurmukhi:wght@400;700;900
                 &family=Noto+Sans+Devanagari:wght@400;700;900
                 &family=Montserrat:wght@400;700;900
                 &display=swap" rel="stylesheet">
</head>
<body>
    <div class="container" style="width: 1080px; height: 1080px;">
        <!-- Background as base64 data URL -->
        <img src="data:image/jpeg;base64,/9j/4AAQ..." class="background">
        
        <!-- Text blocks with calculated positions -->
        <div class="text-block" style="
            position: absolute;
            left: 50%;
            top: 35%;
            transform: translate(-50%, -50%);
            font-size: 108px;
            font-weight: black;
            color: #FFFFFF;
            font-family: 'Noto Sans Gurmukhi', sans-serif;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.7);
        ">ਵਿਸ਼ੇਸ਼ ਪੇਸ਼ਕਸ਼</div>
        
        <!-- More text blocks... -->
    </div>
</body>
</html>
```

**Key techniques:**
- Base64 embedding avoids network requests during render
- Google Fonts CDN loads Noto fonts
- Absolute positioning with `transform: translate()` for precise centering
- Text shadows for readability over any background
- CTA buttons get `background: <brand_color>` with border-radius

#### 2.5 Playwright Renderer

**Screenshots the HTML as PNG:**

```python
async def _render_with_playwright(html_path, width, height):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=2  # 2x resolution for crisp text
        )
        
        await page.goto(f"file://{html_path}")
        await page.wait_for_load_state("networkidle")  # Wait for fonts
        await asyncio.sleep(0.5)  # Extra time for Indic font shaping
        
        await page.screenshot(path=output_path, full_page=False)
        await browser.close()
```

**Why `device_scale_factor=2`?**
- Renders at 2160x2160 internally, scales to 1080x1080
- Results in crisp, retina-quality text
- Avoids pixelation on high-DPI screens

---

### 3. R2 Storage (`services/storage.py`)

**Purpose:** Upload rendered PNGs to Cloudflare R2 (S3-compatible CDN)

```python
class R2Storage:
    def __init__(self):
        # Initialize boto3 S3 client with R2 endpoint
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
    
    async def upload_image(self, file_path, folder="overlays"):
        # Generate unique filename: 20260204_123456_abc123.png
        filename = f"{timestamp}_{random_hex}.png"
        s3_key = f"{folder}/{filename}"
        
        # Upload with cache headers
        self.client.upload_fileobj(
            file,
            bucket_name,
            s3_key,
            ExtraArgs={'ContentType': 'image/png', 'CacheControl': 'public, max-age=31536000'}
        )
        
        # Return public URL
        return f"https://{custom_domain}/{s3_key}"
```

**Configuration:**
- R2 account ID, access key, secret key in `.env`
- Bucket name: `brand-agency-creatives`
- Custom domain (optional): `cdn.yourdomain.com`
- Fallback: R2.dev subdomain (free)

**Cost optimization:**
- 10GB free storage
- $0 egress (unlike S3)
- 1-year cache headers reduce repeated requests

---

## How It Works: Step-by-Step

### End-to-End Request Flow

**1. User sends WhatsApp message:** "Make me a Diwali offer poster"

**2. n8n workflow triggers:**
```
├─ Gemini API: Generate copy
│  Input: "Diwali offer poster for retail shop"
│  Output: {
│      headline: "ਦੀਵਾਲੀ ਵਿਸ਼ੇਸ਼",
│      subtext: "40% ਤੱਕ ਛੋਟ",
│      cta: "ਹੁਣੇ ਖਰੀਦੋ"
│  }
│
├─ Runware API: Generate background
│  Prompt: "Festive background with diyas and lights, no text"
│  Output: https://runware.ai/output/abc123.jpg
│
└─ HTTP Request to Text Overlay Engine
```

**3. FastAPI receives request:**
```json
POST /api/generate-overlay
{
  "background_url": "https://runware.ai/output/abc123.jpg",
  "texts": [
    {"content": "ਦੀਵਾਲੀ ਵਿਸ਼ੇਸ਼", "type": "headline", "color": "#FFFFFF", "weight": "black"},
    {"content": "40% ਤੱਕ ਛੋਟ", "type": "subtext", "color": "#FFD700", "weight": "bold"},
    {"content": "ਹੁਣੇ ਖਰੀਦੋ", "type": "cta", "color": "#FFFFFF", "weight": "bold"}
  ],
  "language": "punjabi",
  "template_type": "festival",
  "brand_color": "#FF6B35"
}
```

**4. OverlayRenderer downloads background:**
```
GET https://runware.ai/output/abc123.jpg
→ Saved to /tmp/overlay-engine/bg_f8a2c1d3.jpg
```

**5. Calculate positions (festival template):**
```python
positions = [
    {"x": 0.5, "y": 0.35, "align": "center", "max_width": 0.85},  # Headline
    {"x": 0.5, "y": 0.50, "align": "center", "max_width": 0.85},  # Subtext
    {"x": 0.5, "y": 0.65, "align": "center", "max_width": 0.70}   # CTA
]
```

**6. Calculate font sizes:**
```python
font_sizes = [
    108,  # headline (1.5x base)
    72,   # subtext (1.0x base)
    58    # cta (0.8x base)
]
```

**7. Generate HTML:**
```html
<div style="position: absolute; left: 50%; top: 35%; font-size: 108px; ...">
    ਦੀਵਾਲੀ ਵਿਸ਼ੇਸ਼
</div>
<div style="position: absolute; left: 50%; top: 50%; font-size: 72px; ...">
    40% ਤੱਕ ਛੋਟ
</div>
<div style="position: absolute; left: 50%; top: 65%; font-size: 58px; background: #FF6B35; ...">
    ਹੁਣੇ ਖਰੀਦੋ
</div>
```

**8. Playwright renders:**
```
Launch Chromium → Load HTML → Wait for fonts → Screenshot at 2x DPI
→ Saved to /tmp/overlay-engine/output_9b3e4f5a.png
```

**9. Upload to R2:**
```
Upload /tmp/overlay-engine/output_9b3e4f5a.png
→ s3://brand-agency-creatives/overlays/20260204_143022_9b3e.png
→ https://cdn.yourdomain.com/overlays/20260204_143022_9b3e.png
```

**10. Return response:**
```json
{
  "success": true,
  "image_url": "https://cdn.yourdomain.com/overlays/20260204_143022_9b3e.png",
  "generation_time": 2.34,
  "metadata": {
    "template_type": "festival",
    "language": "punjabi",
    "text_blocks": 3,
    "dimensions": "1080x1080"
  }
}
```

**11. n8n sends WhatsApp message:**
```
📷 Your Diwali poster is ready!
[Image: https://cdn.yourdomain.com/overlays/...]
```

**Total time:** ~2-3 seconds (most time in Playwright rendering)

---

## Template System Explained

### Why Dynamic Templates?

**Problem:** Static positioning doesn't work for all use cases
- Festival posters need centered, balanced layout
- Discount offers need large, top-heavy headlines
- Product launches need space for product images
- Events need date/time prominence

**Solution:** Template-based position calculator

### Template Comparison

```
┌─────────────────────────────────────────────────────────┐
│              FESTIVAL TEMPLATE                          │
│                                                         │
│                  [ਦੀਵਾਲੀ ਵਿਸ਼ੇਸ਼]                      │
│                                                         │
│                  40% ਤੱਕ ਛੋਟ                           │
│                                                         │
│                  [ਹੁਣੇ ਖਰੀਦੋ]                          │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              OFFER TEMPLATE                             │
│                                                         │
│           *** 50% OFF ***                               │
│                                                         │
│                                                         │
│          ਸਭ ਤੋਂ ਵੱਡੀ ਛੋਟ                                │
│                                                         │
│                                                         │
│                  [ਹੁਣੇ ਆਰਡਰ ਕਰੋ]                      │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              PRODUCT TEMPLATE                           │
│                                                         │
│             [Product Image Space]                       │
│                                                         │
│                                                         │
│                                                         │
│                  ਨਵੀਂ ਆਮਦ                              │
│                  Premium Quality                        │
│                  [ਖਰੀਦੋ]                               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              EVENT TEMPLATE                             │
│                                                         │
│  ਸਟੋਰ ਓਪਨਿੰਗ                                           │
│                                                         │
│  15 ਫਰਵਰੀ, 2026                                        │
│  ਸਵੇਰੇ 10 ਵਜੇ                                          │
│                                                         │
│                                                         │
│                                    [Register] ───→      │
└─────────────────────────────────────────────────────────┘
```

### Customization

**Per-template overrides:**
```python
# In renderer.py, modify calculate_positions()
if template_type == "custom_wedding":
    layouts = {
        "headline": {"x": 0.5, "y": 0.15, "align": "center"},  # Top
        "subtext": {"x": 0.2, "y": 0.50, "align": "left"},     # Left side
        "cta": {"x": 0.8, "y": 0.85, "align": "right"}         # Bottom-right
    }
```

**Add new template type:**
1. Add to Pydantic enum: `template_type: Literal["festival", "offer", "product", "event", "wedding"]`
2. Add case in `calculate_positions()`
3. Document positioning logic

---

## Font Rendering Technology

### Why Playwright Instead of Pillow?

**Pillow (Python PIL) limitations:**
```python
# Pillow approach (DOESN'T WORK WELL)
from PIL import Image, ImageDraw, ImageFont

font = ImageFont.truetype("NotoSansGurmukhi.ttf", 72)
draw.text((x, y), "ਪੰਜਾਬੀ ਲਿਖਤ", font=font)
# Result: Matras misaligned, adhaks missing, ligatures broken
```

**Why?**
- Pillow uses FreeType directly (no text shaping engine)
- Indic scripts require complex glyph substitution (GSUB tables)
- Proper rendering needs HarfBuzz or similar shaping library

**Playwright (Chromium) advantages:**
```html
<div style="font-family: 'Noto Sans Gurmukhi', sans-serif;">
    ਪੰਜਾਬੀ ਲਿਖਤ
</div>
<!-- Chromium uses HarfBuzz internally → perfect rendering -->
```

### Font Loading Flow

**1. Google Fonts CDN:**
```html
<link href="https://fonts.googleapis.com/css2?
             family=Noto+Sans+Gurmukhi:wght@400;700;900
             &display=swap" rel="stylesheet">
```

**2. CSS applies font:**
```css
.punjabi-text {
    font-family: 'Noto Sans Gurmukhi', sans-serif;
}
```

**3. Chromium loads font:**
- Downloads .woff2 from Google's CDN
- Caches in memory
- Applies HarfBuzz shaping
- Renders with subpixel antialiasing

**4. Screenshot captures rendered pixels**

### Font Weight Mapping

```python
weight_to_css = {
    "normal": "400",  # Regular
    "bold": "700",    # Bold
    "black": "900"    # Black/Heavy
}
```

**Visual difference:**
- **Normal (400):** Body text, descriptions
- **Bold (700):** Headlines, emphasis
- **Black (900):** Maximum impact, hero text

---

## Local Testing Workflow

### Setup Steps

**1. Install dependencies:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Install system fonts (Linux)
sudo apt-get install fonts-noto-sans fonts-noto-sans-gurmukhi fonts-noto-sans-devanagari
```

**2. Configure environment:**
```bash
# Copy template
cp .env.example .env

# Edit (R2 credentials optional for local testing)
nano .env
```

**3. Start server:**
```bash
python main.py
# Server starts on http://localhost:8000
```

**4. Run test script:**
```bash
# In another terminal
python test_local.py
```

### Test Script Workflow

```python
# test_local.py does this:

1. Check health endpoint
   GET /health
   ✅ Service healthy

2. Generate test overlay
   POST /api/generate-overlay
   - Punjabi offer template
   - 3 text blocks
   - Unsplash background for testing
   
3. Display results
   ✅ Overlay generated (2.34s)
   🖼️ Image URL: file:///tmp/overlay-engine/output_abc123.png
   
4. Optional: Test all templates
   - Loop through 4 templates × 3 languages
   - 12 total test cases
   - Show success/failure for each
```

### Inspecting Outputs

```bash
# View generated HTML (before Playwright renders)
ls /tmp/overlay-engine/template_*.html

# Open in browser to debug positioning
firefox /tmp/overlay-engine/template_abc123.html

# View final PNG output
eog /tmp/overlay-engine/output_abc123.png
```

### Common Test Scenarios

**1. Test Punjabi offer:**
```bash
curl -X POST http://localhost:8000/api/generate-overlay \
  -H "Content-Type: application/json" \
  -d @test-data/punjabi-offer.json
```

**2. Test Hindi festival:**
```bash
curl -X POST http://localhost:8000/api/generate-overlay \
  -H "Content-Type: application/json" \
  -d @test-data/hindi-festival.json
```

**3. Test English product:**
```bash
curl -X POST http://localhost:8000/api/generate-overlay \
  -H "Content-Type: application/json" \
  -d @test-data/english-product.json
```

---

## Production Deployment

### Hetzner VPS Setup

**1. Create VPS:**
- CPX11: 2 vCPU, 4GB RAM, 40GB SSD (~€4.5/month)
- Ubuntu 24.04 LTS
- Enable IPv4

**2. Initial configuration:**
```bash
# SSH into VPS
ssh root@your-vps-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install docker-compose -y

# Create directory
mkdir -p /opt/text-overlay-engine
cd /opt/text-overlay-engine
```

**3. Deploy application:**
```bash
# Clone repository (or upload via SCP)
git clone <your-repo> .

# Configure environment
cp .env.example .env
nano .env  # Add R2 credentials

# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f
```

**4. Configure reverse proxy (Traefik):**
```yaml
# In main Traefik docker-compose.yml
services:
  overlay-engine:
    image: text-overlay-engine
    networks:
      - traefik
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.overlay.rule=Host(`overlay.yourdomain.com`)"
      - "traefik.http.routers.overlay.tls.certresolver=letsencrypt"
```

**5. DNS configuration:**
```
A record: overlay.yourdomain.com → VPS_IP
```

**6. Test deployment:**
```bash
curl https://overlay.yourdomain.com/health
# Should return: {"status": "healthy", ...}
```

### Performance Tuning

**Memory limits:**
```yaml
# docker-compose.yml
services:
  overlay-engine:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.5'
        reservations:
          memory: 1G
          cpus: '1.0'
```

**Auto-restart on crash:**
```yaml
services:
  overlay-engine:
    restart: unless-stopped
```

**Log rotation:**
```yaml
services:
  overlay-engine:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Monitoring

**Health checks:**
```bash
# Automated monitoring
*/5 * * * * curl -f https://overlay.yourdomain.com/health || systemctl restart docker-overlay
```

**Performance metrics:**
```python
# In main.py, add Prometheus metrics
from prometheus_client import Counter, Histogram

overlay_requests = Counter('overlay_requests_total', 'Total overlay requests')
overlay_duration = Histogram('overlay_duration_seconds', 'Overlay generation time')
```

---

## Integration Patterns

### n8n Workflow

**Complete workflow example:**

```
1. [Webhook] WhatsApp message received
   ↓
2. [Extract] Parse user intent
   - Detect: festival/offer/product keywords
   - Extract: business type, language preference
   ↓
3. [PocketBase: Read] Get client profile
   - Brand color, logo, business category
   ↓
4. [Gemini API] Generate marketing copy
   Prompt: "Create Punjabi marketing copy for {business_type} 
            about {intent}. Output JSON with headline, subtext, cta."
   Output: {
       "headline": "ਦੀਵਾਲੀ ਵਿਸ਼ੇਸ਼",
       "subtext": "40% ਛੋਟ ਸਾਰੇ ਉਤਪਾਦਾਂ 'ਤੇ",
       "cta": "ਹੁਣੇ ਖਰੀਦੋ"
   }
   ↓
5. [Runware API] Generate background
   Prompt: "Festive Diwali background with diyas and lights, 
            warm colors, no text, 1080x1080"
   Output: https://runware.ai/output/abc123.jpg
   ↓
6. [HTTP Request] Text Overlay Engine
   URL: https://overlay.yourdomain.com/api/generate-overlay
   Body: {
       "background_url": "{{$node['Runware'].json.image_url}}",
       "texts": [
           {
               "content": "{{$node['Gemini'].json.headline}}",
               "type": "headline",
               "color": "#FFFFFF",
               "weight": "black"
           },
           {
               "content": "{{$node['Gemini'].json.subtext}}",
               "type": "subtext",
               "color": "#FFD700",
               "weight": "bold"
           },
           {
               "content": "{{$node['Gemini'].json.cta}}",
               "type": "cta",
               "color": "#FFFFFF",
               "weight": "bold"
           }
       ],
       "language": "punjabi",
       "template_type": "festival",
       "brand_color": "{{$node['PocketBase'].json.brand_color}}"
   }
   Output: {
       "image_url": "https://cdn.yourdomain.com/overlays/..."
   }
   ↓
7. [PocketBase: Create] Store campaign
   - Client ID, image URL, copy text, timestamp
   ↓
8. [WhatsApp: Send Media] Deliver to client
   Media URL: {{$node['Overlay'].json.image_url}}
   Caption: "📷 Your Diwali poster is ready! Need any changes?"
```

### Error Handling in n8n

```
[HTTP Request: Overlay Engine]
  ├─ On Success: Continue to PocketBase
  └─ On Error: 
       ├─ Log error to PocketBase
       ├─ Send WhatsApp: "Sorry, image generation failed. Trying again..."
       └─ Retry with fallback template
```

### Webhook Security

```python
# In main.py, add authentication
from fastapi import Header, HTTPException

@app.post("/api/generate-overlay")
async def generate_overlay(
    request: OverlayRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")
```

**n8n configuration:**
```json
{
  "headers": {
    "X-API-Key": "{{$env.OVERLAY_API_KEY}}"
  }
}
```

---

## Troubleshooting & Debugging

### Common Issues

**1. Fonts not rendering:**
```
Symptom: Punjabi text shows as boxes (□□□)
Cause: Noto fonts not installed in Docker

Fix:
# In Dockerfile, ensure these lines exist:
RUN apt-get install -y \
    fonts-noto-sans-gurmukhi \
    fonts-noto-sans-devanagari

# Rebuild image:
docker-compose build --no-cache
```

**2. Background download timeout:**
```
Symptom: httpx.ReadTimeout after 30s
Cause: Slow Runware response or network issue

Fix:
# In services/renderer.py, increase timeout:
async with httpx.AsyncClient(timeout=60.0) as client:
    ...
```

**3. Playwright crashes:**
```
Symptom: Browser launch failed
Cause: Insufficient memory or missing dependencies

Fix:
# Check system resources:
docker stats

# Add memory limit in docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 2G

# Or install missing deps:
playwright install-deps chromium
```

**4. R2 upload fails:**
```
Symptom: botocore.exceptions.ClientError: 403 Forbidden
Cause: Invalid credentials or bucket permissions

Fix:
# Verify credentials in .env:
R2_ACCOUNT_ID=correct_id
R2_ACCESS_KEY_ID=correct_key
R2_SECRET_ACCESS_KEY=correct_secret

# Test R2 access:
aws s3 ls s3://brand-agency-creatives --endpoint-url https://ACCOUNT_ID.r2.cloudflarestorage.com
```

**5. Text positioning off:**
```
Symptom: Text overlaps or goes out of frame
Cause: Long text or incorrect template

Fix:
# Adjust max_width in calculate_positions():
{"x": 0.5, "y": 0.35, "max_width": 0.90}  # Increase from 0.85

# Or use smaller font size:
{"content": "...", "font_size": 60}  # Override auto-size
```

### Debug Mode

**Enable verbose logging:**
```python
# In main.py
logging.basicConfig(level=logging.DEBUG)

# In services/renderer.py
logger.debug(f"Positions calculated: {positions}")
logger.debug(f"Font sizes: {font_sizes}")
logger.debug(f"HTML generated: {len(html_content)} chars")
```

**Inspect HTML before rendering:**
```python
# In services/renderer.py, add after html generation:
debug_path = self.temp_dir / f"debug_{os.urandom(4).hex()}.html"
debug_path.write_text(html_content)
logger.info(f"Debug HTML: {debug_path}")
# Then open in browser: firefox /tmp/overlay-engine/debug_abc123.html
```

### Performance Profiling

```python
import time

# In main.py, add timing:
start = time.time()
background_path = await renderer.download_background(...)
logger.info(f"Download: {time.time() - start:.2f}s")

start = time.time()
output_path = await renderer.render_overlay(...)
logger.info(f"Render: {time.time() - start:.2f}s")

start = time.time()
image_url = await storage.upload_image(...)
logger.info(f"Upload: {time.time() - start:.2f}s")
```

**Optimize slow steps:**
- Download: Use cached backgrounds for repeated requests
- Render: Reduce output_width to 720x720 for testing
- Upload: Use local storage (no R2) during development

---

## Next Steps

### Phase 1 Completion Checklist

- [x] Core overlay engine working locally
- [ ] Deployed to VPS with R2 integration
- [ ] n8n workflow integrated
- [ ] 2-3 pilot clients tested
- [ ] Performance benchmarks met (<5s total)

### Phase 2 Enhancements

**Video output:**
- Add Remotion to generate Ken Burns effect videos
- Animate text entrance (fade in, slide up)
- Add background music for social media

**Quality audit:**
- Integrate Gemini Vision API
- Auto-score generated images (0-1 scale)
- Retry loop if score < 0.8 (max 3 attempts)

**Template library:**
- Store templates in PocketBase
- Admin UI to create custom layouts
- A/B testing with multiple templates per request

**Custom fonts:**
- Allow clients to upload brand fonts to R2
- Font management API endpoint
- Fallback to Noto if custom font fails

---

**End of Implementation Guide**

For questions or issues, check:
1. README.md for setup instructions
2. This guide for technical details
3. Docker logs: `docker-compose logs -f`
4. Test locally: `python test_local.py`
