import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError


# Load environment variables from .env file
load_dotenv()

# Configuration from environment variables
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_DATABASE_ID = os.getenv("CLOUDFLARE_DATABASE_ID")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY")
BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/d1/database/{CLOUDFLARE_DATABASE_ID}/query"

R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT_URL=os.getenv("R2_ENDPOINT_URL")
R2_CUSTOM_DOMAIN=os.getenv("R2_CUSTOM_DOMAIN")

def fetch_uncrawled_record():
    """Fetch a record from Cloudflare D1 database where `is_crawled = false`."""
    try:
        query = {
            "sql": "SELECT * FROM catalan_news WHERE is_crawled = false LIMIT 1"
        }
        headers = {
            "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(BASE_URL, json=query, headers=headers)
        response.raise_for_status()

        data = response.json()
        if data.get("result") and data["result"][0].get('results'):
            return data["result"][0]['results'][0]  # Return the first record
        else:
            print("No uncrawled records found.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching uncrawled record: {e}")
        return None

def fetch_h1_photo_and_content_from_url(url):
    """Fetch the H1 tag content, photo URL, main content, and published date from the given URL."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract H1 tag content
        h1_tag = soup.find('h1')
        h1_content = h1_tag.get_text(strip=True) if h1_tag else None

        # Extract photo URL from <figure>
        figure = soup.find('figure', class_='representative-media_figure__DiZdo')
        img_tag = figure.find('img') if figure else None
        photo_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else None

        # Extract main content
        content_div = soup.find('div', class_='story-body_body__yAPG3')
        content_paragraphs = content_div.find_all(['p', 'h4']) if content_div else []
        main_content = "\n\n".join(
            paragraph.get_text(strip=True) for paragraph in content_paragraphs
        )

        published_date_label = soup.find('label', string=lambda s: s and "First published" in s)
        if published_date_label:
            published_date_strong = published_date_label.find_next('strong')
            published_date = published_date_strong.get_text(strip=True) if published_date_strong else None
        else:
            published_date = None

        return h1_content, photo_url, main_content, published_date
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None, None, None, None

def update_full_record_in_db(record_id, title_en, photo_url, content_en, published_date):
    """Update the record in the Cloudflare D1 database."""
    try:
        # Construct the SQL query
        sql_query = f"""
        UPDATE catalan_news
        SET title_en = '{title_en.replace("'", "''")}',
            photo = '{photo_url.replace("'", "''") if photo_url else 'NULL'}',
            content_en = '{content_en.replace("'", "''") if content_en else 'NULL'}',
            published_date = '{published_date.replace("'", "''") if published_date else 'NULL'}',
            is_crawled = true
        WHERE id = {record_id}
        """

        # Prepare the request payload
        query = {
            "sql": sql_query
        }
        headers = {
            "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
            "Content-Type": "application/json",
        }

        # Make the API request
        response = requests.post(BASE_URL, json=query, headers=headers)
        response.raise_for_status()

        print("Record updated successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error updating record: {e}")
        if e.response:
            print("Response content:", e.response.text)

def upload_photo_to_r2(photo_url, record_id):
    """Download the photo and upload it to Cloudflare R2."""
    try:
        # Step 1: Download the photo
        response = requests.get(photo_url, stream=True)
        response.raise_for_status()

        # Step 2: Connect to R2
        s3_client = boto3.client(
            "s3",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto"  # Specify 'auto' for Cloudflare R2
        )

        # Step 3: Upload the photo
        file_key = f"catalan_news/{record_id}.jpg"  # Example key: catalan_news/45.jpg
        s3_client.upload_fileobj(response.raw, R2_BUCKET_NAME, file_key, ExtraArgs={"ACL": "public-read"})

        # Step 4: Generate the public URL using custom domain
        r2_photo_url = f"{os.getenv('R2_CUSTOM_DOMAIN')}/{file_key}"
        print(f"Uploaded photo to R2: {r2_photo_url}")

        return r2_photo_url
    except requests.exceptions.RequestException as e:
        print(f"Error downloading photo: {e}")
        return None
    except NoCredentialsError as e:
        print(f"Error with R2 credentials: {e}")
        return None
    except Exception as e:
        print(f"Error uploading photo to R2: {e}")
        return None

def main():
    # Step 1: Fetch an uncrawled record
    record = fetch_uncrawled_record()
    if not record:
        return

    # Step 2: Fetch the H1, photo, content, and published date from the source_url
    source_url = record.get("source_url")
    if not source_url:
        print("Source URL not found in the record.")
        return

    h1_content, photo_url, main_content, published_date = fetch_h1_photo_and_content_from_url(source_url)
    if not h1_content and not main_content:
        print("No H1 or main content found on the page.")
        return

    # Step 3: Upload the photo to R2 and get its URL
    r2_photo_url = None
    if photo_url:
        r2_photo_url = upload_photo_to_r2(photo_url, record["id"])


    print(f"Fetched H1: {h1_content}")
    print(f"Fetched Photo URL: {r2_photo_url}")
    # print(f"Fetched Content: {main_content}")
    print(f"Fetched Published Date: {published_date}")

    # Step 3: Update the record in the database
    update_full_record_in_db(record["id"], h1_content, r2_photo_url, main_content, published_date)

if __name__ == "__main__":
    main()
