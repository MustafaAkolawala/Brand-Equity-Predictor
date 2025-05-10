from apify_client import ApifyClient
from langchain_google_genai import ChatGoogleGenerativeAI
from serpapi.google_search import GoogleSearch
import os
import json
from dotenv import load_dotenv
from profile_details import get_details as get_profile_details, extract as extract_profile
from post_details import get_details as get_post_details, extract as extract_post
from comment_scraper import extract_comments

load_dotenv()

def search_linkedin_url(brand, api_key):
    """Use SerpAPI to find LinkedIn company profile URL."""
    query = f"{brand} LinkedIn page site:linkedin.com/company"
    search = GoogleSearch({"q": query, "api_key": api_key})
    results = search.get_dict()

    urls = []
    if "organic_results" in results:
        for result in results["organic_results"]:
            link = result.get("link", "")
            if "linkedin.com/company" in link:
                urls.append(link)
    
    return urls

def pick_best_url(urls, llm, brand):
    """Use LLM to pick the most relevant LinkedIn profile."""
    if not urls:
        return None
    print(urls)
    prompt = f"""
    From the LinkedIn company profile URLs for the brand "{brand}", pick the most likely official page. Prefer the one with the highest number of followers and regular posts, even if it's region-specific or not a global account. Avoid pages with no posts.
    {json.dumps(urls, indent=2)}

    Return only the best URL, nothing else.
    """
    result = llm.invoke(prompt)
    return result.content.strip()

def run_linkedin_agent(brand, api_keys):
    print(f"\n Processing: {brand}")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_keys['genai'])

    urls = search_linkedin_url(brand, api_keys['serpapi'])
    if not urls:
        print(" No LinkedIn profiles found.")
        return
    
    best_url = pick_best_url(urls, llm, brand)
    if not best_url:
        print(" LLM couldn't determine the best URL.")
        return

    print(f"Best LinkedIn profile: {best_url}")

    brand_folder = brand.lower().replace(" ", "-")

    profile_data, profile_fields, profile_csv, _ = get_profile_details(best_url, api_keys['apify'], brand_folder)
    extract_profile(profile_data, profile_fields, profile_csv, brand_folder)

 
    post_data, post_fields, post_csv, _ = get_post_details(best_url, api_keys['apify'], brand_folder)
    extract_post(post_data, post_fields, post_csv, brand_folder)

    extract_comments(post_csv, brand_folder, api_keys['apify'])

def main():
    api_keys = {
        'apify': os.getenv("APIFY"),
        'serpapi': os.getenv("SERPAPI"),
        'genai': os.getenv("GEMINI")
    }

    with open("brand-social-scraping/brands.txt", "r") as f:
        brand_names = [line.strip() for line in f if line.strip()]
    
    for brand in brand_names:
        try:
            run_linkedin_agent(brand, api_keys)
        except Exception as e:
            print(f"Failed for {brand}: {e}")

if __name__ == "__main__":
    main()
