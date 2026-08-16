import streamlit as st
import requests
import json
from groq import Groq
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. SETUP & API INITIALIZATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monad Watchdog", page_icon="⚡", layout="centered")

# Retrieve Groq API Key safely from Secrets
GROQ_KEY = st.secrets.get("GROQ_API_KEY", None)
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

# -----------------------------------------------------------------------------
# 2. MULTI-SOURCE INGREDIENT RETRIEVAL PIPELINE
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_from_open_beauty_facts(query):
    """Source 1: Open Beauty Facts API."""
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
    """Source 2: Open Food Facts API (Fallback registry)."""
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
    """Aggregates results across multiple databases."""
    results = fetch_from_open_beauty_facts(query)
    if not results:
        results = fetch_from_open_food_facts(query)
    return results


# -----------------------------------------------------------------------------
# 3. AI ENGINE: CLINICAL ANALYSIS, DOSING PROTOCOL & SPECTRUM
# -----------------------------------------------------------------------------
def ai_analyze_product(product_name, ingredients):
    """Uses Groq AI to generate a biological report, dosing protocol, and longevity spectrum."""
    if not groq_client:
        return None

    prompt = f"""
    You are Monad, an expert clinical cosmetologist, dermatological chemist, and biological watchdog.
    Analyze this product and its INCI ingredient list:
    Product: {product_name}
    Ingredients: {ingredients}

    Return a JSON object with this exact structure (do not include markdown outside JSON):
    {{
        "analysis": "Brief 2-sentence clinical summary of key active ingredients and target skin barrier interaction.",
        "usage_protocol": {{
            "frequency": "e.g., Start 2-3 nights per week, progress to nightly as tolerated",
            "time_of_day": "e.g., PM only (Photo-sensitive) or AM/PM",
            "application_step": "e.g., Apply after water-based serums, prior to heavy occlusives",
            "time_to_visible_results": "e.g., 4 to 6 weeks for epidermal turnover"
        }},
        "pros": ["Pro 1", "Pro 2"],
        "cons": ["Con 1", "Con 2"],
        "spectrum": {{
            "Day 1": "Immediate barrier and hydration effect upon first application.",
            "Week 1": "Initial cellular adaptation and skin tolerance adjustment.",
            "Month 1": "Visible surface texture and epidermal improvement.",
            "Year 1": "Long-term collagen and structural maintenance benefit.",
            "Year 10": "Cumulative anti-aging / structural preservation effect."
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
                {"role": "system", "content": "You output strictly valid JSON with clinical precision."},
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


def ai_analyze_interaction(product_name, ingredients, user_concern):
    """Analyzes custom user conditions, skin irritation, or product stacking."""
    if not groq_client:
        return None

    prompt = f"""
    Product: {product_name}
    Formula INCI: {ingredients}
    User Query / Condition: {user_concern}

    Analyze potential chemical incompatibilities, skin irritation risks, barrier disruption, or contraindications.
    Structure output in clean Markdown:
    - **Compatibility & Safety Status**: (Safe / Exercise Caution / Avoid Combination)
    - **Biochemical Mechanism**: (Explain why this interaction or irritation occurs at a cellular/barrier level)
    - **Recommended Adjusted Action Plan**: (Specific steps for the user to safely manage or adjust application)
    - **Clinical References**: (Mention standard medical literature like CIR, PubMed, or DermNet NZ)
    """

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a clinical dermatological AI offering precise, evidence-based advice."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Interaction Query Error: {e}")
        return None


# -----------------------------------------------------------------------------
# 4. STREAMLIT INTERFACE & LIVE SEARCH COMPONENT
# -----------------------------------------------------------------------------
st.title("⚡ MONAD: Biological Product Watchdog")
st.caption("Multi-source database engine paired with Groq AI dynamic clinical forecasting.")

st.markdown("> **Medical Disclaimer:** *Monad provides research-backed biological ingredient analysis for educational and barrier-monitoring purposes. Consult a dermatologist for active clinical treatment.*")

if not GROQ_KEY:
    st.warning("⚠️ Groq API Key not detected in Streamlit Secrets. AI dynamic features are disabled.")

# Live Autocomplete Data List HTML/JS Component
html_datalist = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 5px;">
    <label style="font-size: 14px; font-weight: 600; color: #1e293b;">⚡ Instant Live Suggestions (Type to see common matches):</label>
    <input list="skincare_suggestions" id="live_input" placeholder="Type brand name (e.g., CeraVe, La Roche-Posay, The Ordinary)..." 
           style="width: 100%; padding: 10px; margin-top: 6px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 15px; outline: none; background-color: #f8fafc; color: #0f172a;"/>
    <datalist id="skincare_suggestions">
        <option value="CeraVe Hydrating Facial Cleanser">
        <option value="CeraVe Resurfacing Retinol Serum">
        <option value="The Ordinary Niacinamide 10% + Zinc 1%">
        <option value="The Ordinary Glycolic Acid 7% Toning Solution">
        <option value="La Roche-Posay Effaclar Duo">
        <option value="La Roche-Posay Anthelios SPF 50+">
        <option value="Byphasse Micellar Make-up Remover">
        <option value="Paula's Choice 2% BHA Liquid Exfoliant">
        <option value="Bioderma Sensibio H2O Micellar Water">
    </datalist>
</div>
"""
components.html(html_datalist, height=85)

