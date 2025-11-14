import pandas as pd
import requests
from datetime import datetime
import time
from config import API_KEYS, G20_COUNTRIES, OUTPUT_PATH

def fetch_world_bank_data(country_code, indicator, start_year=2019, end_year=2024):
    """Fetch data from World Bank API"""
    base_url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}"
    params = {
        'date': f'{start_year}:{end_year}',
        'format': 'json',
        'per_page': 500
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(data)
        
        if len(data) > 1 and data[1]:
            return pd.DataFrame(data[1])
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching {indicator} for {country_code}: {e}")
        return pd.DataFrame()

def process_country_data(country_code):
    """Process all indicators for a single country"""
    results = []
    
    # World Bank indicators
    indicators = {
        'NY.GDP.MKTP.KD.ZG': 'GDP Growth Rate (%)',
        'FP.CPI.TOTL.ZG': 'Inflation Rate (%)',
        'SL.UEM.TOTL.ZS': 'Unemployment Rate (%)',
        'PA.NUS.FCRF': 'USD Exchange Rate' 
    }
    
    for indicator_code, indicator_name in indicators.items():
        df = fetch_world_bank_data(country_code, indicator_code)
        if not df.empty:
            df['indicator'] = indicator_name
            results.append(df)
            print("fetch world bank data succesfully")
        time.sleep(0.5)  # Be nice to the API
    
    return results

def main():
    """Main execution function"""
    all_data = []
    
    print("Starting data collection for G20 countries...")
    
    for country in G20_COUNTRIES:
        print(f"Processing {country}...")
        country_data = process_country_data(country)
        
        # Combine and reshape data
        if country_data:
            combined = pd.concat(country_data, ignore_index=True)
            combined['Country'] = country
            all_data.append(combined)
    
    # Combine all countries
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        
        # Clean and format
        final_df = final_df[['Country', 'date', 'indicator', 'value']]
        final_df.columns = ['Country', 'Year', 'Indicator', 'Value']
        
        # Convert to quarterly format (simplified - using annual data)
        final_df['Quarter'] = final_df['Year'].astype(str) + '-Q4'
        
        # Pivot to get required column structure
        pivot_df = final_df.pivot_table(
            index=['Country', 'Quarter'],
            columns='Indicator',
            values='Value',
            aggfunc='first'
        ).reset_index()
        
        # Save to files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_path = f"{OUTPUT_PATH}g20_economic_data_{timestamp}.xlsx"
        csv_path = f"{OUTPUT_PATH}g20_economic_data_{timestamp}.csv"
        
        pivot_df.to_excel(excel_path, index=False)
        pivot_df.to_csv(csv_path, index=False)
        
        print(f"\nSuccess! Files saved:")
        print(f"  - {excel_path}")
        print(f"  - {csv_path}")
        print(f"Total records: {len(pivot_df)}")
    else:
        print("No data collected. Check API keys and connection.")

if __name__ == "__main__":
    main()