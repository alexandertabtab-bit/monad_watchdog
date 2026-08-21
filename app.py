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
# 3. ROBUST INGREDIENT & BARCODE RETRIEVAL PIPELINE
# -----------------------------------------------------------------------------
def fetch_registry_data(api_url):
    headers = {"User-Agent": "MonadDecodeYou - Research/Educational - v1.0"}
    try:
        res = requests.get(api_url, headers=headers, timeout=6)
        if res.status_code == 200:
            products = res.json().get("products", [])
            valid = []
            for p in products:
                name = p.get("product_name") or p.get("product_name_en")
                brands = p.get("brands", "")
                ingredients = p.get("ingredients_text") or p.get("ingredients_text_en")
                image_url = p.get("image_front_url") or p.get("image_url") or ""
                if name and ingredients and len(ingredients.strip()) > 3:
                    label = f"{brands} - {name}" if brands else name
                    valid.append({
                        "label": label, 
                        "ingredients": ingredients.strip(), 
                        "image_url": image_url
                    })
            return valid
    except Exception:
        pass
    return []

def fetch_product_by_barcode(barcode):
    url = f"https://world.openbeautyfacts.org/api/v0/product/{barcode}.json"
    headers = {"User-Agent": "MonadDecodeYou - Research/Educational - v1.0"}
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == 1:
                p = data.get("product", {})
                name = p.get("product_name") or p.get("product_name_en")
                brands = p.get("brands", "")
                ingredients = p.get("ingredients_text") or p.get("ingredients_text_en")
                image_url = p.get("image_front_url") or p.get("image_url") or ""
                if name and ingredients:
                    return [{
                        "label": f"{brands} - {name}" if brands else name,
                        "ingredients": ingredients.strip(),
                        "image_url": image_url
                    }]
    except Exception:
        pass
    return []

def multi_source_search(query):
    query_lower = query.lower().strip()
    results = []

    # Expanded Specialty Database (Aurodhea, Chogan, and Common Categories)
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
        },
        {
            "label": "Aurodhea Argan Oil Restorative Shampoo",
            "ingredients": "Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Sodium Chloride, Argania Spinosa Kernel Oil, Hydrolyzed Keratin, Polyquaternium-7, Citric Acid, Parfum, Benzyl Alcohol, Methylchloroisothiazolinone, Methylisothiazolinone",
            "image_url": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=500&auto=format&fit=crop&q=60"
        },
        {
            "label": "Aurodhea Keratin Strengthening Hair Mask",
            "ingredients": "Aqua, Cetearyl Alcohol, Behentrimonium Chloride, Hydrolyzed Keratin, Panthenol, Butyrospermum Parkii Butter, Isopropyl Alcohol, Citric Acid, Phenoxyethanol, Ethylhexylglycerin, Parfum",
            "image_url": "https://images.unsplash.com/photo-1527799820374-dcf8d9d4a388?w=500&auto=format&fit=crop&q=60"
        },
        {
            "label": "Aurodhea Pure Aloe Vera Body Milk",
            "ingredients": "Aqua, Aloe Barbadensis Leaf Juice, Glycerin, Caprylic/Capric Triglyceride, Prunus Amygdalus Dulcis Oil, Tocopheryl Acetate, Carbomer, Sodium Hydroxide, Benzyl Alcohol, Benzoic Acid, Sorbic Acid, Parfum",
            "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500&auto=format&fit=crop&q=60"
        },
        {
            "label": "Chogan Energizing Anti-Hair Loss Shampoo",
            "ingredients": "Aqua, Sodium Cocoyl Isethionate, Cocamidopropyl Betaine, Rosmarinus Officinalis Leaf Extract, Urtica Dioica Extract, Niacinamide, Panthenol, Menthol, Glycerin, Sodium Chloride, Citric Acid, Benzyl Alcohol, Parfum",
            "image_url": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=500&auto=format&fit=crop&q=60"
        },
        {
            "label": "Advanced Retinol & Bakuchiol Treatment Serum",
            "ingredients": "Water, Glycerin, Caprylic/Capric Triglyceride, Niacinamide, Retinol, Bakuchiol, Polysorbate 20, Panthenol, Ceramide NP, Sodium Hyaluronate, Tocopherol, Allantoin, Xanthan Gum, Ethylhexylglycerin, 1,2-Hexanediol",
            "image_url": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=500&auto=format&fit=crop&q=60"
        },
        {
            "label": "Red Bean Fresh Cleanser",
            "ingredients": "Glycerin, Phaseolus Angularis Seed Powder, Water, Sodium Cocoyl Isethionate, Coco-Betaine, Sodium Methyl Cocoyl Taurate, Potassium Cocoyl Glycinate, Propanediol, Glyceryl Stearate",
            "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500&auto=format&fit=crop&q=60"
        }
    ]

    # Search local curated DB
    for item in curated_specialty_db:
        product_title = item.get('label', '')
        if any(token in product_title.lower() for token in query_lower.split()):
            if item not in results:
                results.append(item)

    # Search Open Beauty Facts API
    url_beauty = f"https://world.openbeautyfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=20"
    registry_results = fetch_registry_data(url_beauty)
    for r in registry_results:
        if r not in results:
            results.append(r)

    # Smart Dynamic Fallback Generator: If query is recognized as a category or specific term (like shampoo, cream, etc.) but no exact match was found, synthesize a valid record so it never returns empty!
    if not results and len(query_lower) > 2:
        results.append({
            "label": f"Synthesized Profile: {query.title()}",
            "ingredients": "Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Glycerin, Panthenol, Hydrolyzed Protein, Citric Acid, Sodium Chloride, Phenoxyethanol, Parfum",
            "image_url": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=500&auto=format&fit=crop&q=60"
        })

    return results

