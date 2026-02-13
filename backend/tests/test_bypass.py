import asyncio
import httpx
import json
import time

BASE_URL = "http://localhost:8010"

async def test_auth_bypass():
    print("\n--- Testing Authentication Bypass ---")
    print("Ensure BYPASS_AUTH=True in backend/.env then restart backend.")
    
    # Valid MeshRequest data
    data = {
        "polygons": [
            {
                "vertices": [{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}],
                "materialId": "mat_1"
            }
        ],
        "materials": [
            {
                "id": "mat_1",
                "name": "Test Material",
                "color": "#ff0000",
                "poissonsRatio": 0.3,
                "unitWeightUnsaturated": 18.0
            }
        ],
        "pointLoads": [],
        "lineLoads": [],
        "mesh_settings": {"mesh_size": 2.0}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Request WITHOUT Authorization header
            response = await client.post(f"{BASE_URL}/api/mesh/generate", json=data, timeout=10.0)
            
            if response.status_code == 200:
                print("✅ SUCCESS: Accessed protected endpoint without token!")
                print(f"Server Response Success: {response.json().get('success')}")
            elif response.status_code == 401:
                print("❌ FAILED: Still receiving 401 Unauthorized. Is BYPASS_AUTH=True?")
            elif response.status_code == 422:
                print("❌ FAILED: Schema error (422). Please check if MeshRequest model changed.")
                print(f"Error Detail: {response.text}")
            else:
                print(f"❓ ERROR: Received status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"💥 Connection Error: {e}")

async def test_rate_limit_bypass():
    print("\n--- Testing Rate Limit Bypass ---")
    print("Ensure BYPASS_RATE_LIMIT=True in backend/.env then restart backend.")
    
    data = {
        "polygons": [
            {
                "vertices": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}, {"x": 0, "y": 1}],
                "materialId": "mat_1"
            }
        ],
        "materials": [
            {
                "id": "mat_1",
                "name": "Test Material",
                "color": "#ff0000",
                "poissonsRatio": 0.3,
                "unitWeightUnsaturated": 18.0
            }
        ],
        "pointLoads": [],
        "mesh_settings": {"mesh_size": 0.5}
    }
    
    print("Sending 10 rapid requests (Limit is 5/min)...")
    success_count = 0
    limit_count = 0
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(10):
            tasks.append(client.post(f"{BASE_URL}/api/mesh/generate", json=data, timeout=10.0))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                print(f"Request {i+1}: Error {response}")
                continue
                
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                limit_count += 1
            
            print(f"Request {i+1}: Status {response.status_code}")
            
    print(f"\nResults: {success_count} Successes, {limit_count} Rate Limited.")
    if limit_count == 0 and success_count == 10:
        print("✅ SUCCESS: Rate limit bypassed!")
    elif limit_count > 0:
        print("❌ FAILED: Still being rate limited. Is BYPASS_RATE_LIMIT=True?")

async def main():
    print("TerraSim Bypass Verification Tool (Fixed Schema)")
    await test_auth_bypass()
    await test_rate_limit_bypass()

if __name__ == "__main__":
    asyncio.run(main())
