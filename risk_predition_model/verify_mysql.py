# #!/usr/bin/env python3
# """
# Check if environment variables are loaded correctly
# """

# import os
# from dotenv import load_dotenv

# print("=" * 70)
# print("Environment Variables Check")
# print("=" * 70)

# # Load .env file
# env_file = '.env'
# if os.path.exists(env_file):
#     print(f"✓ Found .env file at: {os.path.abspath(env_file)}")
#     load_dotenv()
# else:
#     print(f"❌ .env file not found at: {os.path.abspath(env_file)}")
#     print("\nSearching for .env in parent directories...")
    
#     # Check parent directories
#     current_dir = os.getcwd()
#     for i in range(3):  # Check up to 3 levels up
#         parent = os.path.dirname(current_dir)
#         env_path = os.path.join(parent, '.env')
#         if os.path.exists(env_path):
#             print(f"✓ Found .env at: {env_path}")
#             load_dotenv(env_path)
#             break
#         current_dir = parent
#     else:
#         print("❌ No .env file found in parent directories")

# print("\n" + "=" * 70)
# print("MySQL Configuration")
# print("=" * 70)

# # Check MySQL variables
# mysql_vars = {
#     'MYSQL_USER': os.getenv('MYSQL_USER'),
#     'MYSQL_PASSWORD': os.getenv('MYSQL_PASSWORD'),
#     'MYSQL_HOST': os.getenv('MYSQL_HOST'),
#     'MYSQL_PORT': os.getenv('MYSQL_PORT'),
#     'MYSQL_DATABASE': os.getenv('MYSQL_DATABASE'),
# }

# all_set = True
# for key, value in mysql_vars.items():
#     if value:
#         # Mask password
#         display_value = '*' * len(value) if 'PASSWORD' in key else value
#         print(f"✓ {key:20} = {display_value}")
#     else:
#         print(f"❌ {key:20} = NOT SET")
#         all_set = False

# # Construct database URI
# if all_set:
#     print("\n" + "=" * 70)
#     print("Database URI")
#     print("=" * 70)
#     user = mysql_vars['MYSQL_USER']
#     password = mysql_vars['MYSQL_PASSWORD']
#     host = mysql_vars['MYSQL_HOST']
#     port = mysql_vars['MYSQL_PORT']
#     database = mysql_vars['MYSQL_DATABASE']
    
#     uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
#     masked_uri = f"mysql+pymysql://{user}:****@{host}:{port}/{database}?charset=utf8mb4"
#     print(masked_uri)
    
#     # Test connection
#     print("\n" + "=" * 70)
#     print("Testing Connection")
#     print("=" * 70)
#     try:
#         import pymysql
#         conn = pymysql.connect(
#             host=host,
#             port=int(port),
#             user=user,
#             password=password,
#             database=database
#         )
#         print("✓ Connection successful!")
#         conn.close()
#     except Exception as e:
#         print(f"❌ Connection failed: {e}")

# print("\n" + "=" * 70)
# print("Other Configuration")
# print("=" * 70)

# other_vars = {
#     'FLASK_ENV': os.getenv('FLASK_ENV', 'not set'),
#     'DEBUG': os.getenv('DEBUG', 'not set'),
#     'JWT_SECRET': '***' if os.getenv('JWT_SECRET') else 'not set',
#     'HOST': os.getenv('HOST', 'not set'),
#     'PORT': os.getenv('PORT', 'not set'),
# }

# for key, value in other_vars.items():
#     print(f"{key:20} = {value}")

# print("\n" + "=" * 70)
# if all_set:
#     print("✓ All required MySQL variables are set!")
#     print("You can now start your Flask application.")
# else:
#     print("❌ Some MySQL variables are missing!")
#     print("\nPlease create/update your .env file with:")
#     print("""
# MYSQL_USER=root
# MYSQL_PASSWORD=20000624
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_DATABASE=mathruai_database
#     """)
# print("=" * 70)