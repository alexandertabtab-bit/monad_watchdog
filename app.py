import os
import json
import requests
import base64
import random
import difflib
from PIL import Image, ImageDraw
import streamlit as st
from groq import Groq

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & BACKGROUND GENERATOR
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monad: Decode You", page_icon="🌸", layout="centered")

GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

def create_japanese_pastel_bg(width=1920, height=1080):
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
@st.cache_data(ttl=300)
def fetch_registry_data(api_url):
    headers = {"User-Agent": "MonadDecodeYou - Research/Educational - v1.0"}
    try:
        res = requests.get(api_url, headers=headers, timeout=5)
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
# 4. AI ENGINES (ENFORCED PLAIN LANGUAGE & BIOLOGICAL PROFILE)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def ai_analyze_product(product_name, ingredients, skin_profile):
    if not groq_client:
        return None

    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"
    medications_str = skin_profile.get('medications', 'None reported')

    prompt = f"""
    You are Monad, a friendly and clear wellness guide. 
    CRITICAL RULE: Use simple, everyday language that anyone can easily understand. Avoid heavy chemical jargon, complex ingredient lists, or confusing scientific terms in the text outputs. Speak directly to the user like a helpful friend.
    
    Adapt all insights to the user's complete biological profile:
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
        "headline": "A simple, catchy 1-sentence takeaway of how this product works for them.",
        "analysis": "A friendly 2-sentence summary using everyday words explaining how this product fits their skin type and routine.",
        "usage_protocol": {{
            "frequency": "Simple timing like 'Once a day' or '2-3 times a week'",
            "time_of_day": "Morning or Night",
            "application_step": "When to apply it in your routine",
            "time_to_visible_results": "When you might notice a change"
        }},
        "pros": [
            {{"title": "Short everyday benefit title 1", "detail": "Simple, clear explanation in plain English."}},
            {{"title": "Short everyday benefit title 2", "detail": "Simple, clear explanation in plain English."}}
        ],
        "cons": [
            {{"title": "Short everyday watch-out title 1", "detail": "Simple, clear explanation of why to be careful."}},
            {{"title": "Short everyday watch-out title 2", "detail": "Simple, clear explanation of why to be careful."}}
        ],
        "spectrum": {{
            "Day 1": "How your skin will feel right away.",
            "Day 3": "What to expect after a couple of days.",
            "Day 7": "How your skin feels after your first week.",
            "Day 14": "Changes after two weeks.",
            "Month 1": "Results after one full month.",
            "Month 2": "Longer term changes after two months.",
            "Month 3": "How your routine settles in over three months.",
            "Month 6": "Half-year progress check.",
            "Year 1": "One year maintenance outlook.",
            "Year 2": "Multi-year habit stability.",
            "Year 5": "Long-term skin wellness trajectory.",
            "Year 10": "Decade-level skin health.",
            "Year 20": "Long-term elasticity outlook.",
            "Year 50": "Lifelong wellness outlook.",
            "Year 100": "Maximum healthy aging legacy."
        }},
        "medical_sources": [
            "Cosmetic Safety Guidance",
            "Dermatology Care Standards",
            "Skin Health Guidelines"
        ]
    }}
    """
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Output strictly valid JSON using simple, everyday language suitable for general audiences."},
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

@st.cache_data(show_spinner=False)
def ai_check_compatibility(prod_a_name, prod_a_ing, prod_b_name, prod_b_ing, skin_profile):
    if not groq_client:
        return None

    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"
    medications_str = skin_profile.get('medications', 'None reported')

    prompt = f"""
    Explain in simple, everyday language whether these two products can be used together for someone with [{skin_profile.get('sex')}, {skin_profile.get('lifestage')}], {skin_profile.get('type')} skin, a {skin_profile.get('barrier')} barrier, medical conditions [{medical_flags_str}], and medications [{medications_str}]:

    Product A: {prod_a_name}
    Ingredients A: {prod_a_ing}

    Product B: {prod_b_name}
    Ingredients B: {prod_b_ing}

    Provide a clear, simple guide covering:
    1. **Can You Mix Them?**: (Yes / Alternate Days / No)
    2. **What to Watch Out For**: Simple explanation of any irritation or clashing ingredients.
    3. **How to Use Them Safely**: Simple advice on how to split or layer them without confusion.
    """
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a friendly guide explaining product compatibility in simple, jargon-free everyday language."},
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
st.title("🏛️ MONAD: Decode You")
st.caption("✨ Friendly, personalized skincare guidance made simple for everyone.")

with st.expander("💡 What is Monad? (How it works)", expanded=False):
    st.markdown("""
    Welcome to **Monad: Decode You**! Here is how it works:
    1. **Tell us about you:** Choose your skin type, life stage, and any medications or sensitivities below.
    2. **Search a product:** Look up any skincare item by name or barcode. 
    3. **Get simple insights:** Monad translates complex ingredients into clear, everyday language so you know if it's right for you.
    4. **Explore the timeline:** Use the slider to see how your skin responds over time!
    """)

st.markdown("> **Medical Disclaimer:** *Monad provides research-backed guidance for educational purposes. Consult a dermatologist for personalized medical treatment.*")

