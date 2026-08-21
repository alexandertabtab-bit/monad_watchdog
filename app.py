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
from openai import OpenAI

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & BACKGROUND GENERATOR (IN-MEMORY)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Monad: Decode You", page_icon="🌸", layout="centered")

GROQ_KEY = os.environ.get("GROQ_API_KEY_1") or os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY_1", "") or st.secrets.get("GROQ_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY", "")

def get_ai_pipeline():
    pipeline = []
    if GROQ_KEY:
        pipeline.append({
            "name": "Groq Primary",
            "client_type": "groq",
            "client": Groq(api_key=GROQ_KEY)
        })
    if OPENROUTER_KEY:
        pipeline.append({
            "name": "OpenRouter Gateway",
            "client_type": "openai",
            "client": OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_KEY)
        })
    return pipeline

@st.cache_data(max_entries=1)
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
            padding-top: 25px !important;
        }}
        [data-testid="stAppViewContainer"] > .main {{
            background-color: rgba(255, 255, 255, 0.75) !important; 
        }}
    """
else:
    bg_style = """
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #fff5f7 0%, #fefcf0 50%, #f0f7f4 100%);
            padding-top: 25px !important;
        }
    """

st.markdown(
    f"""
    <style>
    {bg_style}
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stVerticalBlock"] {{
        overscroll-behavior-y: none !important;
        -webkit-overflow-scrolling: touch;
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

if "saved_routine" not in st.session_state:
    st.session_state["saved_routine"] = []

# -----------------------------------------------------------------------------
# 3. INGREDIENT RETRIEVAL PIPELINE (WITH IMAGE EXTRACTION)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300, max_entries=50) 
def fetch_registry_data(api_url):
    headers = {"User-Agent": "MonadDecodeYou - Research/Educational - v1.0"}
    try:
        res = requests.get(api_url, headers=headers, timeout=8)
        if res.status_code == 200:
            products = res.json().get("products", [])
            valid = []
            for p in products:
                name = p.get("product_name") or p.get("product_name_en")
                brands = p.get("brands", "")
                ingredients = p.get("ingredients_text") or p.get("ingredients_text_en")
                image_url = p.get("image_front_url") or p.get("image_url") or ""
                if name and ingredients and len(ingredients.strip()) > 5:
                    label = f"{brands} - {name}" if brands else name
                    valid.append({
                        "label": label, 
                        "ingredients": ingredients.strip(), 
                        "image_url": image_url
                    })
            return valid
    except requests.exceptions.Timeout:
        st.warning("⚠️ The ingredient registry took too long to respond. Please try again.")
    except Exception:
        pass
    return []

def multi_source_search(query):
    # Make sure all lines inside this function are indented by 4 spaces
    
    curated_specialty_db = [
        {
            "label": "Aurodhea Collagen & Hyaluronic Acid Face Cream",
            "ingredients": "Aqua, Snail Secretion Filtrate, Hydrolyzed Collagen, Sodium Hyaluronate, Prunus Amygdalus Dulcis Oil, Argania Spinosa Kernel Oil, Cetearyl Alcohol, Glycerin, Glyceryl Stearate Citrate, Tocopherol, Xanthan Gum, Benzyl Alcohol, Dehydroacetic Acid, Parfum",
            "image_url": "https://images.unsplash.com/photo-1608248597359-9d74e31189f7?w=500&auto=format&fit=crop&q=60"
        },
        {
            "label": "Aurodhea Hyaluronic Acid Peel-Off Face Mask",
            "ingredients": "Aqua, Polyvinyl Alcohol, Alcohol Denat., Glycerin, Sodium Hyaluronate, Aloe Barbadensis Leaf Juice, Panthenol, Phenoxyethanol, Ethylhexylglycerin, Parfum",
            "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500&auto=format&fit=crop&q=60"
        }
    ]
    
    # This loop must line up vertically with the 'curated_specialty_db' definition above it
    for item in curated_specialty_db:
        if query.lower() in item["label"].lower():
            # Your matching logic here
            pass

    for item in curated_specialty_db:
        if any(token in item['label'].lower() for token in query_lower.split()):
            if item not in results:
                results.append(item)
    if "retinol" in query_lower and not results:
        results = curated_specialty_db

    url_beauty = f"https://world.openbeautyfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=20"
    registry_results = fetch_registry_data(url_beauty)
    
    if not registry_results:
        url_food = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=20"
        registry_results = fetch_registry_data(url_food)

    for r in registry_results:
        if r not in results:
            results.append(r)

    if len(results) < 2:
        broad_url = "https://world.openbeautyfacts.org/cgi/search.pl?action=process&json=1&page_size=100"
        all_products = fetch_registry_data(broad_url)
        if all_products:
            product_labels = [p['label'] for p in all_products]
            close_matches = difflib.get_close_matches(query, product_labels, n=5, cutoff=0.25)
            for m in all_products:
                if m['label'] in close_matches and m not in results:
                    results.append(m)

    return results

