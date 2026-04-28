import os
import json
import re
import time
from google import genai
from google.genai import types


# ---------------------------------------------------------------------------
# REGEX FALLBACK: extracts qualitative fields directly from text when AI fails
# ---------------------------------------------------------------------------
def _regex_fallback(text: str) -> dict:
    """
    Extract qualitative fields from policy text using keyword/section matching.
    Used when AI is unavailable (quota exhausted, network error, etc.)
    Guarantees minimum 3–5 items per section by inferring from policy type
    when regex extraction yields insufficient results.
    """
    text_lower = text.lower()
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # ---- Helper: collect lines near a section heading ----
    def collect_section(heading_kws: list[str], max_lines: int = 15) -> list[str]:
        items = []
        in_section = False
        count = 0
        stop_kws = [
            "exclusion", "benefit", "clause", "condition", "eligibility",
            "premium", "maturity", "section", "note:", "page", "---"
        ]
        for line in lines:
            ll = line.lower()
            if any(kw in ll for kw in heading_kws):
                in_section = True
                count = 0
                continue
            if in_section:
                if count >= max_lines:
                    break
                if len(line) < 10:
                    continue
                # Stop if another major heading detected
                if any(kw in ll for kw in stop_kws) and count > 2:
                    break
                items.append(line)
                count += 1
        return items

    # ---- Benefits ----
    benefit_kws = ["key benefit", "main benefit", "policy benefit", "what you get",
                   "advantages", "features", "highlights", "coverage include"]
    benefits = collect_section(benefit_kws, max_lines=10)

    benefit_signal = [
        "death benefit", "maturity benefit", "survival benefit", "sum assured",
        "tax benefit", "bonus", "rider", "cover", "waiver", "accidental",
        "critical illness", "guaranteed", "lump sum", "income payout",
        "80c", "10(10d)", "life cover", "insurance cover", "income payout",
        "critical illness cover", "disability", "cashback", "money back"
    ]
    for line in lines:
        ll = line.lower()
        if any(sig in ll for sig in benefit_signal):
            clean = re.sub(r"^[\*\-•\d\.\)]+\s*", "", line).strip()
            if 10 < len(clean) < 200 and clean not in benefits:
                benefits.append(clean)
        if len(benefits) >= 8:
            break

    # ---- Exclusions ----
    exclusion_kws = ["exclusion", "not covered", "what is not", "does not cover",
                     "excluded", "exceptions", "not payable"]
    exclusions = collect_section(exclusion_kws, max_lines=10)

    exclusion_signal = [
        "suicide", "pre-existing", "self-inflicted", "war", "terrorism",
        "criminal", "waiting period", "hazardous", "aviation", "not payable",
        "not covered", "excluded if", "not applicable", "non-disclosure",
        "misrepresentation", "fraud", "intoxication", "drug", "alcohol"
    ]
    for line in lines:
        ll = line.lower()
        if any(sig in ll for sig in exclusion_signal):
            clean = re.sub(r"^[\*\-•\d\.\)]+\s*", "", line).strip()
            if 10 < len(clean) < 200 and clean not in exclusions:
                exclusions.append(clean)
        if len(exclusions) >= 6:
            break

    # ---- Hidden clauses ----
    hidden_kws = ["hidden clause", "important condition", "terms and condition",
                  "lock-in", "surrender", "cooling off", "free look",
                  "grace period", "lapse", "revival", "subject to"]
    hidden = collect_section(hidden_kws, max_lines=10)

    hidden_signal = [
        "lock-in", "surrender value", "free look period", "cooling off",
        "grace period", "lapse", "revival", "non-forfeiture", "gst",
        "service tax", "suicide clause", "moral hazard", "substandard",
        "loading", "extra premium", "policy lapse", "paid-up",
        "subject to", "only if", "provided that", "condition precedent",
        "at the discretion", "may vary", "not guaranteed"
    ]
    for line in lines:
        ll = line.lower()
        if any(sig in ll for sig in hidden_signal):
            clean = re.sub(r"^[\*\-•\d\.\)]+\s*", "", line).strip()
            if 10 < len(clean) < 200 and clean not in hidden:
                hidden.append(clean)
        if len(hidden) >= 6:
            break

    # ---- Summary: build a clean, human-friendly version inferred from policy type ----
    _raw_summary_lines = []
    for line in lines[:50]:
        if len(line) > 40:
            _raw_summary_lines.append(line)
        if len(_raw_summary_lines) >= 2:
            break

    # Deduplicate
    def dedup(lst):
        seen = set()
        out = []
        for item in lst:
            k = item.lower()
            if k not in seen:
                seen.add(k)
                out.append(item)
        return out

    benefits   = dedup(benefits)[:8]
    exclusions = dedup(exclusions)[:6]
    hidden     = dedup(hidden)[:6]

    # ------------------------------------------------------------------
    # GUARANTEED MINIMUMS — detect policy type and inject inferred
    # defaults so sections are NEVER empty regardless of PDF quality.
    # ------------------------------------------------------------------
    is_term  = any(kw in text_lower for kw in
                   ["term plan", "pure risk", "click2protect", "term insurance",
                    "term life", "non-linked, non-participating"])
    is_ulip  = any(kw in text_lower for kw in
                   ["ulip", "unit linked", "fund value", "nav", "market linked"])
    is_endow = any(kw in text_lower for kw in
                   ["endowment", "money back", "jeevan", "savings plan", "participating"])

    # --- Benefit defaults (inferred from policy type) ---
    if len(benefits) < 3:
        if is_term:
            term_defaults = [
                "High life cover (sum assured) paid to nominee on policyholder's death during the policy term",
                "Affordable premiums compared to the large death benefit provided",
                "Tax deduction on premiums paid under Section 80C of the Income Tax Act",
                "Tax-free death benefit received by nominee under Section 10(10D)",
                "Optional riders available: accidental death, critical illness, disability waiver",
            ]
        elif is_ulip:
            term_defaults = [
                "Life cover (sum assured) paid to nominee on death during the policy term",
                "Market-linked wealth creation through investment in equity or debt funds",
                "Flexibility to switch between funds based on market conditions",
                "Partial withdrawals allowed after the mandatory 5-year lock-in period",
                "Tax benefits on premiums paid under Section 80C (up to ₹1.5 lakh per year)",
            ]
        else:
            term_defaults = [
                "Guaranteed death benefit equal to sum assured paid to nominee on death",
                "Maturity benefit paid as lump sum to policyholder at the end of the policy term",
                "Bonus additions (reversionary and terminal) may enhance the overall corpus",
                "Tax savings on premiums under Section 80C of the Income Tax Act",
                "Tax-free maturity proceeds under Section 10(10D) of the Income Tax Act",
            ]
        for d in term_defaults:
            if d not in benefits:
                benefits.append(d)
            if len(benefits) >= 5:
                break

    # --- Exclusion defaults (universal for all Indian life insurance) ---
    if len(exclusions) < 3:
        excl_defaults = [
            "Death by suicide within 12 months of policy issuance — only 80% of premiums paid refunded to nominee",
            "Non-disclosure or misrepresentation of health/lifestyle facts at application — claim can be rejected",
            "Death due to participation in hazardous activities, criminal acts, or involvement in war/terrorism",
            "Pre-existing medical conditions not declared at inception may lead to claim repudiation",
            "GST and applicable government taxes are charged over and above the premium — not refundable on exit",
        ]
        for d in excl_defaults:
            if d not in exclusions:
                exclusions.append(d)
            if len(exclusions) >= 5:
                break

    # --- Hidden clause defaults (universal for all Indian life insurance) ---
    if len(hidden) < 3:
        clause_defaults = [
            "Free-look period of 15–30 days: policy can be returned for refund minus proportionate risk premium and stamp duty",
            "Grace period of 15–30 days allowed for delayed premium payment; policy lapses if not paid within this window",
            "A lapsed policy can only be revived by paying all outstanding premiums with interest within the revival period",
            "Surrender value in early years is significantly lower than total premiums paid — exiting early leads to a loss",
            "Bonus declarations (if any) are at the discretion of the insurer and are NOT guaranteed contractually",
        ]
        for d in clause_defaults:
            if d not in hidden:
                hidden.append(d)
            if len(hidden) >= 5:
                break

    # Build a clean, human-friendly summary based on detected policy type
    if is_term:
        summary = (
            "This is a term life insurance plan that provides a large lump-sum payout to your family "
            "if you pass away during the policy period. "
            "You pay a small premium each year in exchange for a high life cover amount. "
            "There is no maturity benefit — it is purely designed to protect your loved ones financially. "
            "It is ideal for people who want maximum life cover at the lowest possible cost."
        )
    elif is_ulip:
        summary = (
            "This is a ULIP (Unit Linked Insurance Plan) that combines life insurance with market-linked investments. "
            "Part of your premium buys life cover, and the rest is invested in funds of your choice. "
            "Your returns depend on how the market performs, so they are not guaranteed. "
            "It is suitable for people who want both wealth creation and life cover in a single plan, and are comfortable with some investment risk."
        )
    elif is_endow:
        summary = (
            "This is a savings-cum-insurance plan that gives you guaranteed money back at the end of the policy term "
            "along with life cover throughout. "
            "If you survive the full term, you receive a maturity amount; if not, your family receives the death benefit. "
            "It also offers tax savings on premiums paid. "
            "It suits people who want safe, guaranteed returns with built-in life protection."
        )
    else:
        hint = " ".join(_raw_summary_lines).strip()
        if hint:
            summary = (
                f"This insurance policy provides financial protection and key benefits to the policyholder and their family. "
                f"It offers life cover along with potential savings or income benefits depending on the plan structure. "
                f"Premiums are paid regularly over the policy term, and benefits are paid as per the plan terms. "
                f"It is suitable for individuals looking for a combination of protection and long-term financial planning."
            )
        else:
            summary = (
                "This insurance policy provides financial protection for you and your family. "
                "It covers the risk of death during the policy term and may offer maturity or savings benefits. "
                "Regular premiums are paid to keep the policy active, and tax benefits may apply. "
                "It is a useful tool for long-term financial security and family protection."
            )

    return {
        "premium": 0,
        "payment_term": 0,
        "policy_term": 0,
        "maturity_value": 0,
        "sum_assured": 0,
        "policy_summary": summary,
        "key_benefits": benefits[:8],
        "exclusions": exclusions[:6],
        "hidden_clauses": hidden[:6],
    }


