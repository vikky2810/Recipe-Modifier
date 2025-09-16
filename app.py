from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from pymongo import MongoClient
from datetime import datetime
import os
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

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# MongoDB Configuration
client = MongoClient(Config.MONGODB_URI)
db = client[Config.DATABASE_NAME]

# Initialize collections
ingredient_rules = db['ingredient_rules']
food_entries = db['food_entries']
patients = db['patients']
recipes = db['recipes']
generated_recipes = db['generated_recipes']

# Ensure indexes for fast lookups
try:
    ingredient_rules.create_index('ingredient', unique=True)
    generated_recipes.create_index([('condition', 1), ('ingredients_key', 1)])
except Exception:
    # Index creation is best-effort; ignore if permissions/environment restrict this
    pass

# Initialize User Manager
user_manager = UserManager(db)

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return user_manager.get_user_by_id(user_id)

def initialize_database():
    """Initialize the database with sample data if collections are empty"""
    
    # Check if ingredient_rules collection is empty
    if ingredient_rules.count_documents({}) == 0:
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
        ingredient_rules.insert_many(sample_rules)
        print("Sample ingredient rules added to database")
    
    # Check if patients collection is empty
    if patients.count_documents({}) == 0:
        sample_patient = {
            "patient_id": "1",
            "name": "John Doe",
            "condition": "diabetes",
            "email": "john.doe@example.com"
        }
        patients.insert_one(sample_patient)
        print("Sample patient added to database")

    # Seed sample recipes if empty
    if recipes.count_documents({}) == 0:
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
        recipes.insert_many(sample_recipes)
        print("Sample recipes added to database")

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
        cursor = ingredient_rules.find({"ingredient": {"$in": unique_ingredients}}, {"ingredient": 1, "harmful_for": 1, "alternative": 1, "_id": 0})
        rules_by_ingredient = {doc["ingredient"]: doc for doc in cursor}
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
    base_dir = os.environ.get('VERCEL') and '/tmp/reports' or 'reports'
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def generate_pdf_report(patient_id):
    """Generate PDF report for a patient with improved formatting"""
    
    # Get patient info - try users collection first, then patients collection
    patient = None
    
    # First try to find user in users collection
    user = user_manager.get_user_by_id(patient_id)
    if user:
        patient = {
            "patient_id": user.user_id,
            "name": user.username,
            "condition": user.medical_condition or "Not specified",
            "email": user.email
        }
    else:
        # Fallback to patients collection for backward compatibility
        patient = patients.find_one({"patient_id": patient_id})
    
    if not patient:
        return None
    
    # Get all food entries for the patient
    entries = list(food_entries.find({"patient_id": patient_id}).sort("timestamp", -1))
    
    # Create PDF
    reports_dir = _reports_dir()
    filename = os.path.join(reports_dir, f"patient_{patient_id}_report.pdf")
    
    doc = SimpleDocTemplate(filename, pagesize=letter, 
                          leftMargin=0.75*inch, rightMargin=0.75*inch,
                          topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles for better formatting
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=1,  # Center alignment
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.darkgreen
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        leftIndent=20
    )
    
    recipe_style = ParagraphStyle(
        'RecipeStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        leftIndent=15,
        rightIndent=15,
        alignment=0,  # Left alignment
        leading=14  # Line spacing
    )
    
    # Title
    story.append(Paragraph("Health-Aware Recipe Modifier Report", title_style))
    story.append(Spacer(1, 15))
    
    # Patient Information Section
    story.append(Paragraph("Patient Information", subtitle_style))
    story.append(Paragraph(f"<b>Name:</b> {patient['name']}", info_style))
    story.append(Paragraph(f"<b>Medical Condition:</b> {patient['condition'].replace('_', ' ').title()}", info_style))
    story.append(Paragraph(f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", info_style))
    story.append(Spacer(1, 15))
    
    # Summary Statistics
    if entries:
        story.append(Paragraph("Summary Statistics", subtitle_style))
        total_entries = len(entries)
        total_harmful = sum(len(entry.get('harmful', [])) for entry in entries)
        story.append(Paragraph(f"<b>Total Food Entries:</b> {total_entries}", info_style))
        story.append(Paragraph(f"<b>Total Harmful Ingredients Detected:</b> {total_harmful}", info_style))
        story.append(Paragraph(f"<b>Average Harmful Ingredients per Entry:</b> {total_harmful/total_entries:.1f}", info_style))
        story.append(Spacer(1, 15))
    
    # Food Entries Section
    if entries:
        story.append(Paragraph("Detailed Food Entries History", subtitle_style))
        story.append(Spacer(1, 10))
        
        for i, entry in enumerate(entries, 1):
            # Entry header
            entry_date = entry['timestamp'].strftime('%B %d, %Y at %I:%M %p')
            story.append(Paragraph(f"<b>Entry #{i} - {entry_date}</b>", info_style))
            
            # Original ingredients
            original_ingredients = ', '.join(entry['input_ingredients'])
            story.append(Paragraph(f"<b>Original Ingredients:</b> {original_ingredients}", recipe_style))
            
            # Harmful ingredients
            harmful_list = entry.get('harmful', [])
            if harmful_list:
                harmful_text = ', '.join(harmful_list)
                story.append(Paragraph(f"<b>⚠️ Harmful Ingredients:</b> {harmful_text}", recipe_style))
            else:
                story.append(Paragraph("<b>✅ No harmful ingredients detected</b>", recipe_style))
            
            # Safe alternatives
            safe_ingredients = ', '.join(entry['safe'])
            story.append(Paragraph(f"<b>✅ Safe Ingredients:</b> {safe_ingredients}", recipe_style))
            
            # Recipe
            recipe_text = entry['recipe']
            # Truncate long recipes to prevent overflow
            if len(recipe_text) > 300:
                recipe_text = recipe_text[:297] + "..."
            story.append(Paragraph(f"<b>📝 Modified Recipe:</b> {recipe_text}", recipe_style))
            
            # Add separator between entries
            if i < len(entries):
                story.append(Spacer(1, 10))
                story.append(Paragraph("<hr/>", styles['Normal']))
                story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("No food entries found for this patient.", info_style))
    
    # Footer
    story.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=1,  # Center alignment
        textColor=colors.grey
    )
    story.append(Paragraph("Generated by Health-Aware Recipe Modifier System", footer_style))
    story.append(Paragraph("For medical advice, always consult with your healthcare provider", footer_style))
    
    # Build PDF
    try:
        doc.build(story)
        return filename
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

