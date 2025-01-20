import os
import json
import requests
from bs4 import BeautifulSoup
from firecrawl import FirecrawlApp
from google.generativeai import genai

FIRE_CRAWL_API_KEY = "my_fire_crawl_api_key"
GEMINI_API_KEY = "my_gemini_api_key"

app = FirecrawlApp(api_key=FIRE_CRAWL_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

COMPANIES = {
    "Kia": "https://www.carwale.com/dealer-showrooms/kia/",
    "Hyundai": "https://www.carwale.com/dealer-showrooms/hyundai/",
    # ...
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
}


def scrape_dealer_data(company_name, url):
    print(f"Scraping data for {company_name}...")

    scrape_result = app.scrape_url(url=url, params={"formats": ["markdown"]})

    os.makedirs("scraped_data", exist_ok=True)
    markdown_path = os.path.join("scraped_data", f"{company_name.lower()}-dealers.md")
    with open(markdown_path, "w") as md_file:
        md_file.write(scrape_result["markdown"])

    response = model.generate_content(f"""
        Extract all relevant data from the following markdown text into a JSON format, without omitting any information:

        {scrape_result["markdown"]}

        The JSON structure should include:
        - States and their corresponding cities, each city having the count of dealerships and its URL.
        - A list of popular cars and their average showroom prices.

        Provide the output **only** as valid JSON. Do not include comments, explanations, or any other text. Here's an example structure to follow:

        {{
          "states": [
            {{
              "state_name": "State1",
              "cities": {{
                  "city_name1": dealership_count_of_city1,
                  "city_name2": dealership_count_of_city2,
                }}
              ]
            }}
          ],
          "popular_cars": [
            {{
              "car_name": "Car1",
              "average_showroom_price": 500000
            }},
            {{
              "car_name": "Car2",
              "average_showroom_price": 700000
            }}
          ]
        }}

        dealership_count_of_city1, dealership_count_of_city2, etc. should be replaced with the actual counts as integer.
        **Note:** The JSON structure should be based on the data extracted from the markdown content.
        """)

    json_data = json.loads(response.text.strip("```json\n").strip("```"))
    json_path = os.path.join("scraped_data", f"{company_name.lower()}-dealers.json")
    with open(json_path, "w") as json_file:
        json.dump(json_data, json_file, indent=4)

    print(f"Data for {company_name} saved to {json_path}")

    # # Additional scraping of city-level URLs if needed
    # for state in json_data.get("states", []):
    #     state_name = state["state_name"]
    #     cities = state.get("cities", {})
    #
    #     for city_name, dealership_count in cities.items():
    #         # Construct the city URL based on the pattern or directly fetch it if provided
    #         city_url = f"https://www.carwale.com/dealer-showrooms/{company_name.lower()}/{city_name.lower()}/"
    #         print(f"Scraping details for city: {city_name} ({city_url})")
    #
    #         try:
    #             # Scrape the city's webpage
    #             city_res = requests.get(city_url, headers=HEADERS)
    #             city_res.raise_for_status()
    #
    #             # Parse and save the page content
    #             soup = BeautifulSoup(city_res.text, "html.parser")
    #             city_data_path = os.path.join(
    #                 "scraped_data", f"{company_name.lower()}_{city_name.lower()}.html"
    #             )
    #             with open(city_data_path, "w", encoding="utf-8") as city_file:
    #                 city_file.write(soup.prettify())
    #
    #         except Exception as e:
    #             print(f"Failed to scrape {city_url}: {e}")


# Process all companies
for company, url in COMPANIES.items():
    scrape_dealer_data(company, url)
