import asyncio
from httpx import AsyncClient

async def run():
    async with AsyncClient() as client:
        # We need a user to log in and get a token. Let's register a temporary user.
        res = await client.post("http://127.0.0.1:8000/api/auth/register", json={
            "username": "test_apply_user1",
            "email": "test_apply1@test.com",
            "password": "password123",
            "full_name": "Test Apply"
        })
        
        # Login
        res = await client.post("http://127.0.0.1:8000/api/auth/login", data={
            "username": "test_apply_user1",
            "password": "password123"
        })
        token = res.json().get("access_token")
        
        # Apply
        res = await client.post("http://127.0.0.1:8000/api/consultants/apply", json={
            "display_name": "Dr. Testing",
            "consultant_type": "clinical",
            "highest_qualification": "MD"
        }, headers={"Authorization": f"Bearer {token}"})
        
        print("Status:", res.status_code)
        print("Body:", res.text)

asyncio.run(run())
