import asyncio
import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.ollama import Ollama
import httpx
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


# Configure settings
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
llm = Ollama(model="qwen2.5:7b", request_timeout=360.0)
Settings.llm = llm


async def fetch_cookies():
    url = f"https://www.nseindia.com/companies-listing/corporate-filings-annual-reports"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            cookies = response.cookies
            print(f"Cookies fetched")
            return {"nseappid": cookies.get("nseappid"), "nsit": cookies.get("nsit")}

    except Exception as e:
        print(f"Error fetching cookies: {e}")
        return ""


async def fetch_report(ticker: str) -> str:
    """
    Fetch the annual report for a given stock ticker.

    Args:
        ticker (str): The stock ticker symbol.

    Returns:
        str: The path to the saved report.
    """
    cookies = await fetch_cookies()
    if not cookies:
        print("Failed to fetch cookies")
        return ""
    
    print(f"Fetching report for ticker: {ticker}")
    url = f"https://www.nseindia.com/api/annual-reports?index=equities&symbol={ticker}"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    # cookies = {
    #     "nseappid": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcGkubnNlIiwiYXVkIjoiYXBpLm5zZSIsImlhdCI6MTc0NDI4OTYzOCwiZXhwIjoxNzQ0Mjk2ODM4fQ.PCSrjpBW48c1VFR38awvxJROPlkYwRebDgwf6i0GzNM",
    #     "nsit": "ufWGT65TcM46Rvd9HIhn5fya",
    # }
    cookies = {
        "nseappid": cookies["nseappid"],
        "nsit": cookies["nsit"],
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, cookies=cookies)
            response.raise_for_status()
            data = response.json()
            file_url = data["data"][0]["fileName"]

            # Download the file
            async with httpx.AsyncClient() as client:
                print("fetching file")
                response = await client.get(file_url, headers=headers, cookies=cookies)
                response.raise_for_status()  # Raise an exception for HTTP errors
                os.makedirs(ticker, exist_ok=True)
                file_path = os.path.join(ticker, file_url.split("/")[-1])
                with open(file_path, "wb") as file:
                    file.write(response.content)

            print(f"Report saved to {file_path}")
            return file_path

    except Exception as e:
        print(f"Error fetching report: {e}")
        return ""

async def analyze_report(ticker: str):
    """
    Analyze the annual report for a given stock ticker using RAG.

    Args:
        ticker (str): The stock ticker symbol.
        query (str): The user's query.

    Returns:
        str: The result of the query.
    """
    print(f"Analyzing report for ticker: {ticker}")
    documents = SimpleDirectoryReader(ticker).load_data()
    index = VectorStoreIndex.from_documents(documents)
    query_engine = index.as_query_engine(llm=Settings.llm, similarity_top_k=10)

    await query_report(query_engine)

    # response = await query_engine.aquery(query)
    # return str(response)

async def query_report(query_engine):
    """
    Query the report using the query engine.

    """
    print("Querying the report...")
    while True:
        query = input("Enter your query (or type 'exit' to quit): ").strip()
        if query.lower() == "exit":
            print("Exiting query loop.")
            break
        response = await query_engine.aquery(query)
        print("Query Response:", response)

    # Uncomment the following lines to test with a different query
    # response = await query_engine.aquery("What is the profit for the last year?")
    # print("Query Response:", response)

async def predefined_flow(ticker: str) -> str:
    """
    Predefined flow to fetch a stock ticker's report and analyze it.

    Args:
        ticker (str): The stock ticker symbol.
        query (str): The user's query.

    Returns:
        str: The result of the query.
    """
    
    # Step 1: Fetch the report
    report_path = await fetch_report(ticker)
    if not report_path:
        return "Failed to fetch the report. Please check the ticker or try again."

    # Step 2: Analyze the report using RAG
    # query = input("Enter your query: ").strip()

    # result = await analyze_report(ticker, query)
    # return result
    await analyze_report(ticker)

# Main function to execute the flow
async def main():
    ticker = input("Enter stock ticker: ").strip()
    # query = input("Enter your query: ").strip()

    # Execute the predefined flow
    response = await predefined_flow(ticker)
    print("Flow Response:", response)

if __name__ == "__main__":
    asyncio.run(main())