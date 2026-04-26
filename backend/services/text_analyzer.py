import os
import json
import re
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class PolicyInsights(BaseModel):
    policy_summary: str = Field(description="A comprehensive, well-structured paragraph summarizing the policy's purpose, main benefits, target audience, and key financial terms in plain English. Avoid jargon.")
    key_benefits: list[str] = Field(description="List of 5-8 highly specific, impactful, and user-friendly key benefits extracted from the policy. Focus on exact numbers, guaranteed returns, tax savings, riders, and unique perks. Make them read like premium marketing highlights but remain strictly factual.")
    exclusions: list[str] = Field(description="List of exclusions in simple, user-friendly bullet points (under 20 words each).")
    hidden_clauses: list[str] = Field(description="List of hidden clauses or catch elements into simple, user-friendly bullet points (under 20 words each).")


# ---------------------------------------------------------------------------
# Regex-based benefit extractor — runs as a safety-net when AI returns nothing
# ---------------------------------------------------------------------------
_BENEFIT_PHRASES = [
    # Death / life cover
    (r"death\s+benefit", "Death benefit paid to nominee upon insured's death"),
    (r"life\s+cover", "Life cover provides financial protection to your family"),
    (r"sum\s+assured", "Guaranteed sum assured paid on maturity or death"),
    # Maturity
    (r"maturity\s+(benefit|amount|value)", "Lump-sum maturity benefit paid at end of policy term"),
    (r"survival\s+benefit", "Survival benefit paid if insured survives the policy term"),
    # Bonus
    (r"(loyalty|guaranteed|simple\s+reversionary|terminal)\s+bonus", "Bonus additions enhance policy returns over time"),
    (r"bonus\s+accrues", "Annual bonus accrues to increase policy value"),
    # Tax
    (r"(tax\s+benefit|section\s+80c|80\s*c\s+deduction)", "Tax deduction benefit under Section 80C on premiums paid"),
    (r"(maturity\s+proceeds.*tax\s+free|section\s+10.*10d)", "Tax-free maturity proceeds under Section 10(10D)"),
    # Rider / waiver
    (r"waiver\s+of\s+premium", "Premium waiver benefit — future premiums waived on disability"),
    (r"(accidental\s+death\s+benefit|adb)", "Accidental death benefit provides additional payout"),
    (r"critical\s+illness", "Critical illness rider covers major diseases like cancer or heart attack"),
    (r"disability\s+(benefit|rider)", "Disability benefit provides income support on permanent disability"),
    # Loan
    (r"(policy\s+loan|loan\s+against\s+policy)", "Policy loan facility available after minimum premium payments"),
    # Surrender
    (r"surrender\s+value", "Surrender value available if policy is discontinued after lock-in"),
    # Partial withdrawal
    (r"partial\s+withdrawal", "Partial withdrawal allowed after lock-in period"),
    # Guaranteed returns
    (r"guaranteed\s+(return|addition|benefit|maturity)", "Guaranteed returns — policy value is not market-linked"),
    # Flexible premium
    (r"flexible\s+premium", "Flexible premium payment options available"),
    # Grace period
    (r"grace\s+period", "Grace period provided for delayed premium payment"),
    # Nominee
    (r"nominee|nomination", "Nominee receives policy benefits in case of insured's death"),
    # Whole life / endowment
    (r"whole\s+life\s+(cover|coverage|protection)", "Whole life coverage — protection for entire lifetime"),
    (r"endowment", "Endowment plan — provides both savings and life cover"),
    # Money back
    (r"money.?back", "Money-back feature pays periodic survival payouts during policy term"),
    # ULIP
    (r"(fund\s+switch|switch\s+fund)", "Free fund switch facility to change investment allocation"),
    (r"unit.?linked", "Market-linked investment component for potential higher returns"),
]

