from apify_client import ApifyClient
import os
import csv

def get_details(url, api_key,brand_name):
    '''returns actor pulled data, cols to consider and result type, csv_file'''
    folder = f"brand-social-scraping/linkedIn/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)
    client = ApifyClient(api_key)
    run_input = {
        "profileUrls": [url]
    }

    run = client.actor("AjfNXEI9qTA2IdaAX").call(run_input=run_input)
    dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    csv_file = f"brand-social-scraping/linkedIn/data/{brand_name}/profile_details.csv"
    fields = [
        "url",
        "companyName",
        "employeeCount",
        "followerCount"
    ]  
    
    return dataset_items , fields, csv_file, brand_name

def extract(dataset_items, fields, csv_file, brand_name):
    '''extract the dataset_items according to their result_type and fields'''
    folder = f"brand-social-scraping/linkedIn/data/{brand_name}"
    os.makedirs(folder, exist_ok=True)

    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        item = dataset_items[0] if dataset_items else {}
        row = {}

        for key in fields:
            value = item.get(key, "")
            if key == "foundedOn" and isinstance(value, dict):
                row[key] = value.get("year", "")
            else:
                row[key] = value

        writer.writerow(row)

    print(f" Extracted {len(dataset_items)} items to {csv_file}")

# dataset_items, fields, csv_file, brand_name = get_details("https://www.linkedin.com/company/volkswagen-group","apify_api_SpjhH1ASpmwDW9aw12i5NiQn3m5Td81bUt1v", "volkswagen-group")
# extract(dataset_items, fields, csv_file, brand_name)