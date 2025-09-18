import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import time
import os
from dotenv import load_dotenv
import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from supabase import create_client
import io
from colorama import Fore, Style, Back, init as colorama_init
load_dotenv()

# Initialize colorama
colorama_init(autoreset=True)

class FinanceDataLayer:
    """
    Lightweight finance data layer using yfinance (Yahoo Finance)
    Free, no API key required, comprehensive financial data
    """
    #TICKERS
    def __init__(self):
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_API_KEY')
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # Set up fixed output directories
        self.base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysed_data", "finance_logs")
        self.json_dir = os.path.join(self.base_dir, "json")
        self.images_dir = os.path.join(self.base_dir, "images")
        
        # Generate timestamp for this analysis session
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create directories if they don't exist
        for directory in [self.json_dir, self.images_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Created directory: {Fore.CYAN}{directory}{Style.RESET_ALL}")
        
        # Currency pairs (Yahoo Finance format)
        self.currency_pairs = {
            'USD_JPY': 'USDJPY=X',
            'USD_CNY': 'USDCNY=X'
        }
        
        # Commodity symbols
        self.commodities = {
            'WTI_CRUDE': 'CL=F',      # WTI Crude Oil Futures
            'BRENT_CRUDE': 'BZ=F',    # Brent Crude Oil Futures
            'CRUDE_ETF': 'USO'        # Oil ETF as backup
        }
        
        # Common supplier stock symbols
        self.supplier_stocks = {
            'STARBUCKS': 'SBUX',
            'APPLE': 'AAPL',
            'MICROSOFT': 'MSFT',
            'AMAZON': 'AMZN'
        }
    
    def upload_to_supabase(self, file_data, filename, bucket_name):
        """
        Upload file to Supabase bucket
        
        Args:
            file_data: File data (bytes or string)
            filename (str): Name of the file
            bucket_name (str): Name of the Supabase bucket
        """
        try:
            # If file_data is a string (JSON), convert to bytes
            if isinstance(file_data, str):
                file_data = file_data.encode('utf-8')
            
            # Add finance_api prefix to filename if not already present
            if 'finance_api' not in filename:
                name, ext = os.path.splitext(filename)
                filename = f"finance_api_{name}_{self.timestamp}{ext}"
            
            # Save locally if it's a JSON file
            if filename.endswith('.json'):
                local_path = os.path.join(self.json_dir, filename)
                with open(local_path, 'wb') as f:
                    f.write(file_data)
                print(f"{Fore.GREEN}✓{Style.RESET_ALL} Saved JSON locally: {Fore.CYAN}{local_path}{Style.RESET_ALL}")
            
            # Upload to Supabase
            self.supabase.storage.from_(bucket_name).upload(
                path=filename,
                file=file_data,
                file_options={"content-type": "application/json" if filename.endswith('.json') else "image/png"}
            )
            
            # Get public URL
            url = self.supabase.storage.from_(bucket_name).get_public_url(filename)
            print(f"{Fore.GREEN}✓{Style.RESET_ALL} File uploaded to Supabase: {Fore.CYAN}{url}{Style.RESET_ALL}")
            return url
            
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error uploading to Supabase: {str(e)}")
            return None

    def save_plot_to_supabase(self, plt, filename, bucket_name):
        """
        Save matplotlib plot to Supabase
        
        Args:
            plt: Matplotlib figure
            filename (str): Name of the file
            bucket_name (str): Name of the Supabase bucket
        """
        try:
            # Save plot to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            
            # Save locally to images directory
            local_path = os.path.join(self.images_dir, filename)
            plt.savefig(local_path, format='png', dpi=300, bbox_inches='tight')
            print(f"{Fore.GREEN}✓{Style.RESET_ALL} Saved plot locally: {Fore.CYAN}{local_path}{Style.RESET_ALL}")
            
            # Upload to Supabase
            return self.upload_to_supabase(buf.getvalue(), filename, bucket_name)
            
        except Exception as e:
            print(f"{Fore.RED}✗{Style.RESET_ALL} Error saving plot to Supabase: {e}")
            return None
        finally:
            plt.close()

    def get_currency_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time currency exchange rate
        Example: USD to JPY, USD to CNY for import cost tracking
        """
        try:
            pair_symbol = f"{from_currency}{to_currency}=X"
            ticker = yf.Ticker(pair_symbol)
            
            # Get current data
            info = ticker.info
            hist = ticker.history(period="2d")
            
            if hist.empty:
                print(f"No data available for {pair_symbol}")
                return None
            
            latest_data = hist.iloc[-1]
            previous_data = hist.iloc[-2] if len(hist) > 1 else latest_data
            
            current_rate = latest_data['Close']
            change = current_rate - previous_data['Close']
            change_percent = (change / previous_data['Close']) * 100
            
            return {
                'from_currency': from_currency,
                'to_currency': to_currency,
                'symbol': pair_symbol,
                'exchange_rate': round(current_rate, 4),
                'previous_close': round(previous_data['Close'], 4),
                'change': round(change, 4),
                'change_percent': round(change_percent, 2),
                'last_updated': hist.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                'bid': info.get('bid', current_rate),
                'ask': info.get('ask', current_rate),
                'volume': int(latest_data.get('Volume', 0))
            }
            
        except Exception as e:
            print(f"Error fetching currency data for {from_currency}/{to_currency}: {e}")
            return None
    
    def get_commodity_price(self, commodity_type: str = 'WTI') -> Optional[Dict[str, Any]]:
        """
        Get commodity prices (WTI or Brent crude oil)
        Used as shipping-fuel cost proxy
        """
        try:
            if commodity_type.upper() == 'WTI':
                symbol = self.commodities['WTI_CRUDE']
            elif commodity_type.upper() == 'BRENT':
                symbol = self.commodities['BRENT_CRUDE']
            else:
                symbol = self.commodities['CRUDE_ETF']
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            info = ticker.info
            
            if hist.empty:
                print(f"No data available for {symbol}")
                return None
            
            latest_data = hist.iloc[-1]
            previous_data = hist.iloc[-2] if len(hist) > 1 else latest_data
            
            current_price = latest_data['Close']
            change = current_price - previous_data['Close']
            change_percent = (change / previous_data['Close']) * 100
            
            return {
                'commodity': commodity_type,
                'symbol': symbol,
                'price': round(current_price, 2),
                'currency': 'USD',
                'previous_close': round(previous_data['Close'], 2),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'volume': int(latest_data.get('Volume', 0)),
                'last_updated': hist.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                'high_52w': info.get('fiftyTwoWeekHigh'),
                'low_52w': info.get('fiftyTwoWeekLow')
            }
            
        except Exception as e:
            print(f"Error fetching commodity data for {commodity_type}: {e}")
            return None
    
    def get_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time stock quote for key suppliers (e.g., SBUX for Starbucks)
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d")
            info = ticker.info
            
            if hist.empty:
                print(f"No data available for {symbol}")
                return None
            
            latest_data = hist.iloc[-1]
            previous_data = hist.iloc[-2] if len(hist) > 1 else latest_data
            
            current_price = latest_data['Close']
            change = current_price - previous_data['Close']
            change_percent = (change / previous_data['Close']) * 100
            
            return {
                'symbol': symbol,
                'company_name': info.get('longName', symbol),
                'price': round(current_price, 2),
                'previous_close': round(previous_data['Close'], 2),
                'open': round(latest_data['Open'], 2),
                'high': round(latest_data['High'], 2),
                'low': round(latest_data['Low'], 2),
                'volume': int(latest_data['Volume']),
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'last_updated': hist.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                '52w_high': info.get('fiftyTwoWeekHigh'),
                '52w_low': info.get('fiftyTwoWeekLow')
            }
            
        except Exception as e:
            print(f"Error fetching stock data for {symbol}: {e}")
            return None
    
    def get_daily_time_series(self, symbol: str, period: str = "1y") -> Optional[Dict[str, Any]]:
        """
        Get daily time series data for detailed stock analysis
        period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        Default changed to 1y to get a more comprehensive view
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            info = ticker.info
            
            if hist.empty:
                print(f"No historical data available for {symbol}")
                return None
            
            # Convert to list of dictionaries
            time_series = []
            for date, row in hist.iterrows():
                time_series.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'open': round(row['Open'], 2),
                    'high': round(row['High'], 2),
                    'low': round(row['Low'], 2),
                    'close': round(row['Close'], 2),
                    'volume': int(row['Volume'])
                })
            
            return {
                'symbol': symbol,
                'company_name': info.get('longName', symbol),
                'period': period,
                'data_points': len(time_series),
                'last_updated': hist.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
                'time_series': sorted(time_series, key=lambda x: x['date'], reverse=True)
            }
            
        except Exception as e:
            print(f"Error fetching time series for {symbol}: {e}")
            return None
    
    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Efficiently fetch multiple stock quotes at once
        """
        try:
            # Join symbols for batch download
            tickers = yf.Tickers(' '.join(symbols))
            results = {}
            
            for symbol in symbols:
                try:
                    ticker = tickers.tickers[symbol]
                    hist = ticker.history(period="2d")
                    info = ticker.info
                    
                    if not hist.empty:
                        latest_data = hist.iloc[-1]
                        previous_data = hist.iloc[-2] if len(hist) > 1 else latest_data
                        
                        current_price = latest_data['Close']
                        change = current_price - previous_data['Close']
                        change_percent = (change / previous_data['Close']) * 100
                        
                        results[symbol] = {
                            'symbol': symbol,
                            'price': round(current_price, 2),
                            'change': round(change, 2),
                            'change_percent': round(change_percent, 2),
                            'volume': int(latest_data['Volume']),
                            'last_updated': hist.index[-1].strftime('%Y-%m-%d %H:%M:%S')
                        }
                except Exception as e:
                    print(f"Error fetching data for {symbol}: {e}")
                    results[symbol] = None
            
            return results
            
        except Exception as e:
            print(f"Error in batch quote fetch: {e}")
            return {}
    
    def fetch_all_trend_data(self, custom_stocks: List[str] = None, currency_pairs: list = None) -> Dict[str, Any]:
        """
        Fetch all required data for trend analysis in one method
        Call this once per day/hour as needed
        """
        print("Fetching finance data for trend analysis...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'currency_rates': {},
            'commodity_prices': {},
            'supplier_stocks': {},
            'summary': {}
        }
        
        # Currency exchange rates for import costs
        print("Fetching currency exchange rates...")
        pairs_to_fetch = currency_pairs if currency_pairs else [('USD', 'JPY'), ('USD', 'CNY')]
        for from_currency, to_currency in pairs_to_fetch:
            rate = self.get_currency_exchange_rate(from_currency, to_currency)
            if rate:
                pair_key = f"{from_currency}_{to_currency}"
                results['currency_rates'][pair_key] = rate
        
        # Commodity prices (oil as shipping-fuel proxy)
        print("Fetching commodity prices...")
        
        wti_crude = self.get_commodity_price('WTI')
        if wti_crude:
            results['commodity_prices']['WTI_CRUDE'] = wti_crude
        
        brent_crude = self.get_commodity_price('BRENT')
        if brent_crude:
            results['commodity_prices']['BRENT_CRUDE'] = brent_crude
        
        # Supplier stocks
        print("Fetching supplier stock data...")
        
        stock_symbols = custom_stocks or ['SBUX', 'AAPL', 'MSFT', 'AMZN']
        
        for symbol in stock_symbols:
            stock_data = self.get_stock_quote(symbol)
            if stock_data:
                results['supplier_stocks'][symbol] = stock_data
        
        # Create summary for quick insights
        results['summary'] = self._create_summary(results)
        
        return results
    
    def _create_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of key metrics for trend analysis"""
        summary = {
            'currency_strength': {},
            'oil_trend': {},
            'stock_performance': {}
        }
        
        # Currency strength indicators
        for pair, rate_data in data['currency_rates'].items():
            if rate_data:
                summary['currency_strength'][pair] = {
                    'rate': rate_data['exchange_rate'],
                    'trend': 'strengthening' if rate_data['change_percent'] > 0 else 'weakening',
                    'impact_on_imports': 'cheaper' if rate_data['change_percent'] > 0 else 'expensive'
                }
        
        # Oil price trend
        if 'WTI_CRUDE' in data['commodity_prices']:
            oil_data = data['commodity_prices']['WTI_CRUDE']
            summary['oil_trend'] = {
                'price': oil_data['price'],
                'trend': 'up' if oil_data['change_percent'] > 0 else 'down',
                'shipping_cost_impact': 'higher' if oil_data['change_percent'] > 0 else 'lower'
            }
        
        # Stock performance summary
        for symbol, stock_data in data['supplier_stocks'].items():
            if stock_data:
                summary['stock_performance'][symbol] = {
                    'price': stock_data['price'],
                    'trend': 'up' if stock_data['change_percent'] > 0 else 'down',
                    'change_percent': stock_data['change_percent']
                }
        
        return summary