@app.route('/')
def index():
    """Main page with ingredient submission form"""
    return render_template('index.html')

@app.route('/check_ingredients', methods=['POST'])
def check_ingredients_route():
    """Process ingredient submission and return results"""
    
    ingredients_text = request.form.get('ingredients', '')
    condition = request.form.get('condition', '')
    
    if not ingredients_text or not condition:
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
    cached_doc = generated_recipes.find_one({"condition": condition, "ingredients_key": ingredients_key}, {"recipe": 1, "_id": 0})
    if cached_doc and cached_doc.get("recipe"):
        recipe = cached_doc["recipe"]
    else:
        # Generate modified recipe via Gemini
        recipe = generate_recipe(ingredients, safe, replacements, condition)
        try:
            generated_recipes.update_one(
                {"condition": condition, "ingredients_key": ingredients_key},
                {"$set": {"recipe": recipe, "updated_at": datetime.now()}},
                upsert=True
            )
        except Exception:
            # Caching is best-effort; ignore failures
            pass
    
    # Store in database
    patient_id = current_user.user_id if current_user.is_authenticated else "1"
    food_entry = {
        "patient_id": patient_id,
        "condition": condition,
        "input_ingredients": ingredients,
        "harmful": harmful,
        "safe": modified_ingredients,
        "recipe": recipe,
        "timestamp": datetime.now()
    }
    
    food_entries.insert_one(food_entry)
    
    # Format recipe for better display
    formatted_recipe = format_recipe_html(recipe)
    
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
    ingredients = list(ingredient_rules.find({}, {"ingredient": 1, "category": 1, "_id": 0}))
    return jsonify(ingredients)

