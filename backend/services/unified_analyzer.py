import os
import json
import re
import time
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
    policy_summary: str = Field(
        description="""Write a clean, human-friendly summary of this policy in MAXIMUM 4-5 lines. 
RULES: Use simple everyday English — no legal jargon. Do NOT copy text from the document. Do NOT include definitions, clauses, or policy wording. Explain: (1) what the policy offers, (2) type of plan, (3) the key benefit (life cover / maturity / income), (4) overall usefulness for a buyer. Write as if explaining to a normal person, not a legal expert."""
    )
    key_benefits: list[str] = Field(
        description="REQUIRED — Do NOT return an empty array. List 5-8 specific key benefits. Include: financial protection, death benefit, maturity benefit, income payouts, premium waiver, riders, tax savings. Infer from context if not explicitly labeled. Each point must be 1-2 lines, clear and factual."
    )
    exclusions: list[str] = Field(
        description="REQUIRED — Do NOT return an empty array. List 3-5 situations where benefits are NOT paid. Include: medical non-disclosure, suicide clause, pre-existing conditions, GST/charges/deductions, any limitation or restriction. Infer from context if not explicitly labeled."
    )
    hidden_clauses: list[str] = Field(
        description="REQUIRED — Do NOT return an empty array. List 3-5 tricky terms or hidden conditions. Include: 'subject to...', 'only if...' conditions, policy changes over time, benefit reductions, lock-in periods, surrender charges, dependencies on age or term. Infer from context."
    )


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

    # Supplement with bullet/numbered lines containing benefit keywords
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
    # (Raw PDF lines are intentionally NOT used — they produce legal jargon)
    # The actual policy-type detection below builds the summary after type is known.
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
        # Generic fallback — use a couple of raw lines only as a hint
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
# HELPER: call Gemini with one retry on 429 rate-limit
# ---------------------------------------------------------------------------
def _call_gemini_with_retry(client, model: str, contents: str, config) -> str:
    """Call Gemini API with one automatic retry after 15s on 429 errors."""
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response.text
        except Exception as e:
            err = str(e)
            if ("429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower()):
                if attempt == 0:
                    print(f"GEMINI 429 RATE LIMIT — waiting 15s before retry...")
                    time.sleep(15)
                    continue
            raise  # re-raise non-429 errors or on second attempt
    return ""


# ---------------------------------------------------------------------------
# MERGE HELPER
# ---------------------------------------------------------------------------
def _merge_qualitative(merged: dict, new_data: dict) -> None:
    """Merge qualitative list fields from new_data into merged (deduplicating)."""
    for field in ("key_benefits", "exclusions", "hidden_clauses"):
        existing_lower = {s.lower().strip() for s in merged.get(field) or []}
        for item in new_data.get(field) or []:
            item_clean = str(item).strip()
            if item_clean and item_clean.lower() not in existing_lower:
                merged.setdefault(field, []).append(item_clean)
                existing_lower.add(item_clean.lower())

    if not merged.get("policy_summary") or merged["policy_summary"] in (
        "Analysis failed partially.", "Analysis failed partially due to processing limits.", ""
    ):
        if new_data.get("policy_summary"):
            merged["policy_summary"] = new_data["policy_summary"]


# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------
def unified_analyze(text: str) -> dict:
    """
    Chunked AI analysis of the policy text.
    - Financial data extracted from the FIRST chunk (calculation logic unchanged).
    - Qualitative insights (benefits, exclusions, hidden clauses) aggregated
      across ALL chunks so no section is missed.
    - On AI failure/quota error: falls back to regex extraction so fields
      are never empty.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("UNIFIED ANALYZE: No API key — using regex fallback")
            return _regex_fallback(text)

        client = genai.Client(api_key=api_key)

        # ---------------------------------------------------------------
        # CHUNK STRATEGY: 5500-char chunks with 300-char overlap
        # ---------------------------------------------------------------
        CHUNK_SIZE = 5500
        OVERLAP = 300
        clean_text = re.sub(r"\s+", " ", text).strip()

        chunks: list[str] = []
        start = 0
        while start < len(clean_text):
            end = start + CHUNK_SIZE
            chunks.append(clean_text[start:end])
            if end >= len(clean_text):
                break
            start = end - OVERLAP

        print(f"UNIFIED ANALYZE: {len(chunks)} chunk(s) to process")

        # ---------------------------------------------------------------
        # PASS 1: Full extraction on the FIRST chunk (financials + qualitative)
        # ---------------------------------------------------------------
        first_prompt = f"""
You are an expert insurance analyst. Analyze the insurance policy text below and extract ALL requested data.

IMPORTANT RULES — READ CAREFULLY:
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
   - Do NOT mention definitions, clause numbers, or policy wording.
   - Explain these 4 things naturally:
       a) What the policy offers (what it does for the buyer)
       b) Type of plan (term / endowment / ULIP / savings)
       c) The key benefit (life cover / maturity payout / income)
       d) Overall usefulness (who should buy it and why)
   - Write as if explaining to a normal person, not a lawyer or agent.

