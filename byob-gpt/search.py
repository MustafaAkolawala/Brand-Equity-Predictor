import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

client = OpenAI()

MAX_CHUNK_SIZE = 2000  
MAX_CONTENT_LENGTH = 50000  
SEARCH_DEPTH = 5  

CUSTOM_SEARCH_API_KEY = os.getenv('CUSTOM_SEARCH_API_KEY')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')

service = build("customsearch", "v1", developerKey=CUSTOM_SEARCH_API_KEY)

def refine_query_with_gpt(search_query):
    print(f"Refining query: {search_query}")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Provide a google search term based on search query provided below in 3-4 words"},
                {"role": "user", "content": search_query}
            ]
        )
        refined_query = response.choices[0].message.content.strip()
        print(f"Refined query: {refined_query}")
        return refined_query
    except Exception as e:
        print(f"Error refining query: {e}")
        return search_query  

def perform_search(query):
    print(f"Performing search for query: {query}")
    refined_query = refine_query_with_gpt(query)

    try:
        res = service.cse().list(
            q=refined_query,
            cx=SEARCH_ENGINE_ID,
            num=SEARCH_DEPTH  
        ).execute()

        items = res.get("items", [])
        if not items:
            print("No results found")
            return None

        print(f"Found {len(items)} search results")
        return items , refined_query
    except Exception as e:
        print(f"Error performing search: {e}")
        return None

# Function to retrieve and clean the content of a web page with fallback logic
def retrieve_content_with_fallback(url):
    print(f"Retrieving content from: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()

        text = soup.get_text(separator=' ', strip=True)
        if len(text) > MAX_CONTENT_LENGTH:  
            print(f"Skipping {url}: Content too large (size: {len(text)})")
            return None

        print(f"Retrieved content from {url}, length: {len(text)}")
        return text
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve {url}: {e}")
        return None
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

# Function to chunk long content
def chunk_content(content, max_chunk_size=MAX_CHUNK_SIZE):
    print(f"Chunking content of length {len(content)}")
    words = content.split()
    for i in range(0, len(words), max_chunk_size):
        print(f"Creating chunk from {i} to {i + max_chunk_size}")
        yield ' '.join(words[i:i + max_chunk_size])

# Function to summarize a chunk with optional context
def summarize_chunk(chunk, search_term, context=None):
    print(f"Summarizing chunk of size: {len(chunk.split())} tokens")
    prompt = (
        f"You are an AI assistant tasked with summarizing content relevant to '{search_term}'. "
        "If provided, use the previous summary as context. Please provide a concise summary in 500 tokens or less."
    )

    messages = [
        {"role": "system", "content": prompt},
    ]

    if context:
        messages.append({"role": "assistant", "content": context})

    messages.append({"role": "user", "content": chunk})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500  
        )
        summary = response.choices[0].message.content.strip()
        print(f"Summary generated: {summary[:100]}...")
        return summary
    except Exception as e:
        print(f"An error occurred during summarization: {e}")
        return "[Error in summarization]"

def summarize_content(content, search_term):
    summaries = []
    for chunk in chunk_content(content):
        context = summaries[-1] if summaries else None
        summary = summarize_chunk(chunk, search_term, context)
        if summary:
            summaries.append(summary)
    print(f"Generated summaries: {len(summaries)} chunks")
    return ' '.join(summaries)

def get_search_results_with_fallback(search_items, search_term):
    results_list = []

    for idx, item in enumerate(search_items, start=1):
        url = item.get('link')
        snippet = item.get('snippet', '')

        print(f"Processing search result {idx}: {url}")

        web_content = retrieve_content_with_fallback(url)

        if web_content is None:
            print(f"Error: skipped URL: {url}")
            summary = f"[Fallback summary] {snippet or 'No snippet available.'}"
        else:
            summary = summarize_content(web_content, search_term)

        result_dict = {
            'order': idx,
            'link': url,
            'title': snippet,
            'Summary': summary
        }
        results_list.append(result_dict)

    print(f"Processed {len(results_list)} search results")
    return results_list

# Main Program Execution
if __name__ == "__main__":
    search_query = "Tata Motors latest financial report of the year 2024, please give me the latest quarter of 2024"  # Example search query
    print("Starting program execution...")

    search_items , search_term = perform_search(search_query)

    if search_items:
        results = get_search_results_with_fallback(search_items, search_term)

        for result in results:
            print(f"Search order: {result['order']}")
            print(f"Link: {result['link']}")
            print(f"Snippet: {result['title']}")
            print(f"Summary: {result['Summary']}")
            print('-' * 80)
    else:
        print("No search results to process.")