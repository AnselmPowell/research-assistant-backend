"""
Test script to verify Neon PostgreSQL database connection.
"""

import os
import sys
import psycopg2
import time
from dotenv import load_dotenv

def test_connection():
    """Test connection to the Neon PostgreSQL database."""
    load_dotenv()
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("ERROR: No DATABASE_URL found in environment variables")
        return False
    
    try:
        print(f"Connecting to Neon database...")
        # Mask credentials in logs
        masked_url = database_url.replace(database_url.split('@')[0], '******')
        print(f"Using: {masked_url}")
        
        # Connect to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Execute a simple query
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        
        # Test a simple table creation and query
        print("Testing database operations...")
        cursor.execute("CREATE TABLE IF NOT EXISTS connection_test (id SERIAL PRIMARY KEY, test_date TIMESTAMP DEFAULT NOW());")
        cursor.execute("INSERT INTO connection_test (test_date) VALUES (NOW()) RETURNING id;")
        test_id = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM connection_test WHERE id = %s;", (test_id,))
        test_result = cursor.fetchone()
        
        # Clean up test table
        cursor.execute("DROP TABLE connection_test;")
        
        # Commit changes
        conn.commit()
        
        # Close the connection
        cursor.close()
        conn.close()
        
        print(f"Successfully connected to PostgreSQL. Version: {db_version[0]}")
        print(f"Database connection test successful. Created test record with ID: {test_id}")
        return True
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
