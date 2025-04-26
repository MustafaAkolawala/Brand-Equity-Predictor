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
        f"You are an AI assistant tasked with summarizing content relevant to '{search_term}' (india Specific). "
        "If provided, use the previous summary as context. Provide a concise summary in 500 tokens or less."
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
        snippet = item.get('snippet', '')
        print(f"Processing search result {idx}: {url}")
        web_content = retrieve_content(url)
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

def generate_rag_response(search_results, search_query, search_term):
    final_prompt = (
        f"Based on the search results, provide a detailed response to the query: **'{search_query}'**. "
        f"Extract the specific **'{search_term}'** data **for India only** and present it in a structured format with citations to the sources used. "
        f"Ignore global data and focus only on regional data relevant to India."
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
        print("Generated RAG Response:")
        print(summary)
        return summary
    except Exception as e:
        print(f"An error occurred while generating the RAG response: {e}")
        return None

def extract_financial_parameters(rag_response, search_term):
    final_prompt = f"""
    Given the following extracted data about **'{search_term}'** in India, analyze and return a single numerical value for **'{search_term}'**.

    - If multiple values exist, provide a weighted or reasonable average.
    - Ignore irrelevant values, textual noise, and any global or non-Indian data.
    - Ensure the output is a **single percentage or numerical value** that is specific to India.

    **Return the result as a valid JSON object** in the following format:

    ```json
    {{
        "{search_term}": <calculated_value>
    }}
    ```

    Ensure the response is **only** this JSON object and nothing else.
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

        if not response.choices or not response.choices[0].message.content.strip():
            raise ValueError(f"Empty response received from GPT for {search_term}")

        raw_response = response.choices[0].message.content.strip()
        print(f"🔍 Raw GPT Response for {search_term}:\n{raw_response}")  

        cleaned_response = re.sub(r"```json\s*(.*?)\s*```", r"\1", raw_response, flags=re.DOTALL)
        cleaned_response = re.sub(r'(\d+),(\d+)', r'\1\2', cleaned_response)

        try:
            parameters = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Cleaned response received: {cleaned_response}")
            return None

        return parameters

    except Exception as e:
        print(f"Unexpected Error extracting {search_term}: {e}")
        return None

def calculate_BEI(market_share, investor_confidence, sales_data, min_sales=100000, max_sales=10000000):
    market_share = market_share / 100
    investor_confidence = investor_confidence / 100
    
    normalized_sales = (sales_data - min_sales) / (max_sales - min_sales)
    normalized_sales = max(0, min(1, normalized_sales))  
    
    bei = ((market_share * 0.4) + (investor_confidence * 0.3) + (normalized_sales * 0.3)) 
    return round(bei, 2)

def execute_pipeline(company_name):
    financial_parameters = ["Market Share", "Investor Confidence", "Sales Data"]
    all_results = {}

    for parameter in financial_parameters:
        print(f"\n🔍 Searching for {parameter} data on {company_name}...\n")
        search_results, refined_query = perform_search(company_name, parameter)

        if not search_results:
            print(f" No search results found for {parameter}. Skipping...")
            continue

        print(f"\n Extracting data from search results for {parameter}...\n")
        summarized_results = get_search_results_with_fallback(search_results, refined_query)

        print(f"\n Generating RAG response for {parameter}...\n")
        rag_response = generate_rag_response(summarized_results, refined_query, parameter)

        if not rag_response:
            print(f" Failed to generate a RAG response for {parameter}. Skipping...")
            continue

        print(f"\n Extracting financial parameters for {parameter}...\n")
        extracted_params = extract_financial_parameters(rag_response, parameter)

        if not extracted_params:
            print(f" Failed to extract financial parameters for {parameter}. Skipping...")
            continue

        all_results.update(extracted_params)    

    if not all_results:
        print(" No financial data could be extracted. Exiting...")
        return None

    print("\n Successfully extracted financial parameters:")
    print(json.dumps(all_results, indent=4))

    market_share = all_results.get("Market Share", 0)
    investor_confidence = all_results.get("Investor Confidence", 0)
    sales_data = all_results.get("Sales Data", 0)

    print("\n Calculating Brand Equity Index (BEI)...\n")
    bei_score = calculate_BEI(market_share, investor_confidence, sales_data)

    print(f"\n Final Brand Equity Index (BEI) Score for {company_name}: {bei_score}/1\n")

    return {
        "Company": company_name,
        "Financial Data": all_results,
        "BEI Score": bei_score
    }

if __name__ == "__main__":
    company = input("Enter the company name: ").strip()
    result = execute_pipeline(company)

    if result:
        with open(f"{company}_financial_report.json", "w") as f:
            json.dump(result, f, indent=4)
        print(f"\n Report saved as {company}_financial_report.json")