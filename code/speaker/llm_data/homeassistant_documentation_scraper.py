import requests
from bs4 import BeautifulSoup
import json
import time

def fetch_urls(url, visited):
    """Fetch URLs from a given page and recursively visit each one."""
    if url in visited:
        return []
    print(f"Visiting: {url}")
    visited.add(url)  # Mark this URL as visited
    page_content = requests.get(url).text
    soup = BeautifulSoup(page_content, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith('/docs')]
    full_links = [f"https://www.home-assistant.io{link}" for link in links if link not in visited]
    for link in full_links:
        fetch_urls(link, visited)  # Recursive call to visit each link
    return visited

def scrape_documentation(start_url):
    visited = set()
    urls_to_scrape = fetch_urls(start_url, visited)
    documentation_text = []
    for url in urls_to_scrape:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_content = ' '.join([p.text for p in soup.find_all('p')])  # Simplify; you may want more structure
            documentation_text.append({'url': url, 'content': text_content})
            time.sleep(1)  # Be polite and don't overwhelm the server
    return documentation_text

start_url = 'https://www.home-assistant.io/docs/'
documentation_data = scrape_documentation(start_url)

filename = 'home_assistant_docs.json'
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(documentation_data, f, ensure_ascii=False, indent=4)

print(f"Data saved to {filename}")