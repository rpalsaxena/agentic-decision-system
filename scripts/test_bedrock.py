"""
Test AWS Bedrock connection for Claude models
"""

import os
from dotenv import load_dotenv
import boto3
import json

load_dotenv()


def test_bedrock():
    try:
        print("🔗 Connecting to AWS Bedrock...")
        
        # Initialize Bedrock client
        bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        model_id = os.getenv('AWS_BEDROCK_MODEL_ID')
        print(f"   Region: {os.getenv('AWS_REGION')}")
        print(f"   Model: {model_id}")
        
        # Test prompt
        print("\n🧪 Testing Claude model...")
        
        # Prepare the request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Say 'Hello from AWS Bedrock!' and nothing else."
                }
            ]
        }
        
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        print(f"✅ Model Response:")
        print(f"   {response_body['content'][0]['text']}")
        print(f"   Stop Reason: {response_body.get('stop_reason')}")
        print(f"   Input Tokens: {response_body['usage']['input_tokens']}")
        print(f"   Output Tokens: {response_body['usage']['output_tokens']}")
        
        print("\n✅ AWS Bedrock test successful!")
        
    except Exception as e:
        print(f"❌ AWS Bedrock test failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure AWS credentials are configured (aws configure)")
        print("   2. Check IAM permissions for Bedrock access")
        print("   3. Verify model ID is correct and available in your region")
        print("   4. Check if Bedrock service is enabled in your AWS account")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("  AWS Bedrock Connection Test")
    print("=" * 60)
    print()
    
    test_bedrock()
    
    print("\n" + "=" * 60)
