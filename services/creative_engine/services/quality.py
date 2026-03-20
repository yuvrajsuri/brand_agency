"""
Quality Audit Service
Uses Gemini Vision to verify generated marketing creatives meet quality standards.
Replaces the n8n 09_svc_quality_audit workflow.
"""

import json
import logging
import base64
import httpx
from typing import Dict

from config import settings

logger = logging.getLogger(__name__)

PASS_THRESHOLD = settings.AUDIT_PASS_THRESHOLD

AUDIT_PROMPT = """\
You are a quality auditor for marketing creatives targeting small businesses in Punjab, India.

STYLE CONSTRAINTS: {style_constraints}
EXPECTED TEXT ON IMAGE: {expected_text}

Analyze this marketing poster image and return a JSON object (no markdown, no backticks):
{{
  "score": 0.0_to_1.0,
  "passed": true_or_false,
  "issues": ["list of specific problems"],
  "suggestions": ["how to fix each issue"]
}}

Check for:
1. Text is legible and properly rendered (no broken/garbled characters)
2. Text actually appears on the image
3. Color contrast is sufficient for readability
4. Style matches the given constraints
5. Culturally appropriate for Punjab/Indian audience
6. Professional quality — no AI artifacts, glitches, or distortions
7. Overall composition is balanced and visually appealing

Scoring guide:
- 0.9-1.0: Excellent, ready to send
- 0.85-0.9: Good, minor issues
- 0.7-0.85: Needs improvement
- Below 0.7: Major issues, must redo\
"""


class QualityAuditService:
    """Gemini Vision quality checker for generated creatives"""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.base_url = settings.GEMINI_BASE_URL
        self.model = settings.GEMINI_MODEL

    async def audit(
        self,
        image_url: str,
        expected_text: str,
        style_constraints: str = "Professional, culturally appropriate for Punjab"
    ) -> Dict:
        """
        Audit a generated creative image using Gemini Vision.

        Returns:
            dict with keys: passed (bool), score (float), issues (list), suggestions (list)
        """

        if not self.api_key:
            logger.warning("No Gemini key — skipping audit, auto-passing")
            return {"passed": True, "score": 1.0, "issues": [], "suggestions": []}

        # Download the image
        image_b64 = None
        mime_type = "image/png"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()
                image_b64 = base64.b64encode(resp.content).decode("utf-8")
                ct = resp.headers.get("content-type", "image/png")
                mime_type = ct.split(";")[0].strip()
        except Exception as e:
            logger.warning(f"Could not download image for audit ({e}) — using URL fallback")

        prompt_text = AUDIT_PROMPT.format(
            style_constraints=style_constraints,
            expected_text=expected_text
        )

        # Build Gemini request
        if image_b64:
            parts = [
                {"text": prompt_text},
                {"inlineData": {"mimeType": mime_type, "data": image_b64}}
            ]
        else:
            parts = [
                {"text": prompt_text},
                {"fileData": {"mimeType": "image/png", "fileUri": image_url}}
            ]

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": parts}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 512,
                            "responseMimeType": "application/json"
                        }
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Gemini Vision audit error: {response.status_code}")
                    return self._fallback_result()

                result = response.json()
                raw_text = result['candidates'][0]['content']['parts'][0]['text'].strip()

                try:
                    audit = json.loads(raw_text)
                except json.JSONDecodeError:
                    # Try extracting from markdown block
                    import re
                    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw_text)
                    if match:
                        audit = json.loads(match.group(1).strip())
                    else:
                        return self._fallback_result()

                score = float(audit.get("score", 0))
                passed = score >= PASS_THRESHOLD

                logger.info(f"Audit complete: score={score:.2f}, passed={passed}")

                return {
                    "passed": passed,
                    "score": score,
                    "issues": audit.get("issues", []),
                    "suggestions": audit.get("suggestions", [])
                }

        except Exception as e:
            logger.error(f"Quality audit failed: {e}", exc_info=True)
            return self._fallback_result()

    def _fallback_result(self) -> Dict:
        """Return a cautious fallback when audit cannot complete"""
        return {
            "passed": False,
            "score": 0.75,
            "issues": ["Could not complete automated audit"],
            "suggestions": ["Manual review recommended"]
        }
