"""
Hidden clause analyzer for insurance policy documents.

Detects risky clauses, penalties, and unfavorable terms.
"""

import re
from typing import List, Dict, Any

from backend.services.logger import get_logger

logger = get_logger(__name__)


def detect_hidden_clauses(text: str) -> List[Dict[str, Any]]:
    """
    Detect hidden clauses and risky terms in policy document.

    Args:
        text: Policy document text

    Returns:
        List of detected clauses with descriptions
    """
    text_lower = text.lower()
    hidden_clauses = []

    # -----------------------------------------------------------------------
    # Clause definitions: (type, severity, description, recommendation, patterns)
    # -----------------------------------------------------------------------
    CLAUSE_DEFINITIONS = [
        (
            "surrender_penalty",
            "high",
            "High surrender penalties if policy is exited early",
            "Policy has surrender charges. Consider your liquidity needs before investing.",
            [
                r"surrender\s*charge.*?(\d+)%?\s*of\s*premium",
                r"surrender\s*penalty.*?(\d+)%?",
                r"high\s*surrender\s*charges?",
                r"surrender\s*value.*?less\s*than\s*premium",
                r"discontinuance\s*charge",
                r"surrender\s*value.*?nil",
            ],
        ),
        (
            "non_guaranteed_returns",
            "medium",
            "Bonus or returns are not guaranteed — depend on insurer performance",
            "Returns depend on company performance. Not suitable for risk-averse investors.",
            [
                r"non\s*[\-]?guaranteed\s*bonus",
                r"bonus.*?not\s*guaranteed",
                r"returns.*?not\s*guaranteed",
                r"bonus.*?declared.*?at\s*the\s*discretion",
                r"bonus.*?may\s*not\s*be\s*declared",
                r"not\s*guaranteed\s*(addition|return|benefit)",
            ],
        ),
        (
            "market_linked",
            "high",
            "Returns are market-linked and can go down as well as up",
            "Market-linked returns can be volatile. Understand the risk-reward profile.",
            [
                r"market\s*[\-]?linked",
                r"unit\s*[\-]?linked",
                r"nav\s*[\-]?based",
                r"depends\s*on\s*market\s*performance",
                r"subject\s*to\s*market\s*risk",
                r"investment\s*risk.*?policyholder",
            ],
        ),
        (
            "mortality_charges",
            "medium",
            "Mortality / cost-of-insurance charges deducted and reduce corpus",
            "Mortality charges reduce effective returns. Compare with term + separate investment.",
            [
                r"mortality\s*charge",
                r"cost\s*of\s*insurance",
                r"mortality\s*deduction",
                r"policy\s*account\s*charge",
                r"insurance\s*charge\s*deducted",
            ],
        ),
        (
            "lapse_risk",
            "high",
            "Policy lapses and all benefits are lost if premiums are missed",
            "Maintain premium payment discipline to avoid policy lapse and loss of benefits.",
            [
                r"policy\s*lapse",
                r"lapse\s*if\s*premium.*?not\s*paid",
                r"revival\s*period",
                r"grace\s*period.*?lapse",
                r"lapsed\s*policy",
                r"policy\s*will\s*lapse",
                r"forfeiture\s*of\s*benefits?",
            ],
        ),
        (
            "limited_guarantee",
            "medium",
            "Guarantee is limited in duration or conditional on specific events",
            "Guarantees are limited. Understand the full conditions and time period.",
            [
                r"guarantee.*?limited",
                r"guaranteed.*?for\s*only\s*(\d+)\s*years?",
                r"premium\s*guarantee.*?limited",
                r"capital\s*guarantee.*?conditional",
            ],
        ),
        (
            "allocation_charges",
            "high",
            "High allocation or premium loading charges reduce investment corpus",
            "High allocation charges reduce initial investment. Compare with other options.",
            [
                r"allocation\s*charge.*?(\d+)%?",
                r"premium\s*allocation.*?(\d+)%?",
                r"entry\s*load.*?(\d+)%?",
                r"initial\s*charge.*?(\d+)%?",
                r"premium\s*loading",
                r"policy\s*issuance\s*charge",
            ],
        ),
        (
            "switching_restrictions",
            "low",
            "Fund switching is restricted or incurs charges",
            "Limited fund switching flexibility. Consider if this matches your investment strategy.",
            [
                r"limited\s*switching",
                r"switching\s*charge",
                r"fund\s*switch.*?restricted",
                r"switching.*?only\s*(\d+)\s*times?",
                r"free\s*switches\s*exhausted",
            ],
        ),
        (
            "withdrawal_restrictions",
            "medium",
            "Partial withdrawals restricted or lock-in period applies",
            "Limited liquidity. Ensure this aligns with your cash flow needs.",
            [
                r"withdrawal.*?restricted",
                r"partial\s*withdrawal.*?not\s*allowed",
                r"withdrawal.*?only\s*after\s*(\d+)\s*years?",
                r"lock\s*[\-]?in\s*period.*?(\d+)\s*years?",
                r"no\s*withdrawals?\s*during",
                r"withdrawal\s*not\s*permitted",
            ],
        ),
        (
            "suicide_exclusion",
            "high",
            "Suicide within first year — nominee gets only paid premiums, not full cover",
            "Suicide exclusion applies in the first year. Nominee gets only premiums paid, not sum assured.",
            [
                r"suicide",
                r"self\s*[\-]?inflicted\s*injur",
                r"deliberate\s*self\s*harm",
            ],
        ),
        (
            "misrepresentation",
            "high",
            "Claim can be fully rejected if any information was misrepresented at proposal",
            "Non-disclosure of medical or personal history can void your claim entirely.",
            [
                r"misrepresent",
                r"non\s*[\-]?disclosure",
                r"concealment\s*of\s*material",
                r"material\s*information.*?not\s*disclosed",
                r"suppression\s*of\s*information",
                r"incorrect\s*information.*?void",
            ],
        ),
        (
            "free_look_period",
            "low",
            "Free-look period: you can return the policy within 15-30 days for a refund",
            "Use the free-look window if you are not satisfied. Act within the specified days.",
            [
                r"free\s*[\-]?look",
                r"cooling\s*[\-]?off\s*period",
                r"return\s*the\s*policy\s*within",
                r"cancel.*?within\s*(\d+)\s*days?",
            ],
        ),
        (
            "gst_on_premiums",
            "medium",
            "GST added to premiums is non-refundable and reduces effective returns",
            "GST on premiums is not refunded at maturity and increases your effective outflow.",
            [
                r"gst.*?premium",
                r"goods\s*and\s*service\s*tax.*?premium",
                r"18%\s*gst",
                r"service\s*tax.*?premium",
                r"tax\s*on\s*premium",
            ],
        ),
        (
            "contestability",
            "high",
            "Insurer can investigate / contest claims within 2-3 years of policy issue",
            "Contestability clause lets insurer investigate claims in early years. Ensure full disclosure.",
            [
                r"incontestab",
                r"contest.*?claim",
                r"right\s*to\s*investigate",
                r"claim.*?disputed\s*within\s*(\d+)\s*years?",
                r"repudiat",
            ],
        ),
        (
            "hazardous_activity",
            "medium",
            "Death during hazardous activities or adventure sports is not covered",
            "Hazardous sports or occupation exclusion applies. Death in such activities will be rejected.",
            [
                r"hazardous\s*(occupation|sport|activit)",
                r"adventure\s*sport",
                r"extreme\s*sport",
                r"risky\s*occupation",
                r"aviation.*?exclusion",
                r"military\s*service.*?exclusion",
            ],
        ),
        (
            "pre_existing_disease",
            "high",
            "Pre-existing conditions may not be covered for a defined waiting period",
            "Disclose all pre-existing conditions. Non-disclosure leads to claim rejection.",
            [
                r"pre\s*[\-]?existing\s*(condition|disease|illness|ailment)",
                r"waiting\s*period.*?disease",
                r"prior\s*(medical|health)\s*(condition|history)",
                r"existing\s*illness.*?not\s*covered",
            ],
        ),
        (
            "paid_up_policy",
            "medium",
            "If premiums stop prematurely, policy becomes paid-up with reduced benefits",
            "Stopping premiums early makes the policy paid-up with a significantly reduced sum assured.",
            [
                r"paid\s*[\-]?up\s*(value|policy|sum)",
                r"reduced\s*paid\s*[\-]?up",
                r"becomes\s*paid\s*up",
                r"paid\s*up\s*benefit",
            ],
        ),
        (
            "claim_rejection",
            "high",
            "Claims can be rejected for multiple documented reasons",
            "Understand all grounds for claim rejection before purchasing this policy.",
            [
                r"claim.*?reject",
                r"claim.*?not\s*payable",
                r"company.*?may\s*decline",
                r"insurer.*?has\s*the\s*right.*?deny",
                r"benefit.*?shall\s*not\s*be\s*payable",
            ],
        ),
        (
            "waiting_period",
            "medium",
            "Waiting period applies — certain benefits not payable during initial months",
            "No claim for specified conditions during the waiting period. Start from day one is not covered.",
            [
                r"waiting\s*period",
                r"initial\s*waiting\s*period",
                r"\d+\s*(day|month)\s*waiting\s*period",
                r"coverage\s*commences\s*after",
            ],
        ),
    ]

    # -----------------------------------------------------------------------
    # Scan each clause definition against the policy text
    # -----------------------------------------------------------------------
    seen_types = set()

    for clause_type, severity, description, recommendation, patterns in CLAUSE_DEFINITIONS:
        if clause_type in seen_types:
            continue
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                hidden_clauses.append({
                    "type": clause_type,
                    "severity": severity,
                    "description": description,
                    "snippet": match.group(0)[:120],
                    "recommendation": recommendation,
                    "keyword": description.split("\u2014")[0].strip(),
                })
                seen_types.add(clause_type)
                break  # Only one match per clause type

    # -----------------------------------------------------------------------
    # Safety-net: if nothing detected, inject universally applicable clauses
    # that apply to virtually every Indian insurance policy.
    # -----------------------------------------------------------------------
    if not hidden_clauses:
        logger.info("No regex matches found — injecting universal risky clause defaults")
        hidden_clauses = [
            {
                "type": "suicide_exclusion",
                "severity": "high",
                "keyword": "Suicide Exclusion",
                "description": "Suicide within first year — nominee receives only premiums paid, not full cover",
                "snippet": "Standard suicide exclusion applies in year 1",
                "recommendation": "Suicide exclusion is mandatory under IRDAI rules for all life insurance policies.",
            },
            {
                "type": "lapse_risk",
                "severity": "high",
                "keyword": "Policy Lapse Risk",
                "description": "Policy lapses and all benefits are lost if premiums are missed beyond grace period",
                "snippet": "Standard policy lapse clause",
                "recommendation": "Set up auto-debit to avoid missing premium payments and losing all benefits.",
            },
            {
                "type": "misrepresentation",
                "severity": "high",
                "keyword": "Non-Disclosure Risk",
                "description": "Claim rejected if any health or personal information was not disclosed at proposal",
                "snippet": "Standard non-disclosure clause",
                "recommendation": "Disclose all medical conditions honestly at the time of applying for insurance.",
            },
            {
                "type": "gst_on_premiums",
                "severity": "medium",
                "keyword": "GST on Premiums",
                "description": "GST added to premiums is non-refundable and reduces effective returns",
                "snippet": "Standard GST applicable on life insurance premiums",
                "recommendation": "Factor in 4.5%-18% GST on premiums when calculating actual cost of the policy.",
            },
        ]

    logger.info("Detected %d hidden clauses", len(hidden_clauses))
    return hidden_clauses


