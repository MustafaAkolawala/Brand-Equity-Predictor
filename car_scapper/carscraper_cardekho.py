import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Fixed constant directory for output files
OUTPUT_DIR = "output"

def construct_url(brand):
    """
    Constructs the URL for a given manufacturer. For known exceptions, 
    use a predefined URL; otherwise, use the default pattern:
    https://www.cardekho.com/cars/<Brand>
    """
    brand_lower = brand.lower()
    exceptions = {
        "maruti": "https://www.cardekho.com/maruti-suzuki-cars",
        "tata": "https://www.cardekho.com/cars/Tata"
        # Add more exceptions here if needed.
    }
    
    if brand_lower in exceptions:
        return exceptions[brand_lower]
    else:
        return f"https://www.cardekho.com/cars/{brand.capitalize()}"

def extract_price(price_text):
    """
    Extracts a price value from a string. First, attempts to match a range 
    (e.g., "7.52 - 13.04 Lakh" or "1.23 - 2.34 Cr"). 
    If no range is found, it attempts to match a single price (e.g., "46.05 Lakh" or "8.89 Cr").
    Returns the matched string or "N/A" if nothing is found.
    """
    match_range = re.search(r"([0-9.]+\s*-\s*[0-9.]+\s*(Lakh|Cr))", price_text, re.IGNORECASE)
    if match_range:
        return match_range.group(1)
    
    match_single = re.search(r"([0-9.]+\s*(Lakh|Cr))", price_text, re.IGNORECASE)
    if match_single:
        return match_single.group(1)
    
    return "N/A"

def fetch_cars_by_brand(brand):
    """
    Fetches car listings for a given manufacturer from CarDekho.
    Returns a list of dictionaries with keys: "Model" and "On-Road Price Range".
    """
    url = construct_url(brand)
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/105.0.0.0 Safari/537.36"),
        "Referer": "https://www.cardekho.com/"
    }
    
    print(f"Fetching data for {brand} from {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print("Error fetching the page:", e)
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Select all listings using the provided sample structure.
    listings = soup.select("div.listView.holder.posS")
    results = []
    
    for listing in listings:
        # Extract the car model name from the <h3> tag inside the <a> tag.
        model = "N/A"
        a_tag = listing.find("a", title=True)
        if a_tag:
            h3_tag = a_tag.find("h3")
            if h3_tag:
                model = h3_tag.get_text(strip=True)
        
        # Extract the on-road price range from the <div class="price"> element.
        price_range = "N/A"
        price_div = listing.find("div", class_="price")
        if price_div:
            price_text = price_div.get_text(separator=" ", strip=True)
            price_range = extract_price(price_text)
        
        results.append({
            "Model": model,
            "On-Road Price Range": price_range
        })
    
    return results

def main():
    brand = input("Enter the manufacturer brand (e.g., maruti, tata, honda, toyota, hyundai, lamborghini): ").strip()
    if not brand:
        print("Please enter a valid brand.")
        return

    # Create the fixed output directory if it doesn't exist.
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    data = fetch_cars_by_brand(brand)
    if not data:
        print("No car data found. Please verify the HTML structure, URL pattern, or your internet connection.")
        return

    df = pd.DataFrame(data)
    csv_file = os.path.join(OUTPUT_DIR, f"{brand.lower()}_cars.csv")
    excel_file = os.path.join(OUTPUT_DIR, f"{brand.lower()}_cars.xlsx")
    
    try:
        df.to_csv(csv_file, index=False)
        df.to_excel(excel_file, index=False)
        print(f"Data saved to {csv_file} and {excel_file}")
    except Exception as e:
        print("Error saving files:", e)

if __name__ == "__main__":
    main()
