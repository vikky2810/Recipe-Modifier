#!/usr/bin/env python3
"""
Test Script for Health-Aware Recipe Modifier
This script tests the core functionality of the application.
"""

from pymongo import MongoClient
from datetime import datetime

def test_ingredient_checking():
    """Test the ingredient checking functionality"""
    
    print("🧪 Testing Health-Aware Recipe Modifier")
    print("=" * 50)
    
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['health_recipe_modifier']
        ingredient_rules = db['ingredient_rules']
        
        print("✅ Connected to MongoDB")
        
        # Test cases
        test_cases = [
            {
                "name": "Diabetes Patient",
                "condition": "diabetes",
                "ingredients": ["sugar", "flour", "butter", "banana"],
                "expected_harmful": ["sugar", "flour"],
                "expected_safe": ["banana", "butter"]
            },
            {
                "name": "Hypertension Patient",
                "condition": "hypertension",
                "ingredients": ["salt", "butter", "flour", "eggs"],
                "expected_harmful": ["salt", "butter"],
                "expected_safe": ["flour", "eggs"]
            },
            {
                "name": "Celiac Patient",
                "condition": "celiac",
                "ingredients": ["wheat", "flour", "milk", "eggs"],
                "expected_harmful": ["wheat", "flour"],
                "expected_safe": ["milk", "eggs"]
            }
        ]
        
        # Run tests
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test {i}: {test_case['name']}")
            print(f"   Condition: {test_case['condition']}")
            print(f"   Ingredients: {', '.join(test_case['ingredients'])}")
            
            # Check ingredients
            harmful_ingredients = []
            safe_ingredients = []
            replacements = {}
            
            for ingredient in test_case['ingredients']:
                ingredient = ingredient.strip().lower()
                rule = ingredient_rules.find_one({"ingredient": ingredient})
                
                if rule and test_case['condition'] in rule.get("harmful_for", []):
                    harmful_ingredients.append(ingredient)
                    replacements[ingredient] = rule["alternative"]
                else:
                    safe_ingredients.append(ingredient)
            
            # Display results
            print(f"   ❌ Harmful: {', '.join(harmful_ingredients) if harmful_ingredients else 'None'}")
            print(f"   ✅ Safe: {', '.join(safe_ingredients)}")
            
            if replacements:
                print(f"   🔄 Replacements:")
                for harmful, alternative in replacements.items():
                    print(f"      {harmful} → {alternative}")
            
            # Generate recipe
            modified_ingredients = []
            for ingredient in test_case['ingredients']:
                ingredient_lower = ingredient.strip().lower()
                if ingredient_lower in replacements:
                    modified_ingredients.append(replacements[ingredient_lower])
                else:
                    modified_ingredients.append(ingredient)
            
            if len(modified_ingredients) <= 3:
                recipe = f"Mix {', '.join(modified_ingredients)} together. Cook in a non-stick pan until done."
            else:
                recipe = f"Combine {', '.join(modified_ingredients[:-1])} and {modified_ingredients[-1]}. Mix well and cook until golden brown."
            
            print(f"   📝 Recipe: {recipe}")
            
            # Verify test results
            harmful_match = set(harmful_ingredients) == set(test_case['expected_harmful'])
            safe_match = set(safe_ingredients) == set(test_case['expected_safe'])
            
            if harmful_match and safe_match:
                print("   ✅ Test PASSED")
            else:
                print("   ❌ Test FAILED")
                if not harmful_match:
                    print(f"      Expected harmful: {test_case['expected_harmful']}, Got: {harmful_ingredients}")
                if not safe_match:
                    print(f"      Expected safe: {test_case['expected_safe']}, Got: {safe_ingredients}")
        
        # Test database statistics
        print(f"\n📊 Database Statistics:")
        print(f"   - Total ingredient rules: {ingredient_rules.count_documents({})}")
        print(f"   - Total patients: {db['patients'].count_documents({})}")
        print(f"   - Total food entries: {db['food_entries'].count_documents({})}")
        
        # Test API endpoints
        print(f"\n🔗 Testing API Endpoints:")
        
        # Get all ingredients
        ingredients = list(ingredient_rules.find({}, {"ingredient": 1, "category": 1}))
        print(f"   - Available ingredients: {len(ingredients)}")
        
        # Get all conditions
        pipeline = [
            {"$unwind": "$harmful_for"},
            {"$group": {"_id": "$harmful_for"}},
            {"$sort": {"_id": 1}}
        ]
        conditions = list(ingredient_rules.aggregate(pipeline))
        condition_list = [condition["_id"] for condition in conditions]
        print(f"   - Supported conditions: {', '.join(condition_list)}")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        print("Make sure MongoDB is running and the database is set up")

if __name__ == "__main__":
    test_ingredient_checking()
