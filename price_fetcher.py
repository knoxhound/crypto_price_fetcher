import requests                         # Allows data fetch from CoinGecko API
from datetime import datetime           # Get current data and time and converts API timestamps to readable format
from tabulate import tabulate           # Creates formatted tables, easier to read data
import time                             # Creates delay between API calls and working with timestamps

def fetch_crypto_prices(crypto_ids):
    """
     Function (fetch_crypto_prices) being defined which is used for retrieving cryptocurrency data from CoinGecko API
    Args: crypto_ids (list): List of cryptocurrency IDs (e.g. Bitcoin, Ethereum, XRP, Doge, etc.)

    """

    url = 'https://api.coingecko.com/api/v3/simple/price'   # CoinGecko API endpoint

    # Parameters for API request
    params = {
     'ids': ','.join(crypto_ids),
     'vs_currencies': 'usd',
     'include_24hr_change': 'true',
     'include_market_cap': 'true',
     'include_last_updated_at': 'true'
    }

    try:        # Handles exceptions in Python
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()      # Converts JSON response to Python dictionary
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CoinGecko: {e}")
        return None


def format_price_data(data):
    """
    Format the API response data into a readable table
    Args: data (dict): API response data
    Returns: list: Formatted data table
    """

    table_data = []
    headers = ["Cryptocurrency", "Price (USD)", "24h Change", "Market Cap", "Last Updated"]

    for crypto, info in data.items():
        # Timestamp formatting
        last_updated = datetime.fromtimestamp(info['last_updated_at']).strftime('%Y-%m-%d %H:%M:%S')

        # Format the row data
        row = [
            crypto.title(),
            f"${info['usd']:,.2f}",
            f"{info['usd_24h_change']:+.2f}%",
            f"{info['usd_market_cap']:,.0f}",
            last_updated
        ]
        table_data.append(row)

    return headers, table_data

def main():
    #List of cryptocurrencies to track
    crypto_ids = [
        'bitcoin',
        'ethereum',
        'dogecoin',
        'cardano',
        'solana',
        'ripple'
    ]

    while True:

        print("\033c", end="")

        #Fetch current prices
        price_data = fetch_crypto_prices(crypto_ids)

        if price_data:
            #Formatting the data
            headers, table_data = format_price_data(price_data)

            #Print formatted table
            print("\nCryptocurrency Price Tracker")
            print("=========================")
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            print(f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            #Wait 60 seconds before next update

            time.sleep(60)

if __name__ == "__main__":
    main()








