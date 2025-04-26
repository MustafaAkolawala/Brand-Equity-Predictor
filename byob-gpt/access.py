import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
import json
import re

load_dotenv()

client = OpenAI()

# Configuration
MAX_CHUNK_SIZE = 2000  
MAX_CONTENT_LENGTH = 50000  
SEARCH_DEPTH = 5  

CUSTOM_SEARCH_API_KEY = os.getenv('CUSTOM_SEARCH_API_KEY')
SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')

service = build("customsearch", "v1", developerKey=CUSTOM_SEARCH_API_KEY)

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

def chunk_content(content, max_chunk_size=MAX_CHUNK_SIZE):
    print(f"Chunking content of length {len(content)}")
    words = content.split()
    for i in range(0, len(words), max_chunk_size):
        print(f"Creating chunk from {i} to {i + max_chunk_size}")
        yield ' '.join(words[i:i + max_chunk_size])

def summarize_chunk(chunk, search_term, context=None):
    print(f"Summarizing chunk of size: {len(chunk.split())} tokens")
    prompt = (
        f"You are an AI assistant summarizing content relevant to '{search_term}' for India only. "
        "If context is available, use it. Provide a summary under 500 tokens, focusing on key insights."
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
        snippet = item.get('snippet', 'No snippet available.')
        print(f"Processing search result {idx}: {url}")
        web_content = retrieve_content(url)
        if web_content is None:
            print(f"Error: skipped URL: {url}")
            summary = f"[Fallback summary] {snippet}"
        else:
            summary = summarize_content(web_content, search_term)
        results_list.append({
            'order': idx,
            'link': url,
            'title': snippet,
            'Summary': summary
        })
    print(f"Processed {len(results_list)} search results")
    return results_list

def generate_rag_response(search_results, search_query, search_term):
    final_prompt = (
        f"Based on the search results, extract data related to **'{search_term}'** for **India only**. "
        f"Present it in a structured format with source citations. Ignore irrelevant or global data."
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
        summary = response.choices[0].message.content
        print("RAG response generated" , summary)
        return summary
    except Exception as e:
        print(f"An error occurred while generating the RAG response: {e}")
        return None

def extract_access_parameters(rag_response, search_term):
    final_prompt = f"""
    Extract a single numerical or categorical value for **'{search_term}'** in India.
    - For dealer network, extract number of dealers or number of regions covered.
    - For social media engagement, extract key engagement metrics.
    - For media mentions, extract the number of mentions.
    
    Return the result as JSON:
    ```json
    {{
        "{search_term}": <value>
    }}
    ```
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": final_prompt}, {"role": "user", "content": rag_response}],
            temperature=0  
        )

        raw_response = response.choices[0].message.content.strip()
        cleaned_response = re.sub(r"```json\s*(.*?)\s*```", r"\1", raw_response, flags=re.DOTALL)
        parameters = json.loads(cleaned_response)

        return parameters
    except Exception as e:
        print(f"Error extracting {search_term}: {e}")
        return None

def execute_access_pipeline(company_name):
    access_parameters = ["Dealer Network", "Social Media Engagement", "Brand Mentions in Media"]
    all_results = {}

    for parameter in access_parameters:
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
            print(f"Failed to generate a RAG response for {parameter}. Skipping...")
            continue

        print(f"\n Extracting access parameters for {parameter}...\n")
        extracted_params = extract_access_parameters(rag_response, parameter)

        if not extracted_params:
            print(f"Failed to extract data for {parameter}. Skipping...")
            continue

        all_results.update(extracted_params)    

    if not all_results:
        print("No access data extracted. Exiting...")
        return None

    print(json.dumps(all_results, indent=4))

    return {"Company": company_name, "Access Data": all_results}

if __name__ == "__main__":
    company = input("Enter the company name: ").strip()
    result = execute_access_pipeline(company)

    if result:
        with open(f"{company}_access_report.json", "w") as f:
            json.dump(result, f, indent=4)
        print(f"\nReport saved as {company}_access_report.json")