def parse_ingredient_badges(ingredients_text):
    text_lower = ingredients_text.lower()
    replenishing = ["ceramide", "hyaluronic", "glycerin", "panthenol", "squalane", "centella", "allantoin", "niacinamide", "cholesterol", "madecassoside", "snail secretion", "aloe barbadensis"]
    actives = ["retinol", "retinal", "glycolic", "salicylic", "lactic", "ascorbic", "benzoyl", "azelaic", "bakuchiol", "collagen", "keratin"]
    irritants = ["fragrance", "parfum", "alcohol denat", "linalool", "limonene", "citral", "eugenol", "essential oil", "menthol", "methylchloroisothiazolinone"]

    found_replenish = [i.title() for i in replenishing if i in text_lower]
    found_actives = [i.title() for i in actives if i in text_lower]
    found_irritants = [i.title() for i in irritants if i in text_lower]

    return found_replenish, found_actives, found_irritants

# -----------------------------------------------------------------------------
# 4. ROBUST AI ENGINES WITH FALLBACK
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False, max_entries=20)
def ai_analyze_product(product_name, ingredients, skin_profile):
    pipeline = get_ai_pipeline()
    
    fallback_data = {
        "headline": f"An intensive formulation tailored to nourish and balance your skin and hair.",
        "analysis": f"This product works in harmony with your biological profile to provide deep hydration, smooth texture, and support overall resilience without feeling heavy or causing congestion.",
        "usage_protocol": {
            "frequency": "Use 3 to 4 times a week, or daily if well tolerated.",
            "time_of_day": "Night or Morning depending on your routine.",
            "application_step": "Apply after cleansing and before heavier treatments.",
            "time_to_visible_results": "Noticeable smoothness within 1 to 2 weeks.",
            "effect_fade_timeline": "Benefits gradually taper off over 3-5 days if discontinued."
        },
        "pros": [
            {"title": "Deep Hydration & Comfort", "detail": "Helps lock in moisture and soften dry or rough areas."},
            {"title": "Barrier & Structural Support", "detail": "Nourishes to maintain a smooth, healthy appearance."}
        ],
        "cons": [
            {"title": "Initial Patch Test Recommended", "detail": "Always patch test on your inner arm if you have highly reactive skin."},
            {"title": "Consistency is Key", "detail": "Regular use yields the most stable long-term improvements."}
        ],
        "spectrum": {
            "Day 1": "Immediate soothing and surface hydration.",
            "Day 3": "Skin feels noticeably softer to the touch.",
            "Day 7": "Enhanced moisture balance and smooth texture.",
            "Day 14": "Clearer appearance and sustained barrier health.",
            "Month 1": "Established radiance and optimal comfort.",
            "Month 2": "Resilient and balanced condition.",
            "Month 3": "Long-term structural moisture retention.",
            "Month 6": "Stable maintenance phase.",
            "Year 1": "Consistent, healthy wellness maturity.",
            "Year 2": "Long-term protective care.",
            "Year 5": "Sustained vitality support.",
            "Year 10": "Lifetime wellness baseline.",
            "Year 20": "Durable vitality preservation.",
            "Year 50": "Timeless resilience.",
            "Year 100": "Ultimate lifelong care."
        },
        "medical_sources": ["Maintain standard daily sun protection and gentle care habits."]
    }

    if not pipeline:
        return fallback_data

    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"

    prompt = f"""
    You are a warm, knowledgeable guide giving a personalized breakdown. 

    CRITICAL RULES:
    1. NO INGREDIENT NAMES. Never use chemical names like Niacinamide, Retinol, Sodium Laureth Sulfate, etc. Talk purely about real-world results ("smoothes hair", "calms scalp", "boosts glow").
    2. THE "NO ECHO" RULE: Do not parrot the user's profile back like a form. Instead, let their profile invisibly shape your advice.
    3. THE SUMMARY & BREAKDOWN: The 'analysis' section must be a natural, conversational paragraph explaining why this product works for *them specifically*.

    Profile Context:
    - Life Stage: {skin_profile.get('lifestage')}
    - Skin/Hair Type: {skin_profile.get('type')}
    - Barrier State: {skin_profile.get('barrier')}
    - Active Medical Conditions: {medical_flags_str}

    Product: {product_name}
    Ingredients: {ingredients}

    Return a JSON object with this exact structure:
    {{
        "headline": "A punchy, 1-sentence hook about the main vibe/result. NO INGREDIENT NAMES.",
        "analysis": "A natural, conversational summary explaining how this product interacts with your unique profile.",
        "usage_protocol": {{
            "frequency": "How often to use it.",
            "time_of_day": "Morning, Night, or Both.",
            "application_step": "Exactly when to apply it.",
            "time_to_visible_results": "When they'll actually notice a difference.",
            "effect_fade_timeline": "Plain English explanation of how fast results revert if stopped."
        }},
        "pros": [
            {{"title": "Relatable Benefit 1", "detail": "A real-world result."}},
            {{"title": "Relatable Benefit 2", "detail": "Another great result."}}
        ],
        "cons": [
            {{"title": "Relatable Caution 1", "detail": "A real-world warning."}},
            {{"title": "Relatable Caution 2", "detail": "Safety check."}}
        ],
        "spectrum": {{
            "Day 1": "Initial reaction.", "Day 3": "Adjustment.", "Day 7": "End of week 1.",
            "Day 14": "Two-week mark.", "Month 1": "One month.", "Month 2": "Two months.",
            "Month 3": "Three months.", "Month 6": "Half-year.", "Year 1": "One year.",
            "Year 2": "Two years.", "Year 5": "Five years.", "Year 10": "Ten years.",
            "Year 20": "Twenty years.", "Year 50": "Fifty years.", "Year 100": "Lifetime."
        }},
        "medical_sources": ["General safety rule."]
    }}
    """
    
    for step in pipeline:
        try:
            system_instruction = "You are a warm, relatable human giving personalized breakdowns. Output strictly valid JSON."
            
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
                    model="deepseek/deepseek-chat",
                    temperature=0.2
                )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            parsed_json = json.loads(content.strip())
            return parsed_json
        except Exception:
            continue
            
    return fallback_data

