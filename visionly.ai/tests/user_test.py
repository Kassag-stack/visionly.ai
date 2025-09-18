import requests
import json
import os

# VM endpoint with the correct path
url = os.getenv("BACKEND_API_URL")
if not url:
    raise ValueError("BACKEND_API_URL not found in environment variables")
function_code = os.getenv("API_FUNCTION_CODE")
params = {"code": function_code} if function_code else None

# Headers
headers = {
    "Content-Type": "application/json"
}

# Read shopify data
with open('shopify_data.json', 'r') as f:
    shopify_data = json.load(f)

# Test data to send
data = {
    "message": shopify_data
}

try:
    # Make the POST request
    response = requests.post(url, params=params, headers=headers, json=data)
    print("Status Code:", response.status_code)
    print("Response:", response.json())
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to the server!")
except Exception as e:
    print("Error:", str(e))
