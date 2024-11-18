import requests
import pandas as pd
from datetime import datetime
import time


class CryptoPriceTracker:
    def __init__(self, coins=('bitcoin', 'ethereum', 'ripple', 'sui', 'solana', 'dogecoin'),
                 output_file='crypto_changes.csv'):
        if coins is None:
            coins = ['bitcoin', 'ethereum']
        self.coins = list(coins)  # Convert to list to ensure consistent handling
        self.output_file = output_file
        self.previous_prices = {}
        self.base_url = "https://api.coingecko.com/api/v3"

        # Create new file or reset existing one
        self.create_initial_csv()

    def create_initial_csv(self):
        """Create or reset the CSV file with proper headers"""
        # Generate headers: first all prices, then all changes
        price_columns = [f'{coin}_price' for coin in self.coins]
        change_columns = [f'{coin}_change' for coin in self.coins]
        headers = ['timestamp'] + price_columns + change_columns

        # Create empty DataFrame with proper headers
        df = pd.DataFrame(columns=headers)

        # Write to CSV with specified formatting
        df.to_csv(self.output_file, index=False)

    def fetch_prices(self):
        try:
            coins_string = ','.join(self.coins)
            response = requests.get(
                f"{self.base_url}/simple/price",
                params={
                    'ids': coins_string,
                    'vs_currencies': 'usd'
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching prices: {e}")
            return None

    def calculate_changes(self, current_prices):
        changes = {}
        for coin in self.coins:
            if coin in self.previous_prices:
                prev_price = self.previous_prices[coin]
                curr_price = current_prices[coin]['usd']
                pct_change = ((curr_price - prev_price) / prev_price) * 100
                changes[coin] = pct_change
            else:
                changes[coin] = 0
            self.previous_prices[coin] = current_prices[coin]['usd']
        return changes

    def log_data(self, current_prices, changes):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Initialize row data with timestamp
        row_data = {'timestamp': timestamp}

        # Add all prices first
        for coin in self.coins:
            row_data[f'{coin}_price'] = current_prices[coin]['usd']

        # Then add all changes
        for coin in self.coins:
            row_data[f'{coin}_change'] = round(changes[coin], 2)

        # Create DataFrame with single row
        df = pd.DataFrame([row_data])

        # Ensure columns are in correct order
        price_columns = [f'{coin}_price' for coin in self.coins]
        change_columns = [f'{coin}_change' for coin in self.coins]
        columns = ['timestamp'] + price_columns + change_columns
        df = df[columns]

        # Append to CSV
        df.to_csv(
            self.output_file,
            mode='a',
            header=False,
            index=False,
            float_format='%.2f'
        )

    def run(self, interval=300):
        print(f"Starting price tracking... Data will be logged to {self.output_file}")
        while True:
            current_prices = self.fetch_prices()
            if current_prices:
                changes = self.calculate_changes(current_prices)
                self.log_data(current_prices, changes)

                print(f"\nUpdate at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                for coin in self.coins:
                    print(f"{coin.capitalize()}: ${current_prices[coin]['usd']:,.2f} "
                          f"(Change: {changes[coin]:+.2f}%)")

            time.sleep(interval)


if __name__ == "__main__":
    tracker = CryptoPriceTracker(coins=['bitcoin', 'ethereum', 'ripple', 'sui', 'solana', 'dogecoin'])
    tracker.run()