def parse_ingredient_badges(ingredients_text):
    text_lower = ingredients_text.lower()
    replenishing = ["ceramide", "hyaluronic", "glycerin", "panthenol", "squalane", "centella", "allantoin", "niacinamide", "cholesterol", "madecassoside"]
    actives = ["retinol", "retinal", "glycolic", "salicylic", "lactic", "ascorbic", "benzoyl", "azelaic", "adapalene", "tretinoin", "bakuchiol"]
    irritants = ["fragrance", "parfum", "alcohol denat", "linalool", "limonene", "citral", "eugenol", "essential oil", "menthol", "eucalyptus"]

    found_replenish = [i.title() for i in replenishing if i in text_lower]
    found_actives = [i.title() for i in actives if i in text_lower]
    found_irritants = [i.title() for i in irritants if i in text_lower]

    return found_replenish, found_actives, found_irritants

# -----------------------------------------------------------------------------
# 4. AI ENGINES
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=20)
def ai_analyze_product(product_name, ingredients, skin_profile):
    pipeline = get_ai_pipeline()
    if not pipeline:
        return None

    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"
    medications_str = skin_profile.get('medications', 'None reported')

    prompt = f"""
    You are a warm, knowledgeable skincare bestie giving a personalized breakdown. 

    CRITICAL RULES:
    1. NO INGREDIENT NAMES. Never use chemical names like Niacinamide, Retinol, Salicylic Acid, etc. Talk purely about real-world results ("smoothes bumps", "calms redness", "boosts glow").
    2. THE "NO ECHO" RULE: Do not parrot the user's profile back like a form ("Since you have oily skin..."). Instead, let their profile invisibly shape your advice.
    3. THE SUMMARY & BREAKDOWN: The 'analysis' section must be a natural, conversational paragraph explaining why this product works for *them specifically* and what it's going to do to their skin vibe, without sounding like a robot checklist.
    4. THE WASHOUT PERIOD: In the 'usage_protocol', calculate the 'effect_fade_timeline' in plain English (surface = fades in 1-2 days; mid = 1-2 weeks; deep cellular = 4-6 weeks).

    Profile Context (Use invisibly):
    - Life Stage: {skin_profile.get('lifestage')}
    - Skin Type: {skin_profile.get('type')}
    - Barrier State: {skin_profile.get('barrier')}
    - Active Medical Conditions: {medical_flags_str}

    Product: {product_name}
    Ingredients: {ingredients}

    Return a JSON object with this exact structure:
    {{
        "headline": "A punchy, 1-sentence hook about the main vibe/result. NO INGREDIENT NAMES.",
        "analysis": "A natural, conversational summary explaining how this product interacts with your unique skin state, what kind of transformation to expect, and why it fits your routine. No robotic list-repeating.",
        "usage_protocol": {{
            "frequency": "How often to use it (e.g., 'Start just 2 nights a week').",
            "time_of_day": "Morning, Night, or Both.",
            "application_step": "Exactly when to apply it.",
            "time_to_visible_results": "When they'll actually notice a difference.",
            "effect_fade_timeline": "Plain English explanation of how fast the skin reverts if they stop using this product."
        }},
        "pros": [
            {{"title": "Relatable Benefit 1", "detail": "A real-world result. NO INGREDIENT NAMES."}},
            {{"title": "Relatable Benefit 2", "detail": "Another great result. NO INGREDIENT NAMES."}}
        ],
        "cons": [
            {{"title": "Relatable Caution 1", "detail": "A real-world warning. NO INGREDIENT NAMES."}},
            {{"title": "Relatable Caution 2", "detail": "Safety check. NO INGREDIENT NAMES."}}
        ],
        "spectrum": {{
            "Day 1": "Initial reaction and hydration feeling.",
            "Day 3": "How it feels after a few days of adjustment.",
            "Day 7": "End of week 1, early smoothing.",
            "Day 14": "Two-week mark, clarity begins.",
            "Month 1": "One month of consistent use.",
            "Month 2": "Two month results.",
            "Month 3": "Three month maturity.",
            "Month 6": "Half-year mark.",
            "Year 1": "One year of progress.",
            "Year 2": "Two year evolution.",
            "Year 5": "Five years of maintenance.",
            "Year 10": "Ten year horizon.",
            "Year 20": "Twenty year longevity.",
            "Year 50": "Fifty year legacy.",
            "Year 100": "Lifetime impact."
        }},
        "medical_sources": [
            "Mention 2-3 general safety rules simply."
        ]
    }}
    """
    
    for step in pipeline:
        try:
            system_instruction = "You are a warm, relatable human giving personalized skincare breakdowns. Output strictly valid JSON. Never use chemical ingredient names. Never repeat the user's profile back to them."
            
            if step["client_type"] == "groq":
                response = step["client"].chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.2, 
                    response_format={"type": "json_object"}
                )
            else:
                response = step["client"].chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model="openrouter/free",
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
            return json.loads(response.choices[0].message.content)
        except Exception:
            continue
    return None