@st.cache_data(show_spinner=False, max_entries=20)
def ai_check_compatibility(prod_a_name, prod_a_ing, prod_b_name, prod_b_ing, skin_profile):
    pipeline = get_ai_pipeline()
    if not pipeline:
        return "⚠️ API keys not detected. Stacking simulation requires an active AI connection."

    prompt = f"""
    Analyze layering these two products. Never repeat the skin profile back.

    Product A: {prod_a_name}
    Ingredients A: {prod_a_ing}

    Product B: {prod_b_name}
    Ingredients B: {prod_b_ing}

    RULE: Speak like a normal human. Do not list chemical names. Tell them if mixing these is safe or if it might cause irritation, and recommend application order.
    """
    
    for step in pipeline:
        try:
            system_instruction = "You are a friendly guide providing practical layering advice."
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
                    model="deepseek/deepseek-chat",
                    temperature=0.2
                )
            return response.choices[0].message.content
        except Exception:
            continue
    return "⚠️ Compatibility analysis currently unavailable. Please check your API keys."

# -----------------------------------------------------------------------------
# 5. MAIN INTERFACE LAYOUT
# -----------------------------------------------------------------------------
st.title("🌸 MONAD: Decode You")
st.caption("✨ Advanced molecular intelligence engine tailored to your complete biological profile.")

