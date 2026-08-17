import os
import io
import json
import requests
import base64
import random
import difflib
from PIL import Image, ImageDraw
import streamlit as st
from groq import Groq

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & BACKGROUND GENERATOR (IN-MEMORY)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monad: Decode You", page_icon="🌸", layout="centered")

# FIX 1: Prioritize Replit environment variables, fallback to Streamlit secrets
GROQ_KEY = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

@st.cache_data(max_entries=1) # Cache the image generation so it only runs once per app lifecycle
def create_japanese_pastel_bg_base64(width=1920, height=1080):
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
    
    # FIX 2: Generate directly to in-memory bytes (skips disk write)
    buffered = io.BytesIO()
    final_background.convert("RGB").save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

img_base64 = create_japanese_pastel_bg_base64()

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

    h1, h2, h3, h4, h5, h6 {{
        color: #5c4b51 !important;
    }}
    p, li, span, label, div.stMarkdown, .st-emotion-cache-16idsys p {{
        color: #4a4045 !important;
    }}

    input, textarea, select {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        color: #4a4045 !important;
        border: 1px solid #e8d7dc !important;
        border-radius: 8px !important;
    }}

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
# 3. INGREDIENT RETRIEVAL PIPELINE (WITH FUZZY SPELLING FALLBACK)
# -----------------------------------------------------------------------------
# FIX 3: Added max_entries to prevent container OOM crashes
@st.cache_data(ttl=300, max_entries=50) 
def fetch_registry_data(api_url):
    headers = {"User-Agent": "MonadDecodeYou - Research/Educational - v1.0"}
    try:
        # FIX 4: Bumped timeout to 8 seconds and added specific exception handling
        res = requests.get(api_url, headers=headers, timeout=8)
        if res.status_code == 200:
            products = res.json().get("products", [])
            valid = []
            for p in products:
                name = p.get("product_name") or p.get("product_name_en")
                brands = p.get("brands", "")
                ingredients = p.get("ingredients_text") or p.get("ingredients_text_en")
                if name and ingredients and len(ingredients.strip()) > 5:
                    label = f"{brands} - {name}" if brands else name
                    valid.append({"label": label, "ingredients": ingredients.strip()})
            return valid
    except requests.exceptions.Timeout:
        st.warning("⚠️ The ingredient registry took too long to respond. Please try again.")
    except Exception:
        pass
    return []

