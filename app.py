import os
import json
import requests
import base64
import math
import random
from PIL import Image, ImageDraw
import streamlit as st
from groq import Groq

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & BACKGROUND GENERATOR
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monad Watchdog", page_icon="🌸", layout="centered")

GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

def create_japanese_pastel_bg(width=1920, height=1080):
    """Generates the custom background if it doesn't exist yet."""
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    color_cream = (255, 253, 208)
    color_pink = (255, 209, 220)
    color_green = (203, 243, 210)

    for y in range(height):
        percentage = y / float(height)
        if percentage < 0.5:
            local_p = percentage * 2.0
            r = int(color_cream[0] + (color_pink[0] - color_cream[0]) * local_p)
            g = int(color_cream[1] + (color_pink[1] - color_cream[1]) * local_p)
            b = int(color_cream[2] + (color_pink[2] - color_cream[2]) * local_p)
        else:
            local_p = (percentage - 0.5) * 2.0
            r = int(color_pink[0] + (color_green[0] - color_pink[0]) * local_p)
            g = int(color_pink[1] + (color_green[1] - color_pink[1]) * local_p)
            b = int(color_pink[2] + (color_green[2] - color_pink[2]) * local_p)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    sun_radius = 250
    sun_center_x = width // 2
    sun_center_y = height // 2 - 50

    overlay_draw.ellipse(
        [
            (sun_center_x - sun_radius, sun_center_y - sun_radius),
            (sun_center_x + sun_radius, sun_center_y + sun_radius),
        ],
        fill=(255, 150, 160, 45),
    )
    image = Image.alpha_composite(image.convert("RGBA"), overlay)

    petal_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    petal_draw = ImageDraw.Draw(petal_layer)
    random.seed(42)

    for _ in range(45):
        px = random.randint(50, width - 50)
        py = random.randint(50, height - 50)
        size = random.randint(12, 28)
        petal_color = (
            random.randint(245, 255),
            random.randint(175, 195),
            random.randint(190, 210),
            random.randint(180, 230),
        )
        petal_draw.ellipse([(px, py), (px + size, py + int(size * 0.6))], fill=petal_color)
        petal_draw.ellipse(
            [(px + int(size * 0.2), py - int(size * 0.2)), (px + size, py + size)],
            fill=petal_color,
        )

    final_background = Image.alpha_composite(image, petal_layer)
    final_background.convert("RGB").save("japanese_pastel_background.png")

# Check and generate background
bg_filename = "japanese_pastel_background.png"
if not os.path.exists(bg_filename):
    create_japanese_pastel_bg()

@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

img_base64 = get_base64_of_bin_file(bg_filename)

# -----------------------------------------------------------------------------
# 2. CUSTOM CSS STYLING
# -----------------------------------------------------------------------------
if img_base64:
    bg_style = f"""
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/jpeg;base64,{img_base64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        [data-testid="stAppViewContainer"] > .main {{
            background-color: rgba(255, 255, 255, 0.75) !important; 
        }}
    """
else:
    bg_style = """
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #fff5f7 0%, #fefcf0 50%, #f0f7f4 100%);
        }
    """

