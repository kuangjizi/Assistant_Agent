# src/services/web_scraper.py
import aiohttp
import asyncio
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Set
import hashlib
from datetime import datetime
import re
import feedparser
from readability import Document as ReadabilityDocument

class WebScraper:
    def __init__(self, config: dict):
        """
        Initialize web scraper with configuration

        Args:
            config: Configuration dictionary with scraping settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Scraping configuration
        self.user_agent = self.config.get('user_agent', 'AI-Assistant-Agent/1.0')
        self.request_delay = self.config.get('request_delay', 1.0)
        self.timeout = self.config.get('timeout', 30)
        self.max_retries = self.config.get('max_retries', 3)
        self.max_content_length = self.config.get('max_content_length', 1024 * 1024)  # 1MB

        # Headers for requests
        self.headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Content type patterns to accept
        self.accepted_content_types = {
            'text/html',
            'text/plain',
            'application/xhtml+xml',
            'application/xml',
            'application/rss+xml',
            'application/atom+xml'
        }

        # Patterns for content extraction
        self.content_selectors = [
            'article',
            'main',
            '.content',
            '.post-content',
            '.entry-content',
            '.article-content',
            '#content',
            '.main-content'
        ]

        # Elements to remove
        self.elements_to_remove = [
            'script', 'style', 'nav', 'header', 'footer', 'aside',
            '.advertisement', '.ads', '.sidebar', '.menu', '.navigation',
            '.social-share', '.comments', '.related-posts'
        ]

    async def scrape_url(self, url: str, session: aiohttp.ClientSession = None) -> Dict:
        """
        Scrape content from a single URL

        Args:
            url: URL to scrape
            session: Optional aiohttp session to reuse

        Returns:
            Dictionary with scraped content and metadata
        """
        should_close_session = False

        if session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
            should_close_session = True

        try:
            result = await self._scrape_with_retries(url, session)
            return result

        except Exception as e:
            self.logger.error(f"Failed to scrape {url}: {e}")
            return {
                'url': url,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            if should_close_session:
                await session.close()

    async def scrape_multiple_urls(self, urls: List[str],
                                 max_concurrent: int = 5) -> List[Dict]:
        """
        Scrape multiple URLs concurrently

        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum number of concurrent requests

        Returns:
            List of scraping results
        """
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit=max_concurrent)

        async with aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout,
            connector=connector
        ) as session:

            semaphore = asyncio.Semaphore(max_concurrent)

            async def scrape_with_semaphore(url):
                async with semaphore:
                    await asyncio.sleep(self.request_delay)  # Rate limiting
                    return await self.scrape_url(url, session)

            tasks = [scrape_with_semaphore(url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions in results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        'url': urls[i],
                        'success': False,
                        'error': str(result),
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    processed_results.append(result)

            return processed_results

    async def _scrape_with_retries(self, url: str,
                                  session: aiohttp.ClientSession) -> Dict:
        """
        Scrape URL with retry logic

        Args:
            url: URL to scrape
            session: aiohttp session

        Returns:
            Scraping result dictionary
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

                async with session.get(url) as response:
                    # Check content type
                    content_type = response.headers.get('content-type', '').lower()
                    if not any(ct in content_type for ct in self.accepted_content_types):
                        return {
                            'url': url,
                            'success': False,
                            'error': f'Unsupported content type: {content_type}',
                            'timestamp': datetime.now().isoformat()
                        }

                    # Check content length
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > self.max_content_length:
                        return {
                            'url': url,
                            'success': False,
                            'error': f'Content too large: {content_length} bytes',
                            'timestamp': datetime.now().isoformat()
                        }

                    # Read content
                    content = await response.text()

                    # Process content based on type
                    if 'xml' in content_type or 'rss' in content_type or 'atom' in content_type:
                        return await self._process_feed_content(url, content, response)
                    else:
                        return await self._process_html_content(url, content, response)

            except asyncio.TimeoutError:
                last_exception = f"Timeout after {self.timeout} seconds"
                self.logger.warning(f"Timeout scraping {url}, attempt {attempt + 1}")

            except aiohttp.ClientError as e:
                last_exception = f"Client error: {e}"
                self.logger.warning(f"Client error scraping {url}, attempt {attempt + 1}: {e}")

            except Exception as e:
                last_exception = f"Unexpected error: {e}"
                self.logger.warning(f"Unexpected error scraping {url}, attempt {attempt + 1}: {e}")

        # All retries failed
        return {
            'url': url,
            'success': False,
            'error': f'Failed after {self.max_retries} attempts: {last_exception}',
            'timestamp': datetime.now().isoformat()
        }

    async def _process_html_content(self, url: str, content: str,
                                  response: aiohttp.ClientResponse) -> Dict:
        """
        Process HTML content and extract meaningful text

        Args:
            url: Source URL
            content: HTML content
            response: HTTP response object

        Returns:
            Processed content dictionary
        """
        try:
            soup = BeautifulSoup(content, 'html.parser')

            # Extract basic metadata
            title = self._extract_title(soup)
            description = self._extract_description(soup)

            # Try to extract main content using readability
            main_content = self._extract_main_content_readability(content)

            # Fallback to manual extraction
            if not main_content or len(main_content.strip()) < 100:
                main_content = self._extract_main_content_manual(soup)

            # Clean and process text
            clean_content = self._clean_text(main_content)

            # Generate content hash for deduplication
            content_hash = hashlib.md5(clean_content.encode()).hexdigest()

            # Extract additional metadata
            metadata = self._extract_metadata(soup, url)

            return {
                'url': url,
                'success': True,
                'title': title,
                'description': description,
                'content': clean_content,
                'content_hash': content_hash,
                'word_count': len(clean_content.split()),
                'metadata': metadata,
                'timestamp': datetime.now().isoformat(),
                'status_code': response.status,
                'headers': dict(response.headers)
            }

        except Exception as e:
            self.logger.error(f"Error processing HTML content from {url}: {e}")
            return {
                'url': url,
                'success': False,
                'error': f'Content processing error: {e}',
                'timestamp': datetime.now().isoformat()
            }

    async def _process_feed_content(self, url: str, content: str,
                                  response: aiohttp.ClientResponse) -> Dict:
        """
        Process RSS/Atom feed content

        Args:
            url: Source URL
            content: Feed content
            response: HTTP response object

        Returns:
            Processed feed dictionary
        """
        try:
            feed = feedparser.parse(content)

            if feed.bozo:
                self.logger.warning(f"Feed parsing issues for {url}: {feed.bozo_exception}")

            # Extract feed metadata
            feed_title = feed.feed.get('title', 'Unknown Feed')
            feed_description = feed.feed.get('description', '')

            # Process entries
            entries = []
            combined_content = []

            for entry in feed.entries[:10]:  # Limit to recent 10 entries
                entry_data = {
                    'title': entry.get('title', 'No Title'),
                    'link': entry.get('link', ''),
                    'description': entry.get('description', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', '')
                }
                entries.append(entry_data)

                # Combine content for full-text search
                entry_text = f"{entry_data['title']}\n{entry_data['description']}\n{entry_data['summary']}"
                combined_content.append(self._clean_text(entry_text))

            full_content = '\n\n'.join(combined_content)
            content_hash = hashlib.md5(full_content.encode()).hexdigest()

            return {
                'url': url,
                'success': True,
                'title': feed_title,
                'description': feed_description,
                'content': full_content,
                'content_hash': content_hash,
                'word_count': len(full_content.split()),
                'feed_entries': entries,
                'metadata': {
                    'type': 'feed',
                    'entry_count': len(entries),
                    'feed_updated': feed.feed.get('updated', '')
                },
                'timestamp': datetime.now().isoformat(),
                'status_code': response.status
            }

        except Exception as e:
            self.logger.error(f"Error processing feed content from {url}: {e}")
            return {
                'url': url,
                'success': False,
                'error': f'Feed processing error: {e}',
                'timestamp': datetime.now().isoformat()
            }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        # Try multiple title sources
        title_sources = [
            soup.find('title'),
            soup.find('h1'),
            soup.find('meta', property='og:title'),
            soup.find('meta', name='twitter:title')
        ]

        for source in title_sources:
            if source:
                if source.name == 'meta':
                    title = source.get('content', '').strip()
                else:
                    title = source.get_text().strip()

                if title:
                    return title[:200]  # Limit title length

        return 'No Title'

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract page description"""
        # Try multiple description sources
        desc_sources = [
            soup.find('meta', name='description'),
            soup.find('meta', property='og:description'),
            soup.find('meta', name='twitter:description')
        ]

        for source in desc_sources:
            if source:
                desc = source.get('content', '').strip()
                if desc:
                    return desc[:500]  # Limit description length

        return ''

    def _extract_main_content_readability(self, html_content: str) -> str:
        """Extract main content using readability algorithm"""
        try:
            doc = ReadabilityDocument(html_content)
            content = doc.summary()

            # Parse the extracted content and get text
            soup = BeautifulSoup(content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)

        except Exception as e:
            self.logger.debug(f"Readability extraction failed: {e}")
            return ''

    def _extract_main_content_manual(self, soup: BeautifulSoup) -> str:
        """Manually extract main content using CSS selectors"""
        # Remove unwanted elements
        for selector in self.elements_to_remove:
            for element in soup.select(selector):
                element.decompose()

        # Try to find main content area
        for selector in self.content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                text = content_element.get_text(separator=' ', strip=True)
                if len(text) > 100:  # Minimum content length
                    return text

        # Fallback to body content
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)

        # Last resort - all text
        return soup.get_text(separator=' ', strip=True)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ''

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', ' ', text)

        # Remove extra spaces again
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract additional metadata from the page"""
        metadata = {
            'domain': urlparse(url).netloc,
            'path': urlparse(url).path,
        }

        # Extract author
        author_selectors = [
            'meta[name="author"]',
            'meta[property="article:author"]',
            '.author',
            '.byline'
        ]

        for selector in author_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    author = element.get('content', '').strip()
                else:
                    author = element.get_text().strip()

                if author:
                    metadata['author'] = author
                    break

        # Extract publication date
        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="date"]',
            'time[datetime]',
            '.date',
            '.published'
        ]

        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == 'meta':
                    date = element.get('content', '').strip()
                elif element.name == 'time':
                    date = element.get('datetime', '').strip()
                else:
                    date = element.get_text().strip()

                if date:
                    metadata['published_date'] = date
                    break

        # Extract keywords/tags
        keywords_element = soup.find('meta', name='keywords')
        if keywords_element:
            keywords = keywords_element.get('content', '').strip()
            if keywords:
                metadata['keywords'] = [k.strip() for k in keywords.split(',')]

        return metadata

    def get_robots_txt(self, domain: str) -> Optional[str]:
        """
        Fetch and return robots.txt content for a domain

        Args:
            domain: Domain to check robots.txt for

        Returns:
            robots.txt content or None if not accessible
        """
        robots_url = f"https://{domain}/robots.txt"

        try:
            import requests
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            self.logger.debug(f"Could not fetch robots.txt for {domain}: {e}")

        return None

    def is_url_allowed(self, url: str, user_agent: str = '*') -> bool:
        """
        Check if URL is allowed according to robots.txt

        Args:
            url: URL to check
            user_agent: User agent to check rules for

        Returns:
            True if URL is allowed, False otherwise
        """
        try:
            from urllib.robotparser import RobotFileParser

            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()

            return rp.can_fetch(user_agent, url)

        except Exception as e:
            self.logger.debug(f"Could not check robots.txt for {url}: {e}")
            return True  # Default to allowing if we can't check
