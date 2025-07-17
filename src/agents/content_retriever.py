# src/agents/content_retriever.py
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from datetime import datetime, timedelta
import logging

class ContentRetriever:
    def __init__(self, vector_store, db_manager):
        self.vector_store = vector_store
        self.db_manager = db_manager
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')

    async def retrieve_content(self, urls: list) -> list:
        """Retrieve content from multiple URLs concurrently"""
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                tasks.append(self._fetch_url_content(session, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_content = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Failed to fetch {urls[i]}: {result}")
            else:
                valid_content.append(result)

        return valid_content

    async def _fetch_url_content(self, session, url: str) -> dict:
        """Fetch and process content from a single URL"""
        try:
            async with session.get(url, timeout=30) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Extract main content (customize based on common patterns)
                content = self._extract_main_content(soup)
                title = soup.find('title').text if soup.find('title') else url

                # Check if content is new (compare with stored hash)
                content_hash = hash(content)
                if self.db_manager.is_content_new(url, content_hash):
                    # Split and store in vector database
                    chunks = self.text_splitter.split_text(content)

                    # Store in vector database
                    self.vector_store.add_texts(
                        texts=chunks,
                        metadatas=[{
                            'url': url,
                            'title': title,
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
        """Extract main content from HTML"""
        # Remove script, style, and other non-content elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Try to find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')

        if main_content:
            return main_content.get_text(strip=True, separator=' ')
        else:
            return soup.get_text(strip=True, separator=' ')
