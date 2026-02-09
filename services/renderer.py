"""
Overlay Renderer Service
Uses Playwright to render text overlays with proper Punjabi/Hindi font support
"""

import asyncio
import os
import sys
import tempfile
import httpx
from pathlib import Path
from typing import List, Dict, Tuple
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)


class OverlayRenderer:
    """Handles text overlay rendering using Playwright for Indic script accuracy"""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "overlay-engine"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Font configurations for different languages
        self.font_config = {
            "punjabi": {
                "family": "Noto Sans Gurmukhi, sans-serif",
                "fallback": "Arial Unicode MS"
            },
            "hindi": {
                "family": "Noto Sans Devanagari, sans-serif",
                "fallback": "Arial Unicode MS"
            },
            "english": {
                "family": "Montserrat, sans-serif",
                "fallback": "Arial"
            }
        }
    
    async def download_background(self, url: str) -> Path:
        """Download background image from URL or use local file path"""
        try:
            # Check if it's a local file path (file:// or direct path)
            if url.startswith('file://'):
                # Extract the actual file path from file:// URL
                local_path = url.replace('file://', '')
                # On Windows, fix path separators
                if sys.platform == 'win32':
                    local_path = local_path.replace('/', '\\')
                local_path = Path(local_path)
                
                if local_path.exists():
                    logger.info(f"Using local file: {local_path}")
                    return local_path
                else:
                    raise FileNotFoundError(f"Local file not found: {local_path}")
            
            # Check if it's already a valid local path
            path_obj = Path(url)
            if path_obj.exists():
                logger.info(f"Using local file: {path_obj}")
                return path_obj
            
            # Otherwise, download from HTTP URL
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Save to temp file
                file_path = self.temp_dir / f"bg_{os.urandom(8).hex()}.jpg"
                file_path.write_bytes(response.content)
                
                logger.info(f"Background downloaded: {file_path}")
                return file_path
                
        except Exception as e:
            logger.error(f"Failed to download background: {str(e)}")
            raise
    
    def calculate_positions(
        self,
        template_type: str,
        text_blocks: List,
        image_width: int,
        image_height: int
    ) -> List[Dict]:
        """
        Calculate dynamic text positions based on template type
        
        Templates:
        - festival: Centered layout with vertical stacking
        - offer: Top-heavy with large headline
        - product: Bottom-third with product space on top
        - event: Asymmetric with date/time prominence
        """
        
        positions = []
        
        if template_type == "festival":
            # Centered vertical layout
            base_y = 0.35  # Start at 35% from top
            spacing = 0.15  # 15% spacing between elements
            
            for i, block in enumerate(text_blocks):
                positions.append({
                    "x": 0.5,  # Centered horizontally
                    "y": base_y + (i * spacing),
                    "align": "center",
                    "max_width": 0.85  # 85% of image width
                })
        
        elif template_type == "offer":
            # Top-heavy layout for discount/offers with better spacing
            layouts = {
                "headline": {"x": 0.5, "y": 0.18, "align": "center", "max_width": 0.85},
                "subtext": {"x": 0.5, "y": 0.50, "align": "center", "max_width": 0.80},
                "cta": {"x": 0.5, "y": 0.80, "align": "center", "max_width": 0.65}
            }
            
            for block in text_blocks:
                positions.append(layouts.get(block.type, layouts["headline"]))
        
        elif template_type == "product":
            # Bottom-third layout (product image on top)
            layouts = {
                "headline": {"x": 0.5, "y": 0.68, "align": "center", "max_width": 0.85},
                "subtext": {"x": 0.5, "y": 0.80, "align": "center", "max_width": 0.75},
                "cta": {"x": 0.5, "y": 0.90, "align": "center", "max_width": 0.6}
            }
            
            for block in text_blocks:
                positions.append(layouts.get(block.type, layouts["headline"]))
        
        elif template_type == "event":
            # Asymmetric layout for events
            layouts = {
                "headline": {"x": 0.15, "y": 0.20, "align": "left", "max_width": 0.75},
                "subtext": {"x": 0.15, "y": 0.40, "align": "left", "max_width": 0.70},
                "cta": {"x": 0.85, "y": 0.85, "align": "right", "max_width": 0.50}
            }
            
            for block in text_blocks:
                positions.append(layouts.get(block.type, layouts["headline"]))
        
        else:
            # Default centered layout
            for i, block in enumerate(text_blocks):
                positions.append({
                    "x": 0.5,
                    "y": 0.4 + (i * 0.15),
                    "align": "center",
                    "max_width": 0.85
                })
        
        return positions
    
    def calculate_font_sizes(
        self,
        text_blocks: List,
        base_size: int = 72
    ) -> List[int]:
        """Calculate responsive font sizes based on text block type"""
        
        size_multipliers = {
            "headline": 1.5,   # 108px at base 72
            "subtext": 1.0,    # 72px
            "cta": 0.8         # 58px
        }
        
        sizes = []
        for block in text_blocks:
            multiplier = size_multipliers.get(block.type, 1.0)
            
            # Use custom size if provided, otherwise calculate
            if block.font_size:
                sizes.append(block.font_size)
            else:
                sizes.append(int(base_size * multiplier))
        
        return sizes
    
    def get_flex_config(self, template_type: str) -> dict:
        """
        Return flexbox CSS configuration for template type
        This replaces the brittle absolute positioning approach
        """
        
        configs = {
            "festival": {
                "justify-content": "center",
                "align-items": "center",
                "gap": "30px",
                "padding": "60px 40px"
            },
            "offer": {
                "justify-content": "center",
                "align-items": "center",
                "gap": "40px",  # More space for offers
                "padding": "60px 40px"
            },
            "product": {
                "justify-content": "flex-end",
                "align-items": "center",
                "gap": "20px",
                "padding": "40px 40px 80px 40px"  # Bottom-heavy
            },
            "event": {
                "justify-content": "space-between",
                "align-items": "flex-start",
                "gap": "20px",
                "padding": "60px 40px"
            }
        }
        
        return configs.get(template_type, configs["festival"])
    
    async def render_overlay(
        self,
        background_path: Path,
        text_blocks: List,
        positions: List[Dict],
        language: str,
        brand_color: str,
        output_width: int,
        output_height: int,
        template_type: str = "festival"  # Add template_type parameter
    ) -> Path:
        """
        Render text overlay using Playwright for accurate Indic script rendering
        """
        
        # Calculate font sizes
        font_sizes = self.calculate_font_sizes(text_blocks)
        
        # Get font family for language
        font_family = self.font_config[language]["family"]
        
        # Generate HTML template with flexbox layout
        html_content = self._generate_html_template(
            background_path=background_path,
            text_blocks=text_blocks,
            positions=positions,  # Not used anymore, kept for compatibility
            font_sizes=font_sizes,
            font_family=font_family,
            brand_color=brand_color,
            output_width=output_width,
            output_height=output_height,
            template_type=template_type  # Pass template_type for flex config
        )
        
        # Save HTML to temp file
        html_path = self.temp_dir / f"template_{os.urandom(8).hex()}.html"
        html_path.write_text(html_content, encoding='utf-8')
        
        # Render with Playwright
        output_path = await self._render_with_playwright(
            html_path=html_path,
            output_width=output_width,
            output_height=output_height
        )
        
        logger.info(f"Overlay rendered: {output_path}")
        return output_path
    
    def _generate_html_template(
        self,
        background_path: Path,
        text_blocks: List,
        positions: List[Dict],  # Kept for backward compatibility, but not used
        font_sizes: List[int],
        font_family: str,
        brand_color: str,
        output_width: int,
        output_height: int,
        template_type: str = "festival"
    ) -> str:
        """Generate HTML template with FLEXBOX layout (best practice)"""
        
        # Convert background to base64 for embedding
        import base64
        bg_data = background_path.read_bytes()
        bg_base64 = base64.b64encode(bg_data).decode('utf-8')
        
        # Get flexbox configuration for this template
        flex_config = self.get_flex_config(template_type)
        
        # Build text elements WITHOUT absolute positioning
        text_elements = []
        
        for i, (block, size) in enumerate(zip(text_blocks, font_sizes)):
            css_class = f"text-{block.type}"  # text-headline, text-subtext, text-cta
            
            # Base style for all text elements
            style = f"""
                font-size: {size}px;
                font-weight: {block.weight};
                color: {block.color};
                line-height: 1.6;
                font-family: {font_family};
                text-align: center;
                max-width: 90%;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
                text-rendering: optimizeLegibility;
                word-wrap: break-word;
                overflow-wrap: break-word;
            """
            
            # Add text shadow for headline and subtext (not CTA)
            if block.type != "cta":
                style += "text-shadow: 2px 2px 12px rgba(0,0,0,0.8);"
            
            # Special styling for CTA buttons
            if block.type == "cta":
                style += f"""
                    background: {brand_color};
                    padding: 20px 40px;
                    border-radius: 50px;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
                    display: inline-block;
                    text-shadow: none;
                """
            
            text_elements.append(f'<div class="{css_class}" style="{style}">{block.content}</div>')
        
        # Complete HTML with Flexbox layout
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Gurmukhi:wght@400;700;900&family=Noto+Sans+Devanagari:wght@400;700;900&family=Montserrat:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            overflow: hidden;
        }}
        
        .container {{
            width: {output_width}px;
            height: {output_height}px;
            position: relative;
            overflow: hidden;
        }}
        
        .background {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            position: absolute;
            top: 0;
            left: 0;
        }}
        
        .content-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: {flex_config['justify-content']};
            align-items: {flex_config['align-items']};
            gap: {flex_config['gap']};
            padding: {flex_config['padding']};
            z-index: 10;
        }}
    </style>
</head>
<body>
    <div class="container">
        <img src="data:image/jpeg;base64,{bg_base64}" class="background" alt="Background">
        <div class="content-overlay">
            {''.join(text_elements)}
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    async def _render_with_playwright(
        self,
        html_path: Path,
        output_width: int,
        output_height: int
    ) -> Path:
        """Use Playwright to render HTML to PNG with proper font rendering"""
        
        output_path = self.temp_dir / f"output_{os.urandom(8).hex()}.png"
        
        async with async_playwright() as p:
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)
            
            # Create page with exact dimensions
            page = await browser.new_page(
                viewport={"width": output_width, "height": output_height},
                device_scale_factor=2  # 2x resolution for crisp text
            )
            
            # Load HTML file
            await page.goto(f"file://{html_path.absolute()}")
            
            # Wait for fonts to load
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(0.5)  # Extra time for font rendering
            
            # Take screenshot
            await page.screenshot(
                path=str(output_path),
                full_page=False,
                omit_background=False
            )
            
            await browser.close()
        
        return output_path