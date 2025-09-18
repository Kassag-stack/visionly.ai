"""
Shopify Data Analyzer - First understands the store data, then generates API recommendations
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init
import requests
import subprocess
import pandas as pd

# Add parent directory to Python path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Add project root and scripts directory to Python path
root_dir = os.path.dirname(parent_dir)
scripts_dir = os.path.join(root_dir, 'scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from run_apis import collect_analysis_files

# Initialize colorama
colorama_init(autoreset=True)

# Load environment variables
load_dotenv()

# Configuration
SHOPIFY_DATA_PATH = Path(parent_dir) / 'shopify_data.json'
API_INPUT_PATH = Path(parent_dir) / 'api_input_data.json'
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL")
if not OPENWEBUI_URL:
    raise ValueError(f"{Fore.RED}OPENWEBUI_URL not found in environment variables")
OUTPUT_DIR = Path(current_dir)  # Set output directory to combined_insight

def parse_openwebui_response(response_json: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the OpenWebUI response to extract the actual content"""
    try:
        # Extract the message content from the response
        if 'choices' in response_json and len(response_json['choices']) > 0:
            message = response_json['choices'][0]['message']
            if message and 'content' in message:
                # The content might be wrapped in ```json ``` markers
                content = message['content']
                if content.startswith('```json'):
                    content = content.split('```json')[1]
                if content.endswith('```'):
                    content = content.rsplit('```', 1)[0]
                return json.loads(content.strip())
        raise ValueError("Could not find valid JSON content in OpenWebUI response")
    except Exception as e:
        print(f"{Fore.RED}Error parsing OpenWebUI response: {str(e)}")
        raise

