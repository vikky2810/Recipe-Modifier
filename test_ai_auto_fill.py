#!/usr/bin/env python3
"""
Comprehensive test suite for AI Auto Fill Ingredient functionality
Tests both the gemini_service.extract_ingredients method and the API endpoint
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from gemini_service import GeminiService


class TestGeminiServiceExtractIngredients(unittest.TestCase):
    """Test the extract_ingredients method in GeminiService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.gemini_service = GeminiService()
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_with_recipe_name(self, mock_genai):
        """Test extracting ingredients from a simple recipe name"""
        # Mock the Gemini API response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "flour, sugar, butter, eggs, vanilla"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Create a new service instance to use the mocked model
        service = GeminiService()
        service.model = mock_model
        
        result = service.extract_ingredients("chocolate chip cookies")
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Check that the model was called
        mock_model.generate_content.assert_called_once()
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_with_recipe_text(self, mock_genai):
        """Test extracting ingredients from recipe text with quantities"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "flour, sugar, butter, eggs"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = GeminiService()
        service.model = mock_model
        
        input_text = "Banana Bread recipe: 2 cups flour, 3 bananas, 1/2 cup sugar, 1/3 cup butter, 2 eggs"
        result = service.extract_ingredients(input_text)
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Verify quantities are removed
        for ingredient in result:
            self.assertNotIn('cup', ingredient.lower())
            self.assertNotIn('2', ingredient)
            self.assertNotIn('3', ingredient)
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_with_regional_dish(self, mock_genai):
        """Test extracting ingredients from a regional dish name"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "wheat flour, chana dal, jaggery, ghee, cardamom, turmeric, salt"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = GeminiService()
        service.model = mock_model
        
        result = service.extract_ingredients("puran poli")
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        # Should infer common ingredients for regional dishes
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_with_indian_dishes(self, mock_genai):
        """Test extracting ingredients from various Indian dish names"""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = GeminiService()
        service.model = mock_model
        
        # Test cases for different Indian dishes
        indian_dishes = [
            {
                "name": "biryani",
                "expected_ingredients": ["basmati rice", "chicken", "onion", "yogurt", "spices", "ghee", "saffron"]
            },
            {
                "name": "butter chicken",
                "expected_ingredients": ["chicken", "butter", "tomato", "cream", "garlic", "ginger", "spices"]
            },
            {
                "name": "dal makhani",
                "expected_ingredients": ["black lentils", "kidney beans", "butter", "cream", "tomato", "spices"]
            },
            {
                "name": "samosa",
                "expected_ingredients": ["flour", "potato", "peas", "spices", "oil"]
            },
            {
                "name": "dosa",
                "expected_ingredients": ["rice", "urad dal", "salt", "oil"]
            },
            {
                "name": "paneer tikka",
                "expected_ingredients": ["paneer", "yogurt", "spices", "bell pepper", "onion"]
            },
            {
                "name": "chole bhature",
                "expected_ingredients": ["chickpeas", "flour", "yogurt", "spices", "onion", "tomato"]
            },
            {
                "name": "rajma",
                "expected_ingredients": ["kidney beans", "onion", "tomato", "spices", "ginger", "garlic"]
            },
            {
                "name": "aloo gobi",
                "expected_ingredients": ["potato", "cauliflower", "onion", "tomato", "spices", "turmeric"]
            },
            {
                "name": "palak paneer",
                "expected_ingredients": ["spinach", "paneer", "onion", "tomato", "spices", "garlic", "ginger"]
            }
        ]
        
        for dish in indian_dishes:
            # Mock response for each dish
            mock_response = MagicMock()
            mock_response.text = ", ".join(dish["expected_ingredients"])
            mock_model.generate_content.return_value = mock_response
            
            result = service.extract_ingredients(dish["name"])
            
            self.assertIsInstance(result, list, 
                                f"Failed for {dish['name']}: result should be a list")
            self.assertGreater(len(result), 0, 
                             f"Failed for {dish['name']}: should extract at least one ingredient")
            
            # Verify that common Indian ingredients are present
            result_lower = [ing.lower() for ing in result]
            # Check for at least one expected ingredient (case-insensitive)
            found_ingredient = any(
                any(exp_ing.lower() in res_ing or res_ing in exp_ing.lower() 
                    for res_ing in result_lower)
                for exp_ing in dish["expected_ingredients"]
            )
            self.assertTrue(found_ingredient, 
                          f"Failed for {dish['name']}: should contain at least one expected ingredient")
    
    def test_extract_ingredients_without_model_fallback(self):
        """Test fallback behavior when Gemini model is not available"""
        service = GeminiService()
        service.model = None  # Simulate no model available
        
        # Should fallback to simple comma splitting
        result = service.extract_ingredients("flour, sugar, butter, eggs")
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        self.assertIn("flour", result)
        self.assertIn("sugar", result)
        self.assertIn("butter", result)
        self.assertIn("eggs", result)
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_removes_descriptors(self, mock_genai):
        """Test that descriptors like 'chopped', 'minced' are removed"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "onion (chopped), garlic (minced), fresh tomatoes, ripe bananas"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = GeminiService()
        service.model = mock_model
        
        result = service.extract_ingredients("recipe with chopped onion")
        
        self.assertIsInstance(result, list)
        # Check that descriptors are removed
        for ingredient in result:
            self.assertNotIn('chopped', ingredient.lower())
            self.assertNotIn('minced', ingredient.lower())
            self.assertNotIn('fresh', ingredient.lower())
            self.assertNotIn('ripe', ingredient.lower())
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_handles_empty_response(self, mock_genai):
        """Test handling of empty API response"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = GeminiService()
        service.model = mock_model
        
        result = service.extract_ingredients("some recipe")
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_handles_api_exception(self, mock_genai):
        """Test handling of API exceptions"""
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = GeminiService()
        service.model = mock_model
        
        result = service.extract_ingredients("some recipe")
        
        # Should return empty list on error
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_normalizes_to_lowercase(self, mock_genai):
        """Test that ingredients are normalized to lowercase"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Flour, SUGAR, Butter, EGGS"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = GeminiService()
        service.model = mock_model
        
        result = service.extract_ingredients("recipe")
        
        self.assertIsInstance(result, list)
        # All ingredients should be lowercase
        for ingredient in result:
            self.assertEqual(ingredient, ingredient.lower())
    
    @patch('gemini_service.genai')
    def test_extract_ingredients_removes_duplicates(self, mock_genai):
        """Test that duplicate ingredients are removed"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "flour, sugar, flour, butter, sugar, eggs"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        service = GeminiService()
        service.model = mock_model
        
        result = service.extract_ingredients("recipe")
        
        self.assertIsInstance(result, list)
        # Should have no duplicates
        self.assertEqual(len(result), len(set(result)))


