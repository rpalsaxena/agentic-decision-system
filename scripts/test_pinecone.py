"""
Test Pinecone connection and vector operations
"""

import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
import time

load_dotenv()


def test_pinecone():
    try:
        # Initialize Pinecone
        print("🔗 Connecting to Pinecone...")
        print(f"   Index: {os.getenv('PINECONE_INDEX')}")
        
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        
        # Get index name
        index_name = os.getenv('PINECONE_INDEX')
        
        # Check if index exists
        print("\n📋 Checking existing indexes...")
        existing_indexes = pc.list_indexes()
        print(f"   Found {len(existing_indexes)} indexes")
        
        index_exists = any(idx['name'] == index_name for idx in existing_indexes)
        
        if not index_exists:
            print(f"\n📦 Creating index '{index_name}'...")
            pc.create_index(
                name=index_name,
                dimension=768,  # Using sentence-transformers dimension
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            print("⏳ Waiting for index to be ready...")
            time.sleep(10)  # Wait for index to initialize
            print("✅ Index created successfully")
        else:
            print(f"✅ Index '{index_name}' already exists")
        
        # Connect to index
        index = pc.Index(index_name)
        
        # Get index stats
        print("\n📊 Index Statistics:")
        stats = index.describe_index_stats()
        print(f"   Total vectors: {stats.get('total_vector_count', 0)}")
        print(f"   Dimension: {stats.get('dimension', 'N/A')}")
        print(f"   Namespaces: {len(stats.get('namespaces', {}))}")
        
        # Test upsert (insert/update)
        print("\n🧪 Testing vector operations...")
        test_vectors = [
            {
                "id": "test-event-1",
                "values": [0.1] * 768,  # Dummy embedding
                "metadata": {
                    "event_type": "test",
                    "source": "test_script",
                    "severity": "low"
                }
            },
            {
                "id": "test-event-2",
                "values": [0.2] * 768,
                "metadata": {
                    "event_type": "test",
                    "source": "test_script",
                    "severity": "medium"
                }
            }
        ]
        
        upsert_response = index.upsert(vectors=test_vectors)
        print(f"✅ Upserted {upsert_response['upserted_count']} vectors")
        
        # Wait for vectors to be indexed
        time.sleep(2)
        
        # Test query
        print("\n🔍 Testing similarity search...")
        query_results = index.query(
            vector=[0.15] * 768,  # Query vector
            top_k=2,
            include_metadata=True
        )
        
        print(f"✅ Found {len(query_results['matches'])} similar vectors:")
        for match in query_results['matches']:
            print(f"   - ID: {match['id']}, Score: {match['score']:.4f}")
            print(f"     Metadata: {match.get('metadata', {})}")
        
        # Test fetch
        print("\n📥 Testing fetch by ID...")
        fetch_response = index.fetch(ids=["test-event-1"])
        if fetch_response['vectors']:
            print(f"✅ Fetched vector: {list(fetch_response['vectors'].keys())}")
        
        # Clean up test data
        print("\n🧹 Cleaning up test vectors...")
        index.delete(ids=["test-event-1", "test-event-2"])
        print("✅ Cleanup successful")
        
        print("\n✅ Pinecone connection test successful!")
        
    except Exception as e:
        print(f"❌ Pinecone test failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Verify PINECONE_API_KEY in .env file")
        print("   2. Check if index name is correct")
        print("   3. Ensure API key has proper permissions")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("  Pinecone Connection Test")
    print("=" * 60)
    print()
    
    test_pinecone()
    
    print("\n" + "=" * 60)
