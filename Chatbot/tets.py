# test_gemini_debug.py
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
import google.generativeai as genai  # Hoặc google.genai


def test_direct_api():
    """Test API trực tiếp không qua wrapper"""
    print("🔍 Testing Gemini API directly...")

    # 1. Test API key
    api_key = Config.GEMINI_API_KEY
    print(f"API Key: {api_key[:10]}...")

    # 2. Configure
    genai.configure(api_key=api_key)

    # 3. Create model
    model = genai.GenerativeModel('gemini-pro')

    # 4. Simple test
    response = model.generate_content("Xin chào, bạn là ai?")

    print("✅ Response received:")
    print(response.text)
    print(f"Response length: {len(response.text)}")
    print(f"Response type: {type(response.text)}")


if __name__ == "__main__":
    test_direct_api()