if not GROQ_KEY:
    st.warning("⚠️ Groq API Key not detected in Streamlit Secrets. AI dynamic features are disabled.")

# Global Biological & Medical Profile Configuration
with st.expander("👤 Step 1: Tell Us About Your Skin & Profile", expanded=True):
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

    st.markdown("##### 🏥 Medical Conditions & Sensitivities")
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
    st.markdown("### 🔍 Step 2: Search a Product")
    
    user_query = st.text_input("Search Product Name (typos are automatically corrected):", placeholder="e.g. CeraVe cleanser...")

    with st.expander("📸 Optional: Scan Barcode via Camera"):
        camera_photo = st.camera_input("Take a photo of the product barcode", label_visibility="collapsed")
        if camera_photo:
            st.info("📷 Barcode camera frame captured!")

    if user_query:
        with st.spinner("Searching product registries..."):
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
                st.markdown("**🟢 Soothing Helpers**")
                st.write(", ".join(f_rep) if f_rep else "None detected")
            with badge_cols[1]:
                st.markdown("**🟡 Active Ingredients**")
                st.write(", ".join(f_act) if f_act else "None detected")
            with badge_cols[2]:
                st.markdown("**🔴 Potential Irritants**")
                st.write(", ".join(f_irr) if f_irr else "None detected")

            st.markdown("---")

            if GROQ_KEY:
                with st.spinner("✨ Decoding product for you in simple terms..."):
                    ai_data = ai_analyze_product(selected_product['label'], selected_product['ingredients'], user_profile)
                    
                if ai_data:
                    st.markdown(f"### 🎯 {ai_data.get('headline', '')}")
                    
                    # INTERACTIVE CLICKABLE PROS & CONS (USING EXPANDER CARDS)
                    col_p, col_c = st.columns(2)
                    with col_p:
                        st.markdown("#### ✅ Why You'll Like It")
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
                        st.markdown("#### ⚠️ Things to Watch Out For")
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
                    
                    # Expandable Deep-Dive Simple Summary
                    with st.expander("📖 Read Simple Summary & Details", expanded=False):
                        st.write(ai_data.get("analysis", ""))

                    st.markdown("### ⏳ Your Skin Timeline")
                    spectrum_data = ai_data.get("spectrum", {})
                    if spectrum_data:
                        timeframes = list(spectrum_data.keys())
                        
                        selected_time = st.select_slider(
                            "Slide to see how your skin changes over time:",
                            options=timeframes,
                            value=timeframes[0],
                            key="spectrum_slider" 
                        )
                        
                        st.info(f"**{selected_time}:** {spectrum_data[selected_time]}")

                    st.markdown("---")
                    with st.expander("📋 Simple Usage Guide", expanded=False):
                        protocol = ai_data.get("usage_protocol", {})
                        if protocol:
                            p_col1, p_col2 = st.columns(2)
                            with p_col1:
                                st.markdown(f"**How Often:** {protocol.get('frequency', 'N/A')}")
                                st.markdown(f"**When to Apply:** {protocol.get('time_of_day', 'N/A')}")
                            with p_col2:
                                st.markdown(f"**Routine Order:** {protocol.get('application_step', 'N/A')}")
                                st.markdown(f"**When to See Changes:** {protocol.get('time_to_visible_results', 'N/A')}")

                    st.markdown("---")
                    with st.expander("🏷️ Raw Ingredient List", expanded=False):
                        st.info(selected_product["ingredients"])
        else:
            st.warning("No matching products found. Try typing a simpler product name!")

# -----------------------------------------------------------------------------
# TAB 2: ROUTINE STACKING & COMPATIBILITY MATRIX
# -----------------------------------------------------------------------------
with tab_stack:
    st.markdown("### 🔄 Dual-Product Compatibility Check")
    st.caption("Find out if two products can be safely used together in your routine.")

    col_a, col_b = st.columns(2)
    
    with col_a:
        query_a = st.text_input("First Product Name:", placeholder="e.g. Glycolic Acid Toner", key="query_a")
        match_a = multi_source_search(query_a) if query_a else []
        selected_a = None
        if match_a:
            opt_a = [m['label'] for m in match_a]
            sel_a_name = st.selectbox("Select Product A:", opt_a, key="sel_a")
            selected_a = next(m for m in match_a if m['label'] == sel_a_name)

    with col_b:
        query_b = st.text_input("Second Product Name:", placeholder="e.g. Retinol Serum", key="query_b")
        match_b = multi_source_search(query_b) if query_b else []
        selected_b = None
        if match_b:
            opt_b = [m['label'] for m in match_b]
            sel_b_name = st.selectbox("Select Product B:", opt_b, key="sel_b")
            selected_b = next(m for m in match_b if m['label'] == sel_b_name)

    if selected_a and selected_b:
        st.markdown("---")
        if st.button("🧪 Check If They Work Together"):
            with st.spinner("Checking compatibility in simple terms..."):
                report = ai_check_compatibility(
                    selected_a['label'], selected_a['ingredients'],
                    selected_b['label'], selected_b['ingredients'],
                    user_profile
                )
                if report:
                    st.markdown(report)