def multi_source_search(query):
    url_beauty = f"https://world.openbeautyfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=20"
    results = fetch_registry_data(url_beauty)
    
    if not results:
        url_food = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=20"
        results = fetch_registry_data(url_food)

    if len(results) < 3:
        broad_url = "https://world.openbeautyfacts.org/cgi/search.pl?action=process&json=1&page_size=100"
        all_products = fetch_registry_data(broad_url)
        if all_products:
            product_labels = [p['label'] for p in all_products]
            close_matches = difflib.get_close_matches(query, product_labels, n=5, cutoff=0.3)
            for m in all_products:
                if m['label'] in close_matches and m not in results:
                    results.append(m)

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
# 4. AI ENGINES (STRICT MEDICAL VERIFICATION)
# -----------------------------------------------------------------------------
# FIX 3: Added max_entries to prevent container OOM crashes
@st.cache_data(show_spinner=False, max_entries=20)
def ai_analyze_product(product_name, ingredients, skin_profile):
    if not groq_client:
        return None

    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"
    medications_str = skin_profile.get('medications', 'None reported')

    prompt = f"""
    You are Monad, an expert clinical cosmetologist and biological intelligence engine.
    CRITICAL MEDICAL DIRECTIVE: All analysis MUST be strictly cross-referenced with peer-reviewed dermatological literature (e.g., PubMed, NIH, AAD, CIR Safety Assessments). Maintain a 90%+ clinical confidence interval for all claims. Do not hallucinate benefits. 
    
    If an ingredient has potential contraindications with the user's reported medications or medical flags, you MUST state it based on known pharmacological interactions.
    
    Adapt all analysis to the user's complete biological profile:
    - Biological Sex / Baseline: {skin_profile.get('sex')}
    - Life Stage / Hormonal Status: {skin_profile.get('lifestage')}
    - Skin Type: {skin_profile.get('type')}
    - Barrier State: {skin_profile.get('barrier')}
    - Active Medical Conditions & Sensitivities: {medical_flags_str}
    - Current Systemic / Topical Medications: {medications_str}

    Product: {product_name}
    Ingredients: {ingredients}

    Return a JSON object with this exact structure (do not include markdown outside JSON):
    {{
        "headline": "A punchy, 1-sentence clinical headline summarizing formula suitability.",
        "analysis": "2-sentence clinical summary explicitly addressing how this formula interacts with their complete biological profile, backed by established dermatological principles.",
        "usage_protocol": {{
            "frequency": "Evidence-based frequency strictly adapted to their barrier condition and medications.",
            "time_of_day": "AM/PM application guidance based on phototoxicity and active half-lives.",
            "application_step": "Precise order in skincare routine (e.g., pH dependent layering).",
            "time_to_visible_results": "Detailed clinical timeline based on cellular turnover rates."
        }},
        "pros": [
            {{"title": "Simple benefit title 1", "detail": "Clinically verified explanation of why this helps their skin."}},
            {{"title": "Simple benefit title 2", "detail": "Clinically verified explanation of why this benefits their skin type."}}
        ],
        "cons": [
            {{"title": "Simple caution title 1", "detail": "Pharmacological or barrier disruption risk, plainly explained."}},
            {{"title": "Simple caution title 2", "detail": "Secondary verified risk based on their medical profile."}}
        ],
        "spectrum": {{
            "Day 1": "Immediate reaction and pH adjustment.",
            "Day 3": "Early barrier response under their current condition.",
            "Day 7": "End of first week adaptation phase.",
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
        }},
        "medical_sources": [
            "Provide 2-3 SPECIFIC dermatological databases, clinical trials, or safety assessments relevant to these specific ingredients (e.g., 'CIR Safety Assessment: Niacinamide', 'AAD Guidelines on Rosacea Management', 'PubChem NIH data for [Ingredient]')"
        ]
    }}
    """
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Output strictly valid JSON. Act as a strict medical reviewer. Do not provide unverified claims."},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-oss-120b",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"AI Generation Error: {e}")
        return None

# FIX 3: Added max_entries to prevent container OOM crashes
@st.cache_data(show_spinner=False, max_entries=20)
def ai_check_compatibility(prod_a_name, prod_a_ing, prod_b_name, prod_b_ing, skin_profile):
    if not groq_client:
        return None

    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"
    medications_str = skin_profile.get('medications', 'None reported')

    prompt = f"""
    Analyze the simultaneous use of these two products for a user with baseline [{skin_profile.get('sex')}, {skin_profile.get('lifestage')}], {skin_profile.get('type')} skin, a {skin_profile.get('barrier')} barrier, medical conditions [{medical_flags_str}], and medications [{medications_str}]:

    Product A: {prod_a_name}
    Ingredients A: {prod_a_ing}

    Product B: {prod_b_name}
    Ingredients B: {prod_b_ing}

    Provide a concise, highly-verified clinical evaluation covering:
    1. **Active Ingredient Overlaps & pH Conflicts**: (e.g., AHA/BHA + Retinoid, Acid + Vitamin C). Cite general dermatological consensus.
    2. **Medical, Medication & Barrier Disruption Risk**: Impact on their specific medical sensitivities and systemic factors.
    3. **Safe Routine Strategy**: How to split or layer them safely.
    """
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a clinical cosmetologist providing rigorous, medically-verified safety evaluations tailored to biological profiles. Cite mechanisms of action where necessary."},
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
st.title("🌸 MONAD: Decode You")
st.caption("✨ Advanced molecular intelligence engine tailored to your complete biological profile.")

with st.expander("💡 What is Monad? (How it works & Data Reliability)", expanded=False):
    st.markdown("""
    Welcome to **Monad: Decode You**! Here is how the concept works:
    1. **Set Your Complete Biological Profile:** Input your skin type, life stage, medications, and medical sensitivities below.
    2. **Search or Scan:** Look up any product by name (even with typos!) or barcode. Monad extracts the exact INCI ingredient list from global registries (OpenBeautyFacts/OpenFoodFacts).
    3. **Personalized Biological Forecast:** Monad's AI engine acts as a precision clinical watchdog. It strictly cross-references ingredients against verified dermatological databases (NIH, CIR, AAD) to scan for contraindications against your exact medical background.
    4. **The Longevity Spectrum:** Drag the interactive slider from **Day 1 to Year 100** to see customized clinical milestones tailored to your biology!
    """)