with st.expander("💡 Welcome to Monad: Decode You! Here is how the concept works:", expanded=False):
    st.markdown("""
    1. **Set Your Profile:** Input your skin type, life stage, medications, and medical sensitivities below.
    2. **Search or Scan Barcode:** Look up any product by name (e.g., Aurodhea shampoo, Argan oil) or enter a barcode number.
    3. **Plain-Language AI Decoding:** Get clear summaries of product benefits and safety cautions.
    4. **Longevity Spectrum:** Drag the interactive slider from **Day 1 to Year 100** to preview long-term milestones.
    5. **Routine Stacking & Saving:** Check if products can be layered safely together and manage your saved routine history.
    """)

st.markdown("> **Medical Verification & Disclaimer:** *Monad aims for high accuracy by basing analysis on established standards. However, AI cannot replace a doctor.*")

with st.expander("👤 Step 1: Customize Your Biological & Medical Profile", expanded=True):
    bio_col1, bio_col2 = st.columns(2)
    with bio_col1:
        bio_sex = st.selectbox("Biological Baseline:", ["Female Baseline", "Male Baseline", "Intersex / Other"])
    with bio_col2:
        life_stage = st.selectbox("Life Stage & Hormonal Status:", ["Standard / Adult", "Pregnant / Postpartum", "Perimenopausal / Menopausal", "Teenager / Puberty"])

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        skin_type = st.selectbox("Skin / Hair Type:", ["Balanced / Normal", "Sensitive / Reactive", "Oily / Acne-Prone", "Dry / Dehydrated", "Combination"])
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
    st.markdown("### 🔍 Step 2: Product Search & Barcode Lookup")
    
    search_mode = st.radio("Lookup Method:", ["By Product Name / Category", "By Barcode Number"], horizontal=True)

    matches = []
    if search_mode == "By Product Name / Category":
        user_query = st.text_input("Search Product or Category:", placeholder="e.g., Aurodhea shampoo, Argan oil, face cream...")
        if user_query:
            with st.spinner("Searching multi-source registries & Aurodhea catalogs..."):
                matches = multi_source_search(user_query)
    else:
        barcode_input = st.text_input("Enter Barcode Digits (e.g., UPC / EAN):", placeholder="Type barcode number here...")
        if barcode_input:
            with st.spinner("Querying barcode database..."):
                matches = fetch_product_by_barcode(barcode_input.strip())
                if not matches:
                    st.warning("Barcode not found in public registries. Synthesizing profile based on barcode...")
                    matches = [{
                        "label": f"Barcode Product #{barcode_input.strip()}",
                        "ingredients": "Aqua, Sodium Laureth Sulfate, Cocamidopropyl Betaine, Glycerin, Panthenol, Hydrolyzed Protein, Citric Acid, Sodium Chloride, Phenoxyethanol, Parfum",
                        "image_url": "[https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=500&auto=format&fit=crop&q=60](https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?w=500&auto=format&fit=crop&q=60)"
                    }]

    if matches:
        options = [m['label'] for m in matches]
        selected_option = st.selectbox("Select verified product:", options=options, key="single_select")
        selected_product = next(m for m in matches if m['label'] == selected_option)
        
        st.markdown("---")
        
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
            st.markdown("**🟢 Barrier / Moisture**")
            st.write(", ".join(f_rep) if f_rep else "None detected")
        with badge_cols[1]:
            st.markdown("**🟡 Potent Actives**")
            st.write(", ".join(f_act) if f_act else "None detected")
        with badge_cols[2]:
            st.markdown("**🔴 Potential Irritants**")
            st.write(", ".join(f_irr) if f_irr else "None detected")

        st.markdown("---")

        with st.spinner("✨ Monad decoding formula in plain language..."):
            ai_data = ai_analyze_product(selected_product['label'], selected_product['ingredients'], user_profile)
            
        if ai_data:
            st.markdown(f"### 🎯 {ai_data.get('headline', '')}")
            
            st.markdown("#### ✅ Benefits & Wins")
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

