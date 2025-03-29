from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import Tool
from serpapi.google_search import GoogleSearch
from firecrawl import FirecrawlApp
import json
import re
import os
import time
from dotenv import load_dotenv

load_dotenv()

def normalize_brand_name(brand: str, site: str) -> str:
    brand = brand.strip().lower()
    if site == "carwale.com":
        return brand.replace(" ", "-")  
    if site == "bikewale.com":
        return brand.replace(" ", "") 
    return brand  
def scrape_carwale(brand: str, api_key: str):
    formatted_brand = normalize_brand_name(brand, "carwale.com")
    url = f"https://www.carwale.com/dealer-showrooms/{formatted_brand}"
    app = FirecrawlApp(api_key=api_key)

    for attempt in range(3):
        try:
            data = app.scrape_url(url, params={
                'formats': ['markdown', 'extract'],
                'extract': { 
                    'prompt': "Find any mentions of specific count and return them",
                    'systemPrompt': "You are a helpful assistant that extracts numerical data of showrooms."
                }
            })
            print(f"CarWale data: {data['extract']}\n")
            
            if 'dealer_count' in data.get('extract', {}) and data['extract']['dealer_count']:
                return data['extract']['dealer_count']['total_showrooms']
            
            if 'showrooms' in data.get('extract', {}) and 'total' in data['extract']['showrooms']:
                return data['extract']['showrooms']['total']
            
            if 'showrooms' in data.get('extract', {}) and 'total_count ' in data['extract']['showrooms']:
                return data['extract']['showrooms']['total_count ']
            
            elif 'dealers' in data.get('extract', {}) and len(data['extract']['dealers']) > 0:
                return len(data['extract']['dealers'])  

        except Exception as e:
            print(f"Error in CarWale scrape: {e}")
            if attempt < 2:
                time.sleep(2)
    return None
def scrape_bikewale(brand: str, api_key: str):
    formatted_brand = normalize_brand_name(brand, "bikewale.com")
    url = f"https://www.bikewale.com/dealer-showrooms/{formatted_brand}"
    app = FirecrawlApp(api_key=api_key)

    for attempt in range(3):
        try:
            data = app.scrape_url(url, params={
                'formats': ['markdown', 'extract'],
                'extract': { 
                    'prompt': "Find any mentions of specific dealer count and return them",
                    'systemPrompt': "You are a helpful assistant that extracts numerical data of dealers or showrooms for given brand."
                }
            })
            print(f"BikeWale data: {data}\n")  
            print(f'\n {data['extract']}')
            dealer_count_data = data['extract'].get('dealer_count', {})
            if dealer_count_data and 'total_showrooms' in dealer_count_data:
                extracted_value = dealer_count_data['total_showrooms']
                print(f"Extracted dealership count: {extracted_value}")  
                return extracted_value

            if 'extract' in data and 'dealers' in data['extract']:
                dealers = data['extract']['dealers']
                brand = brand.capitalize()
                if brand in dealers:
                    brand_data = dealers[brand]
                    if 'showrooms' in brand_data:
                        extracted_value = brand_data['showrooms']
                        print(f"Extracted dealership count from dealers: {extracted_value}") 
                        return extracted_value
                    elif 'total_showrooms' in brand_data:
                        extracted_value = brand_data['total_showrooms']
                        print(f"Extracted dealership count (alternative): {extracted_value}") 
                        return extracted_value
            print("No valid dealership count found.")
            return None
        except Exception as e:
            print(f"Error in BikeWale scrape: {e}")
            if attempt < 2:
                time.sleep(2)
    return None

def extract_count_with_llm(llm, text):
    print(f'Content passed to LLM: {text}')
    """Uses LLM to extract the most likely dealership count from provided content."""
    prompt = f"""
    Identify and extract the total number of showrooms or dealerships of brand in India as of year 2024 from the following content:
    "{text}"
    - Only return the numeric figure for dealerships or showrooms.
    - Ignore unrealted number (eg, for years, or price).
    - If multiple numbers are mentioned, choose the most relevant one for the number of dealerships.
    """
    response = llm.invoke(prompt)
    print(response)
    return response


def search_serpapi(api_key, query, llm):
    search = GoogleSearch({"q": query, "api_key": api_key})
    result = search.get_dict()
    
    # Check the answer box first i.e ai generated text
    if "answer_box" in result and "snippet_highlighted_words" in result["answer_box"]:
        highlighted_text = " ".join(result["answer_box"]["snippet_highlighted_words"])
        if highlighted_text:
            # Pass this directly to the LLM
            return extract_count_with_llm(llm, highlighted_text)
    
    highlighted_texts = []
    if "organic_results" in result:
        for res in result["organic_results"]:
            if "snippet_highlighted_words" in res:
                highlighted_texts.extend(res["snippet_highlighted_words"])
    
    if highlighted_texts:
        context = " ".join(highlighted_texts)
        print(f'\nContent passing to LLM: {context}\n') 
        return extract_count_with_llm(llm, context)
    
    return None

def run_agent(brand: str, api_keys: dict):
    llm = ChatGoogleGenerativeAI(model='gemini-1.5-flash', google_api_key=api_keys['genai'])
    user_query = f"{brand} total number of dealerships in India"
    
    tools = [
        Tool("CarWale Scraper", func=lambda b: scrape_carwale(b, api_keys['firecrawl']), 
             description="Scrapes dealership count from CarWale for a given brand"),
        Tool("BikeWale Scraper", func=lambda b: scrape_bikewale(b, api_keys['firecrawl']), 
             description="Scrapes dealership count from BikeWale for a given brand"),
        Tool("SerpAPI Search", func=lambda b: search_serpapi(api_keys['serpapi'], user_query, llm), 
             description="Scrapes dealership count from SerpAPI for a given brand")  
    ]   
    
    agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)
    
    prompt = f"""
    Your task is to find the total number of dealerships for {brand} in India. Use the available tools.
    - Try CarWale if it's a car brand, and BikeWale if it's a bike brand.
    - If you get a valid number, STOP searching.
    - If both fail, use SerpAPI as a last resort.
    - Extract only the numerical dealership count.
    - Return only the number and no extra text.
    """
    
    count = agent.invoke(prompt)
    return count.get("output", count)

def main():
    brands = ['maruti suzuki','mahindra','fiat','hero','royal enfield','ktm']
    api_keys = {
        'firecrawl': os.getenv("FIRECRAWL"), 
        'serpapi': os.getenv("SERPAPI"),
        'genai': os.getenv("GEMINI")
    }
    
    results = {brand: run_agent(brand, api_keys) for brand in brands}
    with open("results.json", 'w') as f:
        json.dump(results, f, indent=4)
    return results

if __name__ == "__main__":
    main()
