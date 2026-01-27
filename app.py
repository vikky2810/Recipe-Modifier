from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import os
import bleach
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import json
from config import Config
from gemini_service import gemini_service
from models import UserManager
from forms import RegistrationForm, LoginForm, ProfileUpdateForm, ChangePasswordForm
import requests

load_dotenv()

# Validate critical environment variables (warn but don't crash)
def validate_env_vars():
    """Validate that critical environment variables are set"""
    missing = []
    if not os.getenv("SECRET_KEY") or os.getenv("SECRET_KEY") == 'your-secret-key-change-this-in-production':
        missing.append("SECRET_KEY")
    if not os.getenv("MONGODB_URI") or os.getenv("MONGODB_URI") == 'mongodb://localhost:27017/':
        missing.append("MONGODB_URI")
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == 'your-gemini-api-key-here':
        missing.append("GEMINI_API_KEY")
    
    if missing:
        print(f"WARNING: Missing or default environment variables: {', '.join(missing)}")
        print("These should be set in Vercel project settings for production deployment.")
    else:
        print("✅ All critical environment variables are set")

# Only validate in production/serverless (not local dev)
if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
    validate_env_vars()

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config.from_object(Config)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize Flask-Limiter for rate limiting (prevents brute force attacks)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Allowed HTML tags for sanitization (XSS prevention)
ALLOWED_TAGS = ['p', 'h5', 'h6', 'ul', 'ol', 'li', 'strong', 'em', 'i', 'b', 'br', 'span', 'div', 'class']
ALLOWED_ATTRIBUTES = {'*': ['class']}

def sanitize_html(html_content):
    """Sanitize HTML content to prevent XSS attacks"""
    if not html_content:
        return ""
    return bleach.clean(html_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)

# MongoDB Configuration - Lazy initialization for serverless
_client = None
_db = None
_ingredient_rules = None
_food_entries = None
_recipes = None
_generated_recipes = None
_user_manager = None

def get_db():
    """Lazy initialization of MongoDB connection"""
    global _client, _db, _ingredient_rules, _food_entries, _recipes, _generated_recipes, _user_manager
    
    if _db is None:
        try:
            # Increased timeout for serverless cold starts (15 seconds)
            _client = MongoClient(
                Config.MONGODB_URI, 
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=15000,
                socketTimeoutMS=30000
            )
            _db = _client[Config.DATABASE_NAME]
            
            # Initialize collections
            _ingredient_rules = _db['ingredient_rules']
            _food_entries = _db['food_entries']
            _recipes = _db['recipes']
            _generated_recipes = _db['generated_recipes']
            
            # Ensure indexes for fast lookups
            try:
                _ingredient_rules.create_index('ingredient', unique=True)
                _generated_recipes.create_index([('condition', 1), ('ingredients_key', 1)])
            except Exception:
                # Index creation is best-effort; ignore if permissions/environment restrict this
                pass
            
            # Initialize User Manager
            _user_manager = UserManager(_db)
            
            # Initialize database on first connection
            initialize_database()
            ensure_core_ingredients()
            
        except Exception as e:
            print(f"MongoDB connection error: {e}")
            # Create dummy collections to prevent crashes
            class DummyCollection:
                def find_one(self, *args, **kwargs): return None
                def find(self, *args, **kwargs): return []
                def insert_one(self, *args, **kwargs): return type('obj', (object,), {'inserted_id': None})()
                def update_one(self, *args, **kwargs): return type('obj', (object,), {'modified_count': 0})()
                def count_documents(self, *args, **kwargs): return 0
                def create_index(self, *args, **kwargs): pass
                def aggregate(self, *args, **kwargs): return []
                def sort(self, *args, **kwargs): return self
                def limit(self, *args, **kwargs): return self
                def delete_one(self, *args, **kwargs): return type('obj', (object,), {'deleted_count': 0})()
            
            _ingredient_rules = DummyCollection()
            _food_entries = DummyCollection()
            _recipes = DummyCollection()
            _generated_recipes = DummyCollection()
            _user_manager = UserManager(None)
    
    return _db

# Accessor functions for collections
def get_ingredient_rules():
    get_db()
    return _ingredient_rules

