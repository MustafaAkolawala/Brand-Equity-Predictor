from apify_client import ApifyClient
import os
import csv

"""Get multiple brand's twitter profile details"""

def get_details(brand_list, api_key):
    '''returns actor pulled data, cols to consider and result type, csv_file'''
    folder = f"brand-social-scraping/twitter/data/"
    os.makedirs(folder, exist_ok=True)
    client = ApifyClient(api_key)

    run_input = {
        "user_names": brand_list
    }
    run = client.actor("tLs1g71YVTPoXAPnb").call(run_input=run_input)
    dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    csv_file = f"brand-social-scraping/twitter/data/all_brands_profile_details.csv"
    fields = [
            "core.name",
            "core.screen_name", #username
            "core.created_at",  
            "relationship_counts.followers",
            "relationship_counts.following",
            "tweet_counts.tweets",
            "tweet_counts.media_tweets",
    ]

    return dataset_items , fields, csv_file
import csv

def extract(dataset_items, fields, csv_file):
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for item in dataset_items:
            if item.get("type") == "mock_user":
                continue  # Skip mock users

            row = {
                "core.name": item.get("core", {}).get("name", ""),
                "core.screen_name": item.get("core", {}).get("screen_name", ""),
                "core.created_at": item.get("core", {}).get("created_at", ""),
                "relationship_counts.followers": item.get("relationship_counts", {}).get("followers", 0),
                "relationship_counts.following": item.get("relationship_counts", {}).get("following", 0),
                "tweet_counts.tweets": item.get("tweet_counts", {}).get("tweets", 0),
                "tweet_counts.media_tweets": item.get("tweet_counts", {}).get("media_tweets", 0),
            }
            
            writer.writerow(row)

        print(f"Extracted {len(dataset_items)} items to {csv_file}")
