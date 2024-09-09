import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, Iterator, List
from enum import Enum
from typing import List, Dict, Any, Optional
from dont_tell import nyt_api_key

class NYTApiBase:
    def __init__(self):
        self.api_key = nyt_api_key
        self.session = requests.Session()

    def _make_request(self, url: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        params['api-key'] = self.api_key
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"An error occurred: {e}")
            return {}

    def _extract_article_info(self, article: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "pub_date": article.get("pub_date"),
            "document_type": article.get("document_type"),
            "news_desk": article.get("news_desk"),
            "section_name": article.get("section_name"),
            "byline": article.get("byline", {}).get("original"),
            "abstract": article.get("abstract"),
            "web_url": article.get("web_url"),
            "type_of_material": article.get("type_of_material"),
            "headline": article.get("headline", {}).get("main")
        }

class ArticleSearch(NYTApiBase):
    BASE_URL = "https://api.nytimes.com/svc/search/v2/articlesearch.json"

    def search(self, query: str, page: int = 0) -> List[Dict[str, Any]]:
        params = {"q": query, "page": page}
        result = self._make_request(self.BASE_URL, params)
        if 'response' in result and 'docs' in result['response']:
            return [self._extract_article_info(article) for article in result['response']['docs']]
        return []

    def paginated_search(self, query: str, max_pages: int = 10) -> Iterator[List[Dict[str, Any]]]:
        for page in range(max_pages):
            result = self.search(query, page)
            if result:
                yield result
            else:
                break
            
class TopStoriesAPI(NYTApiBase):
    BASE_URL = "https://api.nytimes.com/svc/topstories/v2"

    VALID_SECTIONS = [
        'arts', 'automobiles', 'books/review', 'business', 'fashion', 'food',
        'health', 'home', 'insider', 'magazine', 'movies', 'nyregion',
        'obituaries', 'opinion', 'politics', 'realestate', 'science', 'sports',
        'sundayreview', 'technology', 'theater', 't-magazine', 'travel',
        'upshot', 'us', 'world', 'home'
    ]

    def get_top_stories(self, section='home'):
        if section not in self.VALID_SECTIONS:
            raise ValueError(f"Invalid section. Must be one of: {', '.join(self.VALID_SECTIONS)}")

        endpoint = f"{self.BASE_URL}/{section}.json"
        response = self._make_request(endpoint)
        
        # Assuming the API returns a list of articles in the 'results' key
        if 'results' in response:
            return [self._extract_article_info(article) for article in response['results']]
        return []

    def _extract_article_info(self, article):
        # Override the base method to extract information specific to Top Stories API
        return {
            "section": article.get("section"),
            "subsection": article.get("subsection"),
            "title": article.get("title"),
            "abstract": article.get("abstract"),
            "url": article.get("url"),
            "byline": article.get("byline"),
            "item_type": article.get("item_type"),
            "updated_date": article.get("updated_date"),
            "created_date": article.get("created_date"),
            "published_date": article.get("published_date"),
            "material_type_facet": article.get("material_type_facet"),
            "kicker": article.get("kicker"),
            "short_url": article.get("short_url")
        }

class Period(Enum):
    ONE_DAY = 1
    SEVEN_DAYS = 7
    THIRTY_DAYS = 30

class MostPopularAPI(NYTApiBase):
    BASE_URL = "https://api.nytimes.com/svc/mostpopular/v2"

    def get_most_emailed(self, period: Period) -> List[Dict[str, Any]]:
        """Get most emailed articles for the specified period."""
        endpoint = f"{self.BASE_URL}/emailed/{period.value}.json"
        return self._process_response(self._make_request(endpoint))

    def get_most_shared(self, period: Period) -> List[Dict[str, Any]]:
        """Get most shared articles for the specified period."""
        endpoint = f"{self.BASE_URL}/shared/{period.value}.json"
        return self._process_response(self._make_request(endpoint))

    def get_most_viewed(self, period: Period) -> List[Dict[str, Any]]:
        """Get most viewed articles for the specified period."""
        endpoint = f"{self.BASE_URL}/viewed/{period.value}.json"
        return self._process_response(self._make_request(endpoint))

    def _process_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process the API response and extract article information."""
        if 'results' in response:
            return [self._extract_article_info(article) for article in response['results']]
        return []

    def _extract_article_info(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant information from an article."""
        return {
            "url": article.get("url"),
            "adx_keywords": article.get("adx_keywords"),
            "column": article.get("column"),
            "section": article.get("section"),
            "byline": article.get("byline"),
            "type": article.get("type"),
            "title": article.get("title"),
            "abstract": article.get("abstract"),
            "published_date": article.get("published_date"),
            "source": article.get("source"),
            "id": article.get("id"),
            "asset_id": article.get("asset_id"),
            "views": article.get("views"),
            "des_facet": article.get("des_facet"),
            "org_facet": article.get("org_facet"),
            "per_facet": article.get("per_facet"),
            "geo_facet": article.get("geo_facet"),
            "media": article.get("media"),
            "uri": article.get("uri")
        }

class Archive(NYTApiBase):
    BASE_URL = "https://api.nytimes.com/svc/archive/v1/{year}/{month}.json"

    def get_month_archive(self, year: int, month: int) -> List[Dict[str, Any]]:
        url = self.BASE_URL.format(year=year, month=month)
        result = self._make_request(url)
        if 'response' in result and 'docs' in result['response']:
            return [self._extract_article_info(article) for article in result['response']['docs']]
        return []

    def save_month_archive(self, year: int, month: int, filename: str):
        data = self.get_month_archive(year, month)
        with open(filename, 'w') as f:
            json.dump(data, f)

    @staticmethod
    def process_saved_archive(filename: str, batch_size: int = 100) -> Iterator[List[Dict[str, Any]]]:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        for i in range(0, len(data), batch_size):
            yield data[i:i+batch_size]
            
class BooksAPI(NYTApiBase):
    BASE_URL = "https://api.nytimes.com/svc/books/v3"

    def get_best_seller_lists(self):
        endpoint = f"{self.BASE_URL}/lists/names.json"
        return self._make_request(endpoint)

    def get_best_seller_list_data(self, date, list_name):
        endpoint = f"{self.BASE_URL}/lists/{date}/{list_name}.json"
        return self._make_request(endpoint)

    def search_book_reviews(self, author=None, isbn=None, title=None):
        endpoint = f"{self.BASE_URL}/reviews.json"
        params = {}
        if author:
            params['author'] = author
        if isbn:
            params['isbn'] = isbn
        if title:
            params['title'] = title
        return self._make_request(endpoint, params)
    
    


if __name__ == "__main__":
    article_search = ArticleSearch()
    archive = Archive()

    # Example usage of Article Search
    print("Article Search Example:")
    for page in article_search.paginated_search("New York", max_pages=2):
        for article in page:
            print(json.dumps(article, indent=2))
            print("---")

    # Example usage of Archive
    print("\nArchive Example:")
    archive.save_month_archive(2023, 1, "nyt_archive_2023_01.json")
    for batch in Archive.process_saved_archive("nyt_archive_2023_01.json", batch_size=10):
        for article in batch:
            print(json.dumps(article, indent=2))
            print("---")