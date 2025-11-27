import jwt
import base64

TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkaGFtbWlrYUBnbWFpbC5jb20iLCJpYXQiOjE3NjQyMjU4NzEsImV4cCI6MTc2NDgzMDY3MX0.MBkT-w71kt-8XMhdCentRZ4KnOxA9-fc9r0lqxOJo1U"

# Base64 string from application.properties
JWT_SECRET_BASE64 = "U2VjdXJlSldUS2V5MTIzITIzITIzIUxvbmdFbm91hfshfjshfZ2gadsd"

# Decode it like Spring Boot does
JWT_SECRET = base64.b64decode(JWT_SECRET_BASE64)

try:
    decoded = jwt.decode(TOKEN, JWT_SECRET, algorithms=["HS256"])
    print("✅ SUCCESS!")
    print(f"Email: {decoded['sub']}")
    print(f"Issued at: {decoded['iat']}")
    print(f"Expires: {decoded['exp']}")
except jwt.ExpiredSignatureError:
    print("⚠️ Token expired, but secret is CORRECT!")
except Exception as e:
    print(f"❌ Error: {e}")