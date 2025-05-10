from apify_client import ApifyClient
import os
import csv

def get_details(url, api_key,brand_name):
    '''returns actor pulled data, cols to consider and result type, csv_file'''
    folder = f"brand-social-scraping/linkedIn/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)
    client = ApifyClient(api_key)

    run_input = {
                
        "company_names": [url],
        "limit": 100
    }
    run = client.actor("eUv8d0ndjClMLtT1B").call(run_input=run_input)
    dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    csv_file = f"brand-social-scraping/linkedIn/data/{brand_name}/posts_details.csv"
    fields = [
        "post_url",
        "post_date",
        "text",
        "total_reactions",
        "likes",
        "love",
        "celebrate",
        "comments",
        "reposts",
        "media_urls"
    ]
    return dataset_items , fields, csv_file, brand_name


def extract(dataset_items, fields, csv_file, brand_name):

    folder = f"brand-social-scraping/linkedIn/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()


        for post in dataset_items:
            row = {
                "post_url": post.get("post_url", ""),
                "post_date": post.get("posted_at", {}).get("date", ""),
                "text": post.get("text", "").replace("\n", " ").strip(),
                "total_reactions": post.get("stats", {}).get("total_reactions", 0),
                "likes": post.get("stats", {}).get("like", 0),
                "love": post.get("stats", {}).get("love", 0),
                "celebrate": post.get("stats", {}).get("celebrate", 0),
                "comments": post.get("stats", {}).get("comments", 0),
                "reposts": post.get("stats", {}).get("reposts", 0),
                "media_urls": ", ".join([item["url"] for item in post.get("media", {}).get("items", [])])
            }
            writer.writerow(row)

        print(f" Extracted {len(dataset_items)} items to {csv_file}")

# dataset_items, fields, csv_file, brand_name = get_details("https://www.linkedin.com/company/volkswagen","apify_api_SpjhH1ASpmwDW9aw12i5NiQn3m5Td81bUt1v", "volkswagen-group")
# extract(dataset_items, fields, csv_file, brand_name)