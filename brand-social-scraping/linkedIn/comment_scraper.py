import csv
from apify_client import ApifyClient

ACTOR_ID = "2XnpwxfhSW1fAWElp"
LIMIT = 30

def read_post_urls(csv_file):
    """Read post URLs from a CSV file."""
    urls = []
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("post_url", "").strip()
            if url:
                urls.append(url)
    return urls

def extract_comment_info(raw_comments):
    """Extract only comment text from raw comment items."""
    extracted = []
    for item in raw_comments:
        if "comment_id" not in item:
            continue
        extracted.append({
            "comment_text": item.get("text", "")
        })
    return extracted

def extract_comments(post_csv_path, brand_folder, apify_token):
    """Main function to extract comments from LinkedIn post URLs."""
    client = ApifyClient(apify_token)
    post_urls = read_post_urls(post_csv_path)
    all_comments = []
    output_csv = f"brand-social-scraping/linkedIn/data/{brand_folder}/comments.csv"

    for url in post_urls:
        try:
            print(f"Processing comments for: {url}")
            run_input = {
                "postIds": [url],
                "page_number": 1,
                "sortOrder": "most recent",
                "limit": LIMIT,
            }

            run = client.actor(ACTOR_ID).call(run_input=run_input)

            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                comments = extract_comment_info([item])
                all_comments.extend(comments)

        except Exception as e:
            print(f"Error processing {url}: {e}")

    if all_comments:
        with open(output_csv, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["comment_text"])
            writer.writeheader()
            writer.writerows(all_comments)
        print(f"Extracted comments saved to {output_csv}")
    else:
        print("No comments extracted.")
