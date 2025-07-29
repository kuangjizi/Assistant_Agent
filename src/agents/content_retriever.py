# src/agents/content_retriever.py
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from datetime import datetime, timedelta
import logging
from urllib.parse import urljoin, urlparse
import re
from src.services.web_scraper import WebScraper

class ContentRetriever:
    def __init__(self, vector_store, db_manager):
        self.vector_store = vector_store
        self.db_manager = db_manager
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')

        # Initialize WebScraper with default configuration
        self.web_scraper = WebScraper({
            'user_agent': 'AI-Assistant-Agent/1.0',
            'request_delay': 1.0,
            'timeout': 30,
            'max_retries': 3,
            'max_content_length': 1024 * 1024  # 1MB
        })

        # Maximum number of blog posts to retrieve from a blog index page
        self.max_blog_posts = 10

    async def retrieve_content(self, urls: list) -> list:
        """Retrieve content from multiple URLs concurrently"""
        # Use WebScraper to scrape multiple URLs concurrently
        results = await self.web_scraper.scrape_multiple_urls(urls, max_concurrent=5)

        valid_content = []
        for result in results:
            if not result['success']:
                logging.error(f"Failed to fetch {result['url']}: {result.get('error', 'Unknown error')}")
                continue

            # Process the result based on content type
            if result.get('metadata', {}).get('type') == 'feed':
                # Handle RSS/Atom feed
                feed_content = await self._process_feed_content(result)
                valid_content.extend(feed_content)
            else:
                # Handle regular HTML content
                processed_content = await self._process_html_content(result)
                if processed_content:
                    valid_content.append(processed_content)

                    # If this is a blog index page, also process its posts
                    if self._is_blog_index_from_result(result):
                        blog_posts = await self._process_blog_index_from_result(result)
                        valid_content.extend(blog_posts)

        return valid_content

    def _is_blog_index_from_result(self, result: dict) -> bool:
        """Determine if a scraping result is from a blog index page"""
        url = result['url']
        content = result['content']
        title = result['title']

        # Check URL patterns typical for blog index pages
        parsed_url = urlparse(url)
        path = parsed_url.path

        # Special case for known blog platforms
        if "lilianweng.github.io" in url and (not path or path == "/"):
            logging.info(f"Detected Lilian Weng's blog index: {url}")
            return True

        # If path is empty or just "/", it's likely a homepage/index
        if not path or path == "/":
            # Look for blog-like keywords in title
            blog_keywords = ['blog', 'posts', 'articles', 'journal', 'writing']
            if any(keyword in title.lower() for keyword in blog_keywords):
                return True

            # Check for multiple post-like links in the content
            link_count = content.lower().count('href=')
            if link_count > 10:  # Arbitrary threshold for potential blog index
                return True

        return False

    async def _process_html_content(self, result: dict) -> dict:
        """Process HTML content from WebScraper result"""
        url = result['url']
        content = result['content']
        title = result['title']

        # Check if content is new (compare with stored hash)
        content_hash = result['content_hash']

        if self.db_manager.is_content_new(url, content_hash):
            # Split and store in vector database
            chunks = self.text_splitter.split_text(content)

            if not chunks:
                logging.warning(f"No content chunks extracted from {url}")
                return None

            # Store in vector database
            self.vector_store.add_texts(
                texts=chunks,
                metadatas=[{
                    'url': url,
                    'title': title,
                    'source': url,  # Add source field for RetrievalQAWithSourcesChain
                    'timestamp': datetime.now().isoformat(),
                    'chunk_id': i
                } for i in range(len(chunks))]
            )

            # Update database record
            self.db_manager.update_content_record(url, content_hash, title, content)

            return {
                'url': url,
                'title': title,
                'content': content,
                'is_new': True,
                'timestamp': datetime.now()
            }
        else:
            return {'url': url, 'is_new': False}

    async def _process_feed_content(self, result: dict) -> list:
        """Process RSS/Atom feed content from WebScraper result"""
        url = result['url']
        feed_entries = result.get('feed_entries', [])
        processed_entries = []

        logging.info(f"Processing feed with {len(feed_entries)} entries from {url}")

        for entry in feed_entries:
            entry_title = entry.get('title', 'No Title')
            entry_link = entry.get('link', '')
            entry_content = entry.get('description', '') + '\n' + entry.get('summary', '')

            if not entry_link:
                continue

            # Generate a hash for this entry
            entry_hash = hash(entry_content)

            if self.db_manager.is_content_new(entry_link, entry_hash):
                # Split and store in vector database
                chunks = self.text_splitter.split_text(entry_content)

                if not chunks:
                    continue

                # Store in vector database
                self.vector_store.add_texts(
                    texts=chunks,
                    metadatas=[{
                        'url': entry_link,
                        'title': entry_title,
                        'source': entry_link,
                        'feed_url': url,
                        'timestamp': datetime.now().isoformat(),
                        'chunk_id': i
                    } for i in range(len(chunks))]
                )

                # Update database record
                self.db_manager.update_content_record(entry_link, entry_hash, entry_title, entry_content)

                processed_entries.append({
                    'url': entry_link,
                    'title': entry_title,
                    'content': entry_content,
                    'is_new': True,
                    'timestamp': datetime.now()
                })
            else:
                processed_entries.append({
                    'url': entry_link,
                    'is_new': False
                })

        return processed_entries

    async def _process_blog_index_from_result(self, result: dict) -> list:
        """Process a blog index page by extracting and fetching individual posts"""
        url = result['url']
        content = result['content']

        # Extract potential blog post links using WebScraper's HTML parsing
        soup = BeautifulSoup(content, 'html.parser')
        post_links = []
        seen_urls = set()

        # Common blog post URL patterns
        blog_post_patterns = [
            r'/\d{4}/\d{2}/\d{2}/',  # Date-based: /2023/01/01/
            r'/blog/[^/]+',           # /blog/post-title
            r'/posts?/[^/]+',         # /post/post-title or /posts/post-title
            r'/article/[^/]+',        # /article/post-title
            r'/\d{4}/[^/]+',          # Year-based: /2023/post-title
            r'/[^/]+\.html',          # /post-title.html
        ]

        # Special case for Lilian Weng's blog
        if "lilianweng.github.io" in url:
            blog_post_patterns.extend([
                r'/posts/\d{4}-\d{2}-\d{2}-',    # New pattern: /posts/2024-11-28-reward-hacking/
                r'/lil-log/\d{4}/\d{2}/\d{2}/',  # Old pattern: /lil-log/2023/01/10/
            ])

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(url, href)

            # Skip if already processed or external link
            if full_url in seen_urls or not full_url.startswith(url):
                continue

            # Check if URL matches blog post patterns
            parsed_url = urlparse(full_url)
            path = parsed_url.path

            is_blog_post = any(re.search(pattern, path) for pattern in blog_post_patterns)

            # Also check if link is inside a post title element
            in_title_element = link.parent and link.parent.name in ['h1', 'h2', 'h3']

            if is_blog_post or in_title_element:
                post_links.append(full_url)
                seen_urls.add(full_url)

        post_links = post_links[:self.max_blog_posts]  # Limit number of posts

        if not post_links:
            logging.warning(f"No blog post links found on {url}")
            return []

        logging.info(f"Found {len(post_links)} blog posts on {url}")

        # Use WebScraper to fetch all blog posts
        blog_results = await self.web_scraper.scrape_multiple_urls(post_links)

        processed_posts = []
        for blog_result in blog_results:
            if not blog_result['success']:
                logging.error(f"Failed to fetch blog post {blog_result['url']}: {blog_result.get('error')}")
                continue

            processed_post = await self._process_html_content(blog_result)
            if processed_post:
                processed_posts.append(processed_post)

        return processed_posts

    async def detect_and_process_feed(self, url: str) -> bool:
        """
        Detect if a URL is an RSS/Atom feed and process it

        Returns True if it was a feed and was processed, False otherwise
        """
        try:
            # Try to scrape as a feed first
            result = await self.web_scraper.scrape_url(url)

            # Check if it's a feed based on content type or structure
            if result.get('metadata', {}).get('type') == 'feed' or 'feed_entries' in result:
                logging.info(f"Detected feed at {url}")
                feed_content = await self._process_feed_content(result)
                return True

            return False

        except Exception as e:
            logging.error(f"Error detecting feed at {url}: {e}")
            return False

    async def check_robots_txt(self, url: str) -> bool:
        """
        Check if scraping a URL is allowed according to robots.txt

        Returns True if allowed, False if disallowed
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        return self.web_scraper.is_url_allowed(url)
