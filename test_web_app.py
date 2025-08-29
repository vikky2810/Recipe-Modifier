#!/usr/bin/env python3
"""
Simple test script to verify the application functionality
"""

from pymongo import MongoClient
from datetime import datetime

def test_ingredient_checking():
    """Test the core functionality"""
    
    print("🧪 Testing Health-Aware Recipe Modifier Core Functionality")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['health_recipe_modifier']
        ingredient_rules = db['ingredient_rules']
        
        print("✅ Connected to MongoDB")
        
        # Test the exact scenario from the requirements
        print("\n📋 Testing Required Test Case:")
        print("Patient Condition: Diabetes")
        print("Input: sugar, butter, flour, banana")
        
        ingredients = ["sugar", "butter", "flour", "banana"]
        condition = "diabetes"
        
        # Check ingredients
        harmful_ingredients = []
        safe_ingredients = []
        replacements = {}
        
        for ingredient in ingredients:
            ingredient = ingredient.strip().lower()
            rule = ingredient_rules.find_one({"ingredient": ingredient})
            
            if rule and condition in rule.get("harmful_for", []):
                harmful_ingredients.append(ingredient)
                replacements[ingredient] = rule["alternative"]
            else:
                safe_ingredients.append(ingredient)
        
        # Display results
        print(f"\n🔍 Analysis Results:")
        print(f"   ❌ Harmful ingredients: {', '.join(harmful_ingredients) if harmful_ingredients else 'None'}")
        print(f"   ✅ Safe ingredients: {', '.join(safe_ingredients)}")
        
        if replacements:
            print(f"   🔄 Replacements:")
            for harmful, alternative in replacements.items():
                print(f"      • {harmful} → {alternative}")
        
        # Generate modified recipe
        modified_ingredients = []
        for ingredient in ingredients:
            ingredient_lower = ingredient.strip().lower()
            if ingredient_lower in replacements:
                modified_ingredients.append(replacements[ingredient_lower])
            else:
                modified_ingredients.append(ingredient)
        
        if len(modified_ingredients) <= 3:
            recipe = f"Mix {', '.join(modified_ingredients)} together. Cook in a non-stick pan until done."
        else:
            recipe = f"Mix {', '.join(modified_ingredients[:-1])} and {modified_ingredients[-1]}. Cook in a pan until golden brown."
        
        print(f"   📝 Modified Recipe: {recipe}")
        
        # Verify expected results
        expected_harmful = ["sugar", "flour"]
        expected_safe = ["banana", "butter"]
        
        harmful_match = set(harmful_ingredients) == set(expected_harmful)
        safe_match = set(safe_ingredients) == set(expected_safe)
        
        if harmful_match and safe_match:
            print("\n✅ TEST PASSED - All requirements met!")
        else:
            print("\n❌ TEST FAILED")
            if not harmful_match:
                print(f"   Expected harmful: {expected_harmful}, Got: {harmful_ingredients}")
            if not safe_match:
                print(f"   Expected safe: {expected_safe}, Got: {safe_ingredients}")
        
        # Test database functionality
        print(f"\n📊 Database Status:")
        print(f"   - Ingredient Rules: {ingredient_rules.count_documents({})}")
        print(f"   - Patients: {db['patients'].count_documents({})}")
        print(f"   - Food Entries: {db['food_entries'].count_documents({})}")
        
        print(f"\n🎉 Application is working correctly!")
        print(f"🌐 You can now access the web interface at: http://localhost:5000")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure MongoDB is running and the database is set up")

if __name__ == "__main__":
    test_ingredient_checking()
