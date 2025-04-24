import os
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from urllib.parse import urljoin

# Fixed constant directory for output files
OUTPUT_DIR = "output"
REQUEST_DELAY = 2  # Seconds between requests to be polite

def construct_url(brand):
    """Constructs the URL for a given manufacturer."""
    brand_lower = brand.lower()
    exceptions = {
        "maruti": "https://www.cardekho.com/maruti-suzuki-cars",
        "tata": "https://www.cardekho.com/cars/Tata"
    }
    
    if brand_lower in exceptions:
        return exceptions[brand_lower]
    return f"https://www.cardekho.com/cars/{brand.capitalize()}"

def extract_price(price_text):
    """Extracts price range from text."""
    match = re.search(r"([0-9.]+\s*-\s*[0-9.]+)\s*(Lakh|Cr)", price_text, re.IGNORECASE)
    return f"{match.group(1)} {match.group(2)}" if match else "N/A"

def fetch_cars_by_brand(brand):
    """Fetches car listings with URLs."""
    url = construct_url(brand)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.cardekho.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching main page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    listings = soup.select("div.listView.holder.posS")
    
    cars = []
    for listing in listings:
        a_tag = listing.find("a", title=True)
        if not a_tag:
            continue
            
        model = a_tag.find("h3").get_text(strip=True) if a_tag.find("h3") else "N/A"
        price_div = listing.find("div", class_="price")
        price = extract_price(price_div.get_text(separator=" ", strip=True)) if price_div else "N/A"
        model_url = urljoin(url, a_tag["href"]) if "href" in a_tag.attrs else None
        
        cars.append({
            "Brand": brand.capitalize(),
            "Model": model,
            "Price": price,
            "URL": model_url
        })
    
    return cars

def fetch_model_reviews(model_url):
    """Fetches reviews for a specific model."""
    if not model_url:
        return []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": model_url
    }
    
    try:
        time.sleep(REQUEST_DELAY)  # Be polite
        response = requests.get(model_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching reviews from {model_url}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    reviews = []
    
    # Review container selector (might need adjustment based on website updates)
    review_containers = soup.select("div.reviewContain")
    
    for container in review_containers:
        try:
            user = container.select_one("span.usrName").get_text(strip=True)
            date = container.select_one("span.reviewDate").get_text(strip=True).replace("on ", "")
            rating = container.select_one("span.ratingNum").get_text(strip=True)
            title = container.select_one("h3.reviewTitle").get_text(strip=True)
            comment = container.select_one("p.reviewDesc").get_text(strip=True)
            
            reviews.append({
                "User": user,
                "Review Date": date,
                "Rating": rating,
                "Review Title": title,
                "Comment": comment
            })
        except AttributeError as e:
            print(f"Error parsing review: {e}")
            continue
    
    return reviews

def main():
    brand = input("Enter manufacturer brand: ").strip().lower()
    if not brand:
        print("Please enter a valid brand.")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    cars = fetch_cars_by_brand(brand)
    if not cars:
        print("No car data found.")
        return

    # Collect data with reviews
    full_data = []
    for car in cars:
        reviews = fetch_model_reviews(car["URL"])
        
        if reviews:
            for review in reviews:
                full_data.append({**car, **review})
        else:
            # Include cars without reviews too
            full_data.append({**car, **dict.fromkeys(["User", "Review Date", "Rating", "Review Title", "Comment"], "N/A")})

    # Save to Excel
    df = pd.DataFrame(full_data)
    excel_file = os.path.join(OUTPUT_DIR, f"{brand}_cars_with_reviews.xlsx")
    
    try:
        df.to_excel(excel_file, index=False)
        print(f"Successfully saved data to {excel_file}")
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    main()