# ---------------------------------------------------------------------------
# Regex-based hidden-clause extractor — mirrors the benefit extractor approach
# ---------------------------------------------------------------------------
_HIDDEN_CLAUSE_PHRASES = [
    # Suicide / self-harm
    (r"suicide", "Suicide within first year is not covered — policy becomes void"),
    # Lock-in period
    (r"lock.?in\s+period", "Lock-in period applies — early exit may result in penalties or no returns"),
    # Waiting period
    (r"waiting\s+period", "Waiting period clause — certain claims not payable during initial months"),
    # Lapse / revival
    (r"policy.*lapse|lapse.*policy", "Policy lapses if premium is unpaid beyond grace period — all benefits lost"),
    (r"revival\s+(of\s+)?policy|policy\s+revival", "Revival of lapsed policy may require medical evidence and extra charges"),
    # Free-look / cooling-off
    (r"free.?look", "Free-look period — you can return the policy within 15-30 days for a refund"),
    # Non-disclosure / misrepresentation
    (r"(non.?disclosure|misrepresent|mis.?statement)", "Non-disclosure of medical history can void the claim entirely"),
    # Nomination restriction
    (r"nomination\s+(change|restriction)", "Nomination changes require written intimation and insurer's confirmation"),
    # Cooling period
    (r"cooling.?off\s+period", "Cooling-off period — policy cancellable with refund only within limited window"),
    # Pre-existing conditions
    (r"pre.?existing\s+(condition|disease|illness)", "Pre-existing conditions may not be covered for a defined waiting period"),
    # Assignment
    (r"(policy\s+assignment|assigned\s+policy)", "Policy assignment transfers ownership — original nominee rights may be affected"),
    # Surrender penalty
    (r"(surrender\s+charge|surrender\s+penalty|surrender\s+deduction)", "Surrender charges apply if policy is exited before maturity"),
    # GST / charges on premium
    (r"(gst|goods\s+and\s+service\s+tax).*premium", "GST is levied on premiums and is not returned at maturity"),
    # Market risk (ULIP)
    (r"market\s+risk|fund.*risk", "Returns are market-linked — insurer does not guarantee investment performance"),
    # Fund management charge
    (r"fund\s+management\s+charge", "Annual fund management charges reduce your effective investment returns"),
    # Mortality charge
    (r"mortality\s+charge", "Mortality charges deducted from your fund reduce the investable corpus"),
    # Claim rejection
    (r"(claim.*reject|repudiat)", "Insurer can reject claims if policy conditions or disclosures are violated"),
    # Cooling period after accident / disease
    (r"(exclusion.*accident|accident.*exclusion)", "Accidental death benefit excluded if accident occurs under influence of alcohol"),
    # Sum assured reduction
    (r"(paid.?up|reduced\s+paid.?up)", "Policy becomes paid-up (reduced cover) if premiums stop after minimum period"),
    # Fronting / policy term reduction
    (r"(alteration|policy\s+alteration)", "Policy alteration may reset certain waiting periods or benefit levels"),
    # Hazardous activity
    (r"(hazardous|adventure\s+sport|risky\s+activit)", "Death during hazardous activities or adventure sports may not be covered"),
    # Grace period expiry
    (r"grace\s+period", "Grace period is typically 30 days — no claim payable if insured dies after lapse"),
    # Contestability
    (r"incontestab", "Contestability clause — insurer can dispute claim within 2 years of policy issue"),
]

