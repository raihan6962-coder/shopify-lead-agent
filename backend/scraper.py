import requests
from bs4 import BeautifulSoup
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def find_shopify_stores(keyword: str, country: str):
    stores = []
    queries = [
        f'"{keyword}" "powered by shopify" "{country}"',
        f'site:myshopify.com "{keyword}" "{country}"',
        f'"{keyword}" shopify store "{country}" contact',
    ]

    found_urls = set()

    for query in queries:
        try:
            results = google_search(query)
            for url in results:
                clean = clean_url(url)
                if clean and clean not in found_urls:
                    found_urls.add(clean)
                    print(f"Checking store: {clean}")
                    store_data = extract_store_info(clean, keyword, country)
                    if store_data:
                        stores.append(store_data)
                    time.sleep(2)
        except Exception as e:
            print(f"Search error: {e}")
        time.sleep(3)

    return stores


def google_search(query: str):
    urls = []
    try:
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=10"
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/url?q=" in href:
                actual = href.split("/url?q=")[1].split("&")[0]
                if "http" in actual:
                    urls.append(actual)
    except Exception as e:
        print(f"Google search error: {e}")
    return urls


def clean_url(url: str):
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if len(parsed.netloc) > 4:
            return base
    except:
        pass
    return None


def extract_store_info(url: str, keyword: str, country: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)

        # Password protected = no payment gateway yet = good lead
        is_password = "password" in r.url or "Enter store password" in r.text or "password_page" in r.text

        soup = BeautifulSoup(r.text, "html.parser")

        # Store name
        title = soup.find("title")
        name = title.text.strip().split("|")[0].strip() if title else url

        # Check if actually Shopify
        is_shopify = (
            "myshopify.com" in url or
            "Shopify.theme" in r.text or
            "cdn.shopify.com" in r.text or
            "powered by shopify" in r.text.lower()
        )

        if not is_shopify:
            return None

        # No payment gateway check
        no_payment = is_password or check_no_payment(url)

        if not no_payment:
            return None

        # Extract email
        email = extract_email(r.text, url)

        return {
            "name": name,
            "url": url,
            "email": email,
            "keyword": keyword,
            "country": country,
            "status": "Password Protected" if is_password else "No Payment Gateway",
        }

    except Exception as e:
        print(f"Error extracting {url}: {e}")
        return None


def check_no_payment(store_url: str):
    try:
        # Try to access checkout
        cart_url = f"{store_url}/cart"
        r = requests.get(cart_url, headers=HEADERS, timeout=10)
        if "no payment" in r.text.lower() or "payment provider" not in r.text.lower():
            return True
    except:
        pass
    return False


def extract_email(html: str, url: str):
    # From page HTML
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html)
    for email in emails:
        if not any(skip in email for skip in ["shopify", "example", "test", "placeholder"]):
            return email

    # Try contact page
    try:
        contact_url = f"{url}/pages/contact"
        r = requests.get(contact_url, headers=HEADERS, timeout=10)
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", r.text)
        for email in emails:
            if not any(skip in email for skip in ["shopify", "example", "test"]):
                return email
    except:
        pass

    return None