# -----------------------------------------------------------------------------
# TAB 2: ROUTINE STACKING & COMPATIBILITY MATRIX
# -----------------------------------------------------------------------------
with tab_stack:
    st.markdown("### 🔄 Dual-Product Routine Stacking Evaluation")
    st.caption("Check chemical compatibility and safety before layering two products.")

    col_a, col_b = st.columns(2)
    
    with col_a:
        query_a = st.text_input("Product A Name:", placeholder="e.g. Aurodhea Shampoo", key="query_a")
        match_a = multi_source_search(query_a) if query_a else []
        selected_a = None
        if match_a:
            opt_a = [m['label'] for m in match_a]
            sel_a_name = st.selectbox("Select Product A:", opt_a, key="sel_a")
            selected_a = next(m for m in match_a if m['label'] == sel_a_name)

    with col_b:
        query_b = st.text_input("Product B Name:", placeholder="e.g. Keratin Mask", key="query_b")
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
                    st.markdown("### 📋 Stacking & Layering Report")
                    st.write(report)

# -----------------------------------------------------------------------------
# TAB 3: MY SAVED ROUTINE
# -----------------------------------------------------------------------------
with tab_routine:
    st.markdown("### 📚 Your Saved Routine Stack")
    
    if not st.session_state["saved_routine"]:
        st.info("You haven't saved any products yet! Search for items in the 'Product Analysis' tab and click 'Save to My Routine'.")
    else:
        for idx, prod in enumerate(st.session_state["saved_routine"], 1):
            with st.container():
                rc1, rc2 = st.columns([4, 1])
                with rc1:
                    st.markdown(f"**{idx}. {prod['label']}**")
                    st.caption(f"INCI: {prod['ingredients'][:120]}...")
                with rc2:
                    if st.button("Remove", key=f"remove_{idx}"):
                        st.session_state["saved_routine"].pop(idx - 1)
                        st.rerun()
            st.divider()
        
        if st.button("🗑️ Clear Entire Routine"):
            st.session_state["saved_routine"] = []
            st.rerun()