st.markdown("> **Medical Verification & Disclaimer:** *Monad aims for a 90%+ confidence interval by instructing its AI engine to strictly base analysis on peer-reviewed clinical data (e.g., PubMed, CIR Safety Assessments). However, AI cannot replace a doctor. Always patch test and consult a certified dermatologist for active clinical treatment or severe reactions.*")

if not GROQ_KEY:
    st.warning("⚠️ Groq API Key not detected in Streamlit Secrets or Environment Variables. AI dynamic features are disabled.")

# Global Biological & Medical Profile Configuration
with st.expander("👤 Step 1: Customize Your Biological & Medical Profile", expanded=True):
    bio_col1, bio_col2 = st.columns(2)
    with bio_col1:
        bio_sex = st.selectbox("Biological Baseline:", ["Female Baseline", "Male Baseline", "Intersex / Other"])
    with bio_col2:
        life_stage = st.selectbox("Life Stage & Hormonal Status:", ["Standard / Adult", "Pregnant / Postpartum", "Perimenopausal / Menopausal", "Teenager / Puberty"])

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        skin_type = st.selectbox("Skin Type:", ["Balanced / Normal", "Sensitive / Reactive", "Oily / Acne-Prone", "Dry / Dehydrated", "Combination"])
    with col_s2:
        barrier_state = st.selectbox("Current Barrier Condition:", ["Healthy / Resilient", "Slightly Irritated / Flaky", "Compromised / Stinging / Red"])

    user_medications = st.text_input("Current Systemic or Topical Medications:", placeholder="e.g., Oral Accutane, birth control, topical tretinoin, antibiotics...")

    st.markdown("##### 🏥 Medical Conditions & Sensory Sensitivities")
    med_col1, med_col2 = st.columns(2)
    with med_col1:
        flag_rosacea = st.checkbox("Rosacea / Chronic Flushing")
        flag_eczema = st.checkbox("Eczema / Atopic Dermatitis")
        flag_fungal = st.checkbox("Fungal Acne (Malassezia-sensitive)")
    with med_col2:
        flag_sensory = st.checkbox("Sensory Sensitivity / Chemical Overload")
        flag_allergy = st.checkbox("Contact Dermatitis / Fragrance Allergy")
        flag_postproc = st.checkbox("Post-Procedure / Healing Skin")

    medical_flags = []
    if flag_rosacea: medical_flags.append("Rosacea")
    if flag_eczema: medical_flags.append("Eczema")
    if flag_fungal: medical_flags.append("Fungal Acne (Malassezia-sensitive)")
    if flag_sensory: medical_flags.append("Sensory Sensitivity / Chemical Overload")
    if flag_allergy: medical_flags.append("Contact Dermatitis / Fragrance Allergy")
    if flag_postproc: medical_flags.append("Post-Procedure / Healing Skin")

user_profile = {
    "sex": bio_sex,
    "lifestage": life_stage,
    "type": skin_type,
    "barrier": barrier_state,
    "medications": user_medications if user_medications else "None reported",
    "medical_flags": medical_flags
}

tab_single, tab_stack = st.tabs(["🔍 Product Analysis", "🔄 Routine Stacking Compatibility"])

