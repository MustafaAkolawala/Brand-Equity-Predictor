from openai import OpenAI
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv

load_dotenv()

CUSTOM_SEARCH_API_KEY = os.getenv('CUSTOM_SEARCH_API_KEY')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')

service = build("customsearch", "v1", developerKey=CUSTOM_SEARCH_API_KEY)

client = OpenAI()

def refine_query_with_gpt(query):
    search_term = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Provide a google search term based on search query provided below in 3-4 words"},
            {"role": "user", "content": query}
        ]
    ).choices[0].message.content

    return search_term.strip()

def perform_search(query, num_results=10):
    res = service.cse().list(
        q=query,
        cx=SEARCH_ENGINE_ID,
        num=num_results  
    ).execute()

    items = res.get("items", [])
    if not items:
        print("No results found")
        return None

    search_results = []
    for item in items:
        result = {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet")
        }
        search_results.append(result)

    return search_results

search_query = "Tata Motors latest financial report of the year 2024"

refined_query = refine_query_with_gpt(search_query)
print("Refined Search Query:", refined_query)

results = perform_search(refined_query, num_results=10)

if results:
    for idx, result in enumerate(results, start=1):
        print(f"Link {idx}: {result['link']}")
        print(f"Snippet {idx}: {result['snippet']}\n")
