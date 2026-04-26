import os
import requests
import streamlit as st

def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    @keyframes fadeUp {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    .animate-fade-up {
        animation: fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        opacity: 0;
    }
    .delay-1 { animation-delay: 0.1s; }
    .delay-2 { animation-delay: 0.2s; }
    .delay-3 { animation-delay: 0.3s; }
    .delay-4 { animation-delay: 0.4s; }
    .delay-5 { animation-delay: 0.5s; }
    .delay-6 { animation-delay: 0.6s; }

    html, body, [class*="css"] { 
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
        color: #1C1C1E;
        background-color: #FFFFFF;
    }

    /* Base background */
    .stApp {
        background-color: #FFFFFF !important;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
    }

    /* Reduce top padding */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Hero Section - Apple Style */
    .hero-container {
        background: #F2F2F7;
        padding: 5rem 2.5rem;
        border-radius: 24px;
        text-align: center;
        margin-top: 1rem;
        margin-bottom: 3.5rem;
        border: 1px solid #E5E5EA;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
    }
    .hero-logo {
        font-size: 4.5rem;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 700;
        color: #1C1C1E;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        font-size: 1.35rem;
        color: #8E8E93;
        margin: 0;
        font-weight: 400;
        letter-spacing: -0.01em;
    }

    /* Feature Strip Cards - SaaS */
    .feature-card {
        background: #FFFFFF;
        border: 1px solid #E5E5EA;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .feature-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    }
    .feature-icon {
        font-size: 2.25rem;
        margin-bottom: 1.25rem;
    }
    .feature-title {
        font-weight: 600;
        color: #1C1C1E;
        font-size: 1.25rem;
        margin-bottom: 0.75rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .feature-desc {
        font-size: 1rem;
        color: #8E8E93;
        line-height: 1.6;
        display: block;
    }

    /* Data Cards */
    .data-card {
        background: #FFFFFF;
        border: 1px solid #E5E5EA;
        border-radius: 16px;
        padding: 1.75rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        height: 100%;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .data-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.06);
    }
    .data-card-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #8E8E93;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.75rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .data-card-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1C1C1E;
        margin-bottom: 0.25rem;
        letter-spacing: -0.02em;
    }
    .data-card-sub {
        font-size: 0.9rem;
        color: #8E8E93;
    }

    /* Highlight Card (Blue) */
    .data-card.highlight {
        background: #F2F2F7;
        border: 1px solid #007AFF;
    }
    .data-card.highlight .data-card-value {
        color: #007AFF;
    }

    /* Invest Comparison Cards */
    .invest-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 1.75rem;
        border: 1px solid #E5E5EA;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        text-align: center;
    }
    .invest-card-title {
        font-size: 1rem;
        font-weight: 600;
        color: #8E8E93;
        margin-bottom: 1rem;
    }
    .invest-card-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1C1C1E;
        letter-spacing: -0.02em;
        white-space: nowrap;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 0.4rem 1.25rem;
        border-radius: 9999px;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .badge-good { background: #E8F5E9; color: #34C759; border: 1px solid #C8E6C9; }
    .badge-warning { background: #FFF9C4; color: #FF9500; border: 1px solid #FFF59D; }
    .badge-danger { background: #FFEBEE; color: #FF3B30; border: 1px solid #FFCDD2; }
    .badge-neutral { background: #F2F2F7; color: #8E8E93; border: 1px solid #E5E5EA; }

    /* Pills for text items */
    .pill {
        display: inline-flex;
        align-items: flex-start;
        padding: 0.75rem 1.25rem;
        border-radius: 12px;
        font-size: 1rem;
        margin-bottom: 0.75rem;
        font-weight: 500;
        width: 100%;
        line-height: 1.5;
    }
    .pill-green { background: #FFFFFF; color: #1C1C1E; border: 1px solid #34C759; border-left: 4px solid #34C759; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    .pill-yellow { background: #FFFFFF; color: #1C1C1E; border: 1px solid #FF9500; border-left: 4px solid #FF9500; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
    .pill-red { background: #FFFFFF; color: #1C1C1E; border: 1px solid #FF3B30; border-left: 4px solid #FF3B30; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }

    /* Sections */
    .section-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1C1C1E;
        margin: 3.5rem 0 1.5rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #E5E5EA;
        letter-spacing: -0.01em;
    }

    /* Success Banner */
    .success-banner {
        background: #F2F2F7;
        border: 1px solid #E5E5EA;
        border-left: 4px solid #34C759;
        color: #1C1C1E;
        padding: 1.5rem;
        border-radius: 12px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 2.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        font-size: 1.15rem;
    }

    /* Risk Analysis Box */
    .risk-box {
        background: #FFFFFF;
        border: 1px solid #E5E5EA;
        border-radius: 16px;
        padding: 1.75rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        transition: transform 0.2s ease-out, box-shadow 0.2s ease-out;
    }
    .risk-box:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    }

    /* Recommendation Box */
    .rec-box {
        background: #F2F2F7;
        border: 1px solid #E5E5EA;
        border-left: 4px solid #007AFF;
        padding: 2rem;
        border-radius: 16px;
        color: #1C1C1E;
        font-size: 1.15rem;
        margin: 3rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }

    /* Custom File Uploader */
    [data-testid="stFileUploader"] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        padding: 2rem !important;
        border: 2px dashed #C7C7CC !important;
        transition: border-color 0.2s;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #007AFF !important;
    }

    /* Primary Button */
    .stButton>button {
        background: #007AFF;
        color: #FFFFFF;
        border-radius: 12px;
        font-weight: 600;
        padding: 0.75rem 2rem;
        border: none;
        width: 100%;
        transition: all 0.2s;
        font-size: 1.1rem;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
    }
    .stButton>button:hover {
        background: #0066CC;
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 6px 16px rgba(0, 122, 255, 0.4);
        color: #FFFFFF;
        border: none;
    }

    /* Footer */
    .footer {
        text-align: center;
        margin-top: 6rem;
        padding-top: 3rem;
        border-top: 1px solid #E5E5EA;
        color: #8E8E93;
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Markdown text color overrides */
    .stMarkdown p {
        color: #3A3A3C;
        line-height: 1.6;
    }
    .stMarkdown b, .stMarkdown strong {
        color: #1C1C1E;
    }

    </style>
    """, unsafe_allow_html=True)


def get_backend_url():
    try:
        return st.secrets["BACKEND_URL"]
    except Exception:
        return os.environ.get("BACKEND_URL", "http://localhost:5000")


def call_analyze_api(uploaded_file) -> dict:
    """Send PDF to the Flask backend and return the parsed result dict."""
    backend_url = get_backend_url()
    try:
        file_bytes = uploaded_file.getvalue()
        response = requests.post(
            f"{backend_url}/analyze",
            files={"file": (uploaded_file.name, file_bytes, "application/pdf")},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("status") == "success":
            return payload["data"]
        else:
            return {"error": payload.get("message", "Unknown error from API")}

    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to the backend API at {backend_url}. Is the service running?"}
    except requests.exceptions.Timeout:
        return {"error": "The backend took too long to respond (>120 s). Try a smaller or simpler PDF."}
    except Exception as e:
        return {"error": f"API call failed: {str(e)}"}


def fmt_inr(value):
    if value is None:
        return "N/A"
    try:
        return f"₹{float(value):,.0f}"
    except (TypeError, ValueError):
        return "N/A"

def fmt_pct(value, decimals=2):
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"

def draw_card(title, value, subtext="", highlight=False, tooltip="", anim_class=""):
    hl_class = " highlight" if highlight else ""
    icon = f'<span style="font-size:1rem; cursor:help; color:#64748b;" title="{tooltip}">ⓘ</span>' if tooltip else ""
    
    st.markdown(f"""
    <div class="data-card{hl_class} {anim_class}">
        <div class="data-card-title">
            <span>{title}</span>
            {icon}
        </div>
        <div class="data-card-value">{value}</div>
        <div class="data-card-sub">{subtext}</div>
    </div>
    """, unsafe_allow_html=True)

def draw_invest_card(title, value, color_hex, anim_class=""):
    st.markdown(f"""
    <div class="invest-card {anim_class}" style="border-top-color: {color_hex};">
        <div class="invest-card-title">{title}</div>
        <div class="invest-card-value" style="color: {color_hex};">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def render_result(data: dict) -> None:
    if data.get("degraded_analysis"):
        st.warning("⚠️ Partial analysis: AI could not fully parse the document.")

    st.markdown("""
    <div class="success-banner animate-fade-up">
        <span>✅</span>
        <span>Analysis Completed Successfully</span>
    </div>
    """, unsafe_allow_html=True)

    policy_type = data.get("policy_type_detected", "N/A").upper()
    gvng        = data.get("guaranteed_vs_non_guaranteed", "N/A")
    roi_verdict = data.get("roi_verdict", "Unknown")
    
    badge_cls = "badge-neutral"
    if "Good" in roi_verdict: badge_cls = "badge-good"
    elif "Average" in roi_verdict: badge_cls = "badge-warning"
    elif "Poor" in roi_verdict: badge_cls = "badge-danger"

    st.markdown(f"""
    <div class="animate-fade-up" style="display:flex; gap:1rem; margin-bottom:2.5rem; align-items:center; flex-wrap:wrap;">
        <span class="badge badge-neutral">📋 Policy Type: {policy_type}</span>
        <span class="badge badge-neutral">💰 Returns Type: {gvng}</span>
        <span class="badge {badge_cls}">🎯 Verdict: {roi_verdict}</span>
    </div>
    """, unsafe_allow_html=True)

    summary = data.get("policy_summary", {})
    simple  = summary.get("simple_summary") if isinstance(summary, dict) else str(summary)
    if simple:
        st.markdown(f"<div class='risk-box animate-fade-up delay-1' style='margin-bottom:3rem;'><h4 style='margin-top:0; color:#1C1C1E;'>Summary</h4><p style='color:#3A3A3C; font-size:1.05rem; margin-bottom:0;'>{simple}</p></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-title animate-fade-up delay-2'>Core Financials</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    total_investment = data.get("total_investment") or 0
    maturity_value   = data.get("maturity_value")   or 0
    net_profit       = data.get("net_profit")        or 0
    roi              = data.get("roi") or data.get("roi_percent")

    delta_str = f"+{fmt_inr(net_profit)}" if net_profit >= 0 else f"-{fmt_inr(abs(net_profit))}"

    with c1: draw_card("Total Investment", fmt_inr(total_investment), "Premiums over term", tooltip="Total money you pay to the insurance company over the years.", anim_class="animate-fade-up delay-2")
    with c2: draw_card("Maturity Value", fmt_inr(maturity_value), "Expected corpus", tooltip="The total money you get back at the end of the policy.", anim_class="animate-fade-up delay-2")
    with c3: draw_card("Net Profit", delta_str, "Maturity minus investment", tooltip="Your overall earnings.", anim_class="animate-fade-up delay-2")
    with c4: draw_card("Annualized ROI", fmt_pct(roi), "After-tax return", highlight=True, tooltip="Your yearly return after factoring in the income tax you saved.", anim_class="animate-fade-up delay-2")

    st.markdown("<div class='section-title animate-fade-up delay-3'>Rate Metrics & Premium</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    cagr = data.get("cagr") or data.get("cagr_percent")
    irr  = data.get("irr")  or data.get("irr_percent")
    be   = data.get("break_even_year")
    
    prem_details = data.get("premium_details", {})
    prem_amt = fmt_inr(prem_details.get("amount"))
    prem_freq = (prem_details.get("frequency") or "yearly").title()
    
    with c1: draw_card("CAGR", fmt_pct(cagr), "Pure growth rate", tooltip="Your yearly growth rate equivalent to a savings account.", anim_class="animate-fade-up delay-3")
    with c2: draw_card("IRR", fmt_pct(irr), "Cashflow return rate", tooltip="True yearly return considering exact payment dates.", anim_class="animate-fade-up delay-3")
    with c3: draw_card("Break-Even", f"{float(be):.1f} yrs" if be is not None else "N/A", "Value > Premiums", tooltip="When your policy value exceeds total premiums paid.", anim_class="animate-fade-up delay-3")
    with c4: draw_card("Premium", prem_amt, f"{prem_freq} payment", tooltip="Regular payment amount.", anim_class="animate-fade-up delay-3")

    st.markdown("<div class='section-title animate-fade-up delay-4'>Advanced Insights</div>", unsafe_allow_html=True)
    adv = data.get("advanced_metrics", {})
    c1, c2, c3 = st.columns(3)
    with c1:
        tax_ben = data.get("tax_benefit_80c") or adv.get("tax_saved_estimated") or 0
        draw_card("80C Tax Benefit", fmt_inr(tax_ben), "Estimated tax saved", tooltip="Total tax saved under Section 80C over the premium payment term (assuming 31.2% tax bracket).", anim_class="animate-fade-up delay-4")
    with c2:
        infl_adj = data.get("inflation_adj_net_profit") or adv.get("inflation_adj_net_profit") or 0
        draw_card("Inflation-Adj Profit", fmt_inr(infl_adj), "Today's purchasing power", tooltip="Your net profit expressed in today's money value, assuming a standard 6% annual inflation rate.", anim_class="animate-fade-up delay-4")
    with c3:
        adj_cagr = adv.get("inflation_adjusted_cagr")
        draw_card("Real CAGR", fmt_pct(adj_cagr), "Stripping 6% inflation", tooltip="Your actual compound annual growth rate after deducting the 6% annual inflation rate. A negative number means you are losing purchasing power.", anim_class="animate-fade-up delay-4")

    risky = data.get("risky_clauses", [])
    if risky:
        st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
        st.error("🚨 Risky Clauses Detected", icon="🚨")
        for r in risky:
            st.markdown(f"- **{r.get('keyword', '')}:** {r.get('snippet', '')[:250]}…")

    st.markdown("<div class='section-title animate-fade-up delay-5'>Qualitative Analysis</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("<div class='risk-box animate-fade-up delay-5' style='height: 100%;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#1C1C1E; margin-top:0;'>Key Benefits</h4>", unsafe_allow_html=True)
        benefits = data.get("key_benefits", [])
        if benefits:
            pills = "".join(f"<div class='pill pill-green'><b>✓</b> &nbsp; {b}</div>" for b in benefits)
            st.markdown(f"<div style='margin-bottom: 2rem;'>{pills}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#8E8E93;'>No benefits extracted.</p><br>", unsafe_allow_html=True)

        st.markdown("<h4 style='color:#1C1C1E; margin-top:1rem;'>Hidden Clauses</h4>", unsafe_allow_html=True)
        clauses = data.get("hidden_clauses", [])
        if clauses:
            pills = "".join(f"<div class='pill pill-yellow'><b>⚠️</b> &nbsp; {c}</div>" for c in clauses)
            st.markdown(f"<div style='margin-bottom: 1.5rem;'>{pills}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#8E8E93;'>No hidden clauses identified.</p><br>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='risk-box animate-fade-up delay-6' style='height: 100%;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#1C1C1E; margin-top:0;'>Exclusions</h4>", unsafe_allow_html=True)
        exclusions = data.get("exclusions", [])
        if exclusions:
            pills = "".join(f"<div class='pill pill-red'><b>✕</b> &nbsp; {e}</div>" for e in exclusions)
            st.markdown(f"<div style='margin-bottom: 2rem;'>{pills}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#8E8E93;'>No exclusions extracted.</p><br>", unsafe_allow_html=True)

        risk_score = data.get("risk_score", 5)
        risk_level = data.get("risk_level", "Medium")
        ml_risk    = data.get("ml_risk_prediction", "N/A")
        r_badge = "badge-good" if risk_score <= 3 else ("badge-warning" if risk_score <= 6 else "badge-danger")
        
        st.markdown("<h4 style='color:#1C1C1E; margin-top:1rem;'>Risk Analysis</h4>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="margin-top: 0.5rem; background: #F2F2F7; padding: 1.25rem; border-radius: 12px; border: 1px solid #E5E5EA;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                <span style="color:#3A3A3C; font-weight:500;">Risk Score:</span>
                <span class="badge {r_badge}">{risk_score}/10 ({risk_level})</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="color:#3A3A3C; font-weight:500;">ML Prediction:</span>
                <span style="font-weight:600; color:#1C1C1E;">{str(ml_risk).title()}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


    st.markdown("<div class='section-title animate-fade-up delay-6'>Investment Comparison</div>", unsafe_allow_html=True)
    
    comp = data.get("comparison", {})
    policy_roi = data.get("roi") or data.get("roi_percent") or 0
    fd_val = comp.get("fd_7pct_maturity") or 0
    mf_val = comp.get("mf_sip_12pct_projection") or 0

    c1, c2, c3 = st.columns(3)
    r_color = "#34C759" if policy_roi >= 7 else "#FF3B30"
    with c1:
        draw_invest_card("Your Policy Returns", fmt_pct(policy_roi), "#1C1C1E", anim_class="animate-fade-up delay-6")
    with c2:
        draw_invest_card("Fixed Deposit (7%)", fmt_inr(fd_val), "#8E8E93", anim_class="animate-fade-up delay-6")
    with c3:
        draw_invest_card("Mutual Fund (12%)", fmt_inr(mf_val), "#007AFF", anim_class="animate-fade-up delay-6")

    rec = data.get("recommendation", "")
    if rec:
        st.markdown(f"""
        <div class="rec-box animate-fade-up delay-6">
            <strong>💡 Recommendation:</strong><br/>
            <p style="margin-top: 0.5rem; color: #1C1C1E;">{rec}</p>
        </div>
        """, unsafe_allow_html=True)

    warnings = data.get("warnings", [])
    if warnings:
        with st.expander("ℹ️ Analysis Notes"):
            for w in warnings:
                st.info(w)

def render_footer():
    st.markdown("""
    <div class="footer">
        <p>Made with ❤️ by <strong>BimaBuddy AI</strong></p>
        <p>Contact: bimabuddyai@gmail.com</p>
    </div>
    """, unsafe_allow_html=True)
