import google.generativeai as genai
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        """Initialize Gemini API service"""
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini API service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {e}")
            self.model = None
    
    def generate_recipe_instructions(self, original_ingredients, modified_ingredients, condition, harmful_ingredients=None):
        """
        Generate detailed recipe instructions using Gemini API
        
        Args:
            original_ingredients (list): Original ingredients
            modified_ingredients (list): Modified ingredients with replacements
            condition (str): Medical condition
            harmful_ingredients (list): List of harmful ingredients that were replaced
        
        Returns:
            str: Generated recipe instructions
        """
        if not self.model:
            return self._fallback_recipe_generation(modified_ingredients)
        
        try:
            # Create the prompt for Gemini
            prompt = self._create_recipe_prompt(original_ingredients, modified_ingredients, condition, harmful_ingredients)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                return response.text.strip()
            else:
                return self._fallback_recipe_generation(modified_ingredients)
                
        except Exception as e:
            logger.error(f"Error generating recipe with Gemini: {e}")
            return self._fallback_recipe_generation(modified_ingredients)
    
    def _create_recipe_prompt(self, original_ingredients, modified_ingredients, condition, harmful_ingredients):
        """Create a detailed prompt for recipe generation"""
        
        harmful_text = ""
        if harmful_ingredients:
            harmful_text = f"\nHarmful ingredients replaced: {', '.join(harmful_ingredients)}"
        
        prompt = f"""
You are a professional nutritionist and chef specializing in creating healthy recipes for people with medical conditions.

Patient Information:
- Medical Condition: {condition.replace('_', ' ').title()}
- Original Ingredients: {', '.join(original_ingredients)}
- Safe Ingredients: {', '.join(modified_ingredients)}{harmful_text}

Please create a detailed, step-by-step recipe using the safe ingredients. The recipe should:

1. Be easy to follow for home cooking
2. Include specific cooking times and temperatures
3. Provide clear instructions for each step
4. Include helpful tips for the specific medical condition
5. Be written in a friendly, encouraging tone
6. Include serving suggestions and nutritional notes

Format the recipe with clear sections using markdown:

**Health Benefits**
Brief introduction explaining why this recipe is good for {condition.replace('_', ' ').title()}

**Ingredients**
- List each ingredient with quantities

**Instructions**
1. Step-by-step cooking instructions
2. Include cooking times and temperatures
3. Clear, easy-to-follow format

**Cooking Tips**
- Helpful tips for the specific medical condition
- Cooking suggestions and variations

**Serving Suggestions**
- How to serve and enjoy the dish
- Nutritional notes relevant to the condition

Keep the response concise but informative (around 200-300 words). Use proper markdown formatting with headers, lists, and clear structure.
"""
        return prompt
    
    def _fallback_recipe_generation(self, modified_ingredients):
        """Fallback recipe generation when Gemini API is not available"""
        recipe = f"""**Health Benefits**
This recipe uses healthy, safe ingredients that are suitable for your dietary needs.

**Ingredients**
- {', '.join(modified_ingredients)}

**Instructions**
1. Combine all ingredients in a mixing bowl
2. Mix well until thoroughly combined
3. Cook in a non-stick pan over medium heat
4. Cook until golden brown and fully cooked through

**Cooking Tips**
- Use a non-stick pan to reduce the need for additional oil
- Cook on medium heat to prevent burning
- Stir occasionally for even cooking

**Serving Suggestions**
Serve warm and enjoy! This dish is perfect for a healthy meal that fits your dietary requirements."""
        
        return recipe
    
    def generate_health_tips(self, condition, ingredients):
        """Generate personalized health tips based on condition and ingredients"""
        if not self.model:
            return "Always consult with your healthcare provider for personalized dietary advice."
        
        try:
            prompt = f"""
As a nutritionist, provide 3-4 brief, helpful health tips for someone with {condition.replace('_', ' ')} 
who is cooking with these ingredients: {', '.join(ingredients)}.

Keep tips practical, encouraging, and specific to the condition. Format as a simple list.
"""
            
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            else:
                return "Always consult with your healthcare provider for personalized dietary advice."
                
        except Exception as e:
            logger.error(f"Error generating health tips: {e}")
            return "Always consult with your healthcare provider for personalized dietary advice."

# Global instance
gemini_service = GeminiService()
