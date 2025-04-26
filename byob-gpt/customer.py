import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
import json
import re

# Load environment variables
load_dotenv()

# OpenAI Client
client = OpenAI()

# Configuration
MAX_CHUNK_SIZE = 2000  
MAX_CONTENT_LENGTH = 50000  
SEARCH_DEPTH = 5  

# Google Custom Search API
CUSTOM_SEARCH_API_KEY = os.getenv('CUSTOM_SEARCH_API_KEY')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')

service = build("customsearch", "v1", developerKey=CUSTOM_SEARCH_API_KEY)

# Step 1: Perform Google Search for Sentiment Data
def perform_search(company_name, parameter):
    query = f'{company_name} {parameter} India after:2025-01-01'
    try:
        res = service.cse().list(q=query, cx=SEARCH_ENGINE_ID, num=SEARCH_DEPTH).execute()
        items = res.get("items", [])
        if not items:
            print("No results found")
            return None
        print(f"Found {len(items)} search results")
        return items, query
    except Exception as e:
        print(f"Error performing search: {e}")
        return None

# Step 2: Retrieve Web Content
def retrieve_content(url):
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
            return None

        print(f"Retrieved content from {url}, length: {len(text)})")
        return text
    except Exception as e:
        print(f"Failed to retrieve {url}: {e}")
        return None

# Step 3: Chunk Large Content
def chunk_content(content, max_chunk_size=MAX_CHUNK_SIZE):
    words = content.split()
    for i in range(0, len(words), max_chunk_size):
        yield ' '.join(words[i:i + max_chunk_size])

# Step 4: Summarize Content
def summarize_chunk(chunk, search_term, context=None):
    print(f"Summarizing chunk of size: {len(chunk.split())} tokens")
    prompt = (
        f"You are an AI assistant summarizing customer sentiment data for '{search_term}' (India-specific). "
        "Provide key insights in 500 tokens or less."
    )

    messages = [{"role": "system", "content": prompt}]
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
        return summary
    except Exception as e:
        print(f"Error during summarization: {e}")
        return "[Error in summarization]"

def summarize_content(content, search_term):
    summaries = []
    for chunk in chunk_content(content):
        context = summaries[-1] if summaries else None
        summary = summarize_chunk(chunk, search_term, context)
        if summary:
            summaries.append(summary)
    return ' '.join(summaries)

# Step 5: Get Search Results with Summarization
def get_search_results_with_fallback(search_items, search_term):
    results_list = []
    for idx, item in enumerate(search_items, start=1):
        url = item.get('link')
        snippet = item.get('snippet', '')
        web_content = retrieve_content(url)
        summary = summarize_content(web_content, search_term) if web_content else f"[Fallback] {snippet}"
        results_list.append({'order': idx, 'link': url, 'title': snippet, 'Summary': summary})
    return results_list

# Step 6: Generate RAG Response
def generate_rag_response(search_results, search_query, search_term):
    final_prompt = (
        f"Based on search results, extract customer sentiment data for **'{search_term}'** (India only) "
        "and present it in a structured format with citations."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": json.dumps(search_results, indent=4)}
            ],
            temperature=0  
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating RAG response: {e}")
        return None

# Step 7: Extract Numerical Parameters
def extract_sentiment_parameters(rag_response, search_term):
    final_prompt = f"""
    Extract a single numerical value for **'{search_term}'** in India.
    Provide a JSON response:
    
    ```json
    {{
        "{search_term}": <calculated_value>
    }}
    ```
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": rag_response}
            ],
            temperature=0  
        )

        raw_response = response.choices[0].message.content.strip()
        cleaned_response = re.sub(r"```json\s*(.*?)\s*```", r"\1", raw_response, flags=re.DOTALL)

        return json.loads(cleaned_response)
    except Exception as e:
        print(f"Error extracting {search_term}: {e}")
        return None

# Step 8: Calculate Final Sentiment Score (FSS)
def calculate_FSS(csat, nps, sentiment_score, purchase_experience):
    csat = csat / 100
    nps = nps / 100
    sentiment_score = sentiment_score / 100
    purchase_experience = purchase_experience / 100

    fss = (csat * 0.3) + (nps * 0.3) + (sentiment_score * 0.2) + (purchase_experience * 0.2)
    return round(fss, 2)

# Execute Pipeline
def execute_sentiment_pipeline(company_name):
    sentiment_parameters = [
        "Customer Satisfaction Index (CSAT)", "Net Promoter Score (NPS)", 
        "Customer Reviews & Ratings", "Social Sentiment Analysis", "Purchase & Post-Purchase Experience"
    ]
    all_results = {}

    for parameter in sentiment_parameters:
        print(f"\n🔍 Searching for {parameter} data on {company_name}...\n")
        search_results, refined_query = perform_search(company_name, parameter)

        if not search_results:
            print(f"No search results found for {parameter}. Skipping...")
            continue

        print(f"\n Extracting data from search results for {parameter}...\n")
        summarized_results = get_search_results_with_fallback(search_results, refined_query)

        print(f"\n Generating RAG response for {parameter}...\n")
        rag_response = generate_rag_response(summarized_results, refined_query, parameter)

        extracted_params = extract_sentiment_parameters(rag_response, parameter)

        if extracted_params:
            all_results.update(extracted_params)

    fss_score = calculate_FSS(**all_results)
    return {"Company": company_name, "Sentiment Data": all_results, "FSS Score": fss_score}

if __name__ == "__main__":
    company = input("Enter the company name: ").strip()
    result = execute_sentiment_pipeline(company)
    if result:
        with open(f"{company}_sentiment_report.json", "w") as f:
            json.dump(result, f, indent=4)