# ---------------------------------------------------------------------------
# SINGLE-CALL GEMINI ANALYSIS FUNCTION
# ---------------------------------------------------------------------------
def analyze_policy(text: str) -> dict:
    """
    Analyze insurance policy text using a SINGLE Gemini API call.
    Returns structured qualitative insights.
    Falls back to safe defaults if API or parsing fails.
    """
    FAILSAFE = {
        "summary": "Analysis unavailable",
        "key_benefits": [],
        "hidden_clauses": [],
        "exclusions": [],
        "risk_level": "Unknown",
    }

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return FAILSAFE

        client = genai.Client(api_key=api_key)

        # Truncate to avoid hitting token limits
        policy_text = text[:8000]

        prompt = f"""Return ONLY valid JSON. No explanation.

Extract the following from the insurance policy text:

{{
  "summary": "Explain the policy in 4-5 simple lines in plain English",
  "key_benefits": ["List the main benefits clearly"],
  "hidden_clauses": ["List important hidden or tricky clauses"],
  "exclusions": ["List what is NOT covered"],
  "risk_level": "Low or Medium or High based on overall risk"
}}

If any field is missing, return an empty list or "Unknown".
Do not include markdown or extra text.

Policy Text:
{policy_text}"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        data = json.loads(response.text)
        return data

    except Exception:
        return FAILSAFE


# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def unified_analyze(text: str) -> dict:
    """
    Single-call AI analysis of the policy text.
    Makes ONLY ONE Gemini API call per request to prevent 429 errors.
    Falls back to regex extraction on AI failure.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("UNIFIED ANALYZE: No API key — using regex fallback")
            return _regex_fallback(text)

        client = genai.Client(api_key=api_key)

        # Truncate text to reduce token usage and avoid chunked multi-calls
        clean_text = re.sub(r"\s+", " ", text).strip()
        policy_text = clean_text[:8000]

        prompt = f"""You are an expert insurance analyst. Analyze the insurance policy text below and extract ALL requested data.

IMPORTANT RULES:
- Do NOT return empty arrays for key_benefits, exclusions, or hidden_clauses.
- If data is not explicitly labeled in the text, INFER from context.
- Always extract at least 3-5 meaningful points per qualitative section.
- Keep each point short and clear (1-2 lines, under 20 words).
- Do NOT skip any section.
- Use 0 for missing financial integer fields.
- Return ONLY valid JSON — no explanations outside JSON.

FINANCIAL FIELDS:
1. premium: ANNUAL premium amount (integer). Look for "Annualized Premium" or repeating payments.
2. payment_term: Years premiums are paid (PPT).
3. policy_term: Total years of coverage.
4. maturity_value: Amount paid at survival/maturity.
5. sum_assured: Death benefit / sum assured amount.

QUALITATIVE FIELDS:
6. policy_summary — STRICT RULES:
   - MAXIMUM 4-5 lines only. No more.
   - Use simple, everyday English. Zero legal jargon.
   - Do NOT copy any sentence from the policy text.
   - Explain: what the policy offers, type of plan, key benefit, overall usefulness.
   - Write as if explaining to a normal person, not a lawyer or agent.

7. key_benefits — REQUIRED, minimum 3-5 items. Include death benefit, maturity benefit,
   income payouts, premium waiver, riders, tax savings. Infer from context if not labeled.

8. exclusions — REQUIRED, minimum 3-5 items. Include situations where benefit is NOT paid:
   medical non-disclosure, suicide clause, pre-existing conditions, GST/charges, hazardous activities.
   Infer from standard patterns if not labeled.

9. hidden_clauses — REQUIRED, minimum 3-5 items. Include conditional language, surrender value
   limitations, lock-in periods, non-guaranteed bonuses, revival conditions.
   Infer from policy structure if not labeled.

Return a JSON object with these exact keys:
premium, payment_term, policy_term, maturity_value, sum_assured,
policy_summary, key_benefits, exclusions, hidden_clauses

POLICY TEXT:
{policy_text}"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        # Parse response
        raw = response.text if response else ""
        if not raw:
            raise ValueError("Empty response from Gemini")

        # Strip markdown fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        cleaned = re.sub(r"\s*```\s*$", "", cleaned).strip()

        # Try direct parse first
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: extract JSON object from response
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                result = json.loads(match.group(0))
            else:
                raise ValueError("No valid JSON found in response")

        # Ensure list fields exist
        for f in ("key_benefits", "exclusions", "hidden_clauses"):
            if f not in result or not isinstance(result[f], list):
                result[f] = []

        # If AI returned empty qualitative fields, supplement with regex fallback
        if not result.get("key_benefits") and not result.get("exclusions"):
            print("UNIFIED ANALYZE: AI returned empty qualitative fields — running regex fallback")
            fallback = _regex_fallback(text)
            for f in ("key_benefits", "exclusions", "hidden_clauses"):
                if not result.get(f):
                    result[f] = fallback.get(f, [])
            if not result.get("policy_summary") or len(result.get("policy_summary", "")) < 20:
                result["policy_summary"] = fallback["policy_summary"]

        # Ensure premium_frequency is set (pipeline reads this)
        if "premium_frequency" not in result:
            result["premium_frequency"] = "yearly"

        return result

    except Exception as e:
        print(f"UNIFIED ANALYZE ERROR: {str(e)}")
        # On any total failure, use regex fallback so qualitative fields are never blank
        fallback = _regex_fallback(text)
        fallback.update({
            "error": str(e),
            "status": "partial",
        })
        return fallback
