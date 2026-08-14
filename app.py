import streamlit as st
import requests

# -----------------------------------------------------------------------------
# 1. API HELPER FUNCTIONS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def search_open_beauty_facts(query):
    """Searches Open Beauty Facts for products with valid INCI lists."""
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

def fetch_by_barcode(barcode):
    """Direct lookup via Product Barcode."""
    url = f"https://world.openbeautyfacts.org/api/v2/product/{barcode}.json"
    headers = {"User-Agent": "MonadWatchdog - Research/Educational - v1.0"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 1:
                product = data.get("product", {})
                name = product.get("product_name") or "Scanned Product"
                ingredients = product.get("ingredients_text") or "INCI list not logged for this barcode."
                return name, ingredients
    except Exception:
        pass
    return None, None


# -----------------------------------------------------------------------------
# 2. UPGRADE 1: POSITIONAL INCI INGREDIENT PARSER
# -----------------------------------------------------------------------------
def analyze_inci_positions(inci_string):
    """Analyzes ingredients based on their concentration position in the INCI list."""
    ingredients = [i.strip().lower() for i in inci_string.split(",")]
    total = len(ingredients)
    
    flags = []
    has_actives = False
    
    for idx, ing in enumerate(ingredients):
        is_top5 = idx < 5
        
        # Drying Alcohols
        if "alcohol denat" in ing or "sd alcohol" in ing:
            if is_top5:
                flags.append("🚨 **High Risk:** Drying Alcohol is in the Top 5 ingredients! High potential to strip natural skin lipids.")
            else:
                flags.append("⚠️ **Low/Trace Risk:** Drying alcohol present lower on the label (likely a solvent).")
                
        # Fragrance / Parfum
        if "fragrance" in ing or "parfum" in ing:
            if idx > (total - 3):
                flags.append("ℹ️ **Minimal Risk:** Fragrance is at the very bottom of the label (<1%).")
            else:
                flags.append("⚠️ **Sensitizer Flag:** Fragrance appears higher in the formula; potential sensitizer for reactive skin.")
                
        # Beneficial Actives & Barrier Repair
        if any(active in ing for active in ["petrolatum", "ceramide", "niacinamide", "glycerin", "hyaluronic", "zinc"]):
            has_actives = True

    if has_actives:
        flags.append("✅ **Barrier Actives Detected:** Formula contains proven protective/restorative agents (e.g. Ceramides, Glycerin, Petrolatum, Niacinamide).")
        
    if not flags:
        flags.append("ℹ️ Standard cosmetic baseline. No major drying solvents or perfumes flagged.")
        
    return flags


# -----------------------------------------------------------------------------
# 3. MONAD BENCHMARK MATRIX (With Full Longevity Time Spectrum)
# -----------------------------------------------------------------------------
MONAD_BENCHMARKS = {
    "vaseline": {
        "title": "Vaseline / Pure Petroleum Jelly (100% White Petrolatum USP)",
        "roi_rating": "Highest ROI",
        "roi_explanation": "Reduces Trans-Epidermal Water Loss (TEWL) by over 98%. Most effective barrier sealant available.",
        "pricing": {"retail": "$4.00 (100g)", "daily": "$0.05", "time": "30 secs"},
        "permanence": "Temporary (Protective physical shield while present)",
        "actives": "White Petrolatum USP (100%)",
        "pros": ["Blocks 98%+ transepidermal water loss", "100% non-comedogenic on clean skin", "Inert; zero allergic risk"],
        "cons": ["Greasy texture / heavy finish", "Traps debris if applied over unwashed skin"],
        "truth": "Locks 98%+ of existing dermal moisture inside. Unbeatable value-to-performance ratio.",
        "spectrum": {
            "Day 1": "Instantly forms a physical hydrophobic barrier, stopping moisture evaporation.",
            "Week 1": "Accelerates stratum corneum lipid barrier recovery after harsh cleansing.",
            "Month 1": "Sustained epidermal hydration restores skin flexibility and softens micro-cracks.",
            "Year 1": "Prevents chronic dehydration-induced fine lines across moisture-starved skin.",
            "Year 10": "Maintains baseline epidermal thickness by preventing chronic barrier breakdown.",
            "Year 20": "Dermal matrix retains higher water density compared to untreated dry skin."
        }
    },
    "topical sunscreen": {
        "title": "Broad Spectrum Topical Sunscreen (SPF 30-50+)",
        "roi_rating": "High ROI",
        "roi_explanation": "Prevents up to 80% of visible photoaging and stops UV-induced collagen degradation.",
        "pricing": {"retail": "$18.00 (50ml)", "daily": "$0.50", "time": "2 mins"},
        "permanence": "Temporary (Requires daily reapplication)",
        "actives": "Zinc Oxide, Titanium Dioxide, Avobenzone, Tinosorb",
        "pros": ["Halts photocarcinogenesis and dark spots", "Preserves structural collagen"],
        "cons": ["Washes off with sweat", "Requires strict daily discipline"],
        "truth": "UV protection drops to zero after 2 hours in direct sun. Stopping exposes cells to immediate photo-damage.",
        "spectrum": {
            "Day 1": "Blocks UVA/UVB rays from causing direct cellular DNA strand damage.",
            "Week 1": "Reduces sub-clinical UV micro-inflammation and redness.",
            "Month 1": "Inhibits active melanocytes, halting hyperpigmentation from darkening.",
            "Year 1": "Preserves existing structural collagen and elastin fibers in the dermis.",
            "Year 10": "40% lower risk of skin cancers; drastically fewer deep wrinkling structures.",
            "Year 20": "Dermal collagen matrix remains 5 to 10 years younger than chronological age."
        }
    }
}

DEFAULT_SPECTRUM = {
    "Day 1": "Topical application sits on the stratum corneum; active ingredients begin absorption.",
    "Week 1": "Initial stabilization of surface moisture levels and superficial lipid balance.",
    "Month 1": "One full cellular skin cell turnover cycle (~28 days). Surface texture improvements visible.",
    "Year 1": "Sustained ingredient performance maintains skin barrier stability against environmental stressors.",
    "Year 10": "Long-term barrier preservation cumulative effect reduces structural moisture loss.",
    "Year 20": "Cumulative maintenance preserves cellular health compared to unmaintained skin."
}


# -----------------------------------------------------------------------------
# 4. STREAMLIT INTERFACE
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monad Watchdog", page_icon="⚡", layout="centered")

st.title("⚡ MONAD: Biological Product Watchdog")
st.caption("Objective ingredient analysis, positional INCI inspection, and longevity spectrum forecasting.")

st.markdown("> **Disclaimer:** *Monad provides research-backed biological ingredient analysis for educational purposes.*")

# Navigation Tabs for Upgrades
tab_search, tab_camera = st.tabs(["🔍 Product Search", "📷 Scan Barcode"])

selected_ingredients = None
product_display_name = None

# --- TAB 1: TEXT SEARCH ---
with tab_search:
    user_query = st.text_input("Search product, brand, or ingredient:", placeholder="e.g. vaseline, cerave, fructis, byphasse...")
    
    if user_query:
        clean_query = user_query.strip().lower()
        
        # Check Benchmarks
        matched_bm = next((k for k in MONAD_BENCHMARKS if k in clean_query or clean_query in k), None)
        
        if matched_bm:
            bm_data = MONAD_BENCHMARKS[matched_bm]
            st.divider()
            st.subheader(f"📊 Monad Benchmark: {bm_data['title']}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Longevity ROI", bm_data["roi_rating"])
            c2.metric("Daily Cost", bm_data["pricing"]["daily"])
            c3.metric("Daily Effort", bm_data["pricing"]["time"])
            
            st.info(f"**Biological Logic:** {bm_data['roi_explanation']}")
            st.error(f"**🔥 BRUTAL BIOLOGICAL TRUTH:**\n\n{bm_data['truth']}")
            
            # TIME SPECTRUM FOR BENCHMARKS
            st.markdown("### ⏳ The Longevity Time Spectrum")
            spec_tabs = st.tabs(list(bm_data["spectrum"].keys()))
            for t_tab, (tf, text) in zip(spec_tabs, bm_data["spectrum"].items()):
                with t_tab:
                    st.write(text)
                    
        else:
            # Global Search
            with st.spinner("Analyzing global database..."):
                suggestions = search_open_beauty_facts(user_query)
                
            if suggestions:
                options = [s["label"] for s in suggestions]
                sel_name = st.selectbox(f"Found {len(suggestions)} verified matches:", options=options)
                selected_data = next(s for s in suggestions if s["label"] == sel_name)
                
                product_display_name = selected_data["label"]
                selected_ingredients = selected_data["ingredients"]
            else:
                st.warning("No matched products found. Use the manual INCI parser below:")
                pasted = st.text_area("Paste INCI string from back of bottle:")
                if pasted:
                    product_display_name = "Custom INCI Formula"
                    selected_ingredients = pasted

# --- TAB 2: CAMERA BARCODE SCANNER ---
with tab_camera:
    st.markdown("### 📷 Point Camera at Product Barcode")
    img_input = st.camera_input("Take a clear picture of the product barcode")
    barcode_manual = st.text_input("Or enter 13-digit Barcode number manually:", placeholder="e.g. 3337875597196")
    
    target_barcode = barcode_manual.strip() if barcode_manual else None
    
    if target_barcode:
        with st.spinner("Searching barcode database..."):
            b_name, b_inci = fetch_by_barcode(target_barcode)
            if b_inci:
                product_display_name = b_name
                selected_ingredients = b_inci
            else:
                st.error("Barcode not found in Open Beauty Facts registry.")


# -----------------------------------------------------------------------------
# 5. RENDER ANALYSIS & TIME SPECTRUM FOR SEARCHED / SCANNED PRODUCTS
# -----------------------------------------------------------------------------
if selected_ingredients and product_display_name:
    st.divider()
    st.success(f"**Product Loaded:** {product_display_name}")
    
    st.markdown("### 🔬 Official INCI Ingredient Breakdown")
    st.info(selected_ingredients)
    
    # POSITIONAL INCI ANALYSIS (UPGRADE 1)
    st.markdown("### 🛡️ Positional Biological Risk Inspection")
    pos_flags = analyze_inci_positions(selected_ingredients)
    for flag in pos_flags:
        st.write(flag)
        
    # RESTORED LONGEVITY TIME SPECTRUM
    st.markdown("---")
    st.markdown("### ⏳ Projected Biological Time Spectrum")
    st.caption("Cumulative skin cell impact from Day 1 through 20 Years of use:")
    
    spec_tabs = st.tabs(list(DEFAULT_SPECTRUM.keys()))
    for t_tab, (tf, text) in zip(spec_tabs, DEFAULT_SPECTRUM.items()):
        with t_tab:
            st.write(f"**{tf} Impact:** {text}")
