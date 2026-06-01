import os
import sys
from dotenv import load_dotenv
import psycopg

def main():
    # Load environment variables from .env
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in .env file.")
        sys.exit(1)
        
    sql_file_path = os.path.join(os.path.dirname(__file__), "EstructuraSqlNuevo.sql")
    if not os.path.exists(sql_file_path):
        print(f"Error: SQL file not found at {sql_file_path}")
        sys.exit(1)
        
    print("Connecting to Supabase PostgreSQL database...")
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                print(f"Reading SQL schema from {sql_file_path}...")
                with open(sql_file_path, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                
                print("Executing SQL migration script on Supabase...")
                cursor.execute(sql_content)
                conn.commit()
                print("Database migration completed successfully!")
    except Exception as e:
        print(f"An error occurred during migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