class TestAIExtractIngredientsAPI(unittest.TestCase):
    """Test the /api/ai/extract-ingredients API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True
    
    @patch('app.gemini_service')
    def test_api_extract_ingredients_success(self, mock_gemini_service):
        """Test successful ingredient extraction via API"""
        # Mock the gemini service response
        mock_gemini_service.extract_ingredients.return_value = [
            "flour", "sugar", "butter", "eggs"
        ]
        
        response = self.app.post(
            '/api/ai/extract-ingredients',
            json={'text': 'chocolate chip cookies'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('ingredients', data)
        self.assertIsInstance(data['ingredients'], list)
        self.assertEqual(len(data['ingredients']), 4)
        self.assertIn('flour', data['ingredients'])
        mock_gemini_service.extract_ingredients.assert_called_once_with('chocolate chip cookies')
    
    @patch('app.gemini_service')
    def test_api_extract_ingredients_empty_text(self, mock_gemini_service):
        """Test API with empty text input"""
        response = self.app.post(
            '/api/ai/extract-ingredients',
            json={'text': ''},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('ingredients', data)
        self.assertEqual(data['ingredients'], [])
        # Should not call gemini service for empty text
        mock_gemini_service.extract_ingredients.assert_not_called()
    
    @patch('app.gemini_service')
    def test_api_extract_ingredients_missing_text(self, mock_gemini_service):
        """Test API with missing text field"""
        response = self.app.post(
            '/api/ai/extract-ingredients',
            json={},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('ingredients', data)
        self.assertEqual(data['ingredients'], [])
        mock_gemini_service.extract_ingredients.assert_not_called()
    
    @patch('app.gemini_service')
    def test_api_extract_ingredients_whitespace_only(self, mock_gemini_service):
        """Test API with whitespace-only text"""
        response = self.app.post(
            '/api/ai/extract-ingredients',
            json={'text': '   '},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('ingredients', data)
        self.assertEqual(data['ingredients'], [])
        mock_gemini_service.extract_ingredients.assert_not_called()
    
    @patch('app.gemini_service')
    def test_api_extract_ingredients_service_exception(self, mock_gemini_service):
        """Test API handling of service exceptions"""
        # Mock service to raise an exception
        mock_gemini_service.extract_ingredients.side_effect = Exception("Service error")
        
        response = self.app.post(
            '/api/ai/extract-ingredients',
            json={'text': 'some recipe'},
            content_type='application/json'
        )
        
        # Should return 200 with empty list on error
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('ingredients', data)
        self.assertEqual(data['ingredients'], [])
    
    @patch('app.gemini_service')
    def test_api_extract_ingredients_invalid_json(self, mock_gemini_service):
        """Test API with invalid JSON"""
        response = self.app.post(
            '/api/ai/extract-ingredients',
            data='invalid json',
            content_type='application/json'
        )
        
        # Should handle gracefully
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('ingredients', data)
        self.assertEqual(data['ingredients'], [])
    
    @patch('app.gemini_service')
    def test_api_extract_ingredients_with_recipe_name_variations(self, mock_gemini_service):
        """Test API with different recipe name formats"""
        mock_gemini_service.extract_ingredients.return_value = [
            "wheat flour", "chana dal", "jaggery", "ghee"
        ]
        
        test_cases = [
            "puran poli",
            "Puran Poli (Indian dish)",
            "puran poli recipe",
            "Ingredients for puran poli",
            "biryani",
            "Butter Chicken (Murgh Makhani)",
            "dal makhani recipe",
            "samosa",
            "dosa",
            "paneer tikka masala",
            "chole bhature",
            "rajma chawal",
            "aloo gobi",
            "palak paneer"
        ]
        
        for text in test_cases:
            response = self.app.post(
                '/api/ai/extract-ingredients',
                json={'text': text},
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('ingredients', data)
            self.assertIsInstance(data['ingredients'], list)
    
    @patch('app.gemini_service')
    def test_api_extract_ingredients_with_long_text(self, mock_gemini_service):
        """Test API with long recipe text"""
        mock_gemini_service.extract_ingredients.return_value = [
            "flour", "sugar", "butter", "eggs", "vanilla", "baking powder"
        ]
        
        long_text = "Chocolate Chip Cookies Recipe: " + " ".join([
            "2 cups all-purpose flour",
            "1 cup white sugar",
            "1/2 cup butter",
            "2 large eggs",
            "1 tsp vanilla extract",
            "1 tsp baking powder"
        ])
        
        response = self.app.post(
            '/api/ai/extract-ingredients',
            json={'text': long_text},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('ingredients', data)
        self.assertGreater(len(data['ingredients']), 0)
        mock_gemini_service.extract_ingredients.assert_called_once()


class TestAIAutoFillIntegration(unittest.TestCase):
    """Integration tests for the complete AI auto fill flow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = app.test_client()
        self.app.testing = True
    
    @patch('app.gemini_service')
    def test_complete_auto_fill_flow(self, mock_gemini_service):
        """Test the complete flow from recipe name to ingredient list"""
        # Mock successful extraction
        mock_gemini_service.extract_ingredients.return_value = [
            "flour", "sugar", "butter", "eggs", "vanilla"
        ]
        
        # Simulate the frontend request
        response = self.app.post(
            '/api/ai/extract-ingredients',
            json={'text': 'chocolate chip cookies'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Verify the response format matches what frontend expects
        self.assertIn('ingredients', data)
        self.assertIsInstance(data['ingredients'], list)
        self.assertGreater(len(data['ingredients']), 0)
        
        # Verify ingredients can be joined with commas (as frontend does)
        ingredients_string = ', '.join(data['ingredients'])
        self.assertIsInstance(ingredients_string, str)
        self.assertGreater(len(ingredients_string), 0)


def run_tests():
    """Run all tests and display results"""
    print("🧪 Testing AI Auto Fill Ingredient Functionality")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestGeminiServiceExtractIngredients))
    suite.addTests(loader.loadTestsFromTestCase(TestAIExtractIngredientsAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestAIAutoFillIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   ✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ Failed: {len(result.failures)}")
    print(f"   ⚠️  Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}")
    
    if result.errors:
        print("\n⚠️  Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}")
    
    if result.wasSuccessful():
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