class ShopifyInsightGenerator:
    def __init__(self):
        """Initialize OpenWebUI client and check required environment variables"""
        # Check required API key
        self.api_key = os.getenv('OPENWEBUI_API_KEY')
        
        # Track files created in this run
        self.created_files = []
        
        if not self.api_key:
            raise ValueError(f"{Fore.RED}OPENWEBUI_API_KEY not found in environment variables")
            
        # Check if required files exist
        if not SHOPIFY_DATA_PATH.exists():
            raise FileNotFoundError(f"{Fore.RED}Shopify data file not found: {SHOPIFY_DATA_PATH}")
        if not API_INPUT_PATH.exists():
            raise FileNotFoundError(f"{Fore.RED}API input data file not found: {API_INPUT_PATH}")
            
        print(f"{Fore.GREEN}✓ OpenWebUI client initialized successfully")

    def track_file(self, filepath: str, file_type: str = ""):
        """Track a newly created file"""
        # Convert WindowsPath to string if needed
        if hasattr(filepath, '__fspath__'):
            filepath = str(filepath)
        self.created_files.append((filepath, file_type))

    def save_and_upload(self, df: pd.DataFrame, path: str, fname: str, bucket: str) -> None:
        """Save DataFrame to CSV and upload to Supabase"""
        try:
            df.to_csv(path)
            print(f"{Fore.GREEN}✓ CSV saved → {path}")
            self.track_file(path, "CSV")
            
            # Upload to Supabase
            upload_supabase(df.to_csv(), fname, bucket)
            print(f"{Fore.GREEN}✓ Uploaded to Supabase: {fname}")
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to save/upload file: {str(e)}")
            raise

    def save_json(self, data: Dict, filename: str, fname: str = None) -> Dict:
        """Save JSON data to file and return the data"""
        try:
            # Use OUTPUT_DIR for the file path
            path = OUTPUT_DIR / filename
            with open(str(path), 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"{Fore.GREEN}✓ JSON saved → {path}")
            self.track_file(str(path), "JSON")
            
            if fname:
                # Upload to Supabase if filename provided
                upload_supabase(json.dumps(data, indent=2), fname, "chat-csv")
                print(f"{Fore.GREEN}✓ Uploaded to Supabase: {fname}")
            
            return data
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to save JSON: {str(e)}")
            raise

    def load_shopify_data(self) -> Dict[str, Any]:
        """Load Shopify data from JSON file"""
        try:
            with open(SHOPIFY_DATA_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to load Shopify data: {str(e)}")
            raise

    def load_api_input_data(self) -> Dict[str, Any]:
        """Load current API input data"""
        try:
            with open(API_INPUT_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to load API input data: {str(e)}")
            raise

    def update_api_input_data(self, recommendations: Dict[str, Any]) -> None:
        """Update api_input_data.json with new recommendations"""
        print(f"\n{Fore.CYAN}▶ Updating API input data...")
        
        try:
            # Load current API input data to preserve other fields
            api_input_data = self.load_api_input_data()
            
            # Update the 'apis' section with new recommendations
            if 'apis' in recommendations:
                api_input_data['apis'] = recommendations['apis']
                
                # Write updated data back to file with UTF-8 encoding
                self.save_json(api_input_data, API_INPUT_PATH)
                print(f"{Fore.GREEN}✓ API input data updated successfully")
            else:
                raise ValueError("Recommendations do not contain 'apis' section")
            
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to update API input data: {str(e)}")
            raise

    def run_apis(self) -> None:
        """Run the run_apis.py script"""
        print(f"\n{Fore.CYAN}▶ Running API analysis pipeline...")
        
        try:
            # Set up environment with proper encoding
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # Run the script with shell=True for Windows compatibility
            if os.name == 'nt':  # Windows
                process = subprocess.Popen(
                    ['python', os.path.join('scripts', 'run_apis.py')],  # Execute from scripts folder
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True,
                    encoding='utf-8',
                    env=env,
                    errors='replace'  # Handle any encoding errors gracefully
                )
            else:  # Unix-like
                process = subprocess.Popen(
                    ['python', os.path.join('scripts', 'run_apis.py')],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    env=env
                )
            
            # Print output in real-time with error handling
            while True:
                try:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        # Replace any problematic characters
                        output = output.encode('ascii', 'replace').decode('ascii')
                        print(output.strip())
                except UnicodeEncodeError:
                    # If we get an encoding error, try to print a sanitized version
                    try:
                        print(output.encode('ascii', 'replace').decode('ascii').strip())
                    except:
                        pass
                except KeyboardInterrupt:
                    # Handle Ctrl+C gracefully
                    process.terminate()
                    print(f"\n{Fore.YELLOW}Analysis interrupted by user")
                    return
            
            # Check for errors
            return_code = process.poll()
            if return_code != 0:
                error_output = process.stderr.read()
                if error_output:
                    # Sanitize error output
                    error_output = error_output.encode('ascii', 'replace').decode('ascii')
                    print(f"{Fore.RED}Error output from scripts/run_apis.py:")
                    print(error_output)
                raise Exception(f"scripts/run_apis.py failed with return code {return_code}")
            
            print(f"{Fore.GREEN}✓ API analysis pipeline completed successfully")
            
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to run API analysis pipeline: {str(e)}")
            raise

    def understand_shopify_data(self, shopify_data: Dict[str, Any]) -> Dict[str, Any]:
        """First step: Understand the Shopify store data"""
        print(f"\n{Fore.CYAN}▶ Understanding Shopify store data...")
        
        understanding_prompt = """
        You are analyzing a Shopify store's product data to generate a structured summary.
        Focus only on the factual information present in the data.

        Analyze the provided Shopify store data and extract:
        1. Main product categories (from the actual product titles)
        2. Target market (based on product types and collections)
        3. Price positioning (based on product types)
        4. Primary season relevance
        5. Key distinguishing features

        Store Data:
        {shopify_json}

        Respond ONLY with a JSON object in this exact format, no other text:
        {{
            "main_products": ["product1", "product2"],
            "target_market": "clear description",
            "price_range": "low/medium/high",
            "seasonality": "winter/summer/year-round",
            "unique_features": ["feature1", "feature2"]
        }}
        """.format(shopify_json=json.dumps(shopify_data, indent=2))

        try:
            # Make request to understand the data
            response = requests.post(
                url=OPENWEBUI_URL,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o.gpt-4o',
                    'messages': [
                        {
                            'role': 'user',
                            'content': understanding_prompt
                        }
                    ]
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status code: {response.status_code}")
            
            understanding = parse_openwebui_response(response.json())
            print(f"{Fore.GREEN}✓ Store data understood successfully")
            return understanding
            
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to understand store data: {str(e)}")
            raise

    def prepare_api_recommendations_prompt(self, store_understanding: Dict[str, Any]) -> str:
        """Prepare the API recommendations prompt using the store understanding"""
        return '''
        You are generating specific API queries based on this Shopify store analysis:
        {store_understanding}

        Generate queries for multiple APIs that will help analyze market trends and opportunities.
        
        CRITICAL RULES:
        1. STRICT SINGLE WORD RULE:
           - ALL queries MUST be exactly ONE word
           - NO spaces, NO hyphens, NO underscores (except for finance data)
           - BAD examples: "snowboard market", "winter sports", "snow-boarding"
           - GOOD examples: "snowboarding", "skiing", "sports"

        2. For News API:
           - Still use ONLY ONE word
           - BAD: "snowboard market"
           - GOOD: "snowboarding"

        3. For Financial data ONLY:
           - Currency pairs: Use "/" (e.g., "USD/JPY", "USD/CNY")
           - Commodities: Use "_" (e.g., "WTI_CRUDE", "BRENT_CRUDE", "CRUDE_ETF")
           - Stocks: Single word (e.g., "APPLE", "MICROSOFT", "AMAZON")

        Return ONLY a JSON object in this exact format:
        {{
            "apis": {{
                "tiktokAPI": {{
                    "query": "snowboarding",  // MUST be one word
                    "number": 10
                }},
                "metaAPI": {{
                    "query": "snowboarding"  // MUST be one word
                }},
                "googleTrendsAPI": {{
                    "query": "snowboarding"  // MUST be one word
                }},
                "newsAPI": {{
                    "query": "snowboarding"  // MUST be one word
                }},
                "financeAPI": {{
                    "currency_pairs": [
                        // Choose 1-2 from: "USD/JPY", "USD/CNY"
                    ],
                    "commodities": [
                        // Choose 1-2 from: "WTI_CRUDE", "BRENT_CRUDE", "CRUDE_ETF"
                    ],
                    "stocks": [
                        // Choose 1-3 from: "STARBUCKS", "APPLE", "MICROSOFT", "AMAZON"
                    ]
                }}
            }}
        }}
        '''.format(store_understanding=json.dumps(store_understanding, indent=2))

    def validate_recommendations(self, recommendations: Dict[str, Any]) -> None:
        """Validate the API recommendations"""
        if not isinstance(recommendations, dict) or 'apis' not in recommendations:
            raise ValueError("Response does not contain required 'apis' section")
            
        apis = recommendations['apis']
        required_apis = ['tiktokAPI', 'metaAPI', 'googleTrendsAPI', 'newsAPI', 'financeAPI']
        
        # Check all required APIs are present
        for api in required_apis:
            if api not in apis:
                raise ValueError(f"Missing required API section: {api}")
        
        # Validate single word queries (TikTok, Meta, and Google Trends)
        for api in ['tiktokAPI', 'metaAPI', 'googleTrendsAPI']:
            if 'query' not in apis[api]:
                raise ValueError(f"{api} missing query")
            query = apis[api]['query'].strip()
            if ' ' in query:
                raise ValueError(f"{api} query must be a single word (no spaces)")
            if len(query) > 20:
                raise ValueError(f"{api} query is too long (max 20 characters)")
            if not query.isalnum():
                raise ValueError(f"{api} query must only contain letters and numbers")
        
        # Validate News API query (max 2 words)
        if 'query' not in apis['newsAPI']:
            raise ValueError("News API missing query")
        news_query = apis['newsAPI']['query'].strip()
        if len(news_query.split()) > 2:
            raise ValueError("News API query must be maximum two words")
        
        # Validate Finance API selections
        finance = apis['financeAPI']
        valid_currencies = ["USD/JPY", "USD/CNY"]
        valid_commodities = ["WTI_CRUDE", "BRENT_CRUDE", "CRUDE_ETF"]
        valid_stocks = ["STARBUCKS", "APPLE", "MICROSOFT", "AMAZON"]
        
        for pair in finance.get('currency_pairs', []):
            if pair not in valid_currencies:
                raise ValueError(f"Invalid currency pair: {pair}")
        
        for commodity in finance.get('commodities', []):
            if commodity not in valid_commodities:
                raise ValueError(f"Invalid commodity: {commodity}")
                
        for stock in finance.get('stocks', []):
            if stock not in valid_stocks:
                raise ValueError(f"Invalid stock: {stock}")

    def generate_api_recommendations(self, store_understanding: Dict[str, Any]) -> Dict[str, Any]:
        """Second step: Generate API recommendations based on store understanding"""
        print(f"\n{Fore.CYAN}▶ Generating API recommendations based on store understanding...")
        
        try:
            # Make request for API recommendations
            response = requests.post(
                url=OPENWEBUI_URL,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o.gpt-4o',
                    'messages': [
                        {
                            'role': 'user',
                            'content': self.prepare_api_recommendations_prompt(store_understanding)
                        }
                    ]
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status code: {response.status_code}")
            
            recommendations = parse_openwebui_response(response.json())
            
            # Validate the recommendations
            self.validate_recommendations(recommendations)
            
            print(f"{Fore.GREEN}✓ API recommendations generated successfully")
            return recommendations
            
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to generate API recommendations: {str(e)}")
            raise

    def summarize_analysis_results(self) -> str:
        """Create a text summary of analysis results from files created in this run"""
        summary = []
        
        # Group files by API type
        api_files = {
            "TikTok": [],
            "Meta": [],
            "Google Trends": [],
            "News": [],
            "Finance": []
        }
        
        # Categorize created files by API
        for filepath, _ in self.created_files:
            filepath = str(filepath)
            if "tiktok_api" in filepath:
                api_files["TikTok"].append(filepath)
            elif "meta_api" in filepath:
                api_files["Meta"].append(filepath)
            elif "google_trends" in filepath:
                api_files["Google Trends"].append(filepath)
            elif "news_api" in filepath:
                api_files["News"].append(filepath)
            elif "finance_api" in filepath:
                api_files["Finance"].append(filepath)
        
        # Process each API's files
        for api_name, file_paths in api_files.items():
            if not file_paths:  # Skip if no files for this API
                continue
                
            api_summary = [f"\n{api_name} Analysis:"]
            
            for file_path in file_paths:
                try:
                    if file_path.endswith('.json'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Extract key metrics and insights
                            if isinstance(data, dict):
                                for key, value in data.items():
                                    if isinstance(value, (str, int, float)):
                                        api_summary.append(f"- {key}: {value}")
                                    elif isinstance(value, list) and len(value) < 5:
                                        api_summary.append(f"- {key}: {', '.join(map(str, value))}")
                    
                    elif file_path.endswith('.csv'):
                        df = pd.read_csv(file_path)
                        # Get basic statistics
                        api_summary.append(f"- Row count: {len(df)}")
                        if len(df.columns) < 5:  # Only summarize if few columns
                            for col in df.columns:
                                if df[col].dtype in ['int64', 'float64']:
                                    avg = df[col].mean()
                                    api_summary.append(f"- Average {col}: {avg:.2f}")
                
                except Exception as e:
                    api_summary.append(f"- Error reading file: {str(e)}")
            
            if len(api_summary) > 1:  # Only add if we have actual data
                summary.extend(api_summary)
        
        return "\n".join(summary)

    def get_api_analysis_results(self) -> Dict[str, Any]:
        """Get analysis results from files created in this run"""
        results = {
            "TikTok": {},
            "Meta": {},
            "Google Trends": {},
            "News": {},
            "Finance": {}
        }
        
        # Process files created in this run
        for filepath, _ in self.created_files:
            filepath = str(filepath)
            try:
                if filepath.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                        # Categorize by API
                        if "tiktok_api" in filepath:
                            results["TikTok"].update(data)
                        elif "meta_api" in filepath:
                            results["Meta"].update(data)
                        elif "google_trends" in filepath:
                            results["Google Trends"].update(data)
                        elif "news_api" in filepath:
                            results["News"].update(data)
                        elif "finance_api" in filepath:
                            results["Finance"].update(data)
                
                elif filepath.endswith('.csv'):
                    df = pd.read_csv(filepath)
                    data = {
                        "data": df.to_dict(orient='records'),
                        "summary": {
                            "row_count": len(df),
                            "columns": list(df.columns)
                        }
                    }
                    
                    # Categorize by API
                    if "tiktok_api" in filepath:
                        results["TikTok"][os.path.basename(filepath)] = data
                    elif "meta_api" in filepath:
                        results["Meta"][os.path.basename(filepath)] = data
                    elif "google_trends" in filepath:
                        results["Google Trends"][os.path.basename(filepath)] = data
                    elif "news_api" in filepath:
                        results["News"][os.path.basename(filepath)] = data
                    elif "finance_api" in filepath:
                        results["Finance"][os.path.basename(filepath)] = data
            
            except Exception as e:
                print(f"{Fore.YELLOW}Warning: Could not read {filepath}: {str(e)}")
        
        return results

    def generate_detailed_insights(self, shopify_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed insights and recommendations using ChatGPT"""
        print(f"\n{Fore.CYAN}▶ Generating detailed insights and recommendations...")
        
        # Get API analysis results
        api_results = self.get_api_analysis_results()
        
        insights_prompt = '''
        You are analyzing the results from multiple API analyses to provide insights for a Shopify store.
        
        API Analysis Results:
        {api_results}
        
        Based on these API analysis results, provide a detailed analysis in JSON format with the following structure:
        1. Key findings from each data source
        2. Specific recommendations for the store
        3. Product improvements (title, description, price adjustments)
        4. Marketing strategy suggestions
        5. Growth opportunities
        
        IMPORTANT RULES:
        1. Do not use any hyphens in your response
        2. Use clear, actionable suggestions
        3. Focus on practical, implementable changes
        4. Include specific examples where possible
        5. Keep suggestions realistic and data driven
        
        Return ONLY a JSON object with this structure:
        {{
            "key_findings": {{
                "tiktok_insights": [],
                "meta_insights": [],
                "google_trends_insights": [],
                "news_insights": [],
                "finance_insights": []
            }},
            "store_recommendations": {{
                "product_improvements": {{
                    "title_changes": [],
                    "description_updates": [],
                    "price_adjustments": []
                }},
                "marketing_strategy": [],
                "growth_opportunities": []
            }}
        }}
        '''
        
        try:
            # Make request for detailed insights with API results
            response = requests.post(
                url=OPENWEBUI_URL,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o.gpt-4o',
                    'messages': [
                        {
                            'role': 'user',
                            'content': insights_prompt.format(
                                api_results=json.dumps(api_results, indent=2)
                            )
                        }
                    ],
                    'max_tokens': 4000
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status code: {response.status_code}")
            
            insights = parse_openwebui_response(response.json())
            
            # Save insights with timestamp
            timestamped_file = f'shopify_analysis_response_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            self.save_json(insights, timestamped_file)
            print(f"{Fore.GREEN}✓ Detailed insights saved to: {timestamped_file}")
            
            # Also save a non-timestamped version and return it
            standard_file = 'shopify_analysis_response.json'
            return self.save_json(insights, standard_file)
            
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to generate detailed insights: {str(e)}")
            raise

    def run_analysis(self) -> Dict[str, Any]:
        """Run the complete analysis pipeline"""
        try:
            print(f"\n{Fore.CYAN}={'='*50}")
            print(f"{Fore.CYAN}🔍 ANALYZING STORE & GENERATING API RECOMMENDATIONS")
            print(f"{Fore.CYAN}={'='*50}")
            
            # Step 1: Load and understand the store data
            shopify_data = self.load_shopify_data()
            understanding = self.understand_shopify_data(shopify_data)
            
            # Print store understanding
            print(f"\n{Fore.CYAN}Store Understanding:")
            for key, value in understanding.items():
                print(f"{Fore.YELLOW}{key}:")
                if isinstance(value, list):
                    for item in value:
                        print(f"  - {item}")
                else:
                    print(f"  {value}")
            
            # Step 2: Generate API recommendations
            recommendations = self.generate_api_recommendations(understanding)
            
            # Save results
            output = {
                "store_understanding": understanding,
                "api_recommendations": recommendations
            }
            
            # Save results with UTF-8 encoding
            output_file = f'api_recommendations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            self.save_json(output, output_file)
            
            print(f"\n{Fore.GREEN}✓ Analysis complete! Results saved to: {output_file}")
            
            # Print API recommendations summary
            print(f"\n{Fore.CYAN}API Recommendations Summary:")
            if isinstance(recommendations, dict) and 'apis' in recommendations:
                apis = recommendations['apis']
                for api_name, api_data in apis.items():
                    print(f"\n{Fore.YELLOW}{api_name}:")
                    for key, value in api_data.items():
                        print(f"  {key}: {value}")
                        
                # Step 3: Update api_input_data.json
                print(f"\n{Fore.CYAN}▶ Updating API input data and running analysis...")
                self.update_api_input_data(recommendations)
                
                # Step 4: Run the APIs
                self.run_apis()
                
                # Step 5: Generate detailed insights
                detailed_insights = self.generate_detailed_insights(shopify_data)
                
                # Print insights summary
                print(f"\n{Fore.CYAN}{'='*50}")
                print(f"{Fore.CYAN}📊 DETAILED INSIGHTS SUMMARY")
                print(f"{Fore.CYAN}{'='*50}")
                
                if detailed_insights:
                    # Print key findings
                    print(f"\n{Fore.YELLOW}Key Findings:")
                    for api, insights in detailed_insights.get('key_findings', {}).items():
                        print(f"\n{Fore.CYAN}{api}:")
                        for insight in insights:
                            print(f"  • {insight}")
                
                    # Print recommendations
                    print(f"\n{Fore.YELLOW}Store Recommendations:")
                    recommendations = detailed_insights.get('store_recommendations', {})
                
                    # Product improvements
                    if 'product_improvements' in recommendations:
                        print(f"\n{Fore.CYAN}Product Improvements:")
                        for category, changes in recommendations['product_improvements'].items():
                            print(f"\n  {category.replace('_', ' ').title()}:")
                            for change in changes:
                                print(f"    • {change}")
                    
                    # Marketing and growth
                    for category in ['marketing_strategy', 'growth_opportunities']:
                        if category in recommendations:
                            print(f"\n{Fore.CYAN}{category.replace('_', ' ').title()}:")
                            for item in recommendations[category]:
                                print(f"  • {item}")
                
                    return detailed_insights
            
            # If we get here without returning, return an empty dict
            return {"status": "error", "message": "No valid API recommendations found in response"}
            
        except Exception as e:
            print(f"\n{Fore.RED}✗ Analysis failed: {str(e)}")
            raise

def main():
    """Main entry point"""
    try:
        generator = ShopifyInsightGenerator()
        generator.run_analysis()
    except Exception as e:
        print(f"\n{Fore.RED}Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
