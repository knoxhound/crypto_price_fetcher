import csv

import requests
from datetime import datetime
import pandas as pd
from requests import Response
from tabulate import tabulate
import time
from pathlib import Path
import logging
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoinGeckoAPI:
    def __init__(self):
        self.session = self._create_session()
        self.base_url = 'https://api.coingecko.com/api/v3'
        self.last_request_time = 0
        self.min_request_interval = 1.5  # Minimum 1.5 seconds between requests

    def _create_session(self):
        """Create a session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=2,  # wait 2, 4, 8 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _wait_for_rate_limit(self):
        """Ensure minimum time between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.debug(f"Waiting {sleep_time:.2f} seconds for rate limit")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def make_request(self, endpoint, params=None):
        """Make a rate-limited request to CoinGecko API"""
        self._wait_for_rate_limit()

        url = f"{self.base_url}/{endpoint}"
        try:
            response: Response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit hit. Waiting {retry_after} seconds")
                time.sleep(retry_after)
                return self.make_request(endpoint, params)
            else:
                logger.error(f"HTTP error occurred: {e}")
                raise
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            raise


def fetch_crypto_prices(api, crypto_ids):
    """Fetch current cryptocurrency prices"""
    try:
        params = {
            'ids': ','.join(crypto_ids),
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_market_cap': 'true',
            'include_last_updated_at': 'true'
        }
        return api.make_request('simple/price', params)
    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        return None


def fetch_historical_prices(api, crypto_id, days=30):
    """Fetch historical price data for MACD calculation"""
    try:
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily'
        }
        data = api.make_request(f'coins/{crypto_id}/market_chart', params)
        return [price[1] for price in data['prices']]
    except Exception as e:
        logger.error(f"Error fetching historical data for {crypto_id}: {e}")
        return None


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicators"""
    price_series = pd.Series(prices)

    fast_ema = price_series.ewm(span=fast, adjust=False).mean()
    slow_ema = price_series.ewm(span=slow, adjust=False).mean()

    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]


def format_price_data(data, historical_data):
    """Format the API response data into a readable table"""
    table_data = []
    headers = ["Cryptocurrency", "Price (USD)", "24h Change", "Market Cap",
               "MACD", "Signal", "Histogram", "Last Updated"]

    for crypto, info in data.items():
        if crypto in historical_data and historical_data[crypto]:
            macd_line, signal_line, histogram = calculate_macd(historical_data[crypto])
        else:
            macd_line, signal_line, histogram = None, None, None

        last_updated = datetime.fromtimestamp(info['last_updated_at']).strftime('%Y-%m-%d %H:%M:%S')

        row = [
            crypto.title(),
            f"${info['usd']:,.2f}",
            f"{info['usd_24h_change']:+.2f}%",
            f"{info['usd_market_cap']:,.0f}",
            f"{macd_line:.4f}" if macd_line is not None else "N/A",
            f"{signal_line:.4f}" if signal_line is not None else "N/A",
            f"{histogram:.4f}" if histogram is not None else "N/A",
            last_updated
        ]
        table_data.append(row)

    return headers, table_data


def save_to_csv(headers, data, filename="crypto_data.csv"):
    """Save the cryptocurrency data to a CSV file"""
    filepath = Path(filename)
    mode = 'a' if filepath.exists() else 'w'
    write_headers = not filepath.exists()

    with open(filepath, mode, newline='') as f:
        writer = csv.writer(f)
        if write_headers:
            writer.writerow(['Timestamp'] + headers)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for row in data:
            writer.writerow([timestamp] + row)


def main():
    crypto_ids = [
        'bitcoin',
        'ethereum',
        'dogecoin',
        'cardano',
        'solana',
        'ripple'
    ]

    api = CoinGeckoAPI()

    while True:
        print("\033c", end="")

        try:
            # Fetch current prices
            price_data = fetch_crypto_prices(api, crypto_ids)

            if price_data:
                # Fetch historical data for MACD calculation
                historical_data = {}
                for crypto in crypto_ids:
                    historical_prices = fetch_historical_prices(api, crypto)
                    if historical_prices:
                        historical_data[crypto] = historical_prices

                # Format the data
                headers, table_data = format_price_data(price_data, historical_data)

                # Save to CSV
                save_to_csv(headers, table_data)

                # Print formatted table
                print("\nCryptocurrency Price Tracker with MACD")
                print("====================================")
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
                print(f"\nLast updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Data saved to crypto_data.csv")

            # Wait before next update (minimum 60 seconds)
            time.sleep(60)

        except Exception as e:
            logger.error(f"An error occurred in main loop: {e}")
            print("An error occurred. Waiting before retry...")
            time.sleep(60)


if __name__ == "__main__":
    main()