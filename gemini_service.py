from google import genai
from config import Config
import logging
import os
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        """Initialize Gemini API service"""
        try:
            GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("Gemini API service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {e}")
            self.client = None
    
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
        if not self.client:
            return self._fallback_recipe_generation(modified_ingredients)
        
        try:
            # Create the prompt for Gemini
            prompt = self._create_recipe_prompt(original_ingredients, modified_ingredients, condition, harmful_ingredients)
            
            # Generate response
            response = self.client.generate_content(prompt)
            
            if response and hasattr(response, 'text') and response.text:
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
        if not self.client:
            return "Always consult with your healthcare provider for personalized dietary advice."
        
        try:
            prompt = f"""
As a nutritionist, provide 3-4 brief, helpful health tips for someone with {condition.replace('_', ' ')} 
who is cooking with these ingredients: {', '.join(ingredients)}.

Keep tips practical, encouraging, and specific to the condition. Format as a simple list.
"""
            
            response = self.client.generate_content(prompt)
            if response and hasattr(response, 'text') and response.text:
                return response.text.strip()
            else:
                return "Always consult with your healthcare provider for personalized dietary advice."
                
        except Exception as e:
            logger.error(f"Error generating health tips: {e}")
            return "Always consult with your healthcare provider for personalized dietary advice."

    def extract_ingredients(self, text_or_name):
        """Extract a concise, comma-separated ingredient list from a recipe name or text using Gemini.

        Returns a Python list of lowercased ingredient names without quantities. Falls back to simple parsing.
        """
        # Fallback: split by commas if no client available
        if not self.client:
            raw = [p.strip().lower() for p in text_or_name.split(',') if p.strip()]
            return raw
        
        try:
            few_shots = (
                "Example 1\n"
                "Input: puran poli\n"
                "Output: wheat flour, chana dal, jaggery, ghee, cardamom, turmeric, salt\n\n"
                "Example 2\n"
                "Input: bread\n"
                "Output: flour, water, yeast, salt\n\n"
                "Example 3\n"
                "Input: Banana Bread recipe: 2 cups flour, 3 bananas (ripe), 1/2 cup sugar, 1/3 cup butter, 2 eggs.\n"
                "Output: flour, banana, sugar, butter, eggs\n\n"
            )
            prompt = f"""
                You are an expert at reading recipes and listing only the ingredient names.
                - Input may be just a recipe name (e.g., "puran poli") or a block of text with steps.
                - Return ONLY a simple, comma-separated list of ingredient names.
                - Do NOT include amounts, units, adjectives (like chopped/minced), preparation notes, brands, or extraneous words.
                - Use singular nouns when reasonable (e.g., banana, egg) and lowercase all words.
                - If the input is a regional dish, infer common core ingredients.

                {few_shots}
                Input:
                {text_or_name}

                Output (just the list, no extra words):
                """
            response = self.client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            # print("response is :", response)
            if not response or not hasattr(response, 'text') or not response.text:
                return []
            # Parse and normalize model output
            text = response.text.strip().lower()
            # Remove bullets/numbering and join lines
            lines = [l.strip('-* ').strip() for l in text.splitlines() if l.strip()]
            csv = ', '.join(lines) if len(lines) > 1 else text
            # Split, trim, remove units/descriptors
            raw_items = [p.strip() for p in csv.split(',') if p.strip()]
            cleaned_items = []
            seen = set()
            descriptor_tokens = [
                'chopped', 'minced', 'sliced', 'diced', 'fresh', 'ground', 'powder',
                'to taste', 'optional', 'ripe', 'large', 'small', 'medium'
            ]
            for item in raw_items:
                # Remove parentheticals and extra spaces
                base = item.split('(')[0].strip()
                # Remove common descriptors
                parts = [w for w in base.split() if w not in descriptor_tokens]
                base = ' '.join(parts).strip()
                # Strip quantities/units at start (e.g., '2 cups flour' -> 'flour')
                tokens = base.split()
                # Drop leading numeric tokens and units
                units = {'cup', 'cups', 'tsp', 'tbsp', 'teaspoon', 'teaspoons', 'tablespoon', 'tablespoons', 'g', 'kg', 'ml', 'l', 'ounce', 'ounces', 'oz'}
                while tokens and (tokens[0].replace('/', '').replace('-', '').isdigit() or tokens[0] in units):
                    tokens.pop(0)
                base = ' '.join(tokens).strip()
                if not base:
                    continue
                if base not in seen:
                    seen.add(base)
                    cleaned_items.append(base)
            return cleaned_items
        except Exception as e:
            logger.error(f"Error extracting ingredients with Gemini: {e}")
            return []

# Global instance
gemini_service = GeminiService()
