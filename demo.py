#!/usr/bin/env python3
"""
Demo Script for Health-Aware Recipe Modifier
This script demonstrates the application functionality with sample data.
"""

from pymongo import MongoClient
from datetime import datetime
import os

def run_demo():
    """Run a demonstration of the application features"""
    
    print("🎬 Health-Aware Recipe Modifier - Demo")
    print("=" * 60)
    
    try:
        # Connect to MongoDB
        client = MongoClient('mongodb://localhost:27017/')
        db = client['health_recipe_modifier']
        ingredient_rules = db['ingredient_rules']
        
        print("✅ Connected to database")
        
        # Demo scenarios
        scenarios = [
            {
                "title": "🍰 Diabetes Patient Making Cake",
                "condition": "diabetes",
                "ingredients": ["sugar", "flour", "butter", "eggs", "milk"],
                "description": "A patient with diabetes wants to make a cake but needs to avoid sugar and flour."
            },
            {
                "title": "🥖 Hypertension Patient Making Bread",
                "condition": "hypertension",
                "ingredients": ["salt", "flour", "yeast", "butter", "water"],
                "description": "A patient with hypertension needs to reduce salt and butter in their bread recipe."
            },
            {
                "title": "🥞 Celiac Patient Making Pancakes",
                "condition": "celiac",
                "ingredients": ["wheat", "flour", "milk", "eggs", "sugar"],
                "description": "A patient with celiac disease needs gluten-free alternatives for their pancakes."
            },
            {
                "title": "🥛 Lactose Intolerant Patient Making Smoothie",
                "condition": "lactose_intolerance",
                "ingredients": ["milk", "banana", "strawberries", "honey", "yogurt"],
                "description": "A lactose intolerant patient wants to make a smoothie without dairy products."
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n📋 Scenario {i}: {scenario['title']}")
            print(f"   {scenario['description']}")
            print(f"   Medical Condition: {scenario['condition'].replace('_', ' ').title()}")
            print(f"   Original Ingredients: {', '.join(scenario['ingredients'])}")
            
            # Analyze ingredients
            harmful = []
            safe = []
            replacements = {}
            
            for ingredient in scenario['ingredients']:
                ingredient_lower = ingredient.strip().lower()
                rule = ingredient_rules.find_one({"ingredient": ingredient_lower})
                
                if rule and scenario['condition'] in rule.get("harmful_for", []):
                    harmful.append(ingredient)
                    replacements[ingredient_lower] = rule["alternative"]
                else:
                    safe.append(ingredient)
            
            # Display results
            print(f"\n   🔍 Analysis Results:")
            if harmful:
                print(f"   ❌ Harmful ingredients: {', '.join(harmful)}")
                print(f"   🔄 Suggested replacements:")
                for harmful_ingredient in harmful:
                    harmful_lower = harmful_ingredient.lower()
                    if harmful_lower in replacements:
                        print(f"      • {harmful_ingredient} → {replacements[harmful_lower]}")
            else:
                print(f"   ✅ All ingredients are safe!")
            
            print(f"   ✅ Safe ingredients: {', '.join(safe)}")
            
            # Generate modified recipe
            modified_ingredients = []
            for ingredient in scenario['ingredients']:
                ingredient_lower = ingredient.strip().lower()
                if ingredient_lower in replacements:
                    modified_ingredients.append(replacements[ingredient_lower])
                else:
                    modified_ingredients.append(ingredient)
            
            # Create recipe based on ingredients
            if "cake" in scenario['title'].lower():
                recipe = f"Mix {', '.join(modified_ingredients[:-1])} and {modified_ingredients[-1]}. Pour into a greased pan and bake at 350°F for 25-30 minutes."
            elif "bread" in scenario['title'].lower():
                recipe = f"Combine {', '.join(modified_ingredients[:-1])} and {modified_ingredients[-1]}. Knead dough, let rise, then bake at 375°F for 45 minutes."
            elif "pancakes" in scenario['title'].lower():
                recipe = f"Mix {', '.join(modified_ingredients[:-1])} and {modified_ingredients[-1]}. Cook on a hot griddle until golden brown on both sides."
            elif "smoothie" in scenario['title'].lower():
                recipe = f"Blend {', '.join(modified_ingredients[:-1])} and {modified_ingredients[-1]} until smooth. Serve immediately."
            else:
                recipe = f"Combine {', '.join(modified_ingredients[:-1])} and {modified_ingredients[-1]}. Mix well and cook until done."
            
            print(f"   📝 Modified Recipe: {recipe}")
            
            # Store in database
            food_entry = {
                "patient_id": str(i),
                "condition": scenario['condition'],
                "input_ingredients": scenario['ingredients'],
                "harmful": harmful,
                "safe": modified_ingredients,
                "recipe": recipe,
                "timestamp": datetime.now()
            }
            
            db['food_entries'].insert_one(food_entry)
            print(f"   💾 Saved to database")
        
        # Show database statistics
        print(f"\n📊 Final Database Statistics:")
        print(f"   - Ingredient Rules: {ingredient_rules.count_documents({})}")
        print(f"   - Patients: {db['patients'].count_documents({})}")
        print(f"   - Food Entries: {db['food_entries'].count_documents({})}")
        
        # Show available ingredients and conditions
        print(f"\n🔧 Available Ingredients:")
        ingredients = list(ingredient_rules.find({}, {"ingredient": 1, "category": 1}))
        for ingredient in ingredients:
            print(f"   • {ingredient['ingredient']} ({ingredient['category']})")
        
        print(f"\n🏥 Supported Medical Conditions:")
        pipeline = [
            {"$unwind": "$harmful_for"},
            {"$group": {"_id": "$harmful_for"}},
            {"$sort": {"_id": 1}}
        ]
        conditions = list(ingredient_rules.aggregate(pipeline))
        for condition in conditions:
            print(f"   • {condition['_id'].replace('_', ' ').title()}")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"💡 You can now run the web application with: python app.py")
        print(f"🌐 The application will be available at: http://localhost:5000")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Make sure MongoDB is running and the database is set up")

if __name__ == "__main__":
    run_demo()
