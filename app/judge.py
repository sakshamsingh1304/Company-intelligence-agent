"""
LLM Judge — turns enrichment signals into a structured verdict.
Uses Google Gemini API (free tier) for fast inference.
Produces: fit, confidence, follow-up question, and evidence-based reasoning (Task §4).
"""
import json
import logging

from groq import Groq

from app.config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert company intelligence analyst working for an AI automation startup.
Your job is to evaluate companies based on enrichment data and produce a structured verdict.

You must reason over the EVIDENCE provided — do NOT summarize. Instead, draw conclusions
from specific data points and explain WHY the company is or isn't a good fit.

Consider these evaluation criteria:
1. Technology adoption and digital maturity
2. Market presence and brand recognition
3. Industry relevance to AI/automation partnerships
4. Growth trajectory and innovation signals
5. Open-source engagement and developer ecosystem

Always respond with valid JSON matching this exact schema:
{
    "fit": "strong_fit" | "moderate_fit" | "weak_fit" | "no_fit",
    "confidence": <float 0.0 to 1.0>,
    "reasoning": "<evidence-based reasoning citing specific data points from the signals>",
    "follow_up_question": "<a specific, insightful question to ask during outreach to this company>"
}"""


USER_PROMPT_TEMPLATE = """Evaluate the following company based on the enrichment signals provided.

**Company:** {company_name}

**Enrichment Signals:**
```json
{signals_json}
```

Provide your structured verdict as JSON. Remember:
- "fit" must be one of: strong_fit, moderate_fit, weak_fit, no_fit
- "confidence" must be a float between 0.0 and 1.0
- "reasoning" must reference SPECIFIC evidence from the signals above
- "follow_up_question" must be specific and actionable for outreach

RESPOND WITH ONLY VALID JSON, NO EXTRA TEXT."""


def judge(company_name: str, signals: list[dict]) -> dict:
    """
    Send enrichment signals to the LLM and get a structured verdict.
    Returns dict with fit, confidence, reasoning, follow_up_question.
    """
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is not set")
        return {
            "fit": "no_fit",
            "confidence": 0.0,
            "reasoning": "LLM judge unavailable — GROQ_API_KEY not configured.",
            "follow_up_question": "N/A",
        }

    client = Groq(api_key=GROQ_API_KEY)
    
    signals_json = json.dumps(signals, indent=2, default=str)
    prompt = USER_PROMPT_TEMPLATE.format(
        company_name=company_name,
        signals_json=signals_json,
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content.strip()
            
            # Strip markdown formatting if the model returns it
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            verdict = json.loads(content.strip())

            # Validate required fields
            required = ["fit", "confidence", "reasoning", "follow_up_question"]
            for field in required:
                if field not in verdict:
                    verdict[field] = "N/A" if field != "confidence" else 0.0

            # Clamp confidence
            verdict["confidence"] = max(0.0, min(1.0, float(verdict["confidence"])))

            # Validate fit value
            valid_fits = {"strong_fit", "moderate_fit", "weak_fit", "no_fit"}
            if verdict["fit"] not in valid_fits:
                verdict["fit"] = "weak_fit"

            logger.info(f"LLM verdict for {company_name}: {verdict['fit']} "
                         f"(confidence: {verdict['confidence']})")
            return verdict

        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < max_retries - 1:
                logger.warning(f"Rate limit hit (429) for {company_name}. Retrying in 15s... (Attempt {attempt+1}/{max_retries})")
                import time
                time.sleep(15)
                continue
                
            logger.error(f"LLM judge failed for {company_name}: {e}")
            return {
                "fit": "no_fit",
                "confidence": 0.0,
                "reasoning": f"LLM judge error: {e}",
                "follow_up_question": "N/A",
            }