def get_food_entries():
    get_db()
    return _food_entries


def get_recipes():
    get_db()
    return _recipes

def get_generated_recipes():
    get_db()
    return _generated_recipes

def get_user_manager():
    get_db()
    return _user_manager

# Note: All database access should use the getter functions above
# Direct access to collections is no longer supported

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return get_user_manager().get_user_by_id(user_id)

def initialize_database():
    """Initialize the database with sample data if collections are empty"""
    try:
        ingredient_rules_col = get_ingredient_rules()
        
        recipes_col = get_recipes()
    except Exception as e:
        print(f"Error initializing database: {e}")
        return
    
    # Check if ingredient_rules collection is empty
    try:
        if ingredient_rules_col.count_documents({}) == 0:
            sample_rules = [
                {
                    "ingredient": "sugar",
                    "harmful_for": ["diabetes", "obesity"],
                    "alternative": "stevia",
                    "category": "sweetener"
                },
                {
                    "ingredient": "salt",
                    "harmful_for": ["hypertension", "heart_disease"],
                    "alternative": "low-sodium salt",
                    "category": "seasoning"
                },
                {
                    "ingredient": "flour",
                    "harmful_for": ["celiac", "gluten_intolerance"],
                    "alternative": "almond flour",
                    "category": "baking"
                },
                {
                    "ingredient": "butter",
                    "harmful_for": ["cholesterol", "heart_disease"],
                    "alternative": "olive oil",
                    "category": "fat"
                },
                {
                    "ingredient": "milk",
                    "harmful_for": ["lactose_intolerance"],
                    "alternative": "almond milk",
                    "category": "dairy"
                },
                {
                    "ingredient": "eggs",
                    "harmful_for": ["egg_allergy"],
                    "alternative": "flaxseed meal",
                    "category": "protein"
                },
                {
                    "ingredient": "peanuts",
                    "harmful_for": ["peanut_allergy"],
                    "alternative": "sunflower seeds",
                    "category": "nuts"
                },
                {
                    "ingredient": "soy",
                    "harmful_for": ["soy_allergy"],
                    "alternative": "coconut aminos",
                    "category": "protein"
                },
                {
                    "ingredient": "wheat",
                    "harmful_for": ["celiac", "gluten_intolerance"],
                    "alternative": "quinoa",
                    "category": "grain"
                },
                {
                    "ingredient": "corn",
                    "harmful_for": ["corn_allergy"],
                    "alternative": "rice",
                    "category": "grain"
                }
            ]
            ingredient_rules_col.insert_many(sample_rules)
            print("Sample ingredient rules added to database")
    except Exception as e:
        print(f"Error adding sample ingredient rules: {e}")
    
    # Check if patients collection is empty
    

    # Seed sample recipes if empty
    try:
        if recipes_col.count_documents({}) == 0:
            sample_recipes = [
                {
                    "name": "banana bread",
                    "ingredients": ["flour", "banana", "sugar", "butter", "eggs"],
                    "tags": ["dessert", "bread"]
                },
                {
                    "name": "pancakes",
                    "ingredients": ["flour", "milk", "eggs", "butter", "salt", "sugar"],
                    "tags": ["breakfast"]
                },
                {
                    "name": "peanut stir fry",
                    "ingredients": ["soy", "peanuts", "salt", "corn", "butter"],
                    "tags": ["dinner"]
                },
                {
                    "name": "bread",
                    "ingredients": ["flour", "water", "yeast", "salt"],
                    "tags": ["bread", "basic"]
                },
                {
                    "name": "puran poli",
                    "ingredients": ["wheat flour", "chana dal", "jaggery", "ghee", "cardamom", "turmeric", "salt"],
                    "tags": ["indian", "sweet", "festive"]
                }
            ]
            recipes_col.insert_many(sample_recipes)
            print("Sample recipes added to database")
    except Exception as e:
        print(f"Error adding sample recipes: {e}")
    except Exception as e:
        print(f"Error in initialize_database: {e}")

