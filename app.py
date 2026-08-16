import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & API KEYS
# -----------------------------------------------------------------------------



st.set_page_config(page_title="Monad Watchdog", page_icon="🌸", layout="wide")

# CSS to fix mobile pull-to-refresh
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        overscroll-behavior-y: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Navigation Tabs at the top
tab1, tab2 = st.tabs(
    ["🔍 Product Analysis", "🔄 Routine Stacking Compatibility"]
)

with tab1:
    st.markdown("### 📸 Scan or Enter Product Barcode")

    # This creates the side-by-side layout on PC (and stacks nicely on mobile)
    col_input, col_results = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown("#### Input Method")

        # 1. Manual Barcode Text Input
        manual_barcode = st.text_input(
            "Or type barcode number manually:",
            placeholder="e.g., 5449000000996",
        )

        st.markdown("---")
        st.markdown("**Take a photo of the product barcode**")

        # 2. Camera Input
        camera_image = st.camera_input("Camera Feed", label_visibility="collapsed")

        # 3. Search Action Button
        search_clicked = st.button(
            "Analyze Product", type="primary", use_container_width=True
        )

    with col_results:
        st.markdown("#### Analysis & Results")

        # Your processing/lookup logic goes here
        if manual_barcode:
            st.success(f"Processing manual barcode: {manual_barcode}")
        elif camera_image:
            st.success("Barcode image captured successfully!")
        else:
            st.info(
                "👈 Scan a barcode with your camera or type the code manually to view product analysis results here."
            )

with tab2:
    st.markdown("### Routine Stacking Compatibility")
    st.info("Routine compatibility tools will appear here.")


# Your existing code continues below...

GROQ_KEY = st.secrets.get("GROQ_API_KEY", None)
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

