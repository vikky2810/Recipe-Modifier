#!/usr/bin/env python3
"""
Test script to verify improved PDF report generation
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import generate_pdf_report, initialize_database
from pymongo import MongoClient
from config import Config

def test_pdf_generation():
    """Test the improved PDF report generation"""
    
    print("🧪 Testing Improved PDF Report Generation")
    print("=" * 50)
    
    try:
        # Initialize database
        initialize_database()
        
        # Test PDF generation
        print("\n📄 Generating PDF Report...")
        
        patient_id = "1"
        filename = generate_pdf_report(patient_id)
        
        if filename and os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"✅ PDF generated successfully!")
            print(f"📁 File: {filename}")
            print(f"📏 Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            
            # Check if file is readable
            try:
                with open(filename, 'rb') as f:
                    header = f.read(4)
                    if header.startswith(b'%PDF'):
                        print("✅ PDF file is valid and readable")
                    else:
                        print("❌ PDF file appears to be corrupted")
            except Exception as e:
                print(f"❌ Error reading PDF file: {e}")
                
        else:
            print("❌ PDF generation failed")
            return False
            
        # Test with multiple entries
        print("\n📊 Testing with multiple food entries...")
        
        # Add some test entries to make the report more comprehensive
        client = MongoClient(Config.MONGODB_URI)
        db = client[Config.DATABASE_NAME]
        food_entries = db['food_entries']
        
        # Add a few more test entries
        test_entries = [
            {
                "patient_id": "1",
                "condition": "diabetes",
                "input_ingredients": ["milk", "sugar", "chocolate"],
                "harmful": ["milk", "sugar"],
                "safe": ["almond milk", "stevia", "chocolate"],
                "recipe": "Mix almond milk with stevia and chocolate. Heat gently and serve warm.",
                "timestamp": datetime.now()
            },
            {
                "patient_id": "1",
                "condition": "diabetes",
                "input_ingredients": ["bread", "butter", "jam"],
                "harmful": ["bread", "butter"],
                "safe": ["gluten-free bread", "olive oil", "jam"],
                "recipe": "Toast gluten-free bread, spread with olive oil and jam. Serve immediately.",
                "timestamp": datetime.now()
            }
        ]
        
        for entry in test_entries:
            food_entries.insert_one(entry)
        
        print("✅ Added test entries to database")
        
        # Generate report again
        filename2 = generate_pdf_report(patient_id)
        if filename2 and os.path.exists(filename2):
            file_size2 = os.path.getsize(filename2)
            print(f"✅ Updated PDF generated successfully!")
            print(f"📁 File: {filename2}")
            print(f"📏 Size: {file_size2:,} bytes ({file_size2/1024:.1f} KB)")
            
            if file_size2 > file_size:
                print("✅ PDF size increased (more content added)")
            else:
                print("⚠️ PDF size didn't increase as expected")
        else:
            print("❌ Updated PDF generation failed")
            
        print("\n🎉 PDF report generation test completed successfully!")
        print(f"\n📋 You can view the report at: http://localhost:5000/view_report/{patient_id}")
        print(f"📥 You can download the report at: http://localhost:5000/generate_report/{patient_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during PDF testing: {e}")
        return False

if __name__ == "__main__":
    test_pdf_generation()