def get_finance_summary(from_currency, to_currency):
    """
    Fetches the user-selected currency pair, WTI crude, and a key supplier stock (SBUX by default),
    and returns a summary JSON with 3-5 numeric highlights and a timestamp.
    """
    finance_data = FinanceDataLayer()
    summary = {}
    
    # User-selected currency exchange rate with 1-year history
    user_rate = finance_data.get_currency_exchange_rate(from_currency, to_currency)
    if user_rate:
        summary[f'{from_currency.lower()}_{to_currency.lower()}'] = {
            'current_rate': round(user_rate['exchange_rate'], 3),
            'change_percent': round(user_rate['change_percent'], 2),
            'history': finance_data.get_daily_time_series(f"{from_currency}{to_currency}=X", period="1y")
        }
    
    # WTI crude oil price with 1-year history
    wti = finance_data.get_commodity_price('WTI')
    if wti:
        summary['wti_usd'] = {
            'current_price': round(wti['price'], 2),
            'change_percent': round(wti['change_percent'], 2),
            'history': finance_data.get_daily_time_series('CL=F', period="1y")
        }
    
    # Key supplier stocks with 1-year history
    supplier_data = {}
    for symbol in finance_data.supplier_stocks.values():
        stock_data = finance_data.get_stock_quote(symbol)
        if stock_data:
            supplier_data[symbol] = {
                'current_price': round(stock_data['price'], 2),
                'change_percent': round(stock_data['change_percent'], 2),
                'history': finance_data.get_daily_time_series(symbol, period="1y")
            }
    summary['supplier_stocks'] = supplier_data
    
    # Timestamp
    summary['run_utc'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    return summary

def generate_visualizations(summary: Dict[str, Any], currency_pair: str) -> Tuple[str, str]:
    """
    Generate two comprehensive visualizations for the complete finance data timeframe
    """
    finance_data = FinanceDataLayer()
    
    # 1. Time Series Visualization
    fig1 = plt.figure(figsize=(20, 12))
    gs1 = fig1.add_gridspec(2, 2)
    fig1.suptitle(f'Complete Finance Data Time Series Analysis - {currency_pair}', fontsize=16, y=0.95)
    
    # Currency Exchange Rate History
    ax1 = fig1.add_subplot(gs1[0, :])
    if 'currency_rates' in summary:
        for pair, data in summary['currency_rates'].items():
            if data:
                # Get complete historical data
                from_curr, to_curr = pair.split('_')
                ticker_symbol = f"{from_curr}{to_curr}=X"
                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period="max")  # Get maximum available history
                if not hist.empty:
                    dates = hist.index
                    rates = hist['Close'].values
                    ax1.plot(dates, rates, marker='o', linestyle='-', label=pair, linewidth=2)
                    ax1.set_title('Complete Currency Exchange Rate History', fontsize=12, pad=10)
                    ax1.set_ylabel('Rate', fontsize=10)
                    ax1.grid(True, linestyle='--', alpha=0.7)
                    ax1.legend(fontsize=10)
    
    # Commodity Prices History
    ax2 = fig1.add_subplot(gs1[1, 0])
    if 'commodity_prices' in summary:
        for symbol, data in summary['commodity_prices'].items():
            if data:
                ticker = yf.Ticker(data['symbol'])
                hist = ticker.history(period="max")  # Get maximum available history
                if not hist.empty:
                    dates = hist.index
                    prices = hist['Close'].values
                    ax2.plot(dates, prices, marker='o', linestyle='-', label=symbol, linewidth=2)
        ax2.set_title('Complete Commodity Price History', fontsize=12, pad=10)
        ax2.set_ylabel('Price (USD)', fontsize=10)
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.legend(fontsize=10)
    
    # Stock Prices History
    ax3 = fig1.add_subplot(gs1[1, 1])
    if 'supplier_stocks' in summary:
        for symbol, data in summary['supplier_stocks'].items():
            if data:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="max")  # Get maximum available history
                if not hist.empty:
                    dates = hist.index
                    prices = hist['Close'].values
                    ax3.plot(dates, prices, marker='o', linestyle='-', label=symbol, linewidth=2)
        ax3.set_title('Complete Stock Price History', fontsize=12, pad=10)
        ax3.set_ylabel('Price (USD)', fontsize=10)
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.legend(fontsize=10)
    
    plt.tight_layout()
    
    # Save time series figure
    time_series_filename = f"finance_api_{currency_pair}_complete_timeseries.png"
    time_series_url = finance_data.save_plot_to_supabase(plt, time_series_filename, "chat-images")
    
    # 2. Statistical Analysis Visualization
    fig2 = plt.figure(figsize=(20, 12))
    gs2 = fig2.add_gridspec(2, 2)
    fig2.suptitle(f'Complete Finance Data Statistical Analysis - {currency_pair}', fontsize=16, y=0.95)
    
    # Daily Changes Box Plot
    ax4 = fig2.add_subplot(gs2[0, :])
    if 'supplier_stocks' in summary:
        changes_data = []
        labels = []
        for symbol, data in summary['supplier_stocks'].items():
            if data:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="max")  # Get maximum available history
                if not hist.empty:
                    daily_changes = hist['Close'].pct_change().dropna() * 100
                    changes_data.append(daily_changes.values)
                    labels.append(symbol)
        
        if changes_data:
            box = ax4.boxplot(changes_data, tick_labels=labels, patch_artist=True)
            colors = ['#2ecc71', '#3498db', '#e74c3c', '#f1c40f']
            for patch, color in zip(box['boxes'], colors):
                patch.set_facecolor(color)
            ax4.set_title('Complete Daily Price Changes Distribution', fontsize=12, pad=10)
            ax4.set_ylabel('Change (%)', fontsize=10)
            ax4.grid(True, linestyle='--', alpha=0.7)
    
    # Volatility Analysis
    ax5 = fig2.add_subplot(gs2[1, 0])
    if 'supplier_stocks' in summary:
        symbols = []
        volatilities = []
        for symbol, data in summary['supplier_stocks'].items():
            if data:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="max")  # Get maximum available history
                if not hist.empty:
                    returns = hist['Close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252) * 100  # Annualized volatility
                    symbols.append(symbol)
                    volatilities.append(volatility)
        
        if volatilities:
            bars = ax5.bar(symbols, volatilities, color=colors[:len(symbols)])
            ax5.set_title('Complete Historical Volatility', fontsize=12, pad=10)
            ax5.set_ylabel('Volatility (%)', fontsize=10)
            ax5.grid(True, linestyle='--', alpha=0.7)
            for bar in bars:
                height = bar.get_height()
                ax5.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom')
    
    # Correlation Heatmap
    ax6 = fig2.add_subplot(gs2[1, 1])
    if 'supplier_stocks' in summary:
        price_data = {}
        for symbol, data in summary['supplier_stocks'].items():
            if data:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="max")  # Get maximum available history
                if not hist.empty:
                    price_data[symbol] = hist['Close'].values
        
        if price_data:
            df = pd.DataFrame(price_data)
            corr_matrix = df.corr()
            sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0,
                       ax=ax6, fmt='.2f', square=True)
            ax6.set_title('Complete Price Correlation Matrix', fontsize=12, pad=10)
    
    plt.tight_layout()
    
    # Save statistical analysis figure
    stats_filename = f"finance_api_{currency_pair}_complete_stats.png"
    stats_url = finance_data.save_plot_to_supabase(plt, stats_filename, "chat-images")
    
    return time_series_url, stats_url