@st.cache_data(show_spinner=False, max_entries=20)
def ai_check_compatibility(prod_a_name, prod_a_ing, prod_b_name, prod_b_ing, skin_profile):
    pipeline = get_ai_pipeline()
    if not pipeline:
        return None

    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"
    medications_str = skin_profile.get('medications', 'None reported')

    prompt = f"""
    Analyze layering these two products. NEVER repeat their skin profile back to them (No 'Since you have oily skin...').

    Product A: {prod_a_name}
    Ingredients A: {prod_a_ing}

    Product B: {prod_b_name}
    Ingredients B: {prod_b_ing}

    RULE: Speak like a normal human. Do not list chemical names. Just tell them if mixing these will cause a bad reaction (like burning, peeling) or if it's safe and gives a great glow. Give practical advice on which one goes on first.
    """
    
    for step in pipeline:
        try:
            system_instruction = "You are a friendly guide providing practical, jargon-free layering advice. You never repeat the user's profile back to them."
            
            if step["client_type"] == "groq":
                response = step["client"].chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.2
                )
            else:
                response = step["client"].chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model="openrouter/free",
                    temperature=0.2
                )
            return response.choices[0].message.content
        except Exception:
            continue
    return None

# -----------------------------------------------------------------------------
# 5. MAIN INTERFACE LAYOUT
# -----------------------------------------------------------------------------
st.title("🌸 MONAD: Decode You")
st.caption("✨ Advanced molecular intelligence engine tailored to your complete biological profile.")

with st.expander("💡 Welcome to Monad: Decode You! Here is how the concept works:", expanded=False):
    st.markdown("""
    1. **Set Your Profile:** Input your skin type, life stage, medications, and medical sensitivities below.
    2. **Search or Scan:** Look up any product by name or barcode to view product photos and exact ingredient lists.
    3. **Plain-Language AI Decoding:** Get clear, simple summaries of product benefits and safety cautions.
    4. **Longevity Spectrum:** Drag the interactive slider from **Day 1 to Year 100** to preview long-term biological milestones.
    5. **Routine Stacking & Saving:** Check if products can be layered safely together and manage your saved routine history.
    """)

st.markdown("> **Medical Verification & Disclaimer:** *Monad aims for high accuracy by basing analysis on established dermatological standards. However, AI cannot replace a doctor.*")

if not GROQ_KEY and not OPENROUTER_KEY:
    st.warning("⚠️ No API keys detected in Streamlit Secrets or Environment Variables. AI dynamic features are disabled.")

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

    user_medications = st.text_input("Current Systemic or Topical Medications:", placeholder="e.g., Oral Accutane, birth control, topical tretinoin...")

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

tab_single, tab_stack, tab_routine = st.tabs(["🔍 Product Analysis", "🔄 Routine Stacking", "📚 My Routine"])

