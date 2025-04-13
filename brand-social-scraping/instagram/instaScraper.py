from apify_client import ApifyClient
import os
import csv

def get_details(url, api_key, result_type,brand_name):
    '''returns actor pulled data, cols to consider and result type, csv_file'''
    folder = f"brand-social-scraping/instagram/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)
    client = ApifyClient(api_key)
    run_input = {
        "directUrls": [url],
        "onlyPostsNewerThan": "2024-01-01",
        "resultsType": result_type,
        "resultsLimit": 200,
        "searchType": "hashtag",
        "searchLimit": 1,
    }

    run = client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)
    dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    if result_type == "details":
        csv_file = f"brand-social-scraping/instagram/data/{brand_name}/profile_details.csv"
        fields = [
            "username",
            "url",
            "fullName",
            "followersCount",
            "followsCount",
            "verified",
            "igtvVideoCount",
            "postsCount",
        ]
    elif result_type == "posts":
        csv_file = f"brand-social-scraping/instagram/data/{brand_name}/posts_details.csv"

        fields = [
            "inputUrl",
            "caption",
            "hashtags",
            "commentsCount",
            "url",
            "likesCount",
            "timestamp",
            "videoViewCount",
            "latestCommentsText",
        ]
    elif result_type == "stories":
        csv_file = f"brand-social-scraping/instagram/data/{brand_name}/reels_details.csv"
        fields = [
            "inputUrl",
            "caption",
            "hashtags",
            "commentsCount",
            "url",
            "videoViewCount",
            "likesCount",
            "timestamp",
            "latestCommentsText"
        ]
    return dataset_items , fields, result_type, csv_file, brand_name

def extract(dataset_items, fields, result_type, csv_file, brand_name):
    '''extract the dataset_items according to their result_type and fields, if result_type == 'details' follow some another approach cause json data differs for different result types '''
    folder = f"brand-social-scraping/instagram/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f, open(f"brand-social-scraping/instagram/data/{brand_name}/post_urls.csv", mode="w", newline="", encoding="utf-8") as url_file:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        # post urls csv write objects
        url_writer = csv.writer(url_file)
        url_writer.writerow(["url"]) 

        if result_type == "details":
            item = dataset_items[0] if dataset_items else {}
            row = {key: item.get(key, "") for key in fields}
            writer.writerow(row)

        elif result_type in ["posts", "stories"]:
            for item in dataset_items:
                row = {
                    "inputUrl": item.get("inputUrl", ""),
                    "caption": item.get("caption", ""),
                    "hashtags": ", ".join(item.get("hashtags", [])),
                    "commentsCount": item.get("commentsCount", 0),
                    "likesCount": item.get("likesCount", 0),
                    "timestamp": item.get("timestamp", ""),
                    "url":item.get("url", "")

                }
                post_url = row["url"]
                if post_url:
                    url_writer.writerow([post_url])
                
                if item.get("type") == "Video":
                    row["videoViewCount"] = item.get("videoViewCount", 0)
                else:
                    row["videoViewCount"] = ""
                
                latest_comments = item.get("latestComments", [])
                comment_texts = [comment.get("text", "") for comment in latest_comments]
                row["latestCommentsText"] = " || ".join(comment_texts)

                writer.writerow(row)

    print(f" Extracted {len(dataset_items)} items to {csv_file}")

def pulling_comments(url,api_key):
    client = ApifyClient(api_key)
    run_input = {
        "directUrls": [url],
        "resultsType": "comments",
        "resultsLimit": 50
    }

    run = client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)
    dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    comments_text = [item.get("text", "") for item in dataset_items]
    return comments_text

def get_post_urls(csv_file, brand_name, api_key):
    folder = f"brand-social-scraping/instagram/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)
    with open(csv_file, mode="r", encoding="utf-8") as f, open(f"brand-social-scraping/instagram/data/{brand_name}/comments_text.csv", mode="w", newline="", encoding="utf-8") as out_f:

        reader = csv.DictReader(f)
        writer = csv.writer(out_f)
        writer.writerow(["commentText"])

        for row in reader:
            post_url = row["url"]
            print(post_url)
            # comment_texts = pulling_comments(post_url, api_key)
                
            # for comment in comment_texts:
            #     writer.writerow([comment]) 




# items, fields, result_type, csv_file = get_details("https://www.instagram.com/tatamotorscars", "apify_api_SpjhH1ASpmwDW9aw12i5NiQn3m5Td81bUt1v","stories","tatamotors")
# extract(items, fields, result_type, csv_file)
# get_post_urls(f"brand-social-scraping/instagram/{brand_name}_post_urls.csv")