def ensure_core_ingredients():
    """Ensure critical common ingredients exist (for autocomplete and matching)."""
    try:
        ingredient_rules_col = get_ingredient_rules()
        core_ingredients = [
            {
                "ingredient": "pasta",
                "harmful_for": ["celiac", "gluten_intolerance"],
                "alternative": "gluten-free pasta",
                "category": "grain"
            }
        ]
        for item in core_ingredients:
            try:
                ingredient_rules_col.update_one(
                    {"ingredient": item["ingredient"]},
                    {"$setOnInsert": item},
                    upsert=True
                )
            except Exception:
                # Best-effort; ignore failures in restricted environments
                pass
    except Exception as e:
        print(f"Error ensuring core ingredients: {e}")

def check_ingredients(ingredients, condition):
    """Check ingredients against patient condition and return harmful/safe lists.

    Optimized to perform a single batched MongoDB query instead of per-ingredient lookups.
    """
    harmful_ingredients = []
    safe_ingredients = []
    replacements = {}

    # Normalize and de-duplicate for query
    normalized = [ingredient.strip().lower() for ingredient in ingredients if ingredient and ingredient.strip()]
    unique_ingredients = list({i for i in normalized})

    if unique_ingredients:
        try:
            cursor = get_ingredient_rules().find({"ingredient": {"$in": unique_ingredients}}, {"ingredient": 1, "harmful_for": 1, "alternative": 1, "_id": 0})
            # Use .get() to prevent KeyError if document structure is unexpected
            rules_by_ingredient = {doc.get("ingredient"): doc for doc in cursor if doc.get("ingredient")}
        except Exception as e:
            print(f"Error querying ingredient rules: {e}")
            rules_by_ingredient = {}
    else:
        rules_by_ingredient = {}

    for ingredient in normalized:
        rule = rules_by_ingredient.get(ingredient)
        if rule and condition in rule.get("harmful_for", []):
            harmful_ingredients.append(ingredient)
            replacements[ingredient] = rule.get("alternative")
        else:
            safe_ingredients.append(ingredient)

    return harmful_ingredients, safe_ingredients, replacements

def format_recipe_html(recipe_text):
    """Convert markdown recipe text to formatted HTML"""
    if not recipe_text:
        return "<p class='text-muted'>No recipe instructions available.</p>"
    
    html_parts = []
    lines = recipe_text.split('\n')
    current_section = ''
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('**') and line.endswith('**'):
            # Header
            if current_content:
                html_parts.append(render_current_section(current_section, current_content))
            header_text = line.replace('**', '').strip()
            
            html_parts.append(f'<h6 class="text-success fw-bold mb-2">{header_text}</h6>')
            
            current_section = ''
            current_content = []
        elif line.startswith('*') and line.endswith('*'):
            # Italic text
            if current_section != 'italic':
                if current_content:
                    html_parts.append(render_current_section(current_section, current_content))
                current_section = 'italic'
                current_content = []
            italic_text = line.replace('*', '').strip()
            html_parts.append(f'<strong><em class="text-success fw-light mb-2">{italic_text}</em></strong>')
        elif line.startswith('- ') or line.startswith('* '):
            # List item
            if current_section != 'list':
                if current_content:
                    html_parts.append(render_current_section(current_section, current_content))
                current_section = 'list'
                current_content = []
            clean_item = line.replace('- ', '').replace('* ', '').replace('**', '').strip()
            current_content.append(clean_item)
            
        elif any(line.startswith(f"{i}.") for i in range(1, 10)):
            # Numbered list item
            if current_section != 'numbered':
                if current_content:
                    html_parts.append(render_current_section(current_section, current_content))
                current_section = 'numbered'
                current_content = []
            clean_item = line.split('.', 1)[1].replace('**', '').strip()
            current_content.append(clean_item)
            
        else:
            # Regular text
            if current_section in ['list', 'numbered']:
                html_parts.append(render_current_section(current_section, current_content))
                current_section = 'text'
                current_content = []
            current_content.append(line.replace('**', '').strip())
    
    # Render final section
    if current_content:
        html_parts.append(render_current_section(current_section, current_content))
    
    return '\n'.join(html_parts)

