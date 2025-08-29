# 🧠 Health-Aware Recipe Modifier

A full-stack web application that helps patients modify their recipes based on their medical conditions. The app automatically detects harmful ingredients and suggests healthy alternatives, generating personalized recipes tailored to specific health needs.

## 🎯 Features

### Core Functionality
- **Ingredient Analysis**: Automatically detects harmful ingredients based on medical conditions
- **Smart Replacements**: Suggests healthy alternatives for harmful ingredients
- **AI-Powered Recipe Generation**: Uses Gemini API to create detailed, personalized recipes
- **Enhanced PDF Reports**: Professional, well-formatted reports with summary statistics
- **User Authentication**: Secure registration, login, and profile management
- **Individual Data Storage**: Each user's data is stored separately and securely
- **Session Logging**: Stores all food entries in MongoDB for tracking
- **View & Download Reports**: Both view in browser and download functionality

### Supported Medical Conditions
- Diabetes
- Hypertension
- Heart Disease
- Celiac Disease
- Gluten Intolerance
- Lactose Intolerance
- Egg Allergy
- Peanut Allergy
- Soy Allergy
- Corn Allergy
- Obesity
- High Cholesterol

### Ingredient Database
The app includes a comprehensive database of ingredients with their health implications:
- **Sugar** → Stevia (for diabetes/obesity)
- **Salt** → Low-sodium salt (for hypertension/heart disease)
- **Flour** → Almond flour (for celiac/gluten intolerance)
- **Butter** → Olive oil (for cholesterol/heart disease)
- **Milk** → Almond milk (for lactose intolerance)
- And many more...

## 🏗 Technology Stack

- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Backend**: Python Flask
- **Database**: MongoDB with PyMongo
- **PDF Generation**: ReportLab with improved formatting
- **AI Integration**: Google Gemini API for recipe generation
- **Authentication**: Flask-Login with secure password hashing
- **Forms**: Flask-WTF with validation
- **Styling**: Custom CSS with Font Awesome icons

## 📁 Project Structure

```
project/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   ├── index.html        # Main ingredient submission page
│   └── result.html       # Results display page
├── static/
│   └── styles.css        # Custom CSS styles
├── reports/              # Generated PDF reports
└── database/             # MongoDB setup and data
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.7 or higher
- MongoDB (local installation or MongoDB Atlas)
- pip (Python package manager)

### Step 1: Clone/Download the Project
```bash
# If using git
git clone <repository-url>
cd Recipe-Modifier

# Or download and extract the project files
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Set Up MongoDB

#### Option A: Local MongoDB Installation
1. Download and install MongoDB Community Server from [mongodb.com](https://www.mongodb.com/try/download/community)
2. Start MongoDB service:
   ```bash
   # Windows
   net start MongoDB
   
   # macOS/Linux
   sudo systemctl start mongod
   ```

#### Option B: MongoDB Atlas (Cloud)
1. Create a free account at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a new cluster
3. Get your connection string
4. Update the connection string in `app.py`:
   ```python
   client = MongoClient('your-mongodb-atlas-connection-string')
   ```

### Step 4: Run the Application
```bash
python app.py
```

The application will be available at: `http://localhost:5000`

## 📖 Usage Guide

### 1. Create an Account (Optional but Recommended)
- Click "Register" in the top navigation
- Fill in your username, email, and password
- Optionally select your medical condition for better recommendations
- Click "Create Account" to register

### 2. Login to Your Account
- Click "Login" in the top navigation
- Enter your username/email and password
- Check "Remember Me" to stay logged in
- Click "Sign In"

### 3. Submit Ingredients
- Navigate to the main page
- Enter your ingredients separated by commas (e.g., "sugar, flour, butter, banana")
- Select your medical condition from the dropdown
- Click "Check Ingredients & Generate Recipe"

### 2. Review Results
The app will display:
- **Original Ingredients**: What you entered
- **Harmful Ingredients**: Ingredients that may be problematic for your condition
- **Safe Alternatives**: Healthy replacements for harmful ingredients
- **Modified Recipe**: Your personalized recipe with safe ingredients

### 4. Manage Your Profile
- Click "Profile" in the top navigation when logged in
- View your account information and activity statistics
- Update your email and medical condition
- Change your password
- View your recipe history

### 5. Generate Reports
- Click "Download Health Report" to generate a PDF
- The PDF includes all your food entries with analysis
- Perfect for sharing with healthcare providers

## 🧪 Test Cases

### Test Case 1: Diabetes Patient
**Input**: sugar, butter, flour, banana
**Expected Output**:
- ❌ Harmful: sugar, flour
- ✅ Replaced with: stevia, almond flour
- ✅ Safe: banana, butter (or olive oil)
- **Final Recipe**: "Mix almond flour, banana, stevia, olive oil. Cook in a pan until golden brown."

### Test Case 2: Hypertension Patient
**Input**: salt, butter, flour, eggs
**Expected Output**:
- ❌ Harmful: salt, butter
- ✅ Replaced with: low-sodium salt, olive oil
- ✅ Safe: flour, eggs
- **Final Recipe**: "Combine flour, eggs, low-sodium salt, olive oil. Mix well and cook until golden brown."

## 🔧 Configuration

### Database Configuration
The app automatically initializes the database with sample data on first run:
- Ingredient rules collection
- Sample patient data
- Food entries collection

### Customizing Ingredient Rules
To add new ingredients or modify existing rules, edit the `initialize_database()` function in `app.py`:

```python
{
    "ingredient": "new_ingredient",
    "harmful_for": ["condition1", "condition2"],
    "alternative": "healthy_alternative",
    "category": "category_name"
}
```

## 📊 API Endpoints

### GET `/api/ingredients`
Returns all available ingredients in the database.

### GET `/api/conditions`
Returns all supported medical conditions.

### POST `/check_ingredients`
Processes ingredient submission and returns analysis results.

### GET `/generate_report/<patient_id>`
Generates and downloads PDF report for a specific patient.

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment (Heroku)
1. Create a `Procfile`:
   ```
   web: python app.py
   ```
2. Set environment variables for MongoDB connection
3. Deploy to Heroku

### Production Deployment (Render)
1. Connect your repository to Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python app.py`
4. Configure environment variables

## 🔒 Security Notes

- This is a demonstration application
- No authentication system implemented
- Uses hardcoded patient ID for simplicity
- Always consult healthcare providers for medical advice
- The app is for educational purposes only

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is for educational purposes. Please consult healthcare professionals for medical advice.

## 🆘 Troubleshooting

### Common Issues

**MongoDB Connection Error**
- Ensure MongoDB is running
- Check connection string
- Verify network connectivity

**Port Already in Use**
- Change port in `app.py`: `app.run(debug=True, host='0.0.0.0', port=5001)`

**PDF Generation Fails**
- Ensure `reports/` directory exists
- Check write permissions
- Verify ReportLab installation

### Getting Help
- Check the console output for error messages
- Verify all dependencies are installed
- Ensure MongoDB is properly configured

## 🎉 Features Roadmap

- [x] User authentication system ✅
- [x] Multiple patient support ✅
- [ ] Recipe sharing functionality
- [ ] Nutritional information
- [ ] Mobile app version
- [ ] Integration with health APIs
- [ ] Advanced recipe generation AI

---

**⚠️ Disclaimer**: This application is for educational and demonstration purposes only. Always consult with qualified healthcare professionals for medical advice and dietary recommendations.
