from apify_client import ApifyClient
from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import Tool
from serpapi.google_search import GoogleSearch
import os
import json
from dotenv import load_dotenv
from instaScraper import get_details, extract, get_post_urls  

load_dotenv()

def search_instagram_url(brand, api_key):
    """Use SerpAPI to find Instagram profile URL for the brand."""
    query = f"{brand} official Instagram account site:instagram.com"
    search = GoogleSearch({"q": query, "api_key": api_key})
    results = search.get_dict()

    urls = []
    if "organic_results" in results:
        for result in results["organic_results"]:
            link = result.get("link", "")
            if "instagram.com" in link and "/p/" not in link:  #/p/ are post links
                urls.append(link)
    
    return urls

def pick_best_instagram_url(urls, llm, brand):
    """Use LLM to pick the most relevant (global/official) profile from the list."""
    if not urls:
        return None

    prompt = f"""
    From the following Instagram profile URLs for the brand "{brand}", pick the most likely only one official global account (with many followers, not local or fan page or country specific):
    {json.dumps(urls, indent=2)}

    Return only the best URL, nothing else.
    """
    result = llm.invoke(prompt)
    return result.content.strip()

def run_instagram_agent(brand, api_keys):
    print(f"\nProcessing: {brand}")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_keys['genai'])

    urls = search_instagram_url(brand, api_keys['serpapi'])
    if not urls:
        print("No Instagram profiles found.")
        return
    
    best_url = pick_best_instagram_url(urls, llm, brand)
    if not best_url:
        print("LLM couldn't determine the best URL.")
        return

    print(f"Best profile for {brand}: {best_url}")

    for result_type in ["details", "posts", "stories"]:
        items, fields, rt, csv_file, brand_name = get_details(best_url, api_keys['apify'], result_type, brand.replace(" ", ""))
        extract(items, fields, rt, csv_file, brand_name)

    # pull comments from posts
    get_post_urls(f"brand-social-scraping/instagram/data/{brand.replace(' ', '')}/post_urls.csv",f"{brand.replace(' ', '')}",api_keys['apify'])

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
            run_instagram_agent(brand, api_keys)
        except Exception as e:
            print(f" Failed for {brand}: {e}")

if __name__ == "__main__":
    main()
