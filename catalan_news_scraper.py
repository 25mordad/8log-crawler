import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import hashlib
import base64

# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_DATABASE_ID = os.getenv("CLOUDFLARE_DATABASE_ID")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY")
BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_DATABASE_ID}/query"

# Headers for API requests
HEADERS = {
    "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
    "Content-Type": "application/json",
}

# Base URL of the website
news_base_url = "https://www.catalannews.com"

# Function to generate a hashed ID for a URL
def generate_hashed_id(input_url: str) -> str:
    hash_object = hashlib.sha256(input_url.encode())
    hash_bytes = hash_object.digest()
    hash_base64 = base64.urlsafe_b64encode(hash_bytes).decode("utf-8").rstrip("=")
    return hash_base64[:16]  # Truncate to 16 characters

# Send a GET request to the webpage
response = requests.get(news_base_url)
if response.status_code != 200:
    print(f"Failed to fetch the page: {response.status_code}")
    exit()

# Parse the webpage content
soup = BeautifulSoup(response.text, "html.parser")

# Find all articles
articles = soup.find_all("article", limit=10)

# Collect article data
inserted_count = 0
for article in articles:
    link_tag = article.find("a", class_="home-story_link__6nXJf")
    if not link_tag:
        continue

    # Extract URL
    relative_url = link_tag.get("href", "")
    url = news_base_url + relative_url if relative_url.startswith("/") else relative_url

    # Generate URL ID
    url_id = generate_hashed_id(url)

    # SQL query formatted directly as a string
    sql_query = f"""
    INSERT INTO catalan_news (url_id, source_url)
    VALUES ('{url_id}', '{url}');
    """

    # Create the query payload
    query_payload = {
        "sql": sql_query,
    }

    # Execute query via Cloudflare D1 API
    try:
        response = requests.post(BASE_URL, headers=HEADERS, json=query_payload)
        if response.status_code == 200:
            inserted_count += 1
        elif response.status_code == 409:  # Conflict error
            print(f"Duplicate record skipped for URL: {url}")
        else:
            print(f"Failed to insert record: {response.status_code}, {response.text}")
            print(f"{url}, {url_id}")
    except requests.RequestException as e:
        print(f"Error connecting to Cloudflare D1: {e}")

# Print the results
print(f"Process completed. Inserted {inserted_count} new records.")