# ---------------------------------------------------------------------------
# Regex-based exclusion extractor — mirrors the benefit extractor approach
# ---------------------------------------------------------------------------
_EXCLUSION_PHRASES = [
    # Suicide
    (r"suicide", "Suicide or self-inflicted injury within first year is not covered"),
    # Pre-existing disease
    (r"pre.?existing\s+(condition|disease|illness|ailment)", "Pre-existing diseases not covered for the defined waiting period"),
    # Alcohol / drugs
    (r"(alcohol|intoxicat|drug|narcotic)", "Death or disability under influence of alcohol or drugs is not covered"),
    # War / terrorism
    (r"(war|terrorism|riot|civil\s+unrest)", "Death due to war, terrorism, or civil unrest is excluded"),
    # Aviation / military
    (r"(aviation|aircraft|military\s+service|armed\s+forces)", "Death during military service or private aviation is excluded"),
    # Hazardous sports / adventure
    (r"(hazardous\s+(sport|activit)|adventure\s+sport|extreme\s+sport)", "Injuries from hazardous or adventure sports are not covered"),
    # Criminal / unlawful act
    (r"(criminal\s+act|unlawful\s+act|illegal\s+act|committing\s+a\s+crime)", "Death or injury while committing a criminal act is not covered"),
    # Nuclear / radiation
    (r"(nuclear|radiation|radioactiv)", "Losses due to nuclear or radioactive exposure are excluded"),
    # HIV / AIDS
    (r"(hiv|aids|sexually\s+transmitted)", "Death due to HIV/AIDS or sexually transmitted diseases is not covered"),
    # Congenital / hereditary
    (r"(congenital|hereditary|birth\s+defect)", "Congenital or hereditary conditions are not covered"),
    # Cosmetic / dental / optical
    (r"(cosmetic|aesthetic|dental|optical|vision\s+correct)", "Cosmetic, dental, or optical treatments are excluded"),
    # Mental illness
    (r"(mental\s+(illness|disorder)|psychiatric|psycholog)", "Mental illness or psychiatric disorders may not be covered"),
    # Experimental treatment
    (r"(experimental|unproven|investigational)\s+(treatment|therapy|procedure)", "Experimental or unproven medical treatments are excluded"),
    # Maternity
    (r"(matern|pregnan|childbirth|deliveries)", "Maternity-related expenses may not be covered under this plan"),
    # Foreign travel
    (r"(foreign\s+travel|travel\s+abroad|international\s+travel)", "Death or illness outside India may have limited or no coverage"),
    # Negligence
    (r"(negligence|own\s+negligent\s+act|self.?negligence)", "Losses resulting from own negligent acts are excluded"),
    # Waiting period
    (r"waiting\s+period", "No claim payable for specified conditions during the initial waiting period"),
    # Misrepresentation
    (r"(misrepresent|non.?disclosure|concealment)", "Claim denied if any material information was withheld at inception"),
    # Lapse
    (r"(policy.*lapse|lapse.*policy)", "No benefit payable if the policy has lapsed due to non-payment"),
    # First year exclusion
    (r"(first\s+year\s+exclusion|exclusion.*first\s+year)", "Certain benefits are excluded in the first policy year"),
    # Occupation hazard
    (r"(hazardous\s+occupation|occupational\s+hazard)", "Death arising from a hazardous occupation is not covered"),
    # Natural disaster
    (r"(natural\s+disaster|earthquake|flood|cyclone)", "Death or losses due to natural disasters may not be covered"),
]


def _regex_extract_exclusions(text: str) -> list:
    """
    Mine policy exclusions from raw policy text using keyword matching.
    Returns a deduplicated list of exclusion strings.
    """
    found = []
    seen_labels = set()

    for pattern, label in _EXCLUSION_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            key = " ".join(label.split()[:3]).lower()
            if key not in seen_labels:
                seen_labels.add(key)
                found.append(label)

    # Also scan for exclusion sentences from the text itself
    excl_sentence_pattern = re.compile(
        r"([A-Z][^.!?\n]{5,100}(?:not\s+cover|exclud|not\s+payable|not\s+admissible|disqualif)[^.!?\n]{0,60}[.!?]?)",
        re.IGNORECASE
    )
    for m in excl_sentence_pattern.finditer(text[:20000]):
        sentence = m.group(1).strip()
        if "{" in sentence or len(sentence) > 130:
            continue
        key = " ".join(sentence.split()[:4]).lower()
        if key not in seen_labels and len(sentence) > 25:
            seen_labels.add(key)
            found.append(sentence[:120])
        if len(found) >= 10:
            break

    return found[:7]  # Cap at 7 exclusions


def _regex_extract_benefits(text: str) -> list:
    """
    Mine key benefits from raw policy text using keyword-sentence matching.
    Returns a deduplicated list of benefit strings.
    """
    found = []
    seen_labels = set()

    for pattern, label in _BENEFIT_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            key = " ".join(label.split()[:3]).lower()
            if key not in seen_labels:
                seen_labels.add(key)
                found.append(label)

    # Additionally, pull short benefit sentences that mention key benefit terms
    sentence_pattern = re.compile(
        r"([A-Z][^.!?\n]{5,80}(?:benefit|cover|bonus|waiver|return|assured)[^.!?\n]{0,40}[.!?]?)",
        re.IGNORECASE
    )
    for m in sentence_pattern.finditer(text[:15000]):
        sentence = m.group(1).strip()
        if "{" in sentence or len(sentence) > 120:
            continue
        key = " ".join(sentence.split()[:4]).lower()
        if key not in seen_labels and len(sentence) > 20:
            seen_labels.add(key)
            found.append(sentence[:110])
        if len(found) >= 10:
            break

    return found[:8]  # Cap at 8 benefits