# Primary Query Trigger
user_query = st.text_input("🔍 Search database for exact product or brand name:", placeholder="e.g. CeraVe, Byphasse, Retinol...")

if user_query:
    st.divider()
    
    with st.spinner("Querying multiple database registries..."):
        matches = multi_source_search(user_query)
        
    if matches:
        options = [f"{m['label']} ({m['source']})" for m in matches]
        selected_option = st.selectbox(f"Found {len(matches)} verified matches across registries:", options=options)
        
        selected_product = next(m for m in matches if f"{m['label']} ({m['source']})" == selected_option)
        
        st.markdown("---")
        st.success(f"**Loaded Product:** {selected_product['label']}")
        st.caption(f"Source Database: {selected_product['source']}")
        
        st.markdown("### 🔬 Extracted INCI Label")
        st.info(selected_product["ingredients"])
        
        # Run AI Clinical Analysis
        if GROQ_KEY:
            with st.spinner("🤖 Monad AI analyzing clinical protocol & formula spectrum..."):
                ai_data = ai_analyze_product(selected_product['label'], selected_product['ingredients'])
                
            if ai_data:
                st.markdown("### 🛡️ AI Biological Breakdown")
                st.write(ai_data.get("analysis", ""))
                
                # Dedicated Administration & Dosing Protocol
                protocol = ai_data.get("usage_protocol", {})
                if protocol:
                    st.markdown("#### 📋 Clinical Usage & Dosing Protocol")
                    p_col1, p_col2 = st.columns(2)
                    with p_col1:
                        st.markdown(f"**Frequency:** {protocol.get('frequency', 'N/A')}")
                        st.markdown(f"**Timing:** {protocol.get('time_of_day', 'N/A')}")
                    with p_col2:
                        st.markdown(f"**Routine Order:** {protocol.get('application_step', 'N/A')}")
                        st.markdown(f"**Expected Results Window:** {protocol.get('time_to_visible_results', 'N/A')}")

                col_p, col_c = st.columns(2)
                with col_p:
                    st.markdown("#### ✅ Pros")
                    for p in ai_data.get("pros", []):
                        st.markdown(f"- {p}")
                with col_c:
                    st.markdown("#### ⚠️ Cons")
                    for c in ai_data.get("cons", []):
                        st.markdown(f"- {c}")
                
                # Dynamic Spectrum
                st.markdown("---")
                st.markdown("### ⏳ Customized Product Longevity Spectrum")
                st.caption("AI-forecasted skin cell impact tailored specifically to this formula:")
                
                spectrum_data = ai_data.get("spectrum", {})
                if spectrum_data:
                    spec_tabs = st.tabs(list(spectrum_data.keys()))
                    for t_tab, (tf, text) in zip(spec_tabs, spectrum_data.items()):
                        with t_tab:
                            st.write(f"**{tf} Impact:** {text}")

                # Medical Literature References
                st.markdown("---")
                st.markdown("#### 📚 Grounded Medical Sources")
                for src in ai_data.get("medical_sources", []):
                    st.markdown(f"- *{src}*")

                # Custom Interaction & Irritation Query Assistant
                st.markdown("---")
                st.markdown("### 🩺 Clinical Interaction & Irritation Assistant")
                st.caption("Ask specific questions about skin flare-ups, irritation, or combining this product with other routines.")

                user_concern = st.text_area(
                    "Describe your skin condition or routine stacking query:",
                    placeholder="e.g., I have skin irritation around my cheeks, or I am using 10% Azelaic Acid with this product..."
                )

                if st.button("Analyze Medical Interaction / Irritation") and user_concern:
                    with st.spinner("Analyzing pharmacological interactions..."):
                        interaction_report = ai_analyze_interaction(
                            selected_product['label'], 
                            selected_product['ingredients'], 
                            user_concern
                        )
                        if interaction_report:
                            st.markdown("---")
                            st.markdown(interaction_report)

    else:
        st.warning(f"No database matches found for '{user_query}'. Using AI chemical knowledge base fallback...")
        
        if GROQ_KEY:
            with st.spinner("🤖 Consulting Monad AI Knowledge Base..."):
                ai_fallback = ai_analyze_product(user_query, "Common market formulation for " + user_query)
                
            if ai_fallback:
                st.markdown("### 🛡️ AI Estimated Formulation Analysis")
                st.write(ai_fallback.get("analysis", ""))
                
                protocol = ai_fallback.get("usage_protocol", {})
                if protocol:
                    st.markdown("#### 📋 Estimated Usage Protocol")
                    p_col1, p_col2 = st.columns(2)
                    with p_col1:
                        st.markdown(f"**Frequency:** {protocol.get('frequency', 'N/A')}")
                        st.markdown(f"**Timing:** {protocol.get('time_of_day', 'N/A')}")
                    with p_col2:
                        st.markdown(f"**Routine Order:** {protocol.get('application_step', 'N/A')}")
                        st.markdown(f"**Expected Results Window:** {protocol.get('time_to_visible_results', 'N/A')}")

                st.markdown("### ⏳ Estimated Longevity Spectrum")
                spectrum_data = ai_fallback.get("spectrum", {})
                if spectrum_data:
                    spec_tabs = st.tabs(list(spectrum_data.keys()))
                    for t_tab, (tf, text) in zip(spec_tabs, spectrum_data.items()):
                        with t_tab:
                            st.write(f"**{tf} Impact:** {text}")
