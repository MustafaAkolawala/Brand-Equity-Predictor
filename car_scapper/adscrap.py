import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import urljoin

# Configuration
OUTPUT_DIR = "output"
REQUEST_DELAY = 3  # Seconds between requests to avoid blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.cardekho.com/"
}

def construct_url(brand):
    """Constructs the URL for a given manufacturer."""
    brand_lower = brand.lower()
    exceptions = {
        "maruti": "https://www.cardekho.com/maruti-suzuki-cars",
        "tata": "https://www.cardekho.com/cars/Tata"
    }
    return exceptions.get(brand_lower, f"https://www.cardekho.com/cars/{brand.capitalize()}")

def extract_price(price_text):
    """Extracts price range from text."""
    match = re.search(r"([0-9.]+\s*-\s*[0-9.]+)\s*(Lakh|Cr)", price_text, re.IGNORECASE)
    return f"{match.group(1)} {match.group(2)}" if match else "N/A"

def fetch_cars_by_brand(brand):
    """Fetches car listings with URLs."""
    url = construct_url(brand)
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"🚨 Error fetching main page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    cars = []
    
    for listing in soup.select("div.listView.holder.posS"):
        a_tag = listing.find("a", title=True)
        if not a_tag:
            continue
            
        model = a_tag.find("h3").get_text(strip=True) if a_tag.find("h3") else "N/A"
        price_div = listing.find("div", class_="price")
        price = extract_price(price_div.get_text(separator=" ", strip=True)) if price_div else "N/A"
        model_url = urljoin(url, a_tag["href"]) if a_tag.has_attr("href") else None
        
        cars.append({
            "Brand": brand.capitalize(),
            "Model": model,
            "Price": price,
            "URL": model_url
        })
    
    return cars

def fetch_model_reviews(model_url):
    """Fetches reviews for a specific model using updated selectors"""
    if not model_url:
        return []
    
    try:
        time.sleep(REQUEST_DELAY)
        response = requests.get(model_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠️ Error fetching reviews from {model_url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    reviews = []
    
    # Find all review containers
    for container in soup.select('li.gsc_col-xs-12 div.readReviewBox'):
        try:
            # Extract user name and date
            author_summary = container.select_one('div.authorSummary div.name')
            if author_summary:
                author_text = author_summary.get_text(strip=True)
                parts = author_text.split(' on ', 1)
                user = parts[0] if len(parts) > 0 else 'N/A'
                date = parts[1] if len(parts) > 1 else 'N/A'
            else:
                user, date = 'N/A', 'N/A'
            
            # Extract rating
            rating_tag = container.select_one('span.ratingStarNew')
            rating = rating_tag.get_text(strip=True) if rating_tag else 'N/A'
            
            # Extract review title
            title_tag = container.select_one('span.title.hover')
            title = title_tag.get_text(strip=True) if title_tag else 'N/A'
            
            # Extract review text
            content_tag = container.select_one('div.truncate3L')
            comment = content_tag.get_text(strip=True) if content_tag else 'N/A'
            
            reviews.append({
                "User": user,
                "Review Date": date,
                "Rating": rating,
                "Review Title": title,
                "Comment": comment
            })
            
        except Exception as e:
            print(f"⚠️ Error parsing review: {e}")
            continue
    
    return reviews

def main():
    brand = input("Enter manufacturer brand (e.g., Tata, Maruti): ").strip().lower()
    if not brand:
        print("❌ Please enter a valid brand.")
        return

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Fetch car listings
    print(f"🔍 Searching for {brand.capitalize()} cars...")
    cars = fetch_cars_by_brand(brand)
    
    if not cars:
        print("❌ No car data found. Check brand name or website structure.")
        return

    # Collect data with reviews
    full_data = []
    total_cars = len(cars)
    
    for idx, car in enumerate(cars, 1):
        print(f"📖 Processing {car['Model']} ({idx}/{total_cars})")
        reviews = fetch_model_reviews(car["URL"])
        
        if reviews:
            for review in reviews:
                full_data.append({**car, **review})
        else:
            full_data.append({**car, **{k: "N/A" for k in ["User", "Review Date", "Rating", "Review Title", "Comment"]}})

    # Save to Excel
    df = pd.DataFrame(full_data)
    excel_file = os.path.join(OUTPUT_DIR, f"{brand}_cars_with_reviews.xlsx")
    
    try:
        df.to_excel(excel_file, index=False)
        print(f"✅ Successfully saved data to {excel_file}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")

if __name__ == "__main__":
    main()