def render_current_section(section_type, content):
    """Render the current section based on its type"""
    if section_type == 'list':
        items_html = []
        for item in content:
            items_html.append(f'<li class="mb-1"><i class="fas fa-check-circle text-success me-2"></i>{item}</li>')
        return f'<ul class="list-unstyled ms-3 mb-3">{"".join(items_html)}</ul>'
    elif section_type == 'numbered':
        items_html = []
        for item in content:
            items_html.append(f'<li class="mb-2">{item}</li>')
        return f'<ol class="ms-3 mb-3">{"".join(items_html)}</ol>'
    else:
        return f'<p class="mb-3 lh-base">{" ".join(content)}</p>'

def generate_recipe(original_ingredients, safe_ingredients, replacements, condition):
    """Generate a modified recipe based on safe ingredients using Gemini API"""
    
    # Create modified ingredient list
    modified_ingredients = []
    for ingredient in original_ingredients:
        ingredient = ingredient.strip().lower()
        if ingredient in replacements:
            modified_ingredients.append(replacements[ingredient])
        else:
            modified_ingredients.append(ingredient)
    
    # Get harmful ingredients for Gemini
    harmful_ingredients = list(replacements.keys())
    
    # Use Gemini API to generate detailed recipe
    recipe = gemini_service.generate_recipe_instructions(
        original_ingredients, 
        modified_ingredients, 
        condition, 
        harmful_ingredients
    )
    
    return recipe

def _reports_dir():
    """Return a writable reports directory (handles Vercel /tmp)."""
    # Check if we're on Vercel (serverless environment)
    # Vercel sets VERCEL=1 or we can check if /tmp exists and is writable
    is_vercel = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') is not None
    if is_vercel:
        base_dir = '/tmp/reports'
    else:
        base_dir = 'reports'
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def generate_pdf_report(user_id):
    print(f"[DEBUG] Generating PDF report... {user_id}")
    # make pdf report for user
    try:
        # print(f"[DEBUG] Fetching food entries for user {user_id}...")
        entries = list(get_food_entries().find({"patient_id": user_id}).sort("timestamp", -1))
        print(f"[DEBUG] Entries fetched: {len(entries)}")
        if not entries:
            return None
        filename = os.path.join(_reports_dir(), f"patient_{user_id}_report.pdf")
        doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = getSampleStyleSheet()
        report = []
        for entry in entries:
            timestamp = entry.get("timestamp")
            formatted_time = timestamp.strftime('%B %d, %Y at %I:%M %p') if timestamp else "N/A"
            report.append(Paragraph("Health-Aware Recipe Modifier Report", styles['Title']))
            # horizontal line
            report.append(Paragraph("-" * 136, styles['Normal']))
            report.append(Spacer(1, 6))
            report.append(Paragraph(f"Date: {formatted_time}", styles['Heading4']))
            report.append(Spacer(1, 6))
            
            report.append(Paragraph("Input Ingredients:", styles['Heading5']))
            input_ingredients = ', '.join(entry.get("input_ingredients", []))
            report.append(Paragraph(input_ingredients, styles['Normal']))
                
            harmful = ', '.join(entry.get("harmful", [])) or "None"
            safe = ', '.join(entry.get("safe", [])) or "None"
            report.append(Paragraph(f"Harmful Ingredients:", styles['Heading5']))
            report.append(Paragraph(f"{harmful}", styles['Normal']))
            
            report.append(Paragraph(f"Safe Ingredients: ", styles['Heading5']))
            report.append(Paragraph(f"{safe}", styles['Normal']))
            report.append(Spacer(1, 12))
            
            report.append(Paragraph("Modified Recipe Instructions:", styles['Heading5']))
            recipe_text = entry.get("recipe", "No recipe available.")
            for line in recipe_text.split('\n'):
                report.append(Paragraph(line, styles['Normal']))
                report.append(Spacer(1, 6))
            
            report.append(Spacer(1, 24))
        doc.build(report)
        print(f"PDF report generated for user {user_id}: {filename}")
        return filename
    except Exception as e:
        print(f"Error generating PDF report: {e}")
        return None
    
    
@app.route('/')
def landing_page():
    """Landing page for the application"""
    return render_template('landing_page.html')

@app.route('/app')
def index():
    """Main page with ingredient submission form"""
    return render_template('index.html')

