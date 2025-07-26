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

class ContentRetriever:
    def __init__(self, vector_store, db_manager):
        self.vector_store = vector_store
        self.db_manager = db_manager
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')

        # Maximum number of blog posts to retrieve from a blog index page
        self.max_blog_posts = 10

        # Common blog post URL patterns
        self.blog_post_patterns = [
            r'/\d{4}/\d{2}/\d{2}/',  # Date-based: /2023/01/01/
            r'/blog/[^/]+',           # /blog/post-title
            r'/posts?/[^/]+',         # /post/post-title or /posts/post-title
            r'/article/[^/]+',        # /article/post-title
            r'/\d{4}/[^/]+',          # Year-based: /2023/post-title
            r'/[^/]+\.html',          # /post-title.html
        ]

    async def retrieve_content(self, urls: list) -> list:
        """Retrieve content from multiple URLs concurrently"""
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                tasks.append(self._process_url(session, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_content = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Failed to fetch {urls[i]}: {result}")
            else:
                if isinstance(result, list):
                    # If result is a list (from blog index processing), extend
                    valid_content.extend(result)
                else:
                    # Single result
                    valid_content.append(result)

        return valid_content

    async def _process_url(self, session, url: str) -> list:
        """Process URL, detecting if it's a blog index and handling appropriately"""
        try:
            # First, fetch the URL content
            async with session.get(url, timeout=30) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Check if this looks like a blog index page
                if self._is_blog_index(soup, url):
                    logging.info(f"Detected blog index page: {url}")
                    return await self._process_blog_index(session, soup, url)
                else:
                    # Process as a regular page
                    result = await self._fetch_url_content(session, url, soup=soup)
                    return [result] if result else []

        except Exception as e:
            logging.error(f"Error processing {url}: {e}")
            raise

    def _is_blog_index(self, soup, url: str) -> bool:
        """Detect if the page is likely a blog index page"""
        # Check URL patterns typical for blog index pages
        parsed_url = urlparse(url)
        path = parsed_url.path

        # If path is empty or just "/", it's likely a homepage/index
        if not path or path == "/":
            # Look for multiple article elements or post links
            article_elements = len(soup.find_all(['article', 'div'], class_=re.compile(r'post|article|entry')))
            post_links = self._extract_blog_post_links(soup, url)

            return article_elements >= 3 or len(post_links) >= 3

        return False

    def _extract_blog_post_links(self, soup, base_url: str) -> list:
        """Extract links to blog posts from an index page"""
        post_links = []
        seen_urls = set()

        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)

            # Skip if already processed or external link
            if full_url in seen_urls or not full_url.startswith(base_url):
                continue

            # Check if URL matches blog post patterns
            parsed_url = urlparse(full_url)
            path = parsed_url.path

            is_blog_post = any(re.search(pattern, path) for pattern in self.blog_post_patterns)

            # Also check if link is inside a post title element
            in_title_element = link.parent and link.parent.name in ['h1', 'h2', 'h3']

            if is_blog_post or in_title_element:
                post_links.append(full_url)
                seen_urls.add(full_url)

        return post_links[:self.max_blog_posts]  # Limit number of posts

    async def _process_blog_index(self, session, soup, base_url: str) -> list:
        """Process a blog index page by extracting and fetching individual posts"""
        post_links = self._extract_blog_post_links(soup, base_url)

        if not post_links:
            logging.warning(f"No blog post links found on {base_url}")
            # Process the index page itself as fallback
            result = await self._fetch_url_content(session, base_url, soup=soup)
            return [result] if result else []

        logging.info(f"Found {len(post_links)} blog posts on {base_url}")

        # Fetch each blog post
        tasks = []
        for post_url in post_links:
            tasks.append(self._fetch_url_content(session, post_url))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Failed to fetch blog post {post_links[i]}: {result}")
            elif result:
                valid_results.append(result)

        return valid_results

    async def _fetch_url_content(self, session, url: str, soup=None) -> dict:
        """Fetch and process content from a single URL"""
        try:
            if soup is None:
                async with session.get(url, timeout=30) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

            # Extract main content with improved extraction
            content = self._extract_main_content(soup)
            title = soup.find('title').text if soup.find('title') else url

            # Check if content is new (compare with stored hash)
            content_hash = hash(content)
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

        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            raise

    def _extract_main_content(self, soup) -> str:
        """Extract main content from HTML with improved extraction"""
        # Remove script, style, and other non-content elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Try to find main content area with expanded selectors
        content_selectors = [
            'main', 'article',
            'div.content', 'div.post-content', 'div.entry-content',
            'div.article-content', 'div.blog-post', 'div.post',
            '.markdown-body',  # Common for GitHub Pages blogs
            '.post-body', '.post-content', '.article-body',
            '#content', '#main-content', '#post-content'
        ]

        for selector in content_selectors:
            try:
                main_content = soup.select_one(selector)
                if main_content and len(main_content.get_text(strip=True)) > 200:
                    return main_content.get_text(strip=True, separator=' ')
            except:
                continue

        # If no main content found with selectors, try to find the largest text block
        paragraphs = soup.find_all('p')
        if paragraphs:
            # Get the text from all paragraphs
            paragraph_text = ' '.join([p.get_text(strip=True) for p in paragraphs])
            if len(paragraph_text) > 200:  # Minimum content length
                return paragraph_text

        # Last resort: get all text from body
        body = soup.find('body')
        if body:
            return body.get_text(strip=True, separator=' ')

        # Final fallback
        return soup.get_text(strip=True, separator=' ')
