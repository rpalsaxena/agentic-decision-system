"""
Test OpenAI API connection
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def test_openai():
    try:
        print("🔗 Connecting to OpenAI API...")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Test chat completion
        print("\n🧪 Testing GPT model...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello from OpenAI!' and nothing else."}
            ],
            max_tokens=50
        )
        
        print(f"✅ Model Response:")
        print(f"   {response.choices[0].message.content}")
        print(f"   Model: {response.model}")
        print(f"   Input Tokens: {response.usage.prompt_tokens}")
        print(f"   Output Tokens: {response.usage.completion_tokens}")
        print(f"   Total Tokens: {response.usage.total_tokens}")
        
        # Test embeddings
        print("\n🧪 Testing embeddings...")
        
        embedding_response = client.embeddings.create(
            model="text-embedding-3-small",
            input="This is a test event for embeddings"
        )
        
        embedding_dim = len(embedding_response.data[0].embedding)
        print(f"✅ Embedding created:")
        print(f"   Model: {embedding_response.model}")
        print(f"   Dimension: {embedding_dim}")
        print(f"   Total Tokens: {embedding_response.usage.total_tokens}")
        
        print("\n✅ OpenAI API test successful!")
        
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Verify OPENAI_API_KEY in .env file")
        print("   2. Check if API key is valid and active")
        print("   3. Ensure you have credits/billing set up")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("  OpenAI API Connection Test")
    print("=" * 60)
    print()
    
    test_openai()
    
    print("\n" + "=" * 60)
