import os
import json
import re
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class UnifiedAnalysis(BaseModel):
    # Financial data
    premium: int = Field(description="Annual premium amount as integer")
    payment_term: int = Field(description="Premium paying term in years")
    policy_term: int = Field(description="Total policy term in years")
    maturity_value: int = Field(description="Maturity benefit amount as integer")
    sum_assured: int = Field(description="Sum assured / death benefit as integer")
    
    # Qualitative insights
    policy_summary: str = Field(description="3-5 line simple summary of the policy")
    key_benefits: list[str] = Field(description="List of key benefits in bullet points")
    exclusions: list[str] = Field(description="List of exclusions in bullet points")
    hidden_clauses: list[str] = Field(description="List of hidden clauses or catch elements")

def unified_analyze(text: str) -> dict:
    """
    Performs a single consolidated AI analysis of the policy text.
    Combines financial extraction and qualitative insights into one call.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"error": "GEMINI_API_KEY not set"}

        client = genai.Client(api_key=api_key)
        
        # Clean text to remove extra whitespace and newlines for speed/token savings
        clean_text = re.sub(r'\s+', ' ', text).strip()

        prompt = f"""
        Analyze the insurance policy text below and extract all requested data.
        
        REQUIRED JSON FIELDS:
        1. premium: ANNUAL premium amount (integer). Look for "Annualized Premium" or repeating payments.
        2. payment_term: Years premiums are paid (PPT).
        3. policy_term: Total years of coverage.
        4. maturity_value: Amount paid at survival/maturity. 
        5. sum_assured: Death benefit amount.
        6. policy_summary: 3-5 sentence plain English summary.
        7. key_benefits: List of 4-6 bullet points (under 20 words each).
        8. exclusions: List of 3-5 things NOT covered.
        9. hidden_clauses: List of 3-5 tricky terms (lock-ins, suicide clause, GST impact).
        
        RULES:
        - If financial numbers are missing, use 0.
        - Use ONLY integers for amounts.
        - Return ONLY valid JSON.
        
        POLICY TEXT:
        {clean_text[:3000]}
        """

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=UnifiedAnalysis,
            ),
        )

        return json.loads(response.text)

    except Exception as e:
        print(f"UNIFIED ANALYZE ERROR: {str(e)}")
        # Return a partial structure so the pipeline doesn't crash
        return {
            "error": str(e),
            "status": "partial",
            "premium": 0, "payment_term": 0, "policy_term": 0, "maturity_value": 0, "sum_assured": 0,
            "policy_summary": "Analysis failed partially due to processing limits.",
            "key_benefits": [], "exclusions": [], "hidden_clauses": []
        }
