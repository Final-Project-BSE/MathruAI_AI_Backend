import pymysql
import sys

# Your credentials from config.py
MYSQL_USER = 'root'
MYSQL_PASSWORD = '20000624'
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_DATABASE = 'rag_system'

print("Testing MySQL connection...")
print(f"Host: {MYSQL_HOST}:{MYSQL_PORT}")
print(f"User: {MYSQL_USER}")
print(f"Database: {MYSQL_DATABASE}")
print()

try:
    # Try to connect
    connection = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4'
    )
    print("✓ Connection successful!")
    
    # Test query
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"MySQL version: {version[0]}")
    
    connection.close()
    print("\n✓ All tests passed!")
    
except pymysql.err.OperationalError as e:
    error_code, error_msg = e.args
    print(f"✗ Connection failed!")
    print(f"Error {error_code}: {error_msg}")
    print()
    
    if error_code == 1045:
        print("Possible solutions:")
        print("1. Check if the password is correct")
        print("2. Run: mysql -u root -p")
        print("   Then enter your password to verify it works")
        print("3. If you don't know the password, reset it:")
        print("   - Stop MySQL service")
        print("   - Start MySQL with --skip-grant-tables")
        print("   - Reset password")
    elif error_code == 1049:
        print(f"Database '{MYSQL_DATABASE}' doesn't exist")
        print("Create it with: CREATE DATABASE rag_system;")
    
    sys.exit(1)
    
except Exception as e:
    print(f"✗ Unexpected error: {str(e)}")
    sys.exit(1)