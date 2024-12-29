# Crawler.py README

## Overview

`crawler.py` is a Python script designed to fetch and process uncrawled records from a Cloudflare D1 database. It extracts metadata and content from web pages, uploads images to Cloudflare R2 storage, and updates the database with the processed information.

## Features

- Fetch uncrawled records from a Cloudflare D1 database.
- Scrape H1, main content, images, and publication dates from web pages.
- Upload images to Cloudflare R2 storage and generate public URLs.
- Update processed records in the database.

## Requirements

- Python 3.7 or higher
- Required Python libraries: `requests`, `bs4`, `boto3`, `python-dotenv`
- Environment variables (stored in a `.env` file):
  - `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_DATABASE_ID`, `CLOUDFLARE_API_KEY`
  - `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`
  - `R2_ENDPOINT_URL`, `R2_CUSTOM_DOMAIN`

## Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:25mordad/8log.ir.git
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the `.env.sample` file to create a `.env` file and populate it with your Cloudflare and R2 credentials:
    ```bash
    cp .env.sample .env
    ```

## Usage

Run the script with:
```bash
python crawler.py
```

The script will:
1. Fetch an uncrawled record.
2. Scrape metadata and content from the provided URL.
3. Upload images to Cloudflare R2.
4. Update the database with the processed information.

## Notes

- Ensure your Cloudflare and R2 credentials are correctly configured.
- The script assumes specific database fields and HTML structures; customize as needed for other use cases.

## License

This project is open-source and available under the MIT License.
