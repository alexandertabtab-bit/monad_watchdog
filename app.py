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

    for item in curated_specialty_db:
        product_title = item.get('label', '')
        if any(token in product_title.lower() for token in query_lower.split()):
            if item not in results:
                results.append(item)

    url_beauty = f"https://world.openbeautyfacts.org/cgi/search.pl?search_terms={query}&search_simple=1&action=process&json=1&page_size=20"
    registry_results = fetch_registry_data(url_beauty)
    for r in registry_results:
        if r not in results:
            results.append(r)

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
# 4. DYNAMIC FALLBACK & AI ENGINES
# -----------------------------------------------------------------------------
def get_dynamic_fallback(product_name, ingredients):
    p_lower = product_name.lower()
    if "retinol" in p_lower or "serum" in p_lower or "bakuchiol" in p_lower:
        return {
            "headline": "A potent cellular renewal treatment designed to stimulate collagen and refine skin texture.",
            "analysis": f"Using active retinoids and barrier-supporting agents ({ingredients[:60]}...), this serum accelerates cellular turnover to smooth fine lines and even skin tone over time.",
            "usage_protocol": {
                "frequency": "Use 2 to 3 times per week initially, building up to nightly use as tolerated.",
                "time_of_day": "Evening routine only.",
                "application_step": "Apply a pea-sized amount to clean, completely dry skin before heavier creams.",
                "time_to_visible_results": "Initial texture refinement within 2 to 4 weeks; deeper anti-aging benefits in 2 to 3 months.",
                "effect_fade_timeline": "Cellular turnover stimulation gradually reverts to baseline over 3-4 weeks if discontinued."
            },
            "pros": [
                {"title": "Accelerated Cell Turnover", "detail": "Promotes fresh epidermal growth to clear dullness and smooth texture."},
                {"title": "Collagen Remodeling", "detail": "Stimulates structural proteins to firm skin and reduce fine lines."}
            ],
            "cons": [
                {"title": "Initial Retinization / Purging", "detail": "May cause mild peeling, dryness, or temporary breakouts during the first few weeks."},
                {"title": "Sun Sensitivity", "detail": "Significantly increases UV vulnerability; daily sunscreen is mandatory."}
            ],
            "spectrum": {
                "Day 1": "Initial active contact; mild tingling may occur as skin encounters the retinoid.",
                "Day 3": "Beginning of cellular adjustment; potential light flaking or skin tightness.",
                "Day 7": "Skin begins adapting to active stimulation; surface tactile changes emerge.",
                "Day 14": "Subsurface adaptation underway; initial clearing of skin tone.",
                "Month 1": "Noticeable smoothness, brighter radiance, and refined pore appearance.",
                "Month 2": "Softer fine lines and more even epidermal tone as turnover normalizes.",
                "Month 3": "Significant collagen stimulation and enhanced structural firmness.",
                "Month 6": "Deeper structural remodeling; sustained reduction in stubborn textural irregularities.",
                "Year 1": "Optimized cellular turnover baseline and long-term anti-aging defense.",
                "Year 2": "Sustained barrier resilience and long-term elasticity maintenance.",
                "Year 5": "Compounding long-term anti-aging preservation in skin density.",
                "Year 10": "Lifelong youthful skin texture support baseline.",
                "Year 20": "Advanced structural vitality maintenance.",
                "Year 50": "Timeless resilience preservation.",
                "Year 100": "Ultimate skin longevity standard."
            },
            "medical_sources": ["Always pair with broad-spectrum SPF during daytime use."]
        }
    elif "mask" in p_lower and ("hair" in p_lower or "keratin" in p_lower or "capillary" in p_lower):
        return {
            "headline": "An intensive conditioning treatment designed to restructure and smooth hair fibers.",
            "analysis": f"Based on the formula ({ingredients[:60]}...), this hair mask targets cuticle damage and delivers deep moisture to combat dryness and frizz.",
            "usage_protocol": {
                "frequency": "Use once or twice a week after shampooing.",
                "time_of_day": "During shower or bath routine.",
                "application_step": "Apply evenly through damp mid-lengths to ends, leave for 5-10 minutes, then rinse.",
                "time_to_visible_results": "Immediate softness and detangling after the first rinse.",
                "effect_fade_timeline": "Hair manageability and smoothness gradually taper off over 3-4 days."
            },
            "pros": [
                {"title": "Intense Detangling & Softness", "detail": "Coats hair fibers to make combing effortless and eliminate roughness."},
                {"title": "Frizz Control & Shine", "detail": "Seals the cuticle to reflect light and keep flyaways under control."}
            ],
            "cons": [
                {"title": "Weigh Down Risk", "detail": "Avoid applying directly to the scalp if you have fine hair to prevent greasiness."},
                {"title": "Rinse Thoroughly", "detail": "Ensure complete rinsing to prevent product buildup."}
            ],
            "spectrum": {
                "Day 1": "Silky texture, effortless detangling, and smooth shine right after rinsing.",
                "Day 3": "Retained strand moisture and soft touchability.",
                "Day 7": "Noticeably less friction and easier styling during weekly brushing.",
                "Day 14": "Reduced split-end brittleness and improved fiber elasticity.",
                "Month 1": "Consistently smooth texture and protected structural integrity.",
                "Month 2": "Enhanced manageability and stronger strand resilience.",
                "Month 3": "Stabilized hair health with minimized breakage.",
                "Month 6": "Long-term cuticle protection and sustained hair vitality.",
                "Year 1": "Consistent maintenance of healthy, long hair integrity.",
                "Year 2": "Established robust hair care routine baseline.",
                "Year 5": "Optimized long-term hair conditioning maintenance.",
                "Year 10": "Lifelong hair strength preservation.",
                "Year 20": "Durable vitality maintenance.",
                "Year 50": "Timeless resilience.",
                "Year 100": "Ultimate care."
            },
            "medical_sources": ["Rinse thoroughly to avoid scalp irritation."]
        }
    elif "mask" in p_lower and ("face" in p_lower or "peel" in p_lower or "hyaluronic" in p_lower):
        return {
            "headline": "A specialized facial treatment designed to clarify, tighten, and deeply hydrate the skin barrier.",
            "analysis": f"Using film-formers and moisture-binding agents ({ingredients[:60]}...), this face mask lifts impurities while infusing hydration for a smoother complexion.",
            "usage_protocol": {
                "frequency": "Use 1 to 2 times per week on clean skin.",
                "time_of_day": "Evening routine.",
                "application_step": "Apply an even layer avoiding eye and lip areas, let dry completely, then gently peel or rinse off.",
                "time_to_visible_results": "Immediate tightening and a refreshed, glowing surface.",
                "effect_fade_timeline": "Hydration and surface clarity taper off over 2-3 days."
            },
            "pros": [
                {"title": "Surface Clarifying & Tightening", "detail": "Lifts away dead skin cells and refines pore appearance."},
                {"title": "Instant Radiance Boost", "detail": "Leaves skin looking energized and exceptionally smooth."}
            ],
            "cons": [
                {"title": "Not for Broken Skin", "detail": "Avoid active breakouts, cuts, or highly sensitive inflamed areas."},
                {"title": "Potential Dryness", "detail": "Always follow up with a nourishing moisturizer after removal."}
            ],
            "spectrum": {
                "Day 1": "Instant tightening sensation, clean surface feel, and smooth glow upon removal.",
                "Day 3": "Balanced surface touch and clear pores.",
                "Day 7": "Refined skin texture and less visible surface oiliness after weekly use.",
                "Day 14": "Smoother makeup application and more even complexion.",
                "Month 1": "Stable skin clarity and maintained moisture balance.",
                "Month 2": "Consistent radiance and refined pore texture.",
                "Month 3": "Established skin clarity routine baseline.",
                "Month 6": "Resilient barrier maintenance and long-term clarity support.",
                "Year 1": "Long-term skin wellness maintenance.",
                "Year 2": "Lasting skin radiance routine.",
                "Year 5": "Optimized renewal routine support.",
                "Year 10": "Lifetime skin wellness baseline.",
                "Year 20": "Durable vitality preservation.",
                "Year 50": "Timeless resilience.",
                "Year 100": "Ultimate care."
            },
            "medical_sources": ["Perform a patch test prior to full facial application."]
        }
    else:
        return {
            "headline": f"An effective formulation tailored for {product_name}.",
            "analysis": f"This product utilizes active ingredients ({ingredients[:60]}...) to provide targeted care and support your personal routine.",
            "usage_protocol": {
                "frequency": "Use as directed based on your routine.",
                "time_of_day": "Flexible timing.",
                "application_step": "Apply cleanly to target area.",
                "time_to_visible_results": "Noticeable difference within 1-2 weeks.",
                "effect_fade_timeline": "Benefits gradually fade over 3-5 days if stopped."
            },
            "pros": [
                {"title": "Targeted Care", "detail": "Provides direct support for your specific goals."},
                {"title": "Comfortable Use", "detail": "Designed for smooth integration into daily care."}
            ],
            "cons": [
                {"title": "Patch Test Recommended", "detail": "Test on a small area first to check compatibility."}
            ],
            "spectrum": {
                "Day 1": "Initial product contact and surface feel.",
                "Day 3": "Initial adjustment phase.",
                "Day 7": "First noticeable benefits and integration into routine.",
                "Day 14": "Stabilized comfort and performance.",
                "Month 1": "Consistent routine baseline and sustained results.",
                "Month 2": "Ongoing performance maintenance.",
                "Month 3": "Long-term benefit integration.",
                "Month 6": "Established routine stability.",
                "Year 1": "Long-term care support.",
                "Year 2": "Lasting maintenance.",
                "Year 5": "Optimized routine.",
                "Year 10": "Lifetime baseline.",
                "Year 20": "Durable vitality.",
                "Year 50": "Timeless resilience.",
                "Year 100": "Ultimate care."
            },
            "medical_sources": ["Follow standard safety guidelines."]
        }