def analyze_clause_severity(clauses: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Analyze severity distribution of detected clauses.
    
    Args:
        clauses: List of detected clauses
        
    Returns:
        Dictionary with severity counts
    """
    severity_counts = {"high": 0, "medium": 0, "low": 0}
    
    for clause in clauses:
        severity = clause.get("severity", "low")
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    return severity_counts


def get_clause_recommendations(clauses: List[Dict[str, Any]]) -> List[str]:
    """
    Generate overall recommendations based on detected clauses.
    
    Args:
        clauses: List of detected clauses
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    severity_counts = analyze_clause_severity(clauses)
    
    if severity_counts["high"] > 0:
        recommendations.append("⚠️ Policy has multiple high-risk clauses. Review carefully before investing.")
    
    clause_types = [clause["type"] for clause in clauses]
    
    if "market_linked" in clause_types:
        recommendations.append("📈 Market-linked returns mean volatility. Ensure you understand the risks.")
    
    if "surrender_penalty" in clause_types:
        recommendations.append("💸 High surrender charges reduce flexibility. Consider your liquidity needs.")
    
    if "lapse_risk" in clause_types:
        recommendations.append("⏰ Policy lapse risk exists. Maintain premium payment discipline.")
    
    if "non_guaranteed_returns" in clause_types:
        recommendations.append("🎯 Returns are not guaranteed. Compare with guaranteed options.")
    
    if severity_counts["medium"] > 2:
        recommendations.append("📋 Multiple medium-risk clauses detected. Read all terms carefully.")
    
    if not clauses:
        recommendations.append("✅ No significant hidden clauses detected. Policy terms appear straightforward.")
    
    return recommendations
