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
            b = int(color_pink[2] + (color_green[2] - color_green[2]) * local_p)
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
            background-color: rgba(255, 255, 255, 0.78) !important; 
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
    p, li, span, label, div.stMarkdown {{
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
        background-color: rgba(255, 255, 255, 0.88) !important;
        border: 1px solid #f3e5f5 !important;
        border-radius: 10px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 3. REGISTRY SEARCH & INGREDIENT PARSING
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_registry_data(api_url):
    headers = {"User-Agent": "MonadRoutineGuard - Research/Educational - v2.0"}
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
# 4. AI ENGINES (TRAFFIC LIGHT CONFLICT STRESS TEST & DETAILED USAGE GUIDE)
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def ai_stress_test_routine(new_prod_name, new_prod_ing, routine_products, skin_profile):
    if not groq_client:
        return None

    routine_summary = "\n".join([f"- {p['name']}: {p['ingredients']}" for p in routine_products]) if routine_products else "No current routine items logged yet."
    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"

    prompt = f"""
    You are Monad, an expert clinical routine safety guard.
    Evaluate whether the user can safely introduce this NEW product into their active routine, given their skin profile.

    USER PROFILE:
    - Skin Type: {skin_profile.get('type')}
    - Barrier State: {skin_profile.get('barrier')}
    - Sensitivities/Conditions: {medical_flags_str}
    - Medications: {skin_profile.get('medications')}

    ACTIVE ROUTINE DRAWER:
    {routine_summary}

    PROPOSED NEW PRODUCT:
    - Name: {new_prod_name}
    - Ingredients: {new_prod_ing}

    Return a JSON object with this exact structure (do not include markdown outside JSON):
    {{
        "status": "GREEN" (or "YELLOW" or "RED"),
        "verdict_title": "A short, punchy 3-5 word traffic-light headline (e.g., Safe to Layer, Caution Required, Direct Barrier Conflict)",
        "conditional_logic": "Snappy, direct explanation written in conditional logic tailored to their barrier state and routine (e.g., 'Because your barrier is reported as sensitive/stinging, adding this AHA alongside your routine retinoid will likely trigger micro-inflammation. Hold off for 48 hours or space them out').",
        "pros": [
            {{"title": "Simple benefit title 1", "detail": "Everyday benefit for their skin type."}},
            {{"title": "Simple benefit title 2", "detail": "Complementary support factor."}}
        ],
        "cons": [
            {{"title": "Simple caution title 1", "detail": "Potential irritation or clash."}},
            {{"title": "Simple caution title 2", "detail": "Barrier risk factor."}}
        ],
        "usage_protocol": {{
            "frequency": "Detailed frequency strictly adapted to their barrier condition (e.g., Apply 2-3 times per week initially)",
            "time_of_day": "Detailed AM/PM application guidance with layering rationale",
            "application_step": "Precise order in skincare routine (e.g., Apply after water-based serums and before heavier creams)",
            "time_to_visible_results": "Detailed clinical timeline and expected biological milestones"
        }}
    }}
    """
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Output strictly valid JSON with traffic light status (GREEN, YELLOW, RED), conditional logic, simple pros/cons, and a detailed usage protocol."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"AI Stress Test Error: {e}")
        return None

# -----------------------------------------------------------------------------
# 5. MAIN INTERFACE LAYOUT
# -----------------------------------------------------------------------------
st.title("🌸 MONAD: Decode You")
st.caption("✨ Real-time routine stress-testing and conflict detection for reactive skin.")

with st.expander("💡 How Monad Protects Your Skin", expanded=False):
    st.markdown("""
    Welcome to **Monad Routine Safety Guard**! 
    1. **Set Your Skin Profile:** Input your skin type, barrier state, and sensitivities below.
    2. **Build Your Routine Drawer:** Add your daily AM/PM products so Monad knows what's already on your face.
    3. **Stress-Test New Additions:** Drop in any prospective product to run a live conflict check against your active drawer and barrier condition!
    """)

st.markdown("> **Safety Notice:** *Monad provides educational ingredient compatibility screening. Always patch-test new products and consult a dermatologist for clinical skin conditions.*")

if not GROQ_KEY:
    st.warning("⚠️ Groq API Key not detected in Streamlit Secrets. AI dynamic features are disabled.")

# Session state initialization for Routine Drawer
if "routine_drawer" not in st.session_state:
    st.session_state["routine_drawer"] = []

# Skin Profile Configuration
with st.expander("👤 Step 1: Configure Your Skin Profile & Sensitivities", expanded=True):
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        skin_type = st.selectbox("Skin Type:", ["Balanced / Normal", "Sensitive / Reactive", "Oily / Acne-Prone", "Dry / Dehydrated", "Combination"])
    with col_s2:
        barrier_state = st.selectbox("Current Barrier Condition:", ["Healthy / Resilient", "Slightly Irritated / Flaky", "Compromised / Stinging / Red"])

    user_medications = st.text_input("Current Systemic or Topical Medications:", placeholder="e.g., Tretinoin, Accutane, topical antibiotics...")

    st.markdown("##### 🏥 Sensitivities & Medical Conditions")
    med_col1, med_col2 = st.columns(2)
    with med_col1:
        flag_rosacea = st.checkbox("Rosacea / Flushing")
        flag_eczema = st.checkbox("Eczema / Atopic Dermatitis")
        flag_fungal = st.checkbox("Fungal Acne Sensitive")
    with med_col2:
        flag_sensory = st.checkbox("Chemical Overload / Stinging")
        flag_allergy = st.checkbox("Fragrance / Contact Allergy")
        flag_postproc = st.checkbox("Post-Procedure Skin")

    medical_flags = []
    if flag_rosacea: medical_flags.append("Rosacea")
    if flag_eczema: medical_flags.append("Eczema")
    if flag_fungal: medical_flags.append("Fungal Acne Sensitive")
    if flag_sensory: medical_flags.append("Chemical Overload / Stinging")
    if flag_allergy: medical_flags.append("Fragrance / Contact Allergy")
    if flag_postproc: medical_flags.append("Post-Procedure Skin")

user_profile = {
    "sex": "Female Baseline",
    "lifestage": "Standard / Adult",
    "type": skin_type,
    "barrier": barrier_state,
    "medications": user_medications if user_medications else "None reported",
    "medical_flags": medical_flags
}

tab_drawer, tab_test = st.tabs(["📦 My Active Routine Drawer", "⚡ Safe-To-Add Stress Test"])

# -----------------------------------------------------------------------------
# TAB 1: ACTIVE ROUTINE DRAWER
# -----------------------------------------------------------------------------
with tab_drawer:
    st.markdown("### 📦 Manage Your Current Routine Staples")
    st.caption("Add the products you currently use daily so Monad can test new additions against them.")

    add_query = st.text_input("Search product to add to your routine drawer:", placeholder="e.g. CeraVe Hydrating Cleanser", key="drawer_search")
    if add_query:
        matches = multi_source_search(add_query)
        if matches:
            opts = [m['label'] for m in matches]
            chosen_label = st.selectbox("Select verified product to add:", opts, key="drawer_select")
            chosen_prod = next(m for m in matches if m['label'] == chosen_label)
            
            if st.button("➕ Add to My Active Routine Drawer"):
                if not any(p['name'] == chosen_prod['label'] for p in st.session_state["routine_drawer"]):
                    st.session_state["routine_drawer"].append({
                        "name": chosen_prod['label'],
                        "ingredients": chosen_prod['ingredients']
                    })
                    st.success(f"Added **{chosen_prod['label']}** to your active routine drawer!")
                    st.rerun()
                else:
                    st.warning("This product is already in your routine drawer.")

    st.markdown("---")
    st.markdown("#### 📋 Current Routine Inventory:")
    if st.session_state["routine_drawer"]:
        for idx, item in enumerate(st.session_state["routine_drawer"]):
            col_item1, col_item2 = st.columns([0.85, 0.15])
            with col_item1:
                st.markdown(f"**{idx+1}. {item['name']}**")
            with col_item2:
                if st.button("🗑️ Remove", key=f"rm_{idx} psic"):
                    st.session_state["routine_drawer"].pop(idx)
                    st.rerun()
    else:
        st.info("Your routine drawer is currently empty. Search and add your daily staples above.")

# -----------------------------------------------------------------------------
# TAB 2: SAFE-TO-ADD STRESS TEST
# -----------------------------------------------------------------------------
with tab_test:
    st.markdown("### ⚡ Safe-To-Add Routine Collision Test")
    st.caption("Test whether a prospective product clashes with your skin barrier or your active routine drawer.")

    test_query = st.text_input("Search new product you want to try:", placeholder="e.g. The Ordinary Glycolic Acid 7% Toning Solution", key="test_search")
    
    if test_query:
        test_matches = multi_source_search(test_query)
        if test_matches:
            test_opts = [m['label'] for m in test_matches]
            selected_test_label = st.selectbox("Select verified candidate product:", test_opts, key="test_select")
            selected_test_prod = next(m for m in test_matches if m['label'] == selected_test_label)
            
            st.markdown("---")
            st.success(f"**Candidate Loaded:** {selected_test_prod['label']}")

            # Ingredient ingredient badge breakdown
            f_rep, f_act, f_irr = parse_ingredient_badges(selected_test_prod['ingredients'])
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

            if GROQ_KEY:
                if st.button("🚀 Run Routine Collision Stress-Test"):
                    with st.spinner("Analyzing formula against your skin barrier and active routine..."):
                        stress_result = ai_stress_test_routine(
                            selected_test_prod['label'],
                            selected_test_prod['ingredients'],
                            st.session_state["routine_drawer"],
                            user_profile
                        )
                        
                        if stress_result:
                            status = stress_result.get("status", "GREEN").upper()
                            if status == "GREEN":
                                st.success(f"🟢 **Traffic Light Verdict: {stress_result.get('verdict_title')}**")
                            elif status == "YELLOW":
                                st.warning(f"🟡 **Traffic Light Verdict: {stress_result.get('verdict_title')}**")
                            else:
                                st.error(f"🔴 **Traffic Light Verdict: {stress_result.get('verdict_title')}**")

                            st.markdown(f"### 💬 Conditional Safety Guidance")
                            st.info(stress_result.get("conditional_logic", ""))

                            # Interactive Pros & Cons Expanders
                            col_p, col_c = st.columns(2)
                            with col_p:
                                st.markdown("#### ✅ Skin Benefits")
                                for p in stress_result.get("pros", []):
                                    with st.expander(f"✨ {p.get('title', 'Benefit')}"):
                                        st.write(p.get('detail', ''))

                            with col_c:
                                st.markdown("#### ⚠️ Conflict & Barrier Warnings")
                                for c in stress_result.get("cons", []):
                                    with st.expander(f"⚡ {c.get('title', 'Warning')}"):
                                        st.write(c.get('detail', ''))

                            st.markdown("---")
                            with st.expander("🔬 Detailed Expert Clinical Usage Guide", expanded=True):
                                protocol = stress_result.get("usage_protocol", {})
                                p_col1, p_col2 = st.columns(2)
                                with p_col1:
                                    st.markdown(f"**Frequency:** {protocol.get('frequency', 'N/A')}")
                                    st.markdown(f"**Timing:** {protocol.get('time_of_day', 'N/A')}")
                                with p_col2:
                                    st.markdown(f"**Routine Order:** {protocol.get('application_step', 'N/A')}")
                                    st.markdown(f"**Results Window:** {protocol.get('time_to_visible_results', 'N/A')}")

                            st.markdown("---")
                            with st.expander("🏷️ Extracted INCI Ingredient Formula", expanded=False):
                                st.info(selected_test_prod["ingredients"])
        else:
            st.warning("No matching products found in registries for your query. Try a broader search term!")
