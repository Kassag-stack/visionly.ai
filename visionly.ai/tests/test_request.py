import requests
import json
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API endpoint
OPENWEBUI_URL = os.getenv('OPENWEBUI_URL')
API_KEY = os.getenv('OPENWEBUI_API_KEY')

# Check if required env exists
if not OPENWEBUI_URL:
    raise ValueError("OPENWEBUI_URL not found in environment variables")
if not API_KEY:
    raise ValueError("OPENWEBUI_API_KEY not found in environment variables")

# Read Shopify data
SHOPIFY_DATA_PATH = Path(__file__).resolve().parent.parent / 'shopify_data.json'
if not SHOPIFY_DATA_PATH.exists():
    raise FileNotFoundError(f"Shopify data file not found: {SHOPIFY_DATA_PATH}")

shopify_data = json.loads(SHOPIFY_DATA_PATH.read_text())

# Headers
headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

# Prepare the analysis prompt
PROMPT_ANALYSIS = """
Analyze this Shopify store data and provide insights about:
1. Product trends and popular items
2. Collection organization and potential improvements
3. Inventory management suggestions
4. Marketing recommendations

Store Data:
{shopify_json}

Please provide a detailed analysis with actionable recommendations.
"""

# Request body
data = {
    'model': 'gpt-4o.gpt-4o',
    'messages': [
        {
            'role': 'user',
            'content': PROMPT_ANALYSIS.format(shopify_json=json.dumps(shopify_data, indent=2))
        }
    ]
}

try:
    # Make the POST request
    response = requests.post(
        url=OPENWEBUI_URL,
        headers=headers,
        json=data
    )
    
    # Check response status
    print(f"Status Code: {response.status_code}")
    
    # Try to parse and print JSON response
    try:
        formatted_response = json.dumps(response.json(), indent=2)
        print(f"Response:\n{formatted_response}")
        
        # Save response to file
        output_file = 'shopify_analysis_response.json'
        with open(output_file, 'w') as f:
            f.write(formatted_response)
        print(f"\nResponse saved to: {output_file}")
        
    except json.JSONDecodeError:
        print(f"Raw Response:\n{response.text}")
        
except requests.exceptions.RequestException as e:
    print(f"Error making request: {str(e)}") 