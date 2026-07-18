import asyncio
from fastapi.testclient import TestClient
from app.main import app

def main():
    client = TestClient(app)
    try:
        print("Testing POST /auth/signup via TestClient...")
        response = client.post(
            "/auth/signup",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": "t4@t.com",
                "phone": "03001234567",
                "password": "password123"
            }
        )
        print("Response status:", response.status_code)
        print("Response body:", response.text)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