def run_finance_analysis(from_currency: str, to_currency: str) -> Dict[str, Any]:
    """
    Run finance analysis with provided currency pair parameters
    Args:
        from_currency (str): Base currency code (e.g., 'USD')
        to_currency (str): Quote currency code (e.g., 'JPY')
    Returns:
        Dict containing analysis results, filenames, and status
    """
    finance_data = FinanceDataLayer()
    result = {
        'status': 'success',
        'message': '',
        'data': {},
        'files': {}
    }

    try:
        # Validate currency codes
        if not (len(from_currency) == 3 and len(to_currency) == 3):
            raise ValueError("Invalid currency codes. Please use 3-letter codes (e.g., USD, JPY)")

        # Create base filenames without timestamps
        user_input = f"{from_currency}_{to_currency}"
        time_series_filename = f"finance_api_{user_input}_complete_timeseries.png"
        stats_filename = f"finance_api_{user_input}_complete_stats.png"
        json_filename = f"finance_api_{user_input}_complete_analysis.json"

        # Fetch exchange rate
        user_rate = finance_data.get_currency_exchange_rate(from_currency, to_currency)
        if user_rate:
            result['data']['exchange_rate'] = {
                'rate': user_rate['exchange_rate'],
                'change_percent': user_rate['change_percent']
            }
        else:
            raise ValueError(f"No data found for {from_currency}/{to_currency}")

        # Fetch supplier stock data
        result['data']['supplier_stocks'] = {}
        for symbol in finance_data.supplier_stocks.values():
            stock_data = finance_data.get_stock_quote(symbol)
            if stock_data:
                result['data']['supplier_stocks'][symbol] = {
                    'price': stock_data['price'],
                    'change_percent': stock_data['change_percent']
                }

        # Fetch all trend data for the complete timeframe
        trend_data = finance_data.fetch_all_trend_data(currency_pairs=[(from_currency, to_currency)])
        result['data']['trend_analysis'] = trend_data

        # Get complete finance summary
        summary = get_finance_summary(from_currency, to_currency)
        result['data']['summary'] = summary
        
        # Save JSON file
        json_data = json.dumps(summary, indent=2)
        json_url = finance_data.upload_to_supabase(json_data, json_filename, "chat-csv")
        result['files']['json'] = json_url

        # Generate and save visualizations for the complete timeframe
        time_series_url, stats_url = generate_visualizations(trend_data, user_input)
        result['files']['time_series'] = time_series_url
        result['files']['stats'] = stats_url

    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)

    return result

