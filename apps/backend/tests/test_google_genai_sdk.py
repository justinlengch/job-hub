#!/usr/bin/env python3
"""
Test script to verify the refactored extract_job_info function with google-genai SDK
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, '/home/justin/repos/job-hub/apps/backend/app')

async def test_google_genai_sdk():
    """Test the refactored function with google-genai SDK"""
    
    try:
        from app.models.llm.llm_email import LLMEmailInput
        from app.services.ai.llm import extract_job_info
        
        # Create test input
        test_input = LLMEmailInput(
            subject="Application - Software Engineer II Position",
            body_text="Dear Candidate, Thank you for applying to TechCorp under the role of Software Engineer II position. We have received your application and would like to invite you to complete an online assessment. Details will be attached in a follow-up email. Best wishes, HR Team at TechCorp",
            body_html=None
        )
        
        print("🚀 Testing extract_job_info with google-genai SDK...")
        
        # Call the function
        result = await extract_job_info(test_input)
        
        print("✅ Function call successful!")
        print(f"Intent: {result.intent}")
        print(f"Company: {result.company}")
        print(f"Role: {result.role}")
        print(f"Status: {result.status}")
        print(f"Salary: {result.salary_range}")
        print(f"Event Type: {result.event_type}")
        
        # Validate the result
        assert result.intent is not None
        assert result.company is not None
        assert result.role is not None
        assert result.status is not None
        
        print("✅ All validations passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_configuration():
    """Test that the API is configured correctly"""
    
    try:
        from google import genai
        from google.genai import types
        from app.core.config import settings
        
        # Test client creation
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        print("✅ Client created successfully")
        
        # Test config creation
        config = types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json"
        )
        print("✅ Config created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    
    print("🧪 Testing google-genai SDK integration...")
    print("=" * 50)
    
    # Test 1: API Configuration
    print("\n1. Testing API Configuration...")
    config_ok = await test_api_configuration()
    
    if not config_ok:
        print("❌ Configuration test failed. Cannot proceed.")
        return False
    
    # Test 2: Function Integration
    print("\n2. Testing Function Integration...")
    function_ok = await test_google_genai_sdk()
    
    if function_ok:
        print("\n🎉 All tests passed! The refactored code is working correctly.")
        return True
    else:
        print("\n❌ Function test failed.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
