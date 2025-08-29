#!/usr/bin/env python3
"""
Test script to verify Gemini API integration
"""

from gemini_service import gemini_service

def test_gemini_integration():
    """Test Gemini API integration"""
    
    print("🧪 Testing Gemini API Integration")
    print("=" * 50)
    
    # Test recipe generation
    print("\n📝 Testing Recipe Generation:")
    
    original_ingredients = ["sugar", "flour", "butter", "banana"]
    modified_ingredients = ["stevia", "almond flour", "olive oil", "banana"]
    condition = "diabetes"
    harmful_ingredients = ["sugar", "flour"]
    
    try:
        recipe = gemini_service.generate_recipe_instructions(
            original_ingredients, 
            modified_ingredients, 
            condition, 
            harmful_ingredients
        )
        
        print("✅ Recipe generated successfully!")
        print(f"Recipe length: {len(recipe)} characters")
        print(f"Recipe preview: {recipe[:100]}...")
        
    except Exception as e:
        print(f"❌ Error generating recipe: {e}")
        print("Using fallback recipe generation")
    
    # Test health tips generation
    print("\n💡 Testing Health Tips Generation:")
    
    try:
        health_tips = gemini_service.generate_health_tips(condition, modified_ingredients)
        
        print("✅ Health tips generated successfully!")
        print(f"Tips length: {len(health_tips)} characters")
        print(f"Tips preview: {health_tips[:100]}...")
        
    except Exception as e:
        print(f"❌ Error generating health tips: {e}")
        print("Using fallback health tips")
    
    print("\n🎉 Gemini API integration test completed!")

if __name__ == "__main__":
    test_gemini_integration()
