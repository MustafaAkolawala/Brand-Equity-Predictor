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

# Step 1: Perform Google Search
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
        f"You are an AI assistant summarizing content relevant to '{search_term}' (India specific). "
        "Provide a concise summary in 500 tokens or less."
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
        f"Based on search results, extract data for **'{search_term}'** (India only) "
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
def extract_pricing_parameters(rag_response, search_term):
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

# Step 8: Calculate Pricing Index (PI)
def calculate_PI(pricing_competitive, innovation_score):
    pricing_competitive = pricing_competitive / 100
    innovation_score = innovation_score / 100

    pi = (pricing_competitive * 0.6) + (innovation_score * 0.4)
    return round(pi, 2)

# Execute Pipeline
def execute_pricing_pipeline(company_name):
    pricing_parameters = ["Pricing Competitiveness", "Innovation Score"]
    all_results = {}

    for parameter in pricing_parameters:
        print(f"\n🔍 Searching for {parameter} data on {company_name}...\n")
        search_results, refined_query = perform_search(company_name, parameter)

        if not search_results:
            print(f"No search results found for {parameter}. Skipping...")
            continue

        print(f"\n Extracting data from search results for {parameter}...\n")
        summarized_results = get_search_results_with_fallback(search_results, refined_query)

        print(f"\n Generating RAG response for {parameter}...\n")
        rag_response = generate_rag_response(summarized_results, refined_query, parameter)

        if not rag_response:
            print(f"Failed to generate RAG response for {parameter}. Skipping...")
            continue

        print(f"\n Extracting pricing parameters for {parameter}...\n")
        extracted_params = extract_pricing_parameters(rag_response, parameter)

        if extracted_params:
            all_results.update(extracted_params)

    if not all_results:
        print("No pricing data could be extracted. Exiting...")
        return None

    pricing_comp = all_results.get("Pricing Competitiveness", 0)
    innovation = all_results.get("Innovation Score", 0)

    print("\n Calculating Pricing Index (PI)...\n")
    pi_score = calculate_PI(pricing_comp, innovation)

    return {"Company": company_name, "Pricing Data": all_results, "PI Score": pi_score}

if __name__ == "__main__":
    company = input("Enter the company name: ").strip()
    result = execute_pricing_pipeline(company)
    if result:
        with open(f"{company}_pricing_report.json", "w") as f:
            json.dump(result, f, indent=4)
