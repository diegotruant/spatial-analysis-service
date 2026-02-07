"""
Execute Supabase migration to add rr_intervals column
"""
import psycopg2
import os

# Database connection from .env
DATABASE_URL = "postgresql://postgres.xdqvjqqwywuguuhsehxm:emvtzC2B2Duu6PLg@aws-1-eu-west-3.pooler.supabase.com:6543/postgres"

print("=" * 70)
print("SUPABASE RR_INTERVALS MIGRATION")
print("=" * 70)

try:
    # Connect to database
    print("\n🔌 Connecting to Supabase database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("✅ Connected successfully!")
    
    # Execute migration SQL
    print("\n📝 Executing migration SQL...")
    
    # 1. Add column
    print("   1. Adding rr_intervals column...")
    cursor.execute("""
        ALTER TABLE activities 
        ADD COLUMN IF NOT EXISTS rr_intervals JSONB DEFAULT '[]'::jsonb;
    """)
    print("   ✅ Column added")
    
    # 2. Add index
    print("   2. Creating GIN index...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_activities_rr_intervals 
        ON activities USING GIN (rr_intervals);
    """)
    print("   ✅ Index created")
    
    # 3. Add comment
    print("   3. Adding column comment...")
    cursor.execute("""
        COMMENT ON COLUMN activities.rr_intervals IS 
        'RR interval data in timestamped format: [{timestamp: ISO8601, elapsed: seconds, rr: [ms, ms, ...]}]';
    """)
    print("   ✅ Comment added")
    
    # Commit changes
    conn.commit()
    print("\n✅ Migration committed successfully!")
    
    # Verify column exists
    print("\n🔍 Verifying migration...")
    cursor.execute("""
        SELECT column_name, data_type, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'activities' 
        AND column_name = 'rr_intervals';
    """)
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Column verified:")
        print(f"   Name: {result[0]}")
        print(f"   Type: {result[1]}")
        print(f"   Default: {result[2]}")
    else:
        print("⚠️ Column not found (this shouldn't happen)")
    
    # Close connection
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("🎉 MIGRATION COMPLETE!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. ✅ Database ready to receive RR data")
    print("  2. 📱 Test workout with Rhythm 24")
    print("  3. 🔍 Verify RR data saved in database")
    
except psycopg2.Error as e:
    print(f"\n❌ Database error: {e}")
    print("\nCommon issues:")
    print("  - Connection timeout: Check if IP is whitelisted in Supabase")
    print("  - Authentication: Verify DATABASE_URL is correct")
    
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
