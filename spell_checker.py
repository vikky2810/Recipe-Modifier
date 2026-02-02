"""
Spell Checker Service for Recipe Names

Uses a pre-trained CountVectorizer and cosine similarity to suggest 
correct recipe names when users type misspelled inputs.

Optimized for Vercel serverless deployment with lazy loading.
"""

import pickle
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy imports for serverless optimization
_pd = None
_cosine_similarity = None


def _get_pandas():
    """Lazy load pandas"""
    global _pd
    if _pd is None:
        import pandas as pd
        _pd = pd
    return _pd


def _get_cosine_similarity():
    """Lazy load sklearn cosine_similarity"""
    global _cosine_similarity
    if _cosine_similarity is None:
        from sklearn.metrics.pairwise import cosine_similarity
        _cosine_similarity = cosine_similarity
    return _cosine_similarity


class SpellChecker:
    """ML-based spell checker using vectorized recipe name similarity"""
    
    def __init__(self):
        self.vectorizer = None
        self.recipe_vectors = None
        self.recipes = []
        self.recipes_lower = []
        self._loaded = False
        self._load_attempted = False
    
    def _ensure_loaded(self):
        """Lazy load models on first use (better for serverless cold starts)"""
        if self._load_attempted:
            return self._loaded
        self._load_attempted = True
        self._load_models()
        return self._loaded
    
    def _load_models(self):
        """Load vectorizer, recipe vectors, and recipe list from pkl files"""
        try:
            # Get the correct base path - handles both local and Vercel environments
            base_path = os.path.dirname(os.path.abspath(__file__))
            models_path = os.path.join(base_path, 'models')
            
            # Check if models directory exists
            if not os.path.exists(models_path):
                logger.warning(f"Models directory not found at: {models_path}")
                return
            
            # Load vectorizer
            vectorizer_path = os.path.join(models_path, 'vectorizer.pkl')
            if not os.path.exists(vectorizer_path):
                logger.warning(f"Vectorizer file not found: {vectorizer_path}")
                return
                
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            logger.info("Loaded vectorizer.pkl successfully")
            
            # Load pre-computed recipe vectors
            vectors_path = os.path.join(models_path, 'recipe_vectors.pkl')
            if not os.path.exists(vectors_path):
                logger.warning(f"Recipe vectors file not found: {vectors_path}")
                return
                
            with open(vectors_path, 'rb') as f:
                self.recipe_vectors = pickle.load(f)
            logger.info(f"Loaded recipe_vectors.pkl successfully (shape: {self.recipe_vectors.shape})")
            
            # Load recipe names from CSV
            recipes_path = os.path.join(models_path, 'recipes.csv')
            if not os.path.exists(recipes_path):
                logger.warning(f"Recipes CSV not found: {recipes_path}")
                return
            
            pd = _get_pandas()
            df = pd.read_csv(recipes_path)
            self.recipes = df['recipe'].tolist()
            self.recipes_lower = [r.lower() for r in self.recipes]
            logger.info(f"Loaded {len(self.recipes)} recipe names from recipes.csv")
            
            self._loaded = True
            
        except FileNotFoundError as e:
            logger.error(f"Model file not found: {e}")
            self._loaded = False
        except Exception as e:
            logger.error(f"Error loading spell checker models: {e}")
            self._loaded = False
    
    def check_spelling(self, text, threshold=0.3, top_n=3):
        """
        Check if input matches a recipe; return suggestions if not.
        
        Args:
            text: User input recipe name
            threshold: Minimum similarity score for suggestions (0.0 to 1.0)
            top_n: Maximum number of suggestions to return
            
        Returns:
            dict: {"is_correct": bool, "suggestions": list}
        """
        # Ensure models are loaded (lazy loading for serverless)
        if not self._ensure_loaded() or not text:
            return {"is_correct": True, "suggestions": []}
        
        text_lower = text.strip().lower()
        
        # Check for exact match
        if text_lower in self.recipes_lower:
            return {"is_correct": True, "suggestions": []}
        
        try:
            # Vectorize the input text
            input_vec = self.vectorizer.transform([text_lower])
            
            # Compute cosine similarity against all recipe vectors
            cosine_sim = _get_cosine_similarity()
            similarities = cosine_sim(input_vec, self.recipe_vectors).flatten()
            
            # Get top matches sorted by similarity (descending)
            top_indices = similarities.argsort()[-top_n:][::-1]
            
            # Filter suggestions above threshold
            suggestions = []
            for i in top_indices:
                if similarities[i] >= threshold:
                    suggestions.append(self.recipes[i])
            
            # If the top match has very high similarity, consider it "close enough"
            max_similarity = float(similarities[top_indices[0]]) if len(top_indices) > 0 else 0.0
            is_correct = len(suggestions) == 0 or max_similarity > 0.9
            
            return {
                "is_correct": bool(is_correct),
                "suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Error during spell check: {e}")
            return {"is_correct": True, "suggestions": []}
    
    def get_all_recipes(self):
        """Return all available recipe names for autocomplete"""
        self._ensure_loaded()
        return self.recipes if self._loaded else []


# Global singleton instance (lazy loaded)
spell_checker = SpellChecker()