@app.route('/api/recipes/ingredients')
def get_recipe_ingredients():
    """API endpoint to get ingredients list by recipe name"""
    name = request.args.get('name', '')
    if not name:
        return jsonify({"error": "Missing recipe name"}), 400
    # Try exact case-insensitive match first
    recipe_doc = recipes.find_one({"name": {"$regex": f"^{name.strip()}$", "$options": "i"}})
    if not recipe_doc:
        # Fallback to partial case-insensitive contains match
        recipe_doc = recipes.find_one({"name": {"$regex": name.strip(), "$options": "i"}})
    if not recipe_doc:
        return jsonify({"ingredients": []})
    return jsonify({"ingredients": recipe_doc.get("ingredients", [])})

@app.route('/api/ai/extract-ingredients', methods=['POST'])
def ai_extract_ingredients():
    """Use Gemini to extract ingredients from a recipe name or free text.

    Body: { "text": "..." }
    Returns: { ingredients: [ ... ] }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get('text') or '').strip()
        if not text:
            return jsonify({"ingredients": []}), 200
        items = gemini_service.extract_ingredients(text)
        return jsonify({"ingredients": items}), 200
    except Exception as e:
        print(f"AI extract ingredients error: {e}")
        return jsonify({"ingredients": []}), 200

@app.route('/api/conditions')
def get_conditions():
    """API endpoint to get all available conditions"""
    pipeline = [
        {"$unwind": "$harmful_for"},
        {"$group": {"_id": "$harmful_for"}},
        {"$sort": {"_id": 1}}
    ]
    conditions = list(ingredient_rules.aggregate(pipeline))
    return jsonify([condition["_id"] for condition in conditions])

# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user, error = user_manager.create_user(
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
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to find user by username or email
        user = user_manager.get_user_by_username(form.username.data)
        if not user:
            user = user_manager.get_user_by_email(form.username.data)
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user_manager.update_last_login(user.user_id)
            
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
    # Get user statistics
    user_entries = list(food_entries.find({"patient_id": current_user.user_id}))
    total_entries = len(user_entries)
    
    total_harmful = sum(len(entry.get('harmful', [])) for entry in user_entries)
    total_safe = sum(len(entry.get('safe', [])) for entry in user_entries)
    
    # Get recent entries
    recent_entries = list(food_entries.find({"patient_id": current_user.user_id})
                         .sort("timestamp", -1).limit(10))
    
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
        # Update user data
        user_manager.update_medical_condition(current_user.user_id, form.medical_condition.data)
        
        # Update email if changed
        if form.email.data != current_user.email:
            # Check if email is already taken
            existing_user = user_manager.get_user_by_email(form.email.data)
            if existing_user and existing_user.user_id != current_user.user_id:
                flash('Email address is already in use.', 'error')
                return redirect(url_for('profile'))
            
            # Update email
            user_manager.users.update_one(
                {'user_id': current_user.user_id},
                {'$set': {'email': form.email.data}}
            )
        
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
        if current_user.check_password(form.current_password.data):
            # Update password
            current_user.set_password(form.new_password.data)
            user_manager.users.update_one(
                {'user_id': current_user.user_id},
                {'$set': {'password_hash': current_user.password_hash}}
            )
            flash('Password changed successfully!', 'success')
        else:
            flash('Current password is incorrect.', 'error')
    
    return redirect(url_for('profile'))

if __name__ == '__main__':
    # Initialize database on startup
    initialize_database()
    
    # Create reports directory
    os.makedirs("reports", exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