def _regex_extract_hidden_clauses(text: str) -> list:
    """
    Mine hidden/unfavorable clauses from raw policy text using keyword matching.
    Returns a deduplicated list of clause warning strings.
    """
    found = []
    seen_labels = set()

    for pattern, label in _HIDDEN_CLAUSE_PHRASES:
        if re.search(pattern, text, re.IGNORECASE):
            key = " ".join(label.split()[:3]).lower()
            if key not in seen_labels:
                seen_labels.add(key)
                found.append(label)

    # Additionally, pull short sentences that contain clause-related warning words
    clause_sentence_pattern = re.compile(
        r"([A-Z][^.!?\n]{5,100}(?:not\s+cover|exclud|void|lapse|forfeit|penalt|restrict|condition|shall\s+not)[^.!?\n]{0,60}[.!?]?)",
        re.IGNORECASE
    )
    for m in clause_sentence_pattern.finditer(text[:20000]):
        sentence = m.group(1).strip()
        if "{" in sentence or len(sentence) > 130:
            continue
        key = " ".join(sentence.split()[:4]).lower()
        if key not in seen_labels and len(sentence) > 25:
            seen_labels.add(key)
            found.append(sentence[:120])
        if len(found) >= 10:
            break

    return found[:7]  # Cap at 7 clauses


def _generate_summary_from_text(text: str) -> str:
    """
    Construct a readable policy summary from raw text by mining key facts:
    policy name, type, premium, term, sum assured, maturity, and features.
    Returns a 3-5 sentence paragraph.
    """
    facts = []

    # 1. Policy Name — first long capitalised line that looks like a product name
    name_match = re.search(
        r"(?:plan|policy|scheme|product)[^\n]{0,80}",
        text[:3000], re.IGNORECASE
    )
    policy_name = name_match.group(0).strip()[:80] if name_match else None

    # 2. Policy Type
    policy_type = None
    if re.search(r"term\s+(life\s+)?insurance|term\s+plan", text, re.IGNORECASE):
        policy_type = "term life insurance"
    elif re.search(r"ulip|unit.?linked", text, re.IGNORECASE):
        policy_type = "unit-linked insurance (ULIP)"
    elif re.search(r"money.?back", text, re.IGNORECASE):
        policy_type = "money-back insurance"
    elif re.search(r"endowment", text, re.IGNORECASE):
        policy_type = "endowment insurance"
    elif re.search(r"whole\s+life", text, re.IGNORECASE):
        policy_type = "whole life insurance"
    elif re.search(r"pension|annuity|retirement", text, re.IGNORECASE):
        policy_type = "pension / annuity plan"
    elif re.search(r"health\s+insurance|mediclaim", text, re.IGNORECASE):
        policy_type = "health insurance"

    # 3. Sum Assured
    sa_match = re.search(
        r"sum\s+assured[^\d]*((?:Rs\.?|INR|₹)?\s*[\d,]+(?:\s*(?:lakh|crore|lakhs|crores))?)",
        text, re.IGNORECASE
    )
    sum_assured = sa_match.group(1).strip() if sa_match else None

    # 4. Annual Premium
    prem_match = re.search(
        r"(?:annual|yearly)\s+premium[^\d]*((?:Rs\.?|INR|₹)?\s*[\d,]+)",
        text, re.IGNORECASE
    )
    premium = prem_match.group(1).strip() if prem_match else None

    # 5. Policy Term
    term_match = re.search(
        r"policy\s+term[^\d]*(\d{1,2})\s*(?:years?|yrs?)",
        text, re.IGNORECASE
    )
    policy_term = term_match.group(1).strip() if term_match else None

    # 6. Maturity Benefit
    mat_match = re.search(
        r"maturity\s+(?:benefit|amount|value)[^\d]*((?:Rs\.?|INR|₹)?\s*[\d,]+(?:\s*(?:lakh|crore|lakhs|crores))?)",
        text, re.IGNORECASE
    )
    maturity = mat_match.group(1).strip() if mat_match else None

    # 7. Key feature flags
    has_guaranteed = bool(re.search(r"guaranteed\s+(return|benefit|maturity|addition)", text, re.IGNORECASE))
    has_bonus      = bool(re.search(r"(reversionary|loyalty|terminal)\s+bonus", text, re.IGNORECASE))
    has_tax        = bool(re.search(r"section\s+80c|tax\s+benefit|tax\s+deduction", text, re.IGNORECASE))
    has_rider      = bool(re.search(r"(critical\s+illness|accidental\s+death|disability)\s+(benefit|rider)", text, re.IGNORECASE))
    has_loan       = bool(re.search(r"policy\s+loan|loan\s+against\s+policy", text, re.IGNORECASE))

    # --- Build sentences ---
    sentences = []

    # Sentence 1: What kind of plan is it?
    if policy_name and policy_type:
        sentences.append(f"This is a {policy_type} plan ({policy_name[:60]}) that provides both life coverage and savings.")
    elif policy_type:
        sentences.append(f"This is a {policy_type} plan that provides both life coverage and financial savings.")
    else:
        sentences.append("This is a life insurance policy designed to provide financial security and long-term savings.")

    # Sentence 2: Key numbers
    number_parts = []
    if sum_assured:
        number_parts.append(f"a sum assured of {sum_assured}")
    if premium:
        number_parts.append(f"an annual premium of {premium}")
    if policy_term:
        number_parts.append(f"a policy term of {policy_term} years")
    if maturity:
        number_parts.append(f"a maturity benefit of {maturity}")
    if number_parts:
        sentences.append("The policy offers " + ", ".join(number_parts) + ".")

    # Sentence 3: Returns type
    if has_guaranteed:
        sentences.append("Returns under this plan are guaranteed, making it a low-risk savings instrument.")
    elif re.search(r"market.?linked|nav|fund\s+value", text, re.IGNORECASE):
        sentences.append("Returns are market-linked and depend on the performance of the chosen investment funds.")

    # Sentence 4: Bonus / extra features
    feature_parts = []
    if has_bonus:
        feature_parts.append("bonus additions")
    if has_tax:
        feature_parts.append("tax benefits under Section 80C and 10(10D)")
    if has_rider:
        feature_parts.append("optional riders for critical illness and accidental death")
    if has_loan:
        feature_parts.append("a loan facility against the policy")
    if feature_parts:
        sentences.append("Additional features include " + ", ".join(feature_parts) + ".")

    # Sentence 5: Cover fallback
    if len(sentences) < 3:
        sentences.append("The policy provides a death benefit to the nominee and a maturity benefit if the insured survives the full term.")
        sentences.append("Premiums may qualify for tax deductions, and the maturity proceeds are generally tax-free.")

    return " ".join(sentences)


