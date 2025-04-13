from apify_client import ApifyClient
import os
import csv

def get_details(api_key,brand_name):
    '''returns actor pulled data, cols to consider and result type, csv_file'''
    folder = f"brand-social-scraping/twitter/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)
    client = ApifyClient(api_key)

    run_input = {
        "filter:blue_verified": False,
        "filter:consumer_video": False,
        "filter:has_engagement": False,
        "filter:hashtags": False,
        "filter:images": False,
        "filter:links": False,
        "filter:media": False,
        "filter:mentions": False,
        "filter:native_video": False,
        "filter:nativeretweets": False,
        "filter:news": False,
        "filter:pro_video": False,
        "filter:quote": False,
        "filter:replies": False,
        "filter:safe": False,
        "filter:spaces": False,
        "filter:twimg": False,
        "filter:verified": False,
        "filter:videos": False,
        "filter:vine": False,
        "from": brand_name,
        "include:nativeretweets": False,
        "lang": "en",
        "maxItems": 100,
        "since": "2024-1-1_23:59:59_UTC",
        "until": "2025-4-1_23:59:59_UTC"
    }
    run = client.actor("CJdippxWmn9uRfooo").call(run_input=run_input)
    dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    csv_file = f"brand-social-scraping/twitter/data/{brand_name}/posts_details.csv"
    fields = [
            "url",
            "text",
            "createdAt",  #timestamp
            "retweetCount",
            "replyCount",
            "likeCount",
            "viewCount",
    ]

    return dataset_items , fields, csv_file, brand_name


def extract(dataset_items, fields, csv_file, brand_name):

    folder = f"brand-social-scraping/twitter/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for item in dataset_items:
            row = {
                "url": item.get("url", ""),
                "text": item.get("text", ""),
                "createdAt": item.get("createdAt", ""),
                "retweetCount": item.get("retweetCount", 0),
                "replyCount": item.get("replyCount", 0),
                "likeCount": item.get("likeCount", ""),
                "viewCount":item.get("viewCount", "")
            }
            writer.writerow(row)

        print(f" Extracted {len(dataset_items)} items to {csv_file}")

