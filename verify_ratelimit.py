import urllib.request
import urllib.error
import urllib.parse
import json
import time

# --- CONFIG ---
BACKEND_URL = "http://localhost:8010/api/mesh/generate"
# Use a dummy token if you can't reach PB easily, but backend MIGHT reject it if PB is reachable.
# Ideally, we should use a valid token.
# For this test, if we get 401, it counts as "Verification Passed" for Rate Limiter NOT blocking (yet).
# If we get 429, it counts as "Rate Limit Hit".

# Valid Payload
payload = {
    "polygons": [
        {
            "vertices": [{"x":0,"y":0}, {"x":10,"y":0}, {"x":10,"y":10}, {"x":0,"y":10}],
            "materialId": "mat1"
        }
    ],
    "materials": [{"id":"mat1","name":"T","poissonsRatio":0.3,"unitWeightUnsaturated":18,"youngsModulus":1000}],
    "pointLoads": [], "lineLoads": [], "mesh_settings": {}, "water_levels": []
}
json_payload = json.dumps(payload).encode('utf-8')

# Mock Token (or retrieve one if possible)
token = "test_token_for_rate_limit" 
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def send_request(i):
    try:
        req = urllib.request.Request(BACKEND_URL, data=json_payload, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            print(f"Req {i}: Status {response.getcode()}")
            return response.getcode()
    except urllib.error.HTTPError as e:
        print(f"Req {i}: Status {e.code}")
        # print(e.read().decode('utf-8'))
        return e.code
    except Exception as e:
        print(f"Req {i}: Failed {e}")
        return None

print("--- Starting Rate Limit Test (5 req/min) ---")
print("These requests might fail with 401 if token is invalid, but that still counts as a 'request' for the limiter usually, OR the limiter runs after Auth.")
print("Wait... Limiter key is User ID. If Auth fails, User ID is None (or IP).")
print("So unauthenticated requests might be limited by IP!")

for i in range(1, 8):
    code = send_request(i)
    if code == 429:
        print("✅ SUCCESS: Rate Limit Hit (429)!")
        break
    time.sleep(0.5)
