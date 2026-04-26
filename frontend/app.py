import streamlit as st
import sys
from pathlib import Path

frontend_dir = Path(__file__).resolve().parent
sys.path.append(str(frontend_dir))

from utils import inject_custom_css, call_analyze_api, render_result, render_footer

st.set_page_config(
    page_title="BimaBuddy AI — Intelligent Insurance Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_custom_css()

# Hide the sidebar completely using custom CSS
st.markdown("""
    <style>
    [data-testid="collapsedControl"] {
        display: none;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
    /* Style for horizontal radio navigation - Apple Style */
    div.stRadio > div[role="radiogroup"] {
        flex-direction: row;
        justify-content: center;
        gap: 0.5rem;
        background-color: #F2F2F7;
        padding: 0.5rem;
        border-radius: 9999px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 2rem;
        border: 1px solid #E5E5EA;
        display: inline-flex;
    }
    div.stRadio > div[role="radiogroup"] > label {
        background-color: transparent !important;
        border: none !important;
        padding: 0.5rem 1.5rem;
        border-radius: 9999px;
        cursor: pointer;
        transition: all 0.2s;
        color: #8E8E93;
        font-weight: 500;
    }
    div.stRadio > div[role="radiogroup"] > label:hover {
        color: #1C1C1E;
        background-color: rgba(0,0,0,0.04) !important;
    }
    div.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #FFFFFF !important;
        color: #1C1C1E;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    /* Hide the radio button circle */
    div.stRadio > div[role="radiogroup"] > label > div:first-child {
        display: none;
    }
    /* Center the top nav */
    div[data-testid="stRadio"] {
        margin-top: 1rem;
        display: flex;
        justify-content: center;
    }
    </style>
""", unsafe_allow_html=True)


def show_home():
    st.markdown("""
    <div class="hero-container animate-fade-up">
        <div class="hero-logo">🛡️</div>
        <h1 class="hero-title">BimaBuddy AI</h1>
        <p class="hero-subtitle">Understand Your Insurance Policy Instantly</p>
    </div>
    """, unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown("""
        <div class="feature-card animate-fade-up delay-1">
            <div class="feature-icon">🧠</div>
            <h4 class="feature-title" style="margin-top:0;">Smart Analysis</h4>
            <div class="feature-desc">AI-powered extraction of key benefits, risks, and important policy details</div>
        </div>
        """, unsafe_allow_html=True)
    with f2:
        st.markdown("""
        <div class="feature-card animate-fade-up delay-2">
            <div class="feature-icon">👀</div>
            <h4 class="feature-title" style="margin-top:0;">Risk Detection</h4>
            <div class="feature-desc">Identifies hidden clauses, exclusions, and potential risks in your policy</div>
        </div>
        """, unsafe_allow_html=True)
    with f3:
        st.markdown("""
        <div class="feature-card animate-fade-up delay-3">
            <div class="feature-icon">📊</div>
            <h4 class="feature-title" style="margin-top:0;">Financial Insights</h4>
            <div class="feature-desc">Compares your policy with fixed deposits and mutual funds</div>
        </div>
        """, unsafe_allow_html=True)
    with f4:
        st.markdown("""
        <div class="feature-card animate-fade-up delay-4">
            <div class="feature-icon">⚖️</div>
            <h4 class="feature-title" style="margin-top:0;">Policy Comparison</h4>
            <div class="feature-desc">Compare your policy’s coverage and limitations clearly and objectively</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)


def show_analyze():
    st.markdown("""
        <h1 style='font-size: 2.5rem; font-weight: 700; color: #1C1C1E; margin-bottom: 0.25rem;'>Analyze Your Policy</h1>
        <p style='font-size: 1.1rem; color: #666; margin-top: 0;'>Upload your insurance policy PDF to extract key insights instantly.</p>
        <br>
    """, unsafe_allow_html=True)

    col_up1, col_up2, col_up3 = st.columns([1, 2, 1])
    with col_up2:
        uploaded = st.file_uploader(
            "Upload your Insurance Policy PDF",
            type=["pdf"],
            help="Max 16 MB — text-selectable PDFs work best",
        )

        if st.button("🔍 Analyze Policy", use_container_width=True):
            if uploaded is None:
                st.warning("⚠️ Please upload a PDF file first.")
                return

            with st.spinner("⏳ Sending to BimaBuddy AI backend… this may take 30–60 seconds."):
                try:
                    result = call_analyze_api(uploaded)

                    if result is None:
                        st.error("❌ Analysis failed to return a result.")
                        return

                    if "error" in result:
                        st.error(f"❌ {result['error']}")
                        return

                    st.session_state['analysis_result'] = result
                    st.success("Analysis complete!")

                except Exception as e:
                    import traceback
                    st.error(f"❌ Unexpected error: {str(e)}")
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())

    if 'analysis_result' in st.session_state:
        st.markdown("<hr style='border:1px solid #E5E5EA; margin: 3rem 0;'>", unsafe_allow_html=True)
        render_result(st.session_state['analysis_result'])


def show_how_it_works():
    st.markdown("""
        <h1 style='font-size: 2.5rem; font-weight: 700; color: #1C1C1E; margin-bottom: 0.25rem;'>How It Works</h1>
        <p style='font-size: 1.1rem; color: #666; margin-top: 0;'>Understanding how BimaBuddy AI processes your insurance policy.</p>
        <br>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.markdown("""
        <div class="data-card animate-fade-up delay-1">
            <div class="feature-icon">1️⃣</div>
            <div class="feature-title">Upload</div>
            <div class="feature-desc">Securely upload your policy PDF for instant analysis. Your document is processed in-memory and never stored.</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="data-card animate-fade-up delay-2">
            <div class="feature-icon">2️⃣</div>
            <div class="feature-title">AI Processing</div>
            <div class="feature-desc">Our system reads your policy and pulls out key details like coverage, important clauses, and financial information.</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="data-card animate-fade-up delay-3">
            <div class="feature-icon">3️⃣</div>
            <div class="feature-title">Review Insights</div>
            <div class="feature-desc">Get a clear summary of your policy, including benefits, possible risks, and important details.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### Privacy & Security")
    st.info("Your privacy is our priority. Documents are encrypted during transfer and processed securely in temporary memory. We never store your files or share them with third parties, all data is permanently discarded immediately after analysis.")


def show_about():
    st.markdown("""
        <h1 style='font-size: 2.5rem; font-weight: 700; color: #1C1C1E; margin-bottom: 0.25rem;'>About BimaBuddy AI</h1>
        <p style='font-size: 1.1rem; color: #666; margin-top: 0;'>BimaBuddy AI helps you understand complex insurance policies using simple, AI-powered insights.</p>
        <br>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="risk-box animate-fade-up delay-1" style="margin-bottom: 2rem;">
        <h3 style="color: #1C1C1E; margin-top: 0;">Our Mission</h3>
        <p style="color: #3A3A3C; font-size: 1.05rem; line-height: 1.6;">
            Insurance policies are often full of complex terms, hidden clauses, and confusing details. Our mission is to make this information simple and easy to understand for everyone. We believe every policyholder should clearly know what they are signing up for.ance policies are often filled with complex jargon, hidden clauses, and convoluted financial terms.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Why Choose Us?")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="feature-card animate-fade-up delay-2">
            <h4 class="feature-title" style="margin-top:0;">Unbiased Analysis</h4>
            <div class="feature-desc">We don’t sell insurance. Our insights are unbiased and focused only on helping you make better decisions.</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="feature-card animate-fade-up delay-3">
            <h4 class="feature-title" style="margin-top:0;">Advanced Technology</h4>
            <div class="feature-desc">Powered by advanced AI designed to understand and analyze legal and financial documents.</div>
        </div>
        """, unsafe_allow_html=True)


def show_contact():
    st.markdown("""
        <h1 style='font-size: 2.5rem; font-weight: 700; color: #1C1C1E; margin-bottom: 0.25rem;'>Contact Us</h1>
        <p style='font-size: 1.1rem; color: #666; margin-top: 0;'>Have questions or feedback? We'd love to hear from you.</p>
        <br>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### Get in Touch")
        with st.form("contact_form"):
            name = st.text_input("Name")
            email = st.text_input("Email Address")
            subject = st.text_input("Subject")
            message = st.text_area("Message", height=150)
            
            submit = st.form_submit_button("Send Message", use_container_width=True)
            if submit:
                if name and email and message:
                    st.success("✅ Thank you for your message! We will get back to you shortly.")
                else:
                    st.error("⚠️ Please fill out all required fields (Name, Email, Message).")

    with col2:
        st.markdown("""
        <div class="risk-box animate-fade-up delay-1" style="height: 100%;">
            <h3 style="color: #1C1C1E; margin-top: 0;">Support Information</h3>
            <p style="color: #3A3A3C; margin-bottom: 1.5rem;">
                Our support team is available Monday to Friday to help with any questions about BimaBuddy AI.
            </p>
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <span style="font-size: 1.5rem; margin-right: 1rem;">📧</span>
                <span style="color: #1C1C1E; font-weight: 500;">bimabuddyai@gmail.com</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 1rem;">
                <span style="font-size: 1.5rem; margin-right: 1rem;">🏢</span>
                <span style="color: #1C1C1E; font-weight: 500;">Remote, India</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def main():
    # Hide the radio button label by assigning it to a variable or passing label_visibility="collapsed"
    page = st.radio(
        "Navigation", 
        ["Home", "Analyze", "How it Works", "About", "Contact"], 
        horizontal=True,
        label_visibility="collapsed"
    )

    if page == "Home":
        show_home()
    elif page == "Analyze":
        show_analyze()
    elif page == "How it Works":
        show_how_it_works()
    elif page == "About":
        show_about()
    elif page == "Contact":
        show_contact()

    render_footer()

if __name__ == "__main__":
    main()