@app.route('/check_ingredients', methods=['POST'])
def check_ingredients_route():
    """Process ingredient submission and return results"""
    
    ingredients_text = request.form.get('ingredients', '').strip()
    condition = request.form.get('condition', '').strip()
    
    # Validate ingredients input
    if not ingredients_text:
        flash('Please enter at least one ingredient.', 'error')
        return redirect(url_for('index'))
    
    # Validate ingredients length (prevent abuse)
    if len(ingredients_text) > 2000:
        flash('Ingredients text is too long. Please limit to 2000 characters.', 'error')
        return redirect(url_for('index'))
    
    # Validate condition
    if not condition:
        # For authenticated users, use their stored condition
        if current_user.is_authenticated and current_user.medical_condition:
            condition = current_user.medical_condition
        else:
            flash('Please select a medical condition.', 'error')
            return redirect(url_for('index'))
    
    # Parse ingredients
    ingredients = [ingredient.strip() for ingredient in ingredients_text.split(',') if ingredient.strip()]
    
    # For authenticated users, use their stored condition if none provided
    if current_user.is_authenticated and not condition:
        condition = current_user.medical_condition or 'diabetes'
    
    # Check ingredients
    harmful, safe, replacements = check_ingredients(ingredients, condition)

    # Create modified ingredients list
    modified_ingredients = []
    for ingredient in ingredients:
        ingredient_lower = ingredient.strip().lower()
        if ingredient_lower in replacements:
            modified_ingredients.append(replacements[ingredient_lower])
        else:
            modified_ingredients.append(ingredient)

    # Try to serve from cache first to avoid a slow LLM call
    ingredients_key = ",".join(sorted([i.strip().lower() for i in modified_ingredients if i and i.strip()]))
    try:
        cached_doc = get_generated_recipes().find_one({"condition": condition, "ingredients_key": ingredients_key}, {"recipe": 1, "_id": 0})
        if cached_doc and cached_doc.get("recipe"):
            recipe = cached_doc["recipe"]
        else:
            # Generate modified recipe via Gemini
            recipe = generate_recipe(ingredients, safe, replacements, condition)
            try:
                get_generated_recipes().update_one(
                    {"condition": condition, "ingredients_key": ingredients_key},
                    {"$set": {"recipe": recipe, "updated_at": datetime.now()}},
                    upsert=True
                )
            except Exception:
                # Caching is best-effort; ignore failures
                pass
    except Exception as e:
        print(f"Error checking cache: {e}")
        # Generate modified recipe via Gemini
        recipe = generate_recipe(ingredients, safe, replacements, condition)
    
    # Store in database
    if current_user.is_authenticated:
        patient_id = current_user.user_id
        food_entry = {
            "patient_id": patient_id,
            "condition": condition,
            "input_ingredients": ingredients,
            "harmful": harmful,
            "safe": modified_ingredients,
            "recipe": recipe,
            "timestamp": datetime.now()
        }
        
        try:
            get_food_entries().insert_one(food_entry)
        except Exception as e:
            print(f"Error storing food entry: {e}")
    
    # Format recipe for better display and sanitize HTML to prevent XSS
    formatted_recipe = sanitize_html(format_recipe_html(recipe))
    
    return render_template('result.html', 
                         harmful=harmful, 
                         safe=modified_ingredients, 
                         recipe=formatted_recipe,
                         original_ingredients=ingredients,
                         condition=condition,
                         moment=datetime.now().strftime('%B %d, %Y at %I:%M %p'))

@app.route('/generate_report/<patient_id>')
@login_required
def generate_report(patient_id):
    """Generate and download PDF report"""
    if str(current_user.user_id) != str(patient_id):
        abort(403)
    filename = generate_pdf_report(patient_id)
    
    if filename and os.path.exists(filename):
        return send_file(filename, as_attachment=True, download_name=f"patient_{patient_id}_report.pdf")
    else:
        return "Report generation failed", 400

@app.route('/view_report/<patient_id>')
@login_required
def view_report(patient_id):
    """View PDF report in browser"""
    if str(current_user.user_id) != str(patient_id):
        abort(403)
    filename = generate_pdf_report(patient_id)
    if filename and os.path.exists(filename):
        return send_file(filename, mimetype='application/pdf')
    else:
        return "Report generation failed", 400

