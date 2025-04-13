from langchain_google_genai import ChatGoogleGenerativeAI
from serpapi.google_search import GoogleSearch
from profile_details import get_details as get_profile_details, extract as extract_profile
from post_details import get_details as get_post_details, extract as extract_posts
import os, json
from dotenv import load_dotenv

load_dotenv()

def search_twitter_urls(brand, api_key):
    query = f"{brand} official Twitter account site:x.com"
    search = GoogleSearch({"q": query, "api_key": api_key})
    results = search.get_dict()

    urls = []
    if "organic_results" in results:
        for result in results["organic_results"]:
            link = result.get("link", "")
            if "x.com" in link and "/status/" not in link:
                urls.append(link)
    return urls

def pick_best_url(urls, llm, brand):
    if not urls:
        return None
    prompt = f"""
    From these Twitter profile URLs for the brand \"{brand}\", pick the official/global one (not local, fan-made, or country-specific). Prioritize accounts with high follower counts:
    {json.dumps(urls, indent=2)}

    Return only the best URL, nothing else.
    """
    result = llm.invoke(prompt)
    return result.content.strip()

def extract_username_from_url(url):
    return url.rstrip("/").split("/")[-1]

def main():
    api_keys = {
        "apify": os.getenv("APIFY"),
        "serpapi": os.getenv("SERPAPI"),
        "genai": os.getenv("GEMINI")
    }

    with open("brand-social-scraping/brands.txt", "r") as f:
        brand_names = [line.strip() for line in f if line.strip()]

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_keys["genai"])

    usernames = []
    brand_username_map = {}  # brand -> username

    for brand in brand_names:
        print(f"\nSearching Twitter for: {brand}")
        try:
            urls = search_twitter_urls(brand, api_keys["serpapi"])
            if not urls:
                print("No Twitter profiles found.")
                continue

            best_url = pick_best_url(urls, llm, brand)
            if not best_url:
                print("LLM couldn't determine the best URL.")
                continue

            username = extract_username_from_url(best_url)
            print(f"Best username for {brand}: {username}")
            usernames.append(username)
            brand_username_map[brand] = username

        except Exception as e:
            print(f"Failed during search for {brand}: {e}")

    # Get profile details in one go
    if usernames:
        try:
            dataset_items, fields, csv_file = get_profile_details(usernames, api_keys["apify"])
            extract_profile(dataset_items, fields, csv_file)
        except Exception as e:
            print(f"Failed during profile scraping: {e}")
    else:
        print("No valid usernames to fetch profile details.")

    # Get post details one by one
    for brand, username in brand_username_map.items():
        try:
            dataset_items, fields, csv_file, brand_name = get_post_details(api_keys["apify"], username)
            extract_posts(dataset_items, fields, csv_file, brand_name)
        except Exception as e:
            print(f"Failed to fetch posts for {brand} ({username}): {e}")

if __name__ == "__main__":
    main()
