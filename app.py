import streamlit as st
import requests

# -----------------------------------------------------------------------------
# 1. ENHANCED SEARCH & API FILTERING (Open Beauty Facts)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def search_open_beauty_facts(query):
    """Searches Open Beauty Facts and returns ONLY products with valid ingredient lists."""
    if not query or len(query.strip()) < 2:
        return []
    
    url = f"https://world.openbeautyfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=20"
    headers = {"User-Agent": "MonadWatchdog - Research/Educational - v1.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            
            valid_results = []
            for p in products:
                name = p.get("product_name") or p.get("product_name_en")
                brands = p.get("brands", "")
                ingredients = p.get("ingredients_text") or p.get("ingredients_text_en")
                
                # CRITICAL FILTER: Only include entries that actually have an ingredient list!
                if name and ingredients and len(ingredients.strip()) > 5:
                    display_label = f"{brands} - {name}" if brands else name
                    valid_results.append({
                        "label": display_label,
                        "ingredients": ingredients.strip()
                    })
            return valid_results
    except Exception:
        pass
    return []


# -----------------------------------------------------------------------------
# 2. MONAD HARDCODED BENCHMARK MATRIX (Includes Vaseline & Core Staples)
# -----------------------------------------------------------------------------
MONAD_FALLBACKS = {
    "vaseline": {
        "title": "Vaseline / Pure Petroleum Jelly (100% White Petrolatum USP)",
        "roi_rating": "Highest ROI (Gold Standard Occlusive)",
        "roi_explanation": "Reduces Trans-Epidermal Water Loss (TEWL) by over 98%. Cheapest and most effective barrier sealant available.",
        "pricing": {"retail": "$4.00 (100g)", "daily": "$0.05", "time": "30 secs"},
        "permanence": "Temporary (Protective physical shield while present on skin)",
        "actives": "White Petrolatum USP (100%)",
        "pros": ["Blocks 98%+ transepidermal water loss", "100% non-comedogenic when applied to clean skin", "Inert; zero risk of chemical skin allergy"],
        "cons": ["Greasy texture / heavy finish", "Traps bacteria if applied over unwashed dirty skin"],
        "truth": "Does not add water to skin by itself, but locks 98%+ of existing dermal moisture inside. Unbeatable value-to-performance ratio."
    },
    "topical sunscreen": {
        "title": "Broad Spectrum Topical Sunscreen (SPF 30-50+)",
        "roi_rating": "High ROI",
        "roi_explanation": "Prevents up to 80% of visible skin aging and halts UV-induced collagen breakdown.",
        "pricing": {"retail": "$18.00 (50ml)", "daily": "$0.50", "time": "2 mins"},
        "permanence": "Temporary (Resets daily; requires reapplication)",
        "actives": "Zinc Oxide, Titanium Dioxide, Avobenzone, Tinosorb",
        "pros": ["Halts photocarcinogenesis and dark spots", "Preserves existing collagen fibers"],
        "cons": ["Washes off with sweat/water", "Requires strict daily discipline"],
        "truth": "UV protection drops after 2 hours in direct sun. Stopping exposes cells to immediate photo-damage."
    },
    "ingestible collagen peptides": {
        "title": "Hydrolyzed Collagen Peptides",
        "roi_rating": "Moderate-High ROI",
        "roi_explanation": "Supplies systemic proline and glycine amino acids to support dermal collagen density.",
        "pricing": {"retail": "$30.00 (450g)", "daily": "$1.00", "time": "1 min"},
        "permanence": "Semi-Permanent (Builds dermal density; slowly decays if discontinued)",
        "actives": "Hydrolyzed Collagen Peptides (Types I & III)",
        "pros": ["Improves skin elasticity", "Supports joint cartilage"],
        "cons": ["Requires 8-12 weeks of daily adherence", "Systemic absorption varies"],
        "truth": "Natural dermal collagen drops ~1% per year starting at age 25. Supplementation maintains the structural matrix."
    }
}


# -----------------------------------------------------------------------------
# 3. STREAMLIT WEB INTERFACE
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monad Watchdog", page_icon="⚡", layout="centered")

st.title("⚡ MONAD: Biological Product Watchdog")
st.caption("Search global databases or benchmark formulas for objective ingredient breakdowns.")

st.markdown("""
> **Disclaimer:** *Monad provides research-backed biological ingredient analysis and educational metrics. It does not constitute official legal or medical diagnosis.*
""")

# Search Box
user_query = st.text_input("🔍 Search product or brand name:", placeholder="e.g. vaseline, cerave, fructis, byphasse...")

if user_query:
    st.divider()
    clean_query = user_query.strip().lower()

    # Check hardcoded benchmarks first (e.g. Vaseline)
    matched_benchmark = None
    for key in MONAD_FALLBACKS:
        if key in clean_query or clean_query in key:
            matched_benchmark = key
            break

    if matched_benchmark:
        data = MONAD_FALLBACKS[matched_benchmark]
        st.subheader(f"📊 Monad Benchmark Analysis: {data['title']}")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Longevity ROI", data["roi_rating"])
        col2.metric("Daily Cost", data["pricing"]["daily"])
        col3.metric("Daily Effort", data["pricing"]["time"])
        
        st.info(f"**Biological Logic:** {data['roi_explanation']}")
        st.write(f"**Key Actives:** {data['actives']}")
        
        c_pro, c_con = st.columns(2)
        with c_pro:
            st.markdown("### ✅ Biological Pros")
            for p in data["pros"]:
                st.markdown(f"- {p}")
        with c_con:
            st.markdown("### ⚠️ Considerations")
            for c in data["cons"]:
                st.markdown(f"- {c}")
                
        st.error(f"**🔥 BRUTAL BIOLOGICAL TRUTH:**\n\n{data['truth']}")

    else:
        # Live Search in Open Beauty Facts
        with st.spinner("Filtering global database for products with complete ingredient labels..."):
            suggestions = search_open_beauty_facts(user_query)

        if suggestions:
            options = [s["label"] for s in suggestions]
            selected_product_name = st.selectbox(
                f" Found {len(suggestions)} products with verified ingredient lists:",
                options=options
            )

            # Retrieve selected product details
            selected_data = next(s for s in suggestions if s["label"] == selected_product_name)

            st.markdown("---")
            st.success(f"**Selected Product:** {selected_product_name}")
            
            st.markdown("### 🔬 Official INCI Ingredient Breakdown")
            st.info(selected_data["ingredients"])

            # Biological Safety & Ingredient Watchdog Analysis
            st.markdown("### 🛡️ Watchdog Biological Check")
            ing_text = selected_data["ingredients"].lower()
            
            flags = []
            if "fragrance" in ing_text or "parfum" in ing_text:
                flags.append("⚠️ **Fragrance / Parfum detected:** High potential for sensitizing sensitive dermal tissue.")
            if "alcohol denat" in ing_text or "sd alcohol" in ing_text:
                flags.append("⚠️ **Drying Alcohol detected:** Can strip lipid matrix and disrupt skin barrier integrity.")
            if "petrolatum" in ing_text or "mineral oil" in ing_text:
                flags.append("🛡️ **Strong Occlusive present:** Excellent for preventing moisture evaporation (TEWL).")
            if "niacinamide" in ing_text or "ceramide" in ing_text or "glycerin" in ing_text:
                flags.append("✅ **Barrier Support Actives detected:** Contains proven restorative skin components.")
            
            if flags:
                for flag in flags:
                    st.write(flag)
            else:
                st.write("ℹ️ Standard cosmetic formula. No major drying alcohols or synthetic perfumes flagged.")

        else:
            st.warning(f"No products with complete INCI labels were found for '{user_query}' in the open public registry.")
            st.markdown("### 📋 Manual INCI Ingredient Parser")
            pasted_ingredients = st.text_area("Paste the ingredient list from the back of the bottle here to analyze:", placeholder="e.g. Aqua, Glycerin, Petrolatum, Cetearyl Alcohol, Niacinamide...")
            
            if pasted_ingredients:
                st.markdown("---")
                st.markdown("### 🔬 Manual INCI Analysis Result")
                ing_text = pasted_ingredients.lower()
                
                flags = []
                if "fragrance" in ing_text or "parfum" in ing_text:
                    flags.append("⚠️ **Fragrance / Parfum detected:** High potential for skin irritation.")
                if "alcohol denat" in ing_text or "sd alcohol" in ing_text:
                    flags.append("⚠️ **Drying Alcohol detected:** May dehydrate skin with frequent use.")
                if "petrolatum" in ing_text or "mineral oil" in ing_text:
                    flags.append("🛡️ **Strong Occlusive present:** Excellent for locking in moisture.")
                if "niacinamide" in ing_text or "ceramide" in ing_text or "glycerin" in ing_text:
                    flags.append("✅ **Barrier Support Actives detected:** Proven skin-repairing ingredients.")
                
                if flags:
                    for flag in flags:
                        st.write(flag)
                else:
                    st.write("ℹ️ Formula looks clean. No high-risk drying alcohols or perfumes detected.")
