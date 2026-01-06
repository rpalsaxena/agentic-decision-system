"""
Database Initialization Script for Aurora Serverless
Creates all tables, indexes, and constraints for the Agentic AI Decision System
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()


async def init_database():
    """Initialize database schema"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        raise ValueError("DATABASE_URL not found in .env file")
    
    print(f"🔗 Connecting to Aurora Serverless...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(database_url)
        print("✅ Connected successfully")
        
        # Read schema SQL file
        schema_path = Path(__file__).parent / 'schema.sql'
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        print("📝 Executing schema...")
        
        # Execute schema (split by semicolons to handle multiple statements)
        await conn.execute(schema_sql)
        
        print("✅ Tables created successfully")
        
        # Verify tables were created
        print("\n📊 Verifying tables...")
        tables = await conn.fetch("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        
        print(f"\n✅ Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table['tablename']}")
        
        # Check indexes
        indexes = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY indexname;
        """)
        
        print(f"\n✅ Created {len(indexes)} indexes:")
        for index in indexes:
            print(f"   - {index['indexname']}")
        
    except asyncpg.exceptions.DuplicateTableError:
        print("⚠️  Tables already exist. Skipping creation.")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await conn.close()
        print("\n🔌 Connection closed")


async def test_connection():
    """Test database connection and basic operations"""
    database_url = os.getenv('DATABASE_URL')
    
    print("\n🧪 Testing database connection...")
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Test insert
        event_id = await conn.fetchval("""
            INSERT INTO events (timestamp, source, raw_payload, event_type, severity)
            VALUES (NOW(), 'test-source', '{"test": true}'::jsonb, 'test', 'low')
            RETURNING id;
        """)
        
        print(f"✅ Test insert successful (ID: {event_id})")
        
        # Clean up test data
        await conn.execute("DELETE FROM events WHERE source = 'test-source'")
        print("✅ Test cleanup successful")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("  Aurora Serverless Database Initialization")
    print("=" * 60)
    print()
    
    asyncio.run(init_database())
    asyncio.run(test_connection())
    
    print("\n" + "=" * 60)
    print("  ✅ Database initialization complete!")
    print("=" * 60)