def analyze_policy_text(text: str) -> dict:
    """
    AI-based policy text analysis using Gemini Structured Outputs.
    Falls back to regex extraction if AI returns empty benefit lists.

    Args:
        text (string): full extracted PDF text

    Returns:
        dict: {
            "policy_summary": string,
            "key_benefits": list[str],
            "exclusions": list[str],
            "hidden_clauses": list[str]
        }
    """
    # Safe defaults — empty string triggers the summary fallback exactly like lists trigger regex fallbacks
    result = {
        "policy_summary": "",
        "key_benefits": [],
        "exclusions": [],
        "hidden_clauses": [],
    }

    try:
        if not text or not isinstance(text, str) or len(text.strip()) < 50:
            result["key_benefits"] = _regex_extract_benefits(text or "") or ["Could not extract benefits from this document."]
            result["policy_summary"] = _generate_summary_from_text(text or "")
            return result

        print("TEXT ANALYSIS START - Text length:", len(text))

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY is not set.")
            result["key_benefits"] = _regex_extract_benefits(text)
            result["policy_summary"] = _generate_summary_from_text(text)
            return result

        client = genai.Client(api_key=api_key)

        prompt = f"""
        You are an expert insurance policy analyst. Analyze the following insurance policy text and extract:
        1. Policy Summary — write a highly detailed, comprehensive, and engaging paragraph summarizing the policy. Explain its core purpose, target audience, main benefits, and key financial terms. Make it easy to read but thorough (at least 4-6 sentences). Include:
           - What type of plan this is (term/endowment/ULIP/money-back/whole life)
           - The key numbers: sum assured, annual premium, policy term, maturity benefit (if mentioned)
           - Whether returns are guaranteed or market-linked
           - Key added features (bonus, tax benefit, riders, loan facility)
           NEVER use vague phrases like "Policy details extracted" — always write a specific, informative summary.
        2. Key Benefits — you MUST extract 5-8 highly specific and impactful benefits. Make them read like premium marketing highlights while remaining strictly factual. Focus on exact coverage amounts, guaranteed returns, tax savings, riders, and unique perks.
           - Emphasize exact numbers (e.g. "Rs. 1 Crore Life Cover") if available.
           - Highlight Death/Maturity/Survival benefits, bonuses, and tax deductions (80C, 10(10D)).
           - Detail specific riders (accident, critical illness) and loan/surrender features.
           If the text is sparse, INFER standard benefits from the policy type (endowment/term/ULIP/money-back).
           NEVER return an empty list — always provide at least 5 benefits.
        3. Exclusions — conditions NOT covered. MUST always find at least 3-5. Look for:
           - Suicide exclusion
           - Pre-existing disease exclusion
           - Alcohol / drug-related death
           - War, terrorism, riots
           - Aviation or military service
           - Hazardous sports or activities
           - Criminal or unlawful acts
           - HIV/AIDS or sexually transmitted diseases
           - Congenital or hereditary conditions
           - Misrepresentation / non-disclosure consequences
           If the text is sparse, INFER standard exclusions for the policy type.
           NEVER return an empty exclusions list — always provide at least 3 items.
        4. Hidden clauses — tricky or unfavorable conditions the customer must be aware of. MUST always find at least 3-5. Look for:
           - Suicide exclusion (typically first year)
           - Lock-in periods or surrender charges
           - Waiting periods before benefits activate
           - Policy lapse rules and revival conditions
           - Non-disclosure or misrepresentation consequences
           - GST or charges that erode returns
           - Mortality / fund management charges (ULIP)
           - Market risk disclaimers
           - Contestability or claim rejection conditions
           - Hazardous activity or adventure sport exclusions
           If the text is sparse, INFER standard hidden clauses from the policy type.
           NEVER return an empty hidden_clauses list — always provide at least 3 clauses.

        RULES:
        - Ignore template variables like {{{{NOMINEE_NAME}}}} or {{{{TEXT}}}}.
        - Ignore broken or administrative artifact text.
        - Each bullet point must be under 25 words and plain-English.
        - NEVER return an empty key_benefits, exclusions, or hidden_clauses list.

        Policy Text:
        ---
        {text[:35000]}
        ---
        """

        # Attempt 1: structured schema output
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PolicyInsights,
                ),
            )
            data = json.loads(response.text)
        except Exception as schema_err:
            print("Structured schema failed, trying plain JSON fallback:", schema_err)
            fallback_prompt = f"""Analyze this insurance policy and return ONLY a valid JSON object with exactly these keys:
{{
  "policy_summary": "Highly detailed, comprehensive, and engaging 4-6 sentence plain-English summary of the policy",
  "key_benefits": ["benefit 1", "benefit 2", "benefit 3", "benefit 4"],
  "exclusions": ["exclusion 1", "exclusion 2", "exclusion 3"],
  "hidden_clauses": ["clause 1", "clause 2", "clause 3"]
}}

CRITICAL RULES:
- key_benefits MUST have at least 4 items — NEVER return an empty array.
  Look for: death benefit, maturity benefit, tax savings (80C/10(10D)), bonuses, riders, loans, surrender value.
  If not explicitly stated, infer from the policy type.
- exclusions MUST have at least 3 items — NEVER return an empty array.
  Look for: suicide clause, pre-existing disease, alcohol/drug-related death, war/terrorism, hazardous sports,
  criminal acts, HIV/AIDS, congenital conditions, misrepresentation, occupation hazard.
  If not explicitly stated, infer common exclusions for the policy type.
- hidden_clauses MUST have at least 3 items — NEVER return an empty array.
  Look for: suicide exclusion, lock-in period, lapse rules, waiting period, non-disclosure consequences,
  GST on premiums, mortality/fund charges, market risk disclaimer, surrender penalties, claim rejection conditions.
  If not explicitly stated, infer common hidden clauses for the policy type.
- Keep each point under 25 words.
- Ignore template variables like {{NOMINEE_NAME}} or {{TEXT}}.
- Return ONLY the JSON, no extra text.

Policy Text:
---
{text[:20000]}
---"""
            response2 = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=fallback_prompt,
            )
            raw = response2.text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())

        # Merge AI results — summary: reject generic/empty placeholders
        ai_summary = data.get("policy_summary", "") or ""
        _generic = {"policy details extracted", "unable to", "could not", "no summary", "n/a"}
        if (ai_summary
                and len(ai_summary.strip()) > 30
                and not any(g in ai_summary.lower() for g in _generic)):
            result["policy_summary"] = ai_summary.strip()

        for field in ("key_benefits", "exclusions", "hidden_clauses"):
            ai_val = data.get(field)
            if isinstance(ai_val, list) and len(ai_val) > 0:
                # Filter out placeholder strings the model sometimes emits
                cleaned = [
                    item for item in ai_val
                    if isinstance(item, str)
                    and len(item.strip()) > 5
                    and "benefit 1" not in item.lower()
                    and "exclusion 1" not in item.lower()
                    and "clause 1" not in item.lower()
                    and "{" not in item
                ]
                if cleaned:
                    result[field] = cleaned

        print("TEXT ANALYSIS OK - Benefits:", len(result["key_benefits"]),
              "Exclusions:", len(result["exclusions"]),
              "Clauses:", len(result["hidden_clauses"]))

    except Exception as e:
        print("TEXT ANALYSIS FAILED (both attempts):", e)

    # -----------------------------------------------------------------------
    # Regex safety-net: if AI returned nothing useful for the summary,
    # construct one from key facts mined directly from raw policy text.
    # -----------------------------------------------------------------------
    _generic_defaults = {"policy details extracted", "unable to", "could not", "no summary", "n/a", ""}
    if not result["policy_summary"] or any(g in result["policy_summary"].lower() for g in _generic_defaults):
        print("SUMMARY: AI returned generic/empty — generating rule-based summary from text")
        result["policy_summary"] = _generate_summary_from_text(text)

    # -----------------------------------------------------------------------
    # Regex safety-net: if AI returned nothing useful for key_benefits,
    # fall back to rule-based extraction from raw text.
    # -----------------------------------------------------------------------
    if not result["key_benefits"]:
        print("KEY BENEFITS: AI returned empty — running regex fallback extractor")
        regex_benefits = _regex_extract_benefits(text)
        if regex_benefits:
            result["key_benefits"] = regex_benefits
        else:
            result["key_benefits"] = [
                "Life cover provided to nominee on insured's death",
                "Maturity benefit paid at end of the policy term",
                "Tax deduction on premiums paid under Section 80C",
                "Tax-free maturity proceeds under Section 10(10D)",
            ]

    # -----------------------------------------------------------------------
    # Regex safety-net: if AI returned nothing useful for exclusions,
    # fall back to rule-based extraction from raw text.
    # -----------------------------------------------------------------------
    if not result["exclusions"]:
        print("EXCLUSIONS: AI returned empty — running regex fallback extractor")
        regex_exclusions = _regex_extract_exclusions(text)
        if regex_exclusions:
            result["exclusions"] = regex_exclusions
        else:
            # Absolute last resort — universally applicable exclusion facts
            result["exclusions"] = [
                "Suicide or self-inflicted injury within first year is not covered",
                "Pre-existing diseases not covered during initial waiting period",
                "Death under influence of alcohol or drugs is excluded",
                "Death due to war, terrorism, or civil unrest is not covered",
            ]

    # -----------------------------------------------------------------------
    # Regex safety-net: if AI returned nothing useful for hidden_clauses,
    # fall back to rule-based extraction from raw text.
    # -----------------------------------------------------------------------
    if not result["hidden_clauses"]:
        print("HIDDEN CLAUSES: AI returned empty — running regex fallback extractor")
        regex_clauses = _regex_extract_hidden_clauses(text)
        if regex_clauses:
            result["hidden_clauses"] = regex_clauses
        else:
            # Absolute last resort — universally applicable hidden clause warnings
            result["hidden_clauses"] = [
                "Suicide within first policy year is not covered",
                "Policy lapses if premium unpaid after grace period — benefits are lost",
                "Non-disclosure of medical history can lead to claim rejection",
                "GST on premiums is non-refundable and reduces effective returns",
            ]

    return result


def extract_policy_insights(text):
    """
    Alternative function name for backward compatibility.
    """
    return analyze_policy_text(text)


if __name__ == "__main__":
    # Test function for development
    sample_text = "This policy pays Rs 10000 to {{NOMINEE_NAME}}. Suicide is not covered."
    res = analyze_policy_text(sample_text)
    print(res)