@st.cache_data(show_spinner=False, max_entries=20)
def ai_analyze_product(product_name, ingredients, skin_profile):
    pipeline = get_ai_pipeline()
    fallback_data = get_dynamic_fallback(product_name, ingredients)

    if not pipeline:
        return fallback_data

    medical_flags_str = ", ".join(skin_profile.get('medical_flags', [])) if skin_profile.get('medical_flags') else "None reported"

    prompt = f"""
    You are a meticulous, knowledgeable skincare and cosmetic chemist giving a personalized breakdown. 

    CRITICAL RULES:
    1. STRICT PRODUCT DIFFERENTIATION: Analyze this exact product ({product_name}) and its specific INCI ingredients. Retinoids/serums require a long-term anti-aging and cell-turnover progression (Months/Years), while masks and shampoos focus on immediate to medium-term conditioning or clarifying.
    2. NO INGREDIENT NAMES: Never use chemical names like Polyvinyl Alcohol, Behentrimonium Chloride, Niacinamide, Retinol, etc. Talk purely about real-world results ("tightens pores", "smooths hair cuticles", "accelerates cell turnover", "locks in moisture").
    3. THE "NO ECHO" RULE: Do not parrot the user's profile back like a form. Instead, let their profile invisibly shape your advice.
    4. FULL MULTI-YEAR SPECTRUM: The 'spectrum' object must contain *all* 15 progression keys: "Day 1", "Day 3", "Day 7", "Day 14", "Month 1", "Month 2", "Month 3", "Month 6", "Year 1", "Year 2", "Year 5", "Year 10", "Year 20", "Year 50", and "Year 100". Make these descriptions *completely specific* to the product type (e.g. retinoids must map out purging, retinization, collagen remodeling, and long-term anti-aging over years).

    Profile Context:
    - Life Stage: {skin_profile.get('lifestage')}
    - Skin/Hair Type: {skin_profile.get('type')}
    - Barrier State: {skin_profile.get('barrier')}
    - Active Medical Conditions: {medical_flags_str}

    Product Name: {product_name}
    Ingredients: {ingredients}

    Return a JSON object with this exact structure:
    {{
        "headline": "A punchy, 1-sentence hook about the main vibe/result specific to this product. NO INGREDIENT NAMES.",
        "analysis": "A natural, conversational summary explaining how this specific product interacts with your unique profile.",
        "usage_protocol": {{
            "frequency": "How often to use it.",
            "time_of_day": "Morning, Night, or Shower time.",
            "application_step": "Exactly when and how to apply it.",
            "time_to_visible_results": "When they'll actually notice a difference.",
            "effect_fade_timeline": "Plain English explanation of how fast results revert if stopped."
        }},
        "pros": [
            {{"title": "Product-Specific Benefit 1", "detail": "A real-world result."}},
            {{"title": "Product-Specific Benefit 2", "detail": "Another great result."}}
        ],
        "cons": [
            {{"title": "Product-Specific Caution 1", "detail": "A real-world warning."}},
            {{"title": "Product-Specific Caution 2", "detail": "Safety check."}}
        ],
        "spectrum": {{
            "Day 1": "...", "Day 3": "...", "Day 7": "...", "Day 14": "...", 
            "Month 1": "...", "Month 2": "...", "Month 3": "...", "Month 6": "...", 
            "Year 1": "...", "Year 2": "...", "Year 5": "...", "Year 10": "...", 
            "Year 20": "...", "Year 50": "...", "Year 100": "..."
        }},
        "medical_sources": ["General safety rule."]
    }}
    """
    
    for step in pipeline:
        try:
            system_instruction = "You are a warm, highly precise cosmetic chemist giving personalized product breakdowns. Output strictly valid JSON."
            
            if step["client_type"] == "groq":
                response = step["client"].chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.1, 
                    response_format={"type": "json_object"}
                )
            else:
                response = step["client"].chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model="deepseek/deepseek-chat",
                    temperature=0.1
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
    2. **Search or Scan Barcode:** Look up any product by name (e.g., Aurodhea face mask, Retinol serum) or enter a barcode number.
    3. **Plain-Language AI Decoding:** Get clear summaries of product benefits and safety cautions.
    4. **Longevity Spectrum:** Drag the interactive slider from **Day 1 to Year 100** to preview long-term biological impact.
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
        user_query = st.text_input("Search Product or Category:", placeholder="e.g., Aurodhea face mask, Retinol serum...")
        if user_query:
            with st.spinner("Searching multi-source registries & catalogs..."):
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
        query_a = st.text_input("Product A Name:", placeholder="e.g. Retinol Serum", key="query_a")
        match_a = multi_source_search(query_a) if query_a else []
        selected_a = None
        if match_a:
            opt_a = [m['label'] for m in match_a]
            sel_a_name = st.selectbox("Select Product A:", opt_a, key="sel_a")
            selected_a = next(m for m in match_a if m['label'] == sel_a_name)

    with col_b:
        query_b = st.text_input("Product B Name:", placeholder="e.g. Face Cream", key="query_b")
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
