"""Scrape and download telecom standards and regulations from multiple agencies."""

import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
from pathlib import Path
import argparse

def download_file(url, download_dir, agency_prefix=""):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, stream=True, verify=False, timeout=15)
        response.raise_for_status()

        if "Content-Disposition" in response.headers:
            filename = response.headers["Content-Disposition"].split("filename=")[-1].strip('"')
        else:
            filename = unquote(url.split("/")[-1])
            
        if not filename or filename.endswith('/'):
            filename = f"download_{int(time.time())}.pdf"

        # clean filename
        filename = "".join(c for c in filename if c.isalnum() or c in " ._-")
        
        if agency_prefix and not filename.upper().startswith(agency_prefix.upper()):
            filename = f"{agency_prefix}_{filename}"
            
        filepath = Path(download_dir) / filename
        
        if filepath.exists():
            print(f"File already exists, skipping: {filename}")
            return filepath
            
        print(f"Downloading {filename}...")
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return filepath
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

def scrape_documents(url, download_dir, agency_prefix=""):
    """Scrape the given URL for PDF and DOCX files and download them."""
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        requests.packages.urllib3.disable_warnings()
        print(f"Fetching {url}...")
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        doc_links = []
        for link in links:
            href = link['href'].lower()
            if href.endswith('.pdf') or href.endswith('.doc') or href.endswith('.docx'):
                full_url = urljoin(url, link['href'])
                if full_url not in doc_links:
                    doc_links.append(full_url)
                    
        print(f"Found {len(doc_links)} documents to download from {url}.")
        
        for i, doc_url in enumerate(doc_links, 1):
            print(f"[{i}/{len(doc_links)}] ", end="")
            download_file(doc_url, download_dir, agency_prefix)
            time.sleep(1) # Rate limiting
            
        print(f"Scraping completed for {url}!")
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Telecom Standards & Regulations")
    parser.add_argument("--url", required=True, help="URL to scrape")
    parser.add_argument("--agency", default="", help="Prefix for downloaded files (e.g., TEC, DoT)")
    parser.add_argument("--dir", default=str(Path(__file__).parent.parent / "data" / "raw_regulations"), help="Download directory")
    args = parser.parse_args()
    
    scrape_documents(args.url, args.dir, args.agency)
