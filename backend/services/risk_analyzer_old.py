"""
Risk analysis service for insurance policies.

Generates risk score and identifies risky clauses.
"""

import re
from typing import Any

from config import RISKY_KEYWORDS
from backend.core.logger import get_logger

logger = get_logger(__name__)


def detect_risky_clauses(text: str) -> list[dict[str, Any]]:
    """
    Detect and highlight risky clauses by keyword matching.

    Args:
        text: Policy document text.

    Returns:
        List of dicts with clause snippet and matched keyword.
    """
    text_lower = text.lower()
    found: list[dict[str, Any]] = []
    seen_snippets: set[str] = set()

    for keyword in RISKY_KEYWORDS:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        for match in pattern.finditer(text):
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 120)
            snippet = text[start:end].strip()
            snippet = re.sub(r"\s+", " ", snippet)
            if snippet not in seen_snippets and len(snippet) > 20:
                seen_snippets.add(snippet)
                found.append({"keyword": keyword, "snippet": snippet})

    return found[:20]  # Limit to 20 clauses


def calculate_risk_score(
    waiting_period_years: float = 0,
    lock_in_period_years: float = 0,
    is_guaranteed_return: bool = True,
    tenure_years: float = 0,
    cagr_percent: float | None = None,
    risky_clauses_count: int = 0,
) -> int:
    """
    Calculate risk score from 1 (low) to 10 (high).

    Args:
        waiting_period_years: Waiting period before benefits.
        lock_in_period_years: Lock-in period.
        is_guaranteed_return: Whether returns are guaranteed.
        tenure_years: Policy tenure.
        cagr_percent: CAGR percentage (e.g., 8.5).
        risky_clauses_count: Number of risky clauses detected.

    Returns:
        Risk score 1-10.
    """
    score = 0.0

    # Waiting period (max +2)
    if waiting_period_years >= 3:
        score += 2
    elif waiting_period_years >= 1:
        score += 1

    # Lock-in period (max +2)
    if lock_in_period_years >= 5:
        score += 2
    elif lock_in_period_years >= 3:
        score += 1

    # Non-guaranteed returns (max +3)
    if not is_guaranteed_return:
        score += 3

    # Long tenure >25 years (max +1)
    if tenure_years > 25:
        score += 1

    # Low CAGR <5% (max +2)
    if cagr_percent is not None and cagr_percent < 5 and cagr_percent > 0:
        score += 2

    # Risky clauses (max +2)
    if risky_clauses_count >= 5:
        score += 2
    elif risky_clauses_count >= 2:
        score += 1

    # Clamp to 1-10
    final = min(10, max(1, int(round(score)) + 1))
    return final


def get_risk_level(score: int) -> str:
    """
    Map risk score to level description.

    Args:
        score: Risk score 1-10.

    Returns:
        Risk level string.
    """
    if score <= 2:
        return "Low"
    if score <= 4:
        return "Low-Medium"
    if score <= 6:
        return "Medium"
    if score <= 8:
        return "Medium-High"
    return "High"