st.markdown(
    f"""
    <style>
    {bg_style}
    
    html, body {{
        overscroll-behavior-y: none !important;
    }}

    /* FORCE TEXT COLORS FOR LIGHT BACKGROUND */
    h1, h2, h3, h4, h5, h6 {{
        color: #5c4b51 !important;
    }}
    p, li, span, label, div.stMarkdown, .st-emotion-cache-16idsys p {{
        color: #4a4045 !important;
    }}

    /* Input Fields */
    input, textarea, select {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        color: #4a4045 !important;
        border: 1px solid #e8d7dc !important;
        border-radius: 8px !important;
    }}

    /* Buttons */
    .stButton>button {{
        background-color: #f48fb1 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600;
        transition: background-color 0.2s ease;
    }}
    .stButton>button:hover {{
        background-color: #ec407a !important;
        color: white !important;
    }}

    /* Expanders & Containers */
    div[data-testid="stExpander"], div.stContainer {{
        background-color: rgba(255, 255, 255, 0.85) !important;
        border: 1px solid #f3e5f5 !important;
        border-radius: 10px !important;
    }}
    
    div[data-testid="stExpander"] p {{
        color: #4a4045 !important;
    }}
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
# 4. AI ENGINES (WITH CACHING ADDED)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
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
       "spectrum": {
            "Day 1": "Immediate reaction, pH adjustment, and sensory feel.",
            "Day 3": "Early barrier response and hydration shift.",
            "Day 7": "End of first week adaptation.",
            "Day 14": "Two-week cumulative active integration.",
            "Month 1": "First full cellular turnover cycle (28 days) results.",
            "Month 2": "Deeper dermal impact and pigment/texture shifts.",
            "Month 3": "Stabilized results and long-term tolerance check.",
            "Month 6": "Half-year structural epidermal changes.",
            "Year 1": "Full year maintenance and barrier resilience.",
            "Year 2": "Multi-year cumulative compounding effects.",
            "Year 5": "Long-term cellular aging trajectory impact.",
            "Year 10": "Decade-level structural preservation.",
            "Year 20": "Two-decade biological legacy on skin elasticity.",
            "Year 50": "Half-century cumulative exposure outcomes.",
            "Year 100": "Theoretical lifelong maximum preservation and cellular legacy."
        },
        
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

@st.cache_data(show_spinner=False)
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
# 5. MAIN INTERFACE LAYOUT
# -----------------------------------------------------------------------------
st.title("🌸 MONAD: Biological Watchdog")
st.caption("✨ Multi-source database engine with personalized clinical forecasting.")

st.markdown("> **Medical Disclaimer:** *Monad provides research-backed biological ingredient analysis for educational purposes. Consult a dermatologist for active clinical treatment.*")

if not GROQ_KEY:
    st.warning("⚠️ Groq API Key not detected in Streamlit Secrets. AI dynamic features are disabled.")

# Global Skin Profile Configuration
with st.expander("👤 Customize Your Skin Profile (Personalized Analysis)", expanded=True):
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        skin_type = st.selectbox("Skin Type:", ["Balanced / Normal", "Sensitive / Reactive", "Oily / Acne-Prone", "Dry / Dehydrated", "Combination"])
    with col_s2:
        barrier_state = st.selectbox("Current Barrier Condition:", ["Healthy / Resilient", "Slightly Irritated / Flaky", "Compromised / Stinging / Red"])

user_profile = {"type": skin_type, "barrier": barrier_state}

tab_single, tab_stack = st.tabs(["🔍 Product Analysis", "🔄 Routine Stacking Compatibility"])

# -----------------------------------------------------------------------------
# TAB 1: PRODUCT ANALYSIS & BARCODE SCANNER
# -----------------------------------------------------------------------------
with tab_single:
    st.markdown("### 🔍 Product Search & Barcode Input")
    
    user_query = st.text_input("Search Product:", placeholder="Type brand name, product name, or barcode digits...")

    with st.expander("📸 Optional: Scan Barcode via Camera"):
        camera_photo = st.camera_input("Take a photo of the product barcode", label_visibility="collapsed")
        if camera_photo:
            st.info("📷 Barcode camera frame captured!")

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
                        timeframes = list(spectrum_data.keys())
                        
                        # Added state key to prevent resetting on interaction
                        selected_time = st.select_slider(
                            "Slide to view long-term biological impact:",
                            options=timeframes,
                            value=timeframes[0],
                            key="spectrum_slider" 
                        )
                        
                        st.info(f"**{selected_time} Impact:** {spectrum_data[selected_time]}")

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
        else:
            st.warning("No matching products found in registries for your query.")

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