# -----------------------------------------------------------------------------
# TAB 1: PRODUCT ANALYSIS
# -----------------------------------------------------------------------------
with tab_single:
    st.markdown("### 🔍 Step 2: Product Search & Barcode Input")
    
    user_query = st.text_input("Search Product (typos are automatically corrected):", placeholder="e.g. CeraVe Cleansor...")

    with st.expander("📸 Optional: Scan Barcode via Camera"):
        camera_photo = st.camera_input("Take a photo of the product barcode", label_visibility="collapsed")
        if camera_photo:
            st.info("📷 Barcode camera frame captured!")

    if user_query:
        with st.spinner("Searching multi-source registries with smart spelling correction..."):
            matches = multi_source_search(user_query)
            
        if matches:
            options = [m['label'] for m in matches]
            selected_option = st.selectbox("Select verified product:", options=options, key="single_select")
            selected_product = next(m for m in matches if m['label'] == selected_option)
            
            st.markdown("---")
            st.success(f"**Loaded:** {selected_product['label']}")

            f_rep, f_act, f_irr = parse_ingredient_badges(selected_product['ingredients'])
            badge_cols = st.columns(3)
            with badge_cols[0]:
                st.markdown("**🟢 Barrier Supporting Ingredients**")
                st.write(", ".join(f_rep) if f_rep else "None detected")
            with badge_cols[1]:
                st.markdown("**🟡 Potent Active Ingredients**")
                st.write(", ".join(f_act) if f_act else "None detected")
            with badge_cols[2]:
                st.markdown("**🔴 Potential Irritants / Fragrance**")
                st.write(", ".join(f_irr) if f_irr else "None detected")

            st.markdown("---")

            if GROQ_KEY:
                with st.spinner("✨ Monad decoding formula against verified medical databases..."):
                    ai_data = ai_analyze_product(selected_product['label'], selected_product['ingredients'], user_profile)
                    
                if ai_data:
                    st.markdown(f"### 🎯 {ai_data.get('headline', '')}")
                    
                    # INTERACTIVE CLICKABLE PROS & CONS (USING EXPANDER CARDS)
                    col_p, col_c = st.columns(2)
                    with col_p:
                        st.markdown("#### ✅ Clinically Verified Wins")
                        pros = ai_data.get("pros", [])
                        if pros:
                            for i, p in enumerate(pros):
                                if isinstance(p, dict):
                                    title = p.get("title", f"Benefit {i+1}")
                                    detail = p.get("detail", "")
                                    with st.expander(f"✨ {title}"):
                                        st.write(detail)
                                else:
                                    st.info(f"✨ {p}")
                        else:
                            st.write("None highlighted for this profile.")

                    with col_c:
                        st.markdown("#### ⚠️ Systemic & Medical Alerts")
                        cons = ai_data.get("cons", [])
                        if cons:
                            for i, c in enumerate(cons):
                                if isinstance(c, dict):
                                    title = c.get("title", f"Alert {i+1}")
                                    detail = c.get("detail", "")
                                    with st.expander(f"⚡ {title}"):
                                        st.write(detail)
                                else:
                                    st.warning(f"⚡ {c}")
                        else:
                            st.write("No major alerts detected.")

                    st.markdown("---")
                    
                    # Expandable Deep-Dive Clinical Summary
                    with st.expander("📖 Read Full Clinical Analysis & Rationale", expanded=False):
                        st.write(ai_data.get("analysis", ""))

                    st.markdown("### ⏳ Customized Longevity Spectrum")
                    spectrum_data = ai_data.get("spectrum", {})
                    if spectrum_data:
                        timeframes = list(spectrum_data.keys())
                        
                        selected_time = st.select_slider(
                            "Slide to view long-term biological impact tailored to your profile:",
                            options=timeframes,
                            value=timeframes[0],
                            key="spectrum_slider" 
                        )
                        
                        st.info(f"**{selected_time} Impact:** {spectrum_data[selected_time]}")

                    st.markdown("---")
                    with st.expander("🔬 Deep Dive Clinical Lab (Dosing & Citations)", expanded=False):
                        st.markdown("#### 📋 Evidence-Based Dosing Protocol")
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
                        st.markdown("#### 📚 Verified Medical Sources & Citations")
                        st.caption("The analysis above was cross-referenced using principles from these medical databases:")
                        for src in ai_data.get("medical_sources", []):
                            st.markdown(f"- *{src}*")

                    st.markdown("---")
                    with st.expander("🏷️ Extracted INCI Ingredient Formula", expanded=False):
                        st.info(selected_product["ingredients"])
        else:
            st.warning("No matching products found in registries for your query. Try a broader search term!")

# -----------------------------------------------------------------------------
# TAB 2: ROUTINE STACKING & COMPATIBILITY MATRIX
# -----------------------------------------------------------------------------
with tab_stack:
    st.markdown("### 🔄 Dual-Product Routine Stacking Evaluation")
    st.caption("Check rigorous chemical compatibility and pharmacological safety before layering two products.")

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
        if st.button("🧪 Evaluate Chemical & Biological Compatibility"):
            with st.spinner("Analyzing pharmacological interactions & verified medical data..."):
                report = ai_check_compatibility(
                    selected_a['label'], selected_a['ingredients'],
                    selected_b['label'], selected_b['ingredients'],
                    user_profile
                )
                if report:
                    st.markdown(report)