# -----------------------------------------------------------------------------
# 2. ATMOSPHERIC JAPANESE SAKURA & PARTICLE BACKGROUND
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
    /* Falling Sakura Petals & Particle Animation */
    @keyframes sakuraFall {
        0% {
            background-position: 0px 0px, 0px 0px, 0px 0px;
        }
        100% {
            background-position: 500px 1000px, -400px 800px, 300px 600px;
        }
    }

    /* Ambient Pulsing Glow */
    @keyframes orbGlow {
        0% { opacity: 0.3; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(1.05); }
        100% { opacity: 0.3; transform: scale(1); }
    }

    /* Deep Space Fluid Mesh with Sakura Layers */
    .stApp {
        background-color: #060913 !important;
        background-image: 
            /* Light Rays & Atmospheric Glow */
            radial-gradient(circle at 85% 15%, rgba(244, 114, 182, 0.25) 0%, transparent 45%),
            radial-gradient(circle at 15% 85%, rgba(56, 189, 248, 0.2) 0%, transparent 50%),
            /* Petal Layer 1 - Floating Blossom Dust */
            radial-gradient(2px 2px at 30px 40px, rgba(251, 207, 232, 0.9), rgba(0,0,0,0)),
            radial-gradient(3px 3px at 150px 180px, rgba(244, 114, 182, 0.85), rgba(0,0,0,0)),
            /* Petal Layer 2 - Midground Petals */
            radial-gradient(4px 6px at 280px 90px, rgba(244, 114, 182, 0.75), rgba(0,0,0,0)),
            radial-gradient(3px 5px at 420px 310px, rgba(251, 207, 232, 0.8), rgba(0,0,0,0)),
            /* Dark Background Base */
            radial-gradient(circle at 50% 50%, rgba(15, 23, 42, 0.85) 0%, #060913 100%) !important;
        background-size: 100% 100%, 100% 100%, 350px 350px, 450px 450px, 550px 550px, 650px 650px, 100% 100% !important;
        animation: sakuraFall 28s linear infinite !important;
        color: #f1f5f9;
    }

    /* Glassmorphic UI Cards */
    div[data-testid="stExpander"], 
    div[data-testid="stVerticalBlock"] > div {
        background: rgba(10, 15, 29, 0.65) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(244, 114, 182, 0.25) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        border-radius: 16px !important;
    }

    input, select, textarea {
        background-color: rgba(30, 41, 59, 0.85) !important;
        color: #f8fafc !important;
        border: 1px solid #6366f1 !important;
        border-radius: 10px !important;
    }

    .stButton > button {
        background: linear-gradient(90deg, #ec4899 0%, #8b5cf6 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        box-shadow: 0 0 18px rgba(236, 72, 153, 0.7);
        transform: translateY(-1px);
    }

    h1, h2, h3 {
        color: #f472b6 !important;
        text-shadow: 0 0 15px rgba(244, 114, 182, 0.5) !important;
    }
    
    h4 {
        color: #38bdf8 !important;
        text-shadow: 0 0 10px rgba(56, 189, 248, 0.4) !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 3. INGREDIENT RETRIEVAL PIPELINE
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_from_open_beauty_facts(query):
    url = f"https://world.openbeautyfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=10"
    headers = {"User-Agent": "MonadWatchdog - Research/Educational - v1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            products = res.json().get("products", [])
            valid = []
            for p in products:
                name = p.get("product_name") or p.get("product_name_en")
                brands = p.get("brands", "")
                ingredients = p.get("ingredients_text") or p.get("ingredients_text_en")
                if name and ingredients and len(ingredients.strip()) > 5:
                    label = f"{brands} - {name}" if brands else name
                    valid.append({"label": label, "ingredients": ingredients.strip(), "source": "Open Beauty Facts"})
            return valid
    except Exception:
        pass
    return []

@st.cache_data(ttl=300)
def fetch_from_open_food_facts(query):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=10"
    headers = {"User-Agent": "MonadWatchdog - Research/Educational - v1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            products = res.json().get("products", [])
            valid = []
            for p in products:
                name = p.get("product_name") or p.get("product_name_en")
                brands = p.get("brands", "")
                ingredients = p.get("ingredients_text") or p.get("ingredients_text_en")
                if name and ingredients and len(ingredients.strip()) > 5:
                    label = f"{brands} - {name}" if brands else name
                    valid.append({"label": label, "ingredients": ingredients.strip(), "source": "Open Food Facts Registry"})
            return valid
    except Exception:
        pass
    return []

def multi_source_search(query):
    results = fetch_from_open_beauty_facts(query)
    if not results:
        results = fetch_from_open_food_facts(query)
    return results

def parse_ingredient_badges(ingredients_text):
    text_lower = ingredients_text.lower()
    
    replenishing = ["ceramide", "hyaluronic", "glycerin", "panthenol", "squalane", "centella", "allantoin", "niacinamide", "cholesterol", "madecassoside"]
    actives = ["retinol", "retinal", "glycolic", "salicylic", "lactic", "ascorbic", "benzoyl", "azelaic", "adapalene", "tretinoin"]
    irritants = ["fragrance", "parfum", "alcohol denat", "linalool", "limonene", "citral", "eugenol", "essential oil", "menthol", "eucalyptus"]

    found_replenish = [i.title() for i in replenishing if i in text_lower]
    found_actives = [i.title() for i in actives if i in text_lower]
    found_irritants = [i.title() for i in irritants if i in text_lower]

    return found_replenish, found_actives, found_irritants

# -----------------------------------------------------------------------------
# 4. AI ENGINES
# -----------------------------------------------------------------------------
def ai_analyze_product(product_name, ingredients, skin_profile):
    if not groq_client:
        return None

    prompt = f"""
    You are Monad, an expert clinical cosmetologist and biological watchdog.
    Analyze this product for a user with the following skin profile:
    Skin Type: {skin_profile.get('type')}
    Barrier State: {skin_profile.get('barrier')}

    Product: {product_name}
    Ingredients: {ingredients}

    Return a JSON object with this exact structure (do not include markdown outside JSON):
    {{
        "analysis": "Brief 2-sentence clinical summary tailored specifically to their skin type/barrier state.",
        "usage_protocol": {{
            "frequency": "Frequency adapted to their barrier condition",
            "time_of_day": "AM/PM guidance",
            "application_step": "Order in skincare routine",
            "time_to_visible_results": "Expected timeline"
        }},
        "pros": ["Pro tailored to profile 1", "Pro tailored to profile 2"],
        "cons": ["Con/Caution tailored to profile 1", "Con/Caution tailored to profile 2"],
        "spectrum": {{
            "Day 1": "Immediate reaction / feel",
            "Week 1": "Initial cellular adaptation response",
            "Month 1": "Epidermal structural changes",
            "Year 1": "Long-term maintenance impact",
            "Year 10": "Structural preservation effect"
        }},
        "medical_sources": [
            "Cosmetic Ingredient Review (CIR) Safety Assessment",
            "PubChem Compound Database (NIH)",
            "DermNet NZ Dermatological Guidelines"
        ]
    }}
    """
    
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Output strictly valid JSON with clinical precision."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"AI Generation Error: {e}")
        return None

def ai_check_compatibility(prod_a_name, prod_a_ing, prod_b_name, prod_b_ing, skin_profile):
    if not groq_client:
        return None

    prompt = f"""
    Analyze the simultaneous use of these two products for a user with {skin_profile.get('type')} skin and a {skin_profile.get('barrier')} barrier:

    Product A: {prod_a_name}
    Ingredients A: {prod_a_ing}

    Product B: {prod_b_name}
    Ingredients B: {prod_b_ing}

    Provide a concise clinical evaluation covering:
    1. **Overall Compatibility Verdict**: (Compatible / Alternate Days / Do Not Combine)
    2. **Active Ingredient Overlaps & pH Conflicts**: (e.g., AHA/BHA + Retinoid, Acid + Vitamin C)
    3. **Barrier Disruption Risk**: Impact on lipid matrix and transepidermal water loss.
    4. **Safe Routine Strategy**: How to split or layer them safely (e.g., A in AM, B in PM).
    """

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a clinical cosmetologist providing rigorous safety evaluations."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Compatibility Error: {e}")
        return None

# -----------------------------------------------------------------------------
# 5. STREAMLIT INTERFACE
# -----------------------------------------------------------------------------
st.title("🌸 MONAD: Biological Watchdog")
st.caption("✨ Multi-source database engine with personalized clinical forecasting.")

st.markdown("> **Medical Disclaimer:** *Monad provides research-backed biological ingredient analysis for educational purposes. Consult a dermatologist for active clinical treatment.*")

if not GROQ_KEY:
    st.warning("⚠️ Groq API Key not detected in Streamlit Secrets. AI dynamic features are disabled.")

html_datalist = """
<div style="font-family: sans-serif; margin-bottom: 5px;">
    <label style="font-size: 14px; font-weight: 600; color: #38bdf8;">⚡ Quick Search (Type brand or product name):</label>
    <input list="skincare_suggestions" id="live_input" placeholder="e.g. CeraVe, La Roche-Posay, The Ordinary..." 
           style="width: 100%; padding: 10px; margin-top: 6px; border-radius: 8px; border: 1px solid #6366f1; font-size: 15px; outline: none; background-color: rgba(30, 41, 59, 0.85); color: #f8fafc;"/>
    <datalist id="skincare_suggestions">
        <option value="CeraVe Hydrating Facial Cleanser">
        <option value="CeraVe Resurfacing Retinol Serum">
        <option value="The Ordinary Niacinamide 10% + Zinc 1%">
        <option value="The Ordinary Glycolic Acid 7% Toning Solution">
        <option value="La Roche-Posay Effaclar Duo">
        <option value="La Roche-Posay Anthelios SPF 50+">
        <option value="Paula's Choice 2% BHA Liquid Exfoliant">
    </datalist>
</div>
"""
components.html(html_datalist, height=85)

with st.expander("👤 Customize Your Skin Profile (Personalized Analysis)", expanded=True):
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        skin_type = st.selectbox("Skin Type:", ["Balanced / Normal", "Sensitive / Reactive", "Oily / Acne-Prone", "Dry / Dehydrated", "Combination"])
    with col_s2:
        barrier_state = st.selectbox("Current Barrier Condition:", ["Healthy / Resilient", "Slightly Irritated / Flaky", "Compromised / Stinging / Red"])

user_profile = {"type": skin_type, "barrier": barrier_state}

tab_single, tab_stack = st.tabs(["🔍 Product Analysis", "🔄 Routine Stacking Compatibility"])

# -----------------------------------------------------------------------------
# TAB 1: SINGLE PRODUCT ANALYSIS (WITH CAMERA BARCODE SCANNER)
# -----------------------------------------------------------------------------
with tab_single:
    st.markdown("### 📸 Scan Product Barcode")
    camera_photo = st.camera_input("Take a photo of the product barcode")
    
    if camera_photo:
        st.info("📷 Barcode camera frame captured!")

    st.markdown("---")

    user_query = st.text_input("Product Search:", placeholder="Enter brand or product name...", key="single_search")

    if user_query:
        with st.spinner("Searching multi-source registries..."):
            matches = multi_source_search(user_query)
            
        if matches:
            options = [f"{m['label']} ({m['source']})" for m in matches]
            selected_option = st.selectbox("Select verified product:", options=options, key="single_select")
            selected_product = next(m for m in matches if f"{m['label']} ({m['source']})" == selected_option)
            
            st.markdown("---")
            st.success(f"**Loaded:** {selected_product['label']}")

            f_rep, f_act, f_irr = parse_ingredient_badges(selected_product['ingredients'])
            badge_cols = st.columns(3)
            with badge_cols[0]:
                st.markdown("**🟢 Barrier Support**")
                st.write(", ".join(f_rep) if f_rep else "None detected")
            with badge_cols[1]:
                st.markdown("**🟡 Potent Actives**")
                st.write(", ".join(f_act) if f_act else "None detected")
            with badge_cols[2]:
                st.markdown("**🔴 Irritants / Fragrance**")
                st.write(", ".join(f_irr) if f_irr else "None detected")

            st.markdown("---")

            if GROQ_KEY:
                with st.spinner("✨ Monad AI evaluating formula for your skin profile..."):
                    ai_data = ai_analyze_product(selected_product['label'], selected_product['ingredients'], user_profile)
                    
                if ai_data:
                    st.markdown("### 🛡️ AI Biological Summary")
                    st.write(ai_data.get("analysis", ""))
                    
                    col_p, col_c = st.columns(2)
                    with col_p:
                        st.markdown("#### ✅ Pros")
                        for p in ai_data.get("pros", []):
                            st.markdown(f"- {p}")
                    with col_c:
                        st.markdown("#### ⚠️ Cautions & Cons")
                        for c in ai_data.get("cons", []):
                            st.markdown(f"- {c}")

                    st.markdown("---")
                    st.markdown("### ⏳ Customized Longevity Spectrum")
                    spectrum_data = ai_data.get("spectrum", {})
                    if spectrum_data:
                        spec_tabs = st.tabs(list(spectrum_data.keys()))
                        for t_tab, (tf, text) in zip(spec_tabs, spectrum_data.items()):
                            with t_tab:
                                st.write(f"**{tf} Impact:** {text}")

                    st.markdown("---")
                    with st.expander("🔬 Deep Dive Clinical Lab (Dosing & Citations)", expanded=False):
                        st.markdown("#### 📋 Personalized Dosing Protocol")
                        protocol = ai_data.get("usage_protocol", {})
                        if protocol:
                            p_col1, p_col2 = st.columns(2)
                            with p_col1:
                                st.markdown(f"**Frequency:** {protocol.get('frequency', 'N/A')}")
                                st.markdown(f"**Timing:** {protocol.get('time_of_day', 'N/A')}")
                            with p_col2:
                                st.markdown(f"**Routine Order:** {protocol.get('application_step', 'N/A')}")
                                st.markdown(f"**Results Window:** {protocol.get('time_to_visible_results', 'N/A')}")

                        st.markdown("---")
                        st.markdown("#### 📚 Grounded Medical Sources")
                        for src in ai_data.get("medical_sources", []):
                            st.markdown(f"- *{src}*")

                    st.markdown("---")
                    with st.expander("🏷️ Extracted INCI Ingredient Formula", expanded=False):
                        st.caption(f"Source: {selected_product['source']}")
                        st.info(selected_product["ingredients"])

# -----------------------------------------------------------------------------
# TAB 2: ROUTINE STACKING & COMPATIBILITY MATRIX
# -----------------------------------------------------------------------------
with tab_stack:
    st.markdown("### 🔄 Dual-Product Routine Stacking Evaluation")
    st.caption("Check chemical compatibility and barrier safety before layering two products.")

    col_a, col_b = st.columns(2)
    
    with col_a:
        query_a = st.text_input("Product A Name:", placeholder="e.g. Glycolic Acid Toning Solution", key="query_a")
        match_a = multi_source_search(query_a) if query_a else []
        selected_a = None
        if match_a:
            opt_a = [m['label'] for m in match_a]
            sel_a_name = st.selectbox("Select Product A:", opt_a, key="sel_a")
            selected_a = next(m for m in match_a if m['label'] == sel_a_name)

    with col_b:
        query_b = st.text_input("Product B Name:", placeholder="e.g. Resurfacing Retinol Serum", key="query_b")
        match_b = multi_source_search(query_b) if query_b else []
        selected_b = None
        if match_b:
            opt_b = [m['label'] for m in match_b]
            sel_b_name = st.selectbox("Select Product B:", opt_b, key="sel_b")
            selected_b = next(m for m in match_b if m['label'] == sel_b_name)

    if selected_a and selected_b:
        st.markdown("---")
        if st.button("🧪 Evaluate Chemical & Routine Compatibility"):
            with st.spinner("Analyzing pharmacological interactions & pH conflicts..."):
                report = ai_check_compatibility(
                    selected_a['label'], selected_a['ingredients'],
                    selected_b['label'], selected_b['ingredients'],
                    user_profile
                )
                if report:
                    st.markdown(report)
