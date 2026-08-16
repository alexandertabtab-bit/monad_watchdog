import streamlit as st
import requests
import json
from groq import Groq

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
    """Source 2: Open Food Facts API (Fallback for personal care items registered under main database)."""
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
# 3. AI ENGINE: DYNAMIC LONGEVITY SPECTRUM & ANALYSIS (GROQ)
# -----------------------------------------------------------------------------
def ai_analyze_product(product_name, ingredients):
    """Uses Groq AI to generate a custom longevity spectrum and biological report."""
    if not groq_client:
        return None

    prompt = f"""
    You are Monad, an expert biological skincare & chemical watchdog.
    Analyze this product and its INCI ingredient list:
    Product: {product_name}
    Ingredients: {ingredients}

    Return a JSON object with this exact structure (do not include markdown outside JSON):
    {{
        "analysis": "Brief 2-sentence objective summary of key active ingredients and target skin suitability.",
        "pros": ["Pro 1", "Pro 2"],
        "cons": ["Con 1", "Con 2"],
        "spectrum": {{
            "Day 1": "Specific impact on day 1 based on these exact ingredients.",
            "Week 1": "Specific impact after 1 week based on these exact ingredients.",
            "Month 1": "Specific impact after 1 month based on these exact ingredients.",
            "Year 1": "Specific long-term impact after 1 year.",
            "Year 10": "Specific cumulative impact after 10 years.",
            "Year 20": "Specific structural impact after 20 years."
        }}
    }}
    """
    
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You output strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"AI Generation Error: {e}")
        return None


# -----------------------------------------------------------------------------
# 4. STREAMLIT INTERFACE
# -----------------------------------------------------------------------------
st.title("⚡ MONAD: Biological Product Watchdog")
st.caption("Multi-source database engine paired with Groq AI dynamic spectrum forecasting.")

st.markdown("> **Disclaimer:** *Monad provides research-backed biological ingredient analysis for educational purposes.*")

if not GROQ_KEY:
    st.warning("⚠️ Groq API Key not detected in Streamlit Secrets. AI dynamic features are disabled.")

# Search Input
user_query = st.text_input("🔍 Search product or brand name:", placeholder="e.g. Cerave, Fructis, Byphasse, Retinol...")

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
        
        # Run AI Generation
        if GROQ_KEY:
            with st.spinner("🤖 Monad AI generating custom product timeline & analysis..."):
                ai_data = ai_analyze_product(selected_product['label'], selected_product['ingredients'])
                
            if ai_data:
                st.markdown("### 🛡️ AI Biological Breakdown")
                st.write(ai_data.get("analysis", ""))
                
                col_p, col_c = st.columns(2)
                with col_p:
                    st.markdown("#### ✅ Pros")
                    for p in ai_data.get("pros", []):
                        st.markdown(f"- {p}")
                with col_c:
                    st.markdown("#### ⚠️ Cons")
                    for c in ai_data.get("cons", []):
                        st.markdown(f"- {c}")
                
                # DYNAMIC SPECTRUM
                st.markdown("---")
                st.markdown("### ⏳ Customized Product Longevity Spectrum")
                st.caption("AI-generated cumulative skin cell impact tailored specifically to this formula:")
                
                spectrum_data = ai_data.get("spectrum", {})
                if spectrum_data:
                    spec_tabs = st.tabs(list(spectrum_data.keys()))
                    for t_tab, (tf, text) in zip(spec_tabs, spectrum_data.items()):
                        with t_tab:
                            st.write(f"**{tf} Impact:** {text}")
                            
    else:
        st.warning(f"No database matches found for '{user_query}'. Using AI chemical knowledge base fallback...")
        
        if GROQ_KEY:
            with st.spinner("🤖 Consulting Monad AI Knowledge Base..."):
                ai_fallback = ai_analyze_product(user_query, "Common market formulation for " + user_query)
                
            if ai_fallback:
                st.markdown("### 🛡️ AI Estimated Formulation Analysis")
                st.write(ai_fallback.get("analysis", ""))
                
                st.markdown("### ⏳ Estimated Longevity Spectrum")
                spectrum_data = ai_fallback.get("spectrum", {})
                if spectrum_data:
                    spec_tabs = st.tabs(list(spectrum_data.keys()))
                    for t_tab, (tf, text) in zip(spec_tabs, spectrum_data.items()):
                        with t_tab:
                            st.write(f"**{tf} Impact:** {text}")