# -----------------------------------------------------------------------------
# TAB 1: PRODUCT ANALYSIS
# -----------------------------------------------------------------------------
with tab_single:
    st.markdown("### 🔍 Step 2: Product Search & Barcode Input")
    
    user_query = st.text_input("Search Product:", placeholder="e.g. Retinol Treatment...")

    with st.expander("📸 Optional: Scan Barcode via Camera"):
        camera_photo = st.camera_input("Take a photo of the product barcode", label_visibility="collapsed")
        if camera_photo:
            st.info("📷 Barcode camera frame captured!")

    if user_query:
        with st.spinner("Searching multi-source registries & specialty databases..."):
            matches = multi_source_search(user_query)
            
        if matches:
            options = [m['label'] for m in matches]
            selected_option = st.selectbox("Select verified product:", options=options, key="single_select")
            selected_product = next(m for m in matches if m['label'] == selected_option)
            
            st.markdown("---")
            
            # --- PRODUCT IMAGE DISPLAY ---
            img_col1, img_col2 = st.columns([1, 2])
            with img_col1:
                if selected_product.get('image_url'):
                    try:
                        st.image(selected_product['image_url'], width=160)
                    except Exception:
                        st.markdown("🧴 *Image unavailable*")
                else:
                    st.markdown("🧴 *Image unavailable*")
            with img_col2:
                st.success(f"**Loaded:** {selected_product['label']}")
                if st.button("📌 Save to My Routine"):
                    product_entry = {
                        "label": selected_product['label'],
                        "ingredients": selected_product['ingredients'],
                        "image_url": selected_product.get('image_url', '')
                    }
                    if product_entry not in st.session_state["saved_routine"]:
                        st.session_state["saved_routine"].append(product_entry)
                        st.success("Successfully added to your routine!")
                    else:
                        st.info("Product already saved.")

            f_rep, f_act, f_irr = parse_ingredient_badges(selected_product['ingredients'])
            badge_cols = st.columns(3)
            with badge_cols[0]:
                st.markdown("**🟢 Barrier Supporting**")
                st.write(", ".join(f_rep) if f_rep else "None detected")
            with badge_cols[1]:
                st.markdown("**🟡 Potent Actives**")
                st.write(", ".join(f_act) if f_act else "None detected")
            with badge_cols[2]:
                st.markdown("**🔴 Potential Irritants**")
                st.write(", ".join(f_irr) if f_irr else "None detected")

            st.markdown("---")

            if GROQ_KEY or OPENROUTER_KEY:
                with st.spinner("✨ Monad decoding formula in plain language..."):
                    ai_data = ai_analyze_product(selected_product['label'], selected_product['ingredients'], user_profile)
                    
                if ai_data:
                    st.markdown(f"### 🎯 {ai_data.get('headline', '')}")
                    
                    st.markdown("#### ✅ Skin Benefits & Wins")
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

                    st.markdown("#### ⚠️ Cautions & Things to Watch")
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
                    
                    with st.expander("📖 Read Simple Summary & Breakdown", expanded=False):
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
                        st.markdown(
                            f"""
                            <div style="background-color: rgba(255, 255, 255, 0.85); border: 1px solid #f3e5f5; border-radius: 10px; padding: 15px; margin-top: 10px;">
                                <span style="color: #4a4045; font-weight: 600;">{selected_time} Impact:</span> 
                                <span style="color: #4a4045;">{spectrum_data[selected_time]}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    st.markdown("---")
                    with st.expander("🔬 How to Use & Routine Guidelines", expanded=False):
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
                            st.markdown(f"**⏳ If you stop using it:** {protocol.get('effect_fade_timeline', 'N/A')}")

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
    st.caption("Check chemical compatibility and safety before layering two products.")

    col_a, col_b = st.columns(2)
    
    with col_a:
        query_a = st.text_input("Product A Name:", placeholder="e.g. Retinol Treatment", key="query_a")
        match_a = multi_source_search(query_a) if query_a else []
        selected_a = None
        if match_a:
            opt_a = [m['label'] for m in match_a]
            sel_a_name = st.selectbox("Select Product A:", opt_a, key="sel_a")
            selected_a = next(m for m in match_a if m['label'] == sel_a_name)

    with col_b:
        query_b = st.text_input("Product B Name:", placeholder="e.g. Renewal Cream", key="query_b")
        match_b = multi_source_search(query_b) if query_b else []
        selected_b = None
        if match_b:
            opt_b = [m['label'] for m in match_b]
            sel_b_name = st.selectbox("Select Product B:", opt_b, key="sel_b")
            selected_b = next(m for m in match_b if m['label'] == sel_b_name)

    if selected_a and selected_b:
        st.markdown("---")
        if st.button("🧪 Evaluate Compatibility"):
            with st.spinner("Analyzing product interactions in plain language..."):
                report = ai_check_compatibility(
                    selected_a['label'], selected_a['ingredients'],
                    selected_b['label'], selected_b['ingredients'],
                    user_profile
                )
                if report:
                    st.markdown(report)

# -----------------------------------------------------------------------------
# TAB 3: SAVED ROUTINE HISTORY
# -----------------------------------------------------------------------------
with tab_routine:
    st.markdown("### 📚 Your Saved Routine & History")
    st.caption("Access all your bookmarked products in one place without needing to re-search.")

    if not st.session_state["saved_routine"]:
        st.info("No products saved yet. Search for a product in the 'Product Analysis' tab and click **'Save to My Routine'**!")
    else:
        for idx, item in enumerate(st.session_state["saved_routine"]):
            with st.expander(f"🧴 {item['label']}"):
                if item.get('image_url'):
                    st.image(item['image_url'], width=100)
                st.markdown(f"**Ingredients:**")
                st.caption(item['ingredients'])
                if st.button("🗑️ Remove from Routine", key=f"remove_{idx}"):
                    st.session_state["saved_routine"].pop(idx)
                    st.rerun()

        st.markdown("---")
        if st.button("🧹 Clear All Saved Routine History"):
            st.session_state["saved_routine"] = []
            st.rerun()
