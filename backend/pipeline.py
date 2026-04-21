"""
Consolidated processing pipeline for Insurance Policy Analyzer.
This allows direct integration with Streamlit without requiring a separate Flask API.
"""

import json
import os
import gc
import time
import tempfile
from pathlib import Path
from typing import Any

# Services
from backend.services.pdf_service import get_processed_text
from backend.services.unified_analyzer import unified_analyze
from backend.services.extraction_engine import extract_policy_data as engine_extract
from backend.services.financial_engine import (
    calculate_cagr,
    calculate_inflation_adjusted_cagr,
    calculate_annualized_roi,
    calculate_irr,
    calculate_tax_effective_irr,
    calculate_break_even_year,
    calculate_net_profit,
    calculate_inflation_adjusted_profit,
)
from backend.services.policy_classifier import detect_policy_type, is_term_insurance, is_insurance_policy
from backend.services.risk_analyzer import (
    detect_risky_clauses,
    get_risk_level,
)
from backend.services.model import train_model, predict_risk
from backend.services.logger import get_logger

logger = get_logger(__name__)

def clean_json(data):
    """Clean JSON data to remove NaN, Infinity, and other invalid values."""
    import math
    if isinstance(data, dict):
        return {k: clean_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_json(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
    return data

def _generate_analysis_notes(
    cagr: float,
    irr: float,
    roi: float,
    infl_cagr: float,
    total_investment: float,
    maturity_value: float,
    net_profit: float,
    policy_term: int,
    payment_term: int,
    premium: float,
    be_year: int,
    risk_score: int,
    policy_type: str,
) -> list:
    """
    Generate intelligent, data-driven analysis notes from computed financial metrics.
    Always returns at least 3 notes so the Analysis Notes section is never empty.
    """
    notes = []
    inflation_rate = 6.0  # %

    # 1. CAGR vs inflation
    if cagr and cagr > 0:
        if cagr < inflation_rate:
            notes.append(
                f"⚠️ Your policy CAGR is {cagr:.2f}% — below the average inflation rate of {inflation_rate:.0f}%. "
                f"In real terms, your money is losing purchasing power over time."
            )
        elif cagr < 7:
            notes.append(
                f"📊 CAGR of {cagr:.2f}% is modest. A regular Fixed Deposit currently offers ≈7%. "
                f"Consider if this policy's life cover justifies the lower return."
            )
        else:
            notes.append(
                f"✅ CAGR of {cagr:.2f}% is healthy and above typical FD rates. "
                f"The policy offers good long-term savings growth."
            )

    # 2. Inflation-adjusted CAGR
    if infl_cagr is not None:
        if infl_cagr < 0:
            notes.append(
                f"📉 Inflation-adjusted return is negative ({infl_cagr:.2f}%). "
                f"After accounting for inflation, this policy erodes your wealth in real terms."
            )
        elif infl_cagr < 1:
            notes.append(
                f"⚠️ Real return after inflation is only {infl_cagr:.2f}%. "
                f"You are barely preserving purchasing power — no real wealth creation."
            )

    # 3. Break-even year
    if be_year and be_year > 0:
        if be_year > policy_term if policy_term else False:
            notes.append(
                f"🚨 Break-even year ({be_year}) exceeds the policy term. "
                f"You may never recover your investment within the policy period."
            )
        elif be_year > 10:
            notes.append(
                f"⏳ Break-even is reached only in year {be_year}. "
                f"You are committed to holding this policy for a very long time before turning profitable."
            )
        else:
            notes.append(
                f"✅ Policy breaks even in year {be_year}, which is reasonably early in the policy term."
            )

    # 4. Premium-to-maturity ratio
    if total_investment and maturity_value and total_investment > 0:
        ratio = maturity_value / total_investment
        if ratio < 1:
            notes.append(
                f"🚨 Maturity value (\u20b9{maturity_value:,}) is less than total premiums paid (\u20b9{total_investment:,}). "
                f"You would receive less than what you put in."
            )
        elif ratio < 1.5:
            notes.append(
                f"📊 Maturity value is {ratio:.1f}x your total investment. "
                f"This is a low multiplier — a large portion of your premium is going towards insurance charges."
            )

    # 5. Policy term / commitment
    if policy_term and policy_term > 25:
        notes.append(
            f"⏳ This is a very long-term commitment of {policy_term} years. "
            f"Ensure you can sustain premium payments consistently over this period."
        )
    elif policy_term and policy_term > 15:
        notes.append(
            f"📅 Policy term of {policy_term} years is moderately long. "
            f"Factor in life changes (job, family, income) before committing."
        )

    # 6. GST impact note (always applicable)
    if premium and premium > 0:
        gst_est = int(round(premium * 0.045))  # 4.5% for first year, 2.25% thereafter
        notes.append(
            f"💰 Estimated GST on your first-year premium: \u20b9{gst_est:,} (approx. 4.5%). "
            f"GST is non-refundable and adds to your effective annual outflow."
        )

    # 7. Risk-score note
    if risk_score >= 7:
        notes.append(
            f"🔴 Risk score is {risk_score}/10 (High). "
            f"Multiple risk factors detected — review all policy terms carefully before investing."
        )
    elif risk_score >= 4:
        notes.append(
            f"🟡 Risk score is {risk_score}/10 (Moderate). "
            f"Understand the specific risk factors before committing to this policy."
        )
    else:
        notes.append(
            f"🟢 Risk score is {risk_score}/10 (Low). "
            f"This policy has a conservative risk profile, suitable for risk-averse investors."
        )

    # 8. ULIP-specific note
    if policy_type and "ulip" in policy_type.lower():
        notes.append(
            "📈 This is a ULIP: your returns depend on market performance. "
            "Fund management charges (typically 1.35%/year) reduce effective returns."
        )

    # Safety-net: always return at least 3 notes
    if len(notes) < 3:
        notes.append(
            "ℹ️ Always read the complete policy bond and not just the benefit illustration before signing."
        )
        notes.append(
            "🔍 Compare this policy with a pure term plan + mutual fund SIP combination for the same premium — "
            "it often delivers better results."
        )
        notes.append(
            "📞 In case of any doubt, consult an independent IRDAI-registered financial advisor before purchasing."
        )

    return notes


def process_policy(file_obj) -> dict[str, Any]:
    """
    Main entry point for policy analysis. 
    Accepts a file-like object (e.g. from Streamlit's file_uploader).
    """
    logger.info("Starting policy analysis pipeline")
    
    # Save uploaded file to temp path for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        content = file_obj.getvalue() if hasattr(file_obj, "getvalue") else file_obj.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        # Step 1: Extract text
        full_text, chunks, _ = get_processed_text(tmp_path)
        
        if not full_text:
            return {"error": "Could not extract text from PDF"}

        if not is_insurance_policy(full_text):
            return {"error": "The uploaded document does not appear to be an insurance policy. Please upload a valid insurance policy PDF."}

        # TASK 5: ENSURE AI ALWAYS GETS MEANINGFUL INPUT
        if len(full_text) < 500:
            return {"error": "Insufficient policy content extracted. Please ensure you are uploading a clear, text-readable PDF document."}

        # PERFORMANCE FIX: Start global timer
        start_time = time.time()

        # Step 2: Extraction
        # Unified AI extraction (Consolidated Call)
        ai_data = unified_analyze(full_text)
        
        # Performance check (Increased budget for better quality)
        if time.time() - start_time > 90:
             # Fast exit for slow responses
             return {
                 "status": "partial",
                 "policy_summary": {"simple_summary": "Analysis completed partially due to system limits and document complexity."},
                 "warnings": ["The document is being processed in safe-mode. Analysis is limited to prevent system timeout."]
             }

        # Regex extraction (Safety net)
        regex_data = engine_extract(full_text)

        # Smart merge
        def pick_best(ai_val, regex_val, is_term=False):
            def is_valid(v, term_mode):
                if v is None: return False
                try: v = float(v)
                except: return False
                if v <= 0: return False
                if term_mode: return 1 <= v <= 100
                return v >= 1000

            if is_valid(ai_val, is_term): return int(float(ai_val))
            if is_valid(regex_val, is_term): return int(float(regex_val))
            return None

        premium        = pick_best(ai_data.get("premium"),        regex_data.get("premium"),        is_term=False)
        policy_term    = pick_best(ai_data.get("policy_term"),    regex_data.get("policy_term"),    is_term=True)
        payment_term   = pick_best(ai_data.get("payment_term"),   regex_data.get("payment_term"),   is_term=True)
        maturity_value = pick_best(ai_data.get("maturity_value"), regex_data.get("maturity_value"), is_term=False)
        sum_assured    = pick_best(ai_data.get("sum_assured"),    regex_data.get("sum_assured"),    is_term=False)

        premium_frequency = (ai_data.get("premium_frequency") or "yearly") if isinstance(ai_data, dict) else "yearly"
        premium_frequency = str(premium_frequency).lower().strip()

        if payment_term is None and policy_term is not None:
            payment_term = policy_term

        # Step 3: Financials
        warnings = []
        freq_multiplier = 1
        if "month" in premium_frequency: freq_multiplier = 12
        elif "quarter" in premium_frequency: freq_multiplier = 4
        elif "half" in premium_frequency or "semi" in premium_frequency: freq_multiplier = 2

        annualized_premium = 0
        first_year_premium = 0
        total_investment   = 0

        if premium and payment_term:
            annualized_premium = premium * freq_multiplier
            first_year_premium = int(round(annualized_premium * 1.022))
            total_investment   = first_year_premium + annualized_premium * (payment_term - 1)
        else:
            warnings.append("Could not calculate total investment (missing premium or payment term)")

        # Actuarial fallback
        is_term_plan = is_term_insurance(detect_policy_type(full_text))
        if not is_term_plan and total_investment > 0 and policy_term and policy_term > 0:
            if not maturity_value or maturity_value < total_investment:
                r = 0.055
                ppt = payment_term if payment_term and payment_term > 0 else policy_term
                annual_p = annualized_premium if annualized_premium > 0 else (total_investment / ppt if ppt else 0)
                if annual_p > 0:
                    fv_ppt = annual_p * (((1 + r) ** ppt - 1) / r) * (1 + r)
                    remaining_years = policy_term - ppt
                    final_fv = fv_ppt * ((1 + r) ** remaining_years) if remaining_years > 0 else fv_ppt
                    maturity_value = int(round(final_fv))
                    warnings.append(f"Maturity value actuarially estimated at Rs.{maturity_value:,}")

        # Calculations
        INFLATION = 0.06
        TAX_RATE = 0.312
        SEC80C_LIMIT = 150000.0

        tax_saved = 0
        if annualized_premium > 0 and payment_term:
            tax_saved = min(annualized_premium, SEC80C_LIMIT) * TAX_RATE * payment_term

        mat_val = maturity_value or 0
        ppt_eval = max(int(payment_term or 1), 1)
        term_eval = max(int(policy_term or ppt_eval), ppt_eval)
        avg_time = max(term_eval - (ppt_eval - 1) / 2.0, 1.0)

        net_profit = int(round(calculate_net_profit(mat_val, total_investment))) if total_investment > 0 else 0
        infl_prof = int(round(calculate_inflation_adjusted_profit(mat_val, total_investment, term_eval, INFLATION))) if total_investment > 0 else 0
        cagr = calculate_cagr(total_investment, mat_val, avg_time) if total_investment > 0 else 0
        infl_cagr = calculate_inflation_adjusted_cagr(cagr, INFLATION) if cagr else 0
        
        irr = calculate_irr(annualized_premium, ppt_eval, term_eval, mat_val, first_year_premium if first_year_premium > annualized_premium else None)
        if irr is None: irr = cagr
        
        tax_irr = calculate_tax_effective_irr(annualized_premium, ppt_eval, term_eval, mat_val, TAX_RATE, SEC80C_LIMIT, first_year_premium if first_year_premium > annualized_premium else None)
        roi = tax_irr if tax_irr is not None else cagr
        
        be_year = calculate_break_even_year(annualized_premium, ppt_eval, term_eval, mat_val, cagr)

        # Risk
        try:
            ml_risk = predict_risk({
                "premium": premium or 0,
                "policy_term": policy_term or 0,
                "payment_term": payment_term or 0,
                "total_investment": total_investment or 0,
                "maturity_value": maturity_value or 0,
                "roi": roi or 0,
                "cagr": cagr or 0,
                "irr": irr or 0,
                "claim_ratio": 90,
            })
        except: ml_risk = "medium"

        risk_score = 5
        if ml_risk == "low": risk_score = 2
        elif ml_risk == "high": risk_score = 8

        # Append intelligent contextual analysis notes
        analysis_notes = _generate_analysis_notes(
            cagr=cagr,
            irr=irr if irr else 0,
            roi=roi if roi else 0,
            infl_cagr=infl_cagr if infl_cagr else 0,
            total_investment=total_investment,
            maturity_value=mat_val,
            net_profit=net_profit,
            policy_term=int(policy_term or 0),
            payment_term=int(payment_term or 0),
            premium=float(premium or 0),
            be_year=int(be_year or 0),
            risk_score=risk_score,
            policy_type=detect_policy_type(full_text),
        )
        warnings.extend(analysis_notes)
        result = {
            "total_investment": total_investment,
            "maturity_value": maturity_value,
            "net_profit": net_profit,
            "absolute_return": net_profit,
            "roi": roi,
            "roi_percent": roi,
            "cagr": cagr,
            "irr": irr,
            "tax_benefit_80c": int(round(tax_saved)),
            "break_even_year": be_year,
            "risk_score": risk_score,
            "risk_level": get_risk_level(risk_score),
            "ml_risk_prediction": ml_risk,
            "policy_type_detected": detect_policy_type(full_text),
            "guaranteed_vs_non_guaranteed": "Guaranteed" if "guaranteed" in full_text.lower() else "Non-Guaranteed",
            "warnings": warnings,
            "premium_details": {
                "amount": premium,
                "frequency": premium_frequency,
                "payment_term": payment_term,
            },
            "comparison": {
                "fd_7pct_maturity": round(total_investment * (1.07 ** term_eval), 2) if total_investment else 0,
                "mf_sip_12pct_projection": round(total_investment * (1.12 ** term_eval), 2) if total_investment else 0,
            },
            "advanced_metrics": {
                "inflation_adjusted_cagr": infl_cagr,
                "inflation_adj_net_profit": infl_prof,
            }
        }

        # Unified AI provides qualitative insights
        result.update({
            "policy_summary": {"simple_summary": ai_data.get("policy_summary", "Summary not available.")},
            "key_benefits": ai_data.get("key_benefits", []),
            "exclusions": ai_data.get("exclusions", []),
            "hidden_clauses": ai_data.get("hidden_clauses", []),
            "risky_clauses": detect_risky_clauses(full_text),
        })

        return clean_json(result)

    finally:
        # Step 9: Immediate memory cleanup
        if 'full_text' in locals():
            del full_text
        if 'chunks' in locals():
            del chunks
        if 'table_data' in locals():
            del table_data
        
        gc.collect()

        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def run_analysis(file_bytes: bytes) -> dict:
    """
    Entry point for the Flask API.
    Accepts raw PDF bytes (from request.files['file'].read())
    and delegates to process_policy().
    """
    import io
    file_obj = io.BytesIO(file_bytes)
    return process_policy(file_obj)


if __name__ == "__main__":
    # Ensure model is trained on first run
    try: train_model()
    except: pass