def main():
    """
    Main function that can handle both command-line arguments and direct function calls
    """
    import sys
    
    # Check if arguments are provided
    if len(sys.argv) > 1:
        # Parse first argument as currency pair
        currency_pair = sys.argv[1].upper()
        if '/' in currency_pair:
            from_currency, to_currency = currency_pair.split('/')
        else:
            # Default to USD/JPY if format is incorrect
            print(f"{Fore.YELLOW}Warning: Invalid currency pair format. Use FROM/TO (e.g., USD/JPY)")
            from_currency = "USD"
            to_currency = "JPY"
    else:
        # Default to USD/JPY if no arguments provided
        print(f"{Fore.YELLOW}No currency pair provided. Using default USD/JPY")
        from_currency = "USD"
        to_currency = "JPY"

    # Run analysis
    result = run_finance_analysis(from_currency, to_currency)
    
    # Print results
    if result['status'] == 'success':
        print(f"\n{Fore.GREEN}✓{Style.RESET_ALL} Analysis complete!")
        print("\nEXCHANGE RATE:")
        print(f"{from_currency}/{to_currency}: {result['data']['exchange_rate']['rate']} "
              f"({result['data']['exchange_rate']['change_percent']:+.2f}%)")
        
        print("\nSUPPLIER STOCKS:")
        for symbol, data in result['data']['supplier_stocks'].items():
            print(f"{symbol}: ${data['price']} ({data['change_percent']:+.2f}%)")
        
        print("\nFILES GENERATED:")
        for file_type, filename in result['files'].items():
            print(f"{Fore.CYAN}- {file_type}: {filename}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}✗{Style.RESET_ALL} Error: {result['message']}")

if __name__ == "__main__":
    main()