7. key_benefits — REQUIRED, minimum 3-5 items. Extract from:
   - Financial protection provided
   - Death benefit (sum assured or higher)
   - Maturity / survival benefit
   - Income payouts or cashback
   - Premium waiver benefits
   - Additional riders (accidental, critical illness, etc.)
   - Tax benefits under 80C / 10(10D)
   - Guaranteed vs non-guaranteed returns
   If none are labeled, infer from the policy description.

8. exclusions — REQUIRED, minimum 3-5 items. Extract from:
   - Situations where the death/maturity benefit is NOT paid
   - Medical non-disclosure or misrepresentation
   - Suicide clause (typically within 1st year)
   - Pre-existing conditions or waiting periods
   - GST, charges, or deductions not refunded
   - Hazardous activities or criminal acts
   If none are labeled, infer from standard exclusion patterns for this policy type.

9. hidden_clauses — REQUIRED, minimum 3-5 items. Extract from:
   - Conditional language: "subject to...", "only if...", "provided that..."
   - Policy changes over time (e.g., benefit reductions after age 60)
   - Surrender value below total premiums paid in early years
   - Lock-in periods or revival conditions
   - Non-guaranteed bonuses or market-linked charges
   - Any dependency on age, term, or other variables
   If none are labeled, infer from the policy structure and terms used.

POLICY TEXT:
{chunks[0]}
        """

        raw = _call_gemini_with_retry(
            client,
            model="gemini-2.0-flash",
            contents=first_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=UnifiedAnalysis,
            ),
        )

        merged = json.loads(raw) if raw else {}

        # Ensure list fields exist
        for f in ("key_benefits", "exclusions", "hidden_clauses"):
            if f not in merged:
                merged[f] = []

        # ---------------------------------------------------------------
        # PASS 2: Qualitative-only extraction on REMAINING chunks
        # ---------------------------------------------------------------
        class QualitativeOnly(BaseModel):
            policy_summary: str = Field(description="1-2 sentence summary of this section.")
            key_benefits: list[str] = Field(description="Benefits found in this section.")
            exclusions: list[str] = Field(description="Exclusions found in this section.")
            hidden_clauses: list[str] = Field(description="Hidden clauses in this section.")

        for i, chunk in enumerate(chunks[1:], start=2):
            try:
                q_prompt = f"""
You are an expert insurance analyst. This is part {i} of {len(chunks)} of an insurance policy document.
Extract ONLY qualitative information from this section.

IMPORTANT RULES:
- Do NOT return empty arrays.
- If data is not explicitly labeled, INFER from context.
- Always extract at least 3 meaningful points per section where relevant content exists.
- Keep each point under 20 words.
- Return ONLY valid JSON — no text outside JSON.

FIELDS TO EXTRACT:

1. policy_summary — Write 1-2 clean, human-friendly sentences about what this section covers.
   Use simple English. No legal jargon. No copying from text.

2. key_benefits — Look for:
   - Death benefit, maturity benefit, income payout, premium waiver
   - Riders: accidental death, critical illness, disability
   - Tax savings (80C / 10(10D)), guaranteed returns, bonuses
   - Return empty list ONLY if this section has zero benefit-related content.

3. exclusions — Look for:
   - Situations where benefit is NOT paid
   - Suicide clause, non-disclosure, pre-existing conditions
   - Hazardous activities, criminal acts, waiting periods
   - GST / charges not refunded
   - Return empty list ONLY if this section has zero exclusion-related content.

4. hidden_clauses — Look for:
   - Conditional language: "subject to", "only if", "provided that"
   - Surrender value limitations, lock-in periods, revival rules
   - Benefit reductions tied to age or term
   - Non-guaranteed bonus disclaimers
   - Return empty list ONLY if this section has zero clause-related content.

POLICY SECTION (Part {i} of {len(chunks)}):
{chunk}
                """

                raw_q = _call_gemini_with_retry(
                    client,
                    model="gemini-2.0-flash",
                    contents=q_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=QualitativeOnly,
                    ),
                )

                if raw_q:
                    chunk_data = json.loads(raw_q)
                    _merge_qualitative(merged, chunk_data)

            except Exception as chunk_err:
                print(f"CHUNK {i} QUALITATIVE ERROR: {chunk_err}")
                continue

        # ---------------------------------------------------------------
        # If AI returned empty qualitative fields, run regex fallback
        # ---------------------------------------------------------------
        if not merged.get("key_benefits") and not merged.get("exclusions"):
            print("UNIFIED ANALYZE: AI returned empty qualitative fields — running regex fallback")
            fallback = _regex_fallback(text)
            _merge_qualitative(merged, fallback)
            if not merged.get("policy_summary") or len(merged.get("policy_summary", "")) < 20:
                merged["policy_summary"] = fallback["policy_summary"]

        # Ensure premium_frequency is set (pipeline reads this)
        if "premium_frequency" not in merged:
            merged["premium_frequency"] = "yearly"

        return merged

    except Exception as e:
        print(f"UNIFIED ANALYZE ERROR: {str(e)}")
        # On any total failure, use regex fallback so qualitative fields are never blank
        fallback = _regex_fallback(text)
        fallback.update({
            "error": str(e),
            "status": "partial",
        })
        return fallback