@app.route('/api/ingredients')
def get_ingredients():
    """API endpoint to get all available ingredients"""
    try:
        ingredients = list(get_ingredient_rules().find({}, {"ingredient": 1, "category": 1, "_id": 0}))
        return jsonify(ingredients)
    except Exception as e:
        print(f"Error getting ingredients: {e}")
        return jsonify([])

@app.route('/api/recipes/ingredients')
def get_recipe_ingredients():
    """API endpoint to get ingredients list by recipe name"""
    name = request.args.get('name', '')
    if not name:
        return jsonify({"error": "Missing recipe name"}), 400
    try:
        # Try exact case-insensitive match first
        recipe_doc = get_recipes().find_one({"name": {"$regex": f"^{name.strip()}$", "$options": "i"}})
        if not recipe_doc:
            # Fallback to partial case-insensitive contains match
            recipe_doc = get_recipes().find_one({"name": {"$regex": name.strip(), "$options": "i"}})
        if not recipe_doc:
            return jsonify({"ingredients": []})
        return jsonify({"ingredients": recipe_doc.get("ingredients", [])})
    except Exception as e:
        print(f"Error getting recipe ingredients: {e}")
        return jsonify({"ingredients": []})

@app.route('/api/ai/extract-ingredients', methods=['POST'])
def ai_extract_ingredients():
    """Use Gemini to extract ingredients from a recipe name or free text.

    Body: { "text": "..." }
    Returns: { ingredients: [ ... ] }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        # print(f"Data : {data}")
        text = (data.get('text'))
        # print(f"Text : {text}")
        if not text:
            return jsonify({"ingredients": []}), 200

        # 1) Try AI extraction first
        ai_items = gemini_service.extract_ingredients(text) or []
        ai_items_normalized = [i.strip().lower() for i in ai_items if i and i.strip()]
        input_normalized = text.lower()

        # If AI returned a meaningful list (not just echoing the input), use it
        if ai_items_normalized and not (len(ai_items_normalized) == 1 and ai_items_normalized[0] == input_normalized):
            return jsonify({"ingredients": ai_items_normalized}), 200

        # 2) Fallback to recipes DB lookup by name (exact, then partial)
        try:
            recipe_doc = get_recipes().find_one({"name": {"$regex": f"^{text}$", "$options": "i"}})
            if not recipe_doc:
                recipe_doc = get_recipes().find_one({"name": {"$regex": text, "$options": "i"}})
            if recipe_doc:
                return jsonify({"ingredients": recipe_doc.get("ingredients", [])}), 200
        except Exception as e:
            print(f"Error looking up recipe: {e}")

        # 3) External recipe API fallback (TheMealDB)
        try:
            api_url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={requests.utils.quote(text)}"
            resp = requests.get(api_url, timeout=6)
            if resp.ok:
                payload = resp.json() or {}
                meals = payload.get("meals") or []
                if meals:
                    first = meals[0]
                    api_ingredients = []
                    for idx in range(1, 21):
                        val = (first.get(f"strIngredient{idx}") or "").strip()
                        if val:
                            api_ingredients.append(val.lower())
                    if api_ingredients:
                        return jsonify({"ingredients": api_ingredients}), 200
        except Exception:
            pass

        # 4) Last resort: parse comma-separated list; avoid echoing single term
        guessed = [t.strip().lower() for t in text.split(',') if t.strip()]
        if len(guessed) > 1:
            return jsonify({"ingredients": guessed}), 200

        # 5) Heuristic defaults for common single-term dishes
        defaults = {
            "pasta": ["pasta", "olive oil", "garlic", "salt", "water"],
            "pizza": ["pizza dough", "tomato sauce", "mozzarella", "olive oil", "salt"],
            "salad": ["lettuce", "tomato", "cucumber", "olive oil", "salt"],
            "sandwich": ["bread", "lettuce", "tomato", "cheese", "mayonnaise"],
        }
        if input_normalized in defaults:
            return jsonify({"ingredients": defaults[input_normalized]}), 200

        # Nothing reliable
        return jsonify({"ingredients": []}), 200
    except Exception as e:
        print(f"AI extract ingredients error: {e}")
        return jsonify({"ingredients": []}), 200

@app.route('/api/conditions')
def get_conditions():
    """API endpoint to get all available conditions"""
    try:
        pipeline = [
            {"$unwind": "$harmful_for"},
            {"$group": {"_id": "$harmful_for"}},
            {"$sort": {"_id": 1}}
        ]
        conditions = list(get_ingredient_rules().aggregate(pipeline))
        return jsonify([condition["_id"] for condition in conditions])
    except Exception as e:
        print(f"Error getting conditions: {e}")
        return jsonify([])

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute", error_message="Too many registration attempts. Please try again later.")
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user, error = get_user_manager().create_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            medical_condition=form.medical_condition.data if form.medical_condition.data else None
        )
        
        if user:
            login_user(user)
            flash('Account created successfully! Welcome to Health-Aware Recipe Modifier.', 'success')
            return redirect(url_for('index'))
        else:
            flash(error, 'error')
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", error_message="Too many login attempts. Please try again later.")
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to find user by username or email
        user = get_user_manager().get_user_by_username(form.username.data)
        if not user:
            user = get_user_manager().get_user_by_email(form.username.data)
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            get_user_manager().update_last_login(user.user_id)
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(url_for('index'))
        else:
            flash('Invalid username/email or password.', 'error')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    try:
        # Get user statistics
        user_entries = list(get_food_entries().find({"patient_id": current_user.user_id}))
        total_entries = len(user_entries)
        
        total_harmful = sum(len(entry.get('harmful', [])) for entry in user_entries)
        total_safe = sum(len(entry.get('safe', [])) for entry in user_entries)
        
        # Get recent entries
        recent_entries = list(get_food_entries().find({"patient_id": current_user.user_id})
                             .sort("timestamp", -1).limit(10))
    except Exception as e:
        print(f"Error getting user profile data: {e}")
        user_entries = []
        total_entries = 0
        total_harmful = 0
        total_safe = 0
        recent_entries = []
    
    # Create forms
    profile_form = ProfileUpdateForm()
    password_form = ChangePasswordForm()
    
    # Set current values
    profile_form.email.data = current_user.email
    profile_form.medical_condition.data = current_user.medical_condition
    
    return render_template('profile.html', 
                         profile_form=profile_form,
                         password_form=password_form,
                         total_entries=total_entries,
                         harmful_ingredients=total_harmful,
                         safe_ingredients=total_safe,
                         recent_entries=recent_entries)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    form = ProfileUpdateForm()
    if form.validate_on_submit():
        try:
            # Update user data
            get_user_manager().update_medical_condition(current_user.user_id, form.medical_condition.data)
            
            # Update email if changed
            if form.email.data != current_user.email:
                # Check if email is already taken
                existing_user = get_user_manager().get_user_by_email(form.email.data)
                if existing_user and existing_user.user_id != current_user.user_id:
                    flash('Email address is already in use.', 'error')
                    return redirect(url_for('profile'))
                
                # Update email
                get_user_manager().users.update_one(
                    {'user_id': current_user.user_id},
                    {'$set': {'email': form.email.data}}
                )
        except Exception as e:
            print(f"Error updating profile: {e}")
            flash('Error updating profile. Please try again.', 'error')
            return redirect(url_for('profile'))
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    flash('Please correct the errors below.', 'error')
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        try:
            if current_user.check_password(form.current_password.data):
                # Update password
                current_user.set_password(form.new_password.data)
                get_user_manager().users.update_one(
                    {'user_id': current_user.user_id},
                    {'$set': {'password_hash': current_user.password_hash}}
                )
                flash('Password changed successfully!', 'success')
            else:
                flash('Current password is incorrect.', 'error')
        except Exception as e:
            print(f"Error changing password: {e}")
            flash('Error changing password. Please try again.', 'error')
    
    return redirect(url_for('profile'))

if __name__ == '__main__':
    # Initialize database on startup (only for local development)
    # On Vercel, initialization happens lazily on first request
    initialize_database()
    ensure_core_ingredients()
    
    # Create reports directory
    os.makedirs("reports", exist_ok=True)
    
    app.run()
