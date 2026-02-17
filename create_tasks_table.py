"""
Create 'analysis_tasks' table in Supabase for async job tracking.
"""
import psycopg2
import os

# Database connection from .env (hardcoded for this script based on previous context)
DATABASE_URL = "postgresql://postgres.xdqvjqqwywuguuhsehxm:emvtzC2B2Duu6PLg@aws-1-eu-west-3.pooler.supabase.com:6543/postgres"

print("=" * 70)
print("SUPABASE ANALYSIS_TASKS MIGRATION")
print("=" * 70)

try:
    # Connect to database
    print("\n🔌 Connecting to Supabase database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ Connected successfully!")
    
    # Execute migration SQL
    print("\n📝 Executing migration SQL...")
    
    # 1. Create Table
    print("   1. Creating analysis_tasks table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_tasks (
            task_id UUID PRIMARY KEY,
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            result JSONB,
            error TEXT
        );
    """)
    print("   ✅ Table created")
    
    # 2. Add Index on Status (optional but good for polling if we had many)
    print("   2. Creating index on status...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status 
        ON analysis_tasks (status);
    """)
    print("   ✅ Index created")
    
    # Commit changes
    conn.commit()
    print("\n✅ Migration committed successfully!")
    
    # Verify table
    print("\n🔍 Verifying table...")
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'analysis_tasks';
    """)
    columns = cursor.fetchall()
    
    if columns:
        print(f"✅ Table verified with {len(columns)} columns:")
        for col in columns:
            print(f"   - {col[0]} ({col[1]})")
    else:
        print("⚠️ Table not found (this shouldn't happen)")
    
    # Close connection
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("🎉 MIGRATION COMPLETE!")
    print("=" * 70)
    
except psycopg2.Error as e:
    print(f"\n❌ Database error: {e}")